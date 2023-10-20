import json
from graphviz import Digraph

# Load your JSON data
with open('gameTrace.json') as f:
    data = json.load(f)

def add_edges(graph, data, parent=None, depth=0):
    node_label = f'{data["type"]}\nDepth: {data["depth"]}' if 'type' in data else f'Score: {data["score"]}\nMove: {data["move"]}'
    node_name = f'{node_label}_{depth}'
    graph.node(node_name, label=node_label)
    if parent:
        graph.edge(parent, node_name)
    if 'children' in data:
        for child in data['children']:
            add_edges(graph, child, node_name, depth+1)

# Create a directed graph
dot = Digraph(comment='The Tree')

# Call the function to add edges
add_edges(dot, data)

# Render the graph to a file (creates 'tree.gv' and 'tree.gv.pdf')
dot.render('tree', view=True)