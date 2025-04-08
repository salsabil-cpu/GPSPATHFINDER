import networkx as nx
from utils.geo_utils import calculate_distance

def optimize_route(start_point, waypoints):
    """
    Optimize the route from a starting point through all waypoints
    using the Traveling Salesman Problem (TSP) solver in NetworkX.
    
    Args:
        start_point (dict): Dictionary with 'name', 'lat', 'lng'
        waypoints (list): List of dictionaries, each with 'name', 'lat', 'lng'
    
    Returns:
        list: Ordered list of points for the optimized route
    """
    if not waypoints:
        return [start_point]
    
    # Create a complete graph
    G = nx.Graph()
    
    # Create a list of all points (start point + waypoints)
    all_points = [start_point] + waypoints
    
    # Add nodes to the graph
    for i, point in enumerate(all_points):
        G.add_node(i, point=point)
    
    # Add edges with distances as weights
    for i in range(len(all_points)):
        for j in range(i + 1, len(all_points)):
            point_i = (all_points[i]['lat'], all_points[i]['lng'])
            point_j = (all_points[j]['lat'], all_points[j]['lng'])
            distance = calculate_distance(point_i, point_j)
            G.add_edge(i, j, weight=distance)
    
    # Find the approximate solution to the TSP
    # We need to ensure the start point (index 0) is the first node in the path
    # Since newer versions of NetworkX don't support 'source' parameter, we will handle this differently
    tsp_path = nx.approximation.traveling_salesman_problem(G, cycle=False)
    
    # If the first element is not 0 (our start point), we need to reorder the path
    if tsp_path[0] != 0:
        # Find the position of 0 in the path
        start_pos = tsp_path.index(0)
        # Reorder the path to start from position 0
        tsp_path = tsp_path[start_pos:] + tsp_path[:start_pos]
    
    # Convert node indices back to waypoints
    optimized_route = [all_points[i] for i in tsp_path]
    
    return optimized_route
