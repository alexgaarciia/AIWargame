import json
from graphviz import Digraph

# Load your JSON data
with open('gameTrace_defender_AI.json') as f:
    data = json.load(f)

def add_edges(graph, data, parent=None, depth=0, index=0):
    node_id = f'{parent}-{index}' if parent else '0'
    if 'children' in data:
        # For inner nodes
        node_label = f'{data["type"]}\nDepth: {data["depth"]}'
    else:
        # For leaf nodes
        node_label = f'Score: {data["score"]}\nMove: {data["move"]}'
    
    graph.node(node_id, label=node_label)
    if parent:
        graph.edge(parent, node_id)
    
    if 'children' in data:
        for i, child in enumerate(data['children']):
            add_edges(graph, child, node_id, depth+1, i)

# Create a directed graph
dot = Digraph(comment='The Defender Tree', format='pdf', engine='dot', graph_attr={'rankdir':'LR'})

# Call the function to add edges
add_edges(dot, data)

# Render the graph to a file (creates 'tree.gv' and 'tree.gv.pdf')
dot.render(view=True)
