import json
from graphviz import Digraph

# Load your JSON data
with open('gameTrace.json') as f:
    data = json.load(f)

def add_edges(graph, data, parent=None):
    for key, value in data.items():
        if isinstance(value, dict):
            graph.node(key)
            if parent:
                graph.edge(parent, key)
            add_edges(graph, value, key)
        else:
            graph.node(f'{key}_{value}')
            graph.edge(parent, f'{key}_{value}')

# Create a directed graph
dot = Digraph(comment='The Tree')

# Call the function to add edges
add_edges(dot, data)

# Render the graph to a file (creates 'tree.gv' and 'tree.gv.pdf')
dot.render('tree', view=True)