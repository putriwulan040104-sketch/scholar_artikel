from flask import Flask, jsonify
import networkx as nx

app = Flask(__name__)

papers = ["P1", "P2", "P3", "P4", "P5"]

citations = [
    ("P1", "P2"),
    ("P1", "P3"),
    ("P2", "P3"),
    ("P4", "P1"),
    ("P5", "P3")
]

@app.route("/")
def home():
    return "Backend Flask siap 🚀"

@app.route("/citation")
def citation_graph():
    G = nx.DiGraph()

    # tambah node
    for p in papers:
        G.add_node(p)

    # tambah edge
    for c in citations:
        G.add_edge(c[0], c[1])

    nodes = []
    for node in G.nodes():
        nodes.append({
            "id": node,
            "in_degree": G.in_degree(node),
            "out_degree": G.out_degree(node)
        })

    edges = [{"source": s, "target": t} for s, t in G.edges()]

    return jsonify({
        "nodes": nodes,
        "edges": edges
    })

if __name__ == "__main__":
    app.run(debug=True)
