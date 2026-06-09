"""
agents/graph.py — LangGraph Reflexion Loop (State Machine).

Flow:
  START → route_intent →
      "chat" → retrieve_and_draft → END
      "code" → code_exec          → END

The reflexion grading loop is kept commented out for speed but can be
re-enabled when needed.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TypedDict, Annotated, Literal, Any

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage

from backend.config import MAX_RETRIES, TOP_K

logger = logging.getLogger(__name__)

CANNOT_ANSWER = (
    "I don't have enough information in the provided documents to confidently answer this question. "
    "Please ensure the relevant document is indexed, or rephrase your question."
)


# ─── State schema ─────────────────────────────────────────────────────────────

class BrainState(TypedDict):
    question: str
    answer: str
    sources: list[dict]
    grade: str                  # "YES" | "NO" | ""
    grade_reason: str
    retry_count: int
    n_results: int
    final: bool
    intent: str                 # "chat" | "code" | "report"
    generated_code: str         # populated when intent == "code"
    code_result: dict           # execution result dict from python_executor
    code_error: str             # populated when python_executor fails
    report_content: str         # populated when intent == "report"
    report_path: str            # path to saved report
    image_path: str             # path to uploaded image for vision tasks


# ─── Graph builder ────────────────────────────────────────────────────────────

def build_graph(vectorstore, llm):
    """
    Build and compile the LangGraph reflexion state machine.
    Returns a compiled graph you can call with .invoke(initial_state).
    """
    from backend.agents.researcher import ResearcherAgent
    from backend.agents.grader import GraderAgent
    from backend.agents.intent_router import IntentRouter
    from backend.agents.code_generator import CodeGeneratorAgent
    from backend.agents.reporting import ReportingAgent
    from backend.tools.chroma_tool import ChromaTool
    from backend.tools.fs_tool import FSTool

    researcher = ResearcherAgent(vectorstore=vectorstore, llm=llm)
    grader = GraderAgent(llm=llm)
    intent_router = IntentRouter(llm=llm)
    code_generator = CodeGeneratorAgent(vectorstore=vectorstore, llm=llm)
    reporting_agent = ReportingAgent(llm=llm, root_dir=".")
    chroma_tool = ChromaTool()
    fs_tool = FSTool()

    # ── Node: route_intent ─────────────────────────────────────────────────────
    def route_intent(state: BrainState) -> BrainState:
        intent = intent_router.route(state["question"])
        logger.info("Intent routed -> %s", intent)
        return {**state, "intent": intent}

    # ── Conditional edge after route_intent ────────────────────────────────────
    def pick_path(state: BrainState) -> Literal["retrieve_and_draft", "code_exec", "reporting_node", "db_node", "fs_node"]:
        intent = state.get("intent", "chat")
        if intent == "report":
            return "reporting_node"
        if intent == "db":
            return "db_node"
        if intent == "file":
            return "fs_node"
        return "retrieve_and_draft" if intent == "chat" else "code_exec"

    # ── Node: retrieve_and_draft ───────────────────────────────────────────────
    def retrieve_and_draft(state: BrainState) -> BrainState:
        n = state.get("n_results", TOP_K)
        result = researcher.run(state["question"], n_results=n)
        return {
            **state,
            "answer":       result["answer"],
            "sources":      result["sources"],
            "grade":        "YES",
            "grade_reason": "Bypassed for speed.",
        }

    # ── Node: code_exec ────────────────────────────────────────────────────────
    def code_exec(state: BrainState) -> BrainState:
        """Generate Python code from the question, execute it in Docker sandbox."""
        question = state["question"]
        retry_count = state.get("retry_count", 0)

        try:
            gen_result = code_generator.generate(question)
        except Exception as e:
            logger.error("Single-pass code generation failed: %s", e)
            return {**state, "answer": f"⚠️ Math engine error: {e}", "grade": "YES"}

        code = gen_result["code"]
        explanation = gen_result["explanation"]
        data_context = gen_result["data_context"]


        # If LLM identified missing data, return immediately
        if "Required numeric data not found" in code:
            return {
                **state,
                "generated_code": code.strip(),
                "answer": "Required numeric data not found.",
                "sources": data_context,
                "final": True,
                "grade": "YES"
            }

        logger.info("code_exec: generated code (%d lines)", len(code.splitlines()))


        # Step 2: Execute natively
        import io
        import sys
        import traceback
        
        old_stdout = sys.stdout
        sys.stdout = redirected_stdout = io.StringIO()
        success = False
        try:
            exec(code, {})
            success = True
            stderr = ""
        except Exception as exc:
            stderr = traceback.format_exc()
        finally:
            sys.stdout = old_stdout

        exec_result = {
            "stdout": redirected_stdout.getvalue(),
            "stderr": stderr,
            "success": success,
            "timed_out": False,
        }


        # Step 3: Format the answer
        is_instruction_violation = "LLM violation" in exec_result.get("stdout", "")
        
        if exec_result["success"] and exec_result["stdout"] and not is_instruction_violation:
            answer = (
                f"**🐍 Python Result**\n\n"
                f"_{explanation}_\n\n"
                f"```\n{exec_result['stdout']}\n```"
            )
        else:
            stderr = exec_result.get("stderr", "")
            if "Docker is not running" in stderr:
                answer = "🐳 **Docker is not running.** " + researcher.run(state["question"]).get("answer", CANNOT_ANSWER)
            else:
                answer = f"⚠️ Calculation failed: {exec_result.get('stdout') or stderr}"

        return {
            **state,
            "answer":         answer,
            "sources":        data_context,
            "generated_code": code,
            "code_result":    exec_result,
            "grade":          "YES",
        }



    # ── Node: reporting_node ──────────────────────────────────────────────────
    def reporting_node(state: BrainState) -> BrainState:
        """Crawl workspace and generate report."""
        result = reporting_agent.run(state["question"])
        content = result["report_content"]
        
        # Save to file
        report_filename = "Workspace_Report.md"
        # Check if user specified a name in the question
        import re
        match = re.search(r"report called ['\"](.+?\.md)['\"]", state["question"])
        if match:
            report_filename = match.group(1)
        
        try:
            with open(report_filename, "w", encoding="utf-8") as f:
                f.write(content)
            report_path = str(Path(report_filename).resolve())
        except Exception as e:
            logger.error("Failed to save report: %s", e)
            report_path = f"Error saving: {e}"

        answer = (
            f"✅ **Report Generated**\n\n"
            f"The workspace report has been saved to: `{report_filename}`\n\n"
            f"---\n\n"
            f"{content[:1000]}..." if len(content) > 1000 else content
        )

        return {
            **state,
            "answer": answer,
            "report_content": content,
            "report_path": report_path,
            "grade": "YES",
        }

    # ── Node: db_node ─────────────────────────────────────────────────────────
    def db_node(state: BrainState) -> BrainState:
        """Inspect ChromaDB via ChromaTool."""
        q = state["question"].lower()
        if "inspect" in q or "chunk" in q:
            # Simple heuristic to find source name
            words = q.split()
            source = words[-1]
            answer = chroma_tool.run("inspect", source=source)
        else:
            answer = chroma_tool.run("list")
        
        return {**state, "answer": answer, "grade": "YES"}

    # ── Node: fs_node ─────────────────────────────────────────────────────────
    def fs_node(state: BrainState) -> BrainState:
        """Interact with file system via FSTool."""
        q = state["question"].lower()
        if "read" in q:
            # Simple extraction of filename
            words = q.split()
            filename = words[-1] # naive
            result = fs_tool.read_file(filename)
        else:
            result = fs_tool.list_files()
            
        return {**state, "answer": result, "grade": "YES"}


    # ── Node: grade_answer ────────────────────────────────────────────────────
    def grade_answer(state: BrainState) -> BrainState:
        verdict = grader.grade(
            question=state["question"],
            answer=state["answer"],
            sources=state["sources"],
        )
        return {
            **state,
            "grade":        verdict.get("grade", "YES"),
            "grade_reason": verdict.get("reason", ""),
        }

    # ── Node: handle_no ───────────────────────────────────────────────────────
    def handle_no(state: BrainState) -> BrainState:
        retry = state.get("retry_count", 0) + 1
        new_n = state.get("n_results", TOP_K) + 3

        logger.info(
            "Grade: NO (retry %d/%d). Reason: %s. Expanding to n=%d.",
            retry, MAX_RETRIES, state.get("grade_reason", ""), new_n,
        )

        if retry >= MAX_RETRIES:
            logger.info("Max retries reached — returning CANNOT_ANSWER.")
            return {
                **state,
                "answer":      CANNOT_ANSWER,
                "grade":       "YES",
                "retry_count": retry,
                "n_results":   new_n,
                "final":       True,
            }

        return {**state, "retry_count": retry, "n_results": new_n}

    def route_after_grade(state: BrainState) -> Literal["handle_no", "__end__"]:
        if state.get("grade", "YES") == "YES":
            return "__end__"
        return "handle_no"

    def route_after_handle_no(state: BrainState) -> Literal["retrieve_and_draft", "__end__"]:
        if state.get("final", False):
            return "__end__"
        return "retrieve_and_draft"

    # ── Wire graph ────────────────────────────────────────────────────────────
    g = StateGraph(BrainState)
    g.add_node("route_intent",       route_intent)
    g.add_node("retrieve_and_draft", retrieve_and_draft)
    g.add_node("code_exec",          code_exec)
    g.add_node("reporting_node",     reporting_node)
    g.add_node("db_node",            db_node)
    g.add_node("fs_node",            fs_node)
    g.add_node("grade_answer",       grade_answer)
    g.add_node("handle_no",          handle_no)

    g.add_edge(START, "route_intent")
    g.add_conditional_edges("route_intent", pick_path)
    g.add_edge("retrieve_and_draft", END)
    g.add_edge("reporting_node", END)
    g.add_edge("db_node", END)
    g.add_edge("fs_node", END)
    g.add_edge("code_exec", END)
    # Grading loop (disabled for speed — re-enable by swapping the next 4 lines):
    # g.add_edge("retrieve_and_draft", "grade_answer")
    # g.add_conditional_edges("grade_answer", route_after_grade)
    # g.add_conditional_edges("handle_no", route_after_handle_no)

    memory = MemorySaver()
    return g.compile(checkpointer=memory)


# ─── Convenience wrapper ──────────────────────────────────────────────────────

class BrainGraph:
    """Stateless wrapper around the compiled LangGraph."""

    def __init__(self, vectorstore, llm):
        self._graph = build_graph(vectorstore=vectorstore, llm=llm)

    def stream_ask(self, question: str, thread_id: str = "default_thread", image_path: str | None = None, intent: str | None = None):
        """
        Yields (node_name, state) events from the graph stream.
        """
        initial: BrainState = {
            "question":      question,
            "answer":        "",
            "sources":       [],
            "grade":         "",
            "grade_reason":  "",
            "retry_count":   0,
            "n_results":     TOP_K,
            "final":         False,
            "intent":        intent or "chat",
            "generated_code": "",
            "code_result":   {},
            "code_error":    "",
            "image_path":    image_path or "",
        }

        config = {"configurable": {"thread_id": thread_id}}
        try:
            for event in self._graph.stream(initial, config=config):
                for node_name, state in event.items():
                    yield node_name, state
        except Exception as exc:
            logger.error("BrainGraph stream error: %s", exc)
            yield "error", {"answer": f"An error occurred: {exc}", "sources": [], "grade": "YES"}

    def ask(self, question: str, thread_id: str = "default_thread", image_path: str | None = None, intent: str | None = None) -> dict[str, Any]:
        """
        Run the full loop and return:
          { "answer": str, "sources": [...], "retries": int, "grounded": bool,
            "intent": str, "generated_code": str, "code_result": dict }
        """
        initial: BrainState = {
            "question":      question,
            "answer":        "",
            "sources":       [],
            "grade":         "",
            "grade_reason":  "",
            "retry_count":   0,
            "n_results":     TOP_K,
            "final":         False,
            "intent":        intent or "chat",
            "generated_code": "",
            "code_result":   {},
            "code_error":    "",
            "image_path":    image_path or "",
        }

        try:
            config = {"configurable": {"thread_id": thread_id}}
            final_state = self._graph.invoke(initial, config=config)
        except Exception as exc:
            logger.error("BrainGraph error: %s", exc)
            return {
                "answer":         f"An error occurred during reasoning: {exc}",
                "sources":        [],
                "retries":        0,
                "grounded":       False,
                "intent":         "chat",
                "generated_code": "",
                "code_result":    {},
            }

        return {
            "answer":         final_state["answer"],
            "sources":        final_state["sources"],
            "retries":        final_state.get("retry_count", 0),
            "grounded":       final_state.get("grade", "YES") == "YES",
            "intent":         final_state.get("intent", "chat"),
            "generated_code": final_state.get("generated_code", ""),
            "code_result":    final_state.get("code_result", {}),
            "report_path":    final_state.get("report_path", ""),
        }
