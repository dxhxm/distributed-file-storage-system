# In-memory node storage

nodes_status = {
    "nodeA": "ALIVE",
    "nodeB": "ALIVE",
    "nodeC": "ALIVE"
}


def get_all_nodes():
    return nodes_status


def update_node_status(node_name, status):
    if node_name in nodes_status:
        nodes_status[node_name] = status
        return True
    return False