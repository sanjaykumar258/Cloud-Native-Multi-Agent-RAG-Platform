"""
brain/knowledge_graph.py — NetworkX Graph Manager.

Maintains a graph of extracted entities. Persists to disk via pickle for
simplicity. Can render to PyVis HTML.
"""

import os
import pickle
import logging
from pathlib import Path
from typing import Any

import networkx as nx

logger = logging.getLogger(__name__)

GRAPH_FILE_PATH = Path("./db/graph/knowledge_graph.pkl")


class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self._load()

    def _load(self):
        if GRAPH_FILE_PATH.exists():
            try:
                with open(GRAPH_FILE_PATH, "rb") as f:
                    self.graph = pickle.load(f)
                logger.debug("Loaded Knowledge Graph with %d nodes and %d edges.", 
                            self.graph.number_of_nodes(), self.graph.number_of_edges())
            except Exception as e:
                logger.error("Failed to load Knowledge Graph: %s", e)
        else:
            logger.debug("Initialized empty Knowledge Graph.")

    def save(self):
        try:
            GRAPH_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(GRAPH_FILE_PATH, "wb") as f:
                pickle.dump(self.graph, f)
            logger.debug("Saved Knowledge Graph.")
        except Exception as e:
            logger.error("Failed to save Knowledge Graph: %s", e)

    def add_entities_and_relations(self, source_name: str, extraction_data: dict[str, Any]):
        """Integrate extracted entities and relations for a given source doc."""
        # Always add the Document itself as a node
        doc_node = f"Doc: {source_name}"
        self.graph.add_node(doc_node, type="Document", label=source_name, title=f"Source File: {source_name}", color="#6366f1", size=25)

        entities = extraction_data.get("entities", [])
        for ent in entities:
            name = ent.get("name")
            typ = ent.get("type", "Concept")
            if not name:
                continue
            
            # Use upper type bounds to keep it clean
            n_id = name.strip()
            self.graph.add_node(n_id, type=typ, label=n_id, title=f"{typ}: {n_id}", color="#10b981", size=15)
            # Connect entity to document
            self.graph.add_edge(n_id, doc_node, label="MENTIONED_IN", color="#94a3b8")

        relations = extraction_data.get("relations", [])
        for rel in relations:
            src = rel.get("from")
            dst = rel.get("to")
            lbl = rel.get("label", "RELATES_TO")
            if src and dst:
                src_id = src.strip()
                dst_id = dst.strip()
                # Ensure nodes exist
                if not self.graph.has_node(src_id):
                    self.graph.add_node(src_id, type="Concept", label=src_id, color="#10b981", size=15)
                if not self.graph.has_node(dst_id):
                    self.graph.add_node(dst_id, type="Concept", label=dst_id, color="#10b981", size=15)
                self.graph.add_edge(src_id, dst_id, label=lbl, color="#64748b")
        
        self.save()

    def clear(self):
        self.graph.clear()
        self.save()

    def to_pyvis_html(self) -> str:
        """Returns HTML string containing the interactive graph."""
        if self.graph.number_of_nodes() == 0:
            return "<div style='color: white; padding: 2rem; text-align: center;'>Graph is empty. Index documents to populate.</div>"

        try:
            from pyvis.network import Network
            # PyVis configuration
            net = Network(height="600px", width="100%", bgcolor="transparent", font_color="#e2e8f0")
            
            # Physics options for a clean look
            net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=150)
            
            # Create a subgraph if it's too large to keep browser responsive.
            # Max 300 nodes for visualization
            if self.graph.number_of_nodes() > 300:
                # Keep highest degree nodes
                degrees = dict(self.graph.degree())
                top_nodes = sorted(degrees, key=degrees.get, reverse=True)[:300]
                display_graph = self.graph.subgraph(top_nodes)
            else:
                display_graph = self.graph
                
            net.from_nx(display_graph)
            
            # Generate HTML string directly
            return net.generate_html()
        except Exception as e:
            logger.error("Failed to generate PyVis HTML: %s", e)
            return f"<div style='color: red;'>Visualization error: {e}</div>"
