"""
agents/code_generator.py — LLM → Python code translator.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a precision math engine. Your ONLY job is to extract LITERAL numbers from the provided DATA and print the calculation.

RULES:
1. OUTPUT ONLY CODE inside triple backticks: ```python ... ```
2. NO explanations. NO prose.
3. USE EXACT VALUES from the DATA. Never guess or make up numbers.
4. COLUMN MATCHING (CRITICAL):
   - When the DATA contains a table, CAREFULLY read ALL column headers.
   - Match the QUESTION to the CORRECT column. For example:
     * "total sales" → use the "Total" column, NOT individual product columns
     * "Product A sales" → use only the "Product A" column
     * "all employees" → include ALL rows, not just some
   - If a "Total" or "Sum" column already exists, USE IT directly instead of re-summing sub-columns.
5. STRICT FILTERING: If the QUESTION asks for a specific category, date, or instance (e.g., "February only"), EXCLUDE data from other categories/dates.
6. Define each number as a variable first (e.g., amount_1 = 20000), then print the final math expression.
7. If the DATA is clearly missing numbers for the QUESTION, output exactly: print("Required numeric data not found")

EXAMPLES:
- Data has columns: Month | Product A | Product B | Total
  User asks "total sales for Q1":
```python
jan_total = 270
feb_total = 270
mar_total = 330
print(jan_total + feb_total + mar_total)
```
- User asks for "Product A sales in February":
```python
feb_product_a = 140
print(feb_product_a)
```
- User asks for "average score of all employees" and Data has: Alice=88, Bob=82, Charlie=91:
```python
alice = 88
bob = 82
charlie = 91
print((alice + bob + charlie) / 3)
```
"""

class CodeGeneratorAgent:
    def __init__(self, vectorstore, llm, top_k: int = 10):
        self.vs = vectorstore
        self.llm = llm
        self.top_k = top_k

    def generate(
        self, 
        question: str, 
        previous_code: str | None = None, 
        error_message: str | None = None
    ) -> dict[str, Any]:
        """Retrieve relevant chunks and generate Python code."""
        results = self.vs.query(question, n_results=self.top_k) or []
        data_context = [
            {"text": r.get("text", ""), "metadata": r.get("metadata", {})}
            for r in results
        ]

        if not data_context:
            return {"code": 'print("No data")', "explanation": "No data", "data_context": []}

        # For Ollama (local), use larger snippets to ensure the model sees the numbers
        from backend.llm_provider import get_active_provider
        is_local = get_active_provider() == "ollama"
        limit = 2000 if is_local else 4000
        max_sections = 10
        
        doc_sections = []
        for i, chunk in enumerate(data_context[:max_sections], 1):
            src = chunk["metadata"].get("source", "?")
            text = chunk["text"][:limit] 
            doc_sections.append(f"Source: {src}\n{text}")

        full_data_view = "\n\n".join(doc_sections)

        user_prompt = (
            f"DATA:\n{full_data_view}\n\n"
            f"QUESTION: {question}\n\n"
            f"TASK: Write a Python script to answer the QUESTION using ONLY the literal values found in the DATA.\n"
            f"CRITICAL: If the DATA contains a table, read ALL column headers carefully. "
            f"Match the question to the CORRECT column (e.g., if asking for 'total sales', use the 'Total' column, NOT individual product columns). "
            f"If a pre-computed Total/Sum column exists, use those values directly.\n"
            f"IMPORTANT: Respect all constraints in the QUESTION (e.g., 'only', 'specific month', 'excluding X'). "
            f"Avoid unnecessary aggregation if the question asks for a single data point."
        )

        if previous_code and error_message:
            user_prompt += f"\n\nFIX THIS FAILED CODE:\n{previous_code}\nERROR: {error_message}"

        response = self.llm.invoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        raw_code = response.content if hasattr(response, "content") else str(response)
        
        # Immediate cleanup
        code = _strip_code_fences(raw_code)
        
        # ─── Hard-Stop Validators for Local Accuracy ─────────────────────────
        # Instead of raising ValueError, we return a clear message so the system remains fast.
        
        if "[" in code or "]" in code:
            return {
                "code": 'print("LLM violation: Forbidden use of brackets []. Define variables like x=100 first.")',
                "explanation": "Calculation error",
                "data_context": data_context
            }
        
        # Automatic print() wrapping and validation
        if "print(" not in code:
            lines = [l for l in code.splitlines() if l.strip()]
            if not lines:
                return {
                    "code": 'print("LLM violation: Generated code is empty. No numbers found.")',
                    "explanation": "Data extraction error",
                    "data_context": data_context
                }
            
            last_line = lines[-1].strip()
            if "=" in last_line:
                target_match = re.search(r"\b([a-zA-Z_]\w*)\s*=", last_line)
                if target_match:
                    target_var = target_match.group(1)
                    code += f"\nprint({target_var})"
                else:
                    code += f"\nprint({last_line.split('=')[0].strip()})"
            else:
                lines[-1] = f"print({last_line})"
                code = "\n".join(lines)

        # Relaxed defined variable check
        print_match = re.search(r"print\((.*?)\)", code)
        if print_match:
            expr = print_match.group(1)
            # Remove string literals to avoid flagging words inside strings as undefined variables
            expr_no_strings = re.sub(r'([\'"]).*?\1', '', expr)
            used_vars = re.findall(r"\b([a-zA-Z_]\w*)\b", expr_no_strings)
            for var in used_vars:
                if var in ["sum", "min", "max", "round", "abs", "math", "float", "int"]: continue
                if not re.search(rf"\b{var}\s*=", code):
                    # We return the defined error message in the code itself
                    error_msg = f"LLM violation: Variable '{var}' not defined."
                    return {
                        "code": f'print("{error_msg}")',
                        "explanation": "Variable error",
                        "data_context": data_context
                    }

        explanation = _extract_explanation(code, question)

        return {
            "code": code,
            "explanation": explanation,
            "data_context": data_context,
        }

def _strip_code_fences(text: str) -> str:
    # Extract ALL code blocks and take the LAST one (usually the refined answer)
    matches = re.findall(r"```(?:python)?\n?(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if matches: 
        return matches[-1].strip()
    
    return _clean_llm_prose(text)

def _clean_llm_prose(text: str) -> str:
    # Aggressively filter out conversational filler while keeping code-like content
    lines = []
    # If the text is very short and contains a calculation, just keep it
    if len(text.splitlines()) < 4 and any(op in text for op in ["*", "/", "+", "-"]):
        return text.strip()

    for line in text.splitlines():
        trimmed = line.strip()
        if not trimmed: continue
        # Valid code lines: contain math, assignments, or common keywords
        if any(c in trimmed for c in ["=", "(", ")", "+", "-", "*", "/"]) or trimmed.startswith("import") or trimmed.startswith("#"):
            lines.append(line)
    
    return "\n".join(lines).strip()

def _extract_explanation(code: str, question: str) -> str:
    for line in code.splitlines():
        if line.strip().startswith("#"): return line.strip().lstrip("# ").strip()
    return f"Result for {question[:40]}"
