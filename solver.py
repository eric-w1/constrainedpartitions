import networkx as nx
import os
import operator
from collections import defaultdict


path_to_inputs = "./all_inputs"
path_to_outputs = "./outputs"

def parse_input(folder_name):
    '''
        Parses an input and returns the corresponding graph and parameters

        Inputs:
            folder_name - a string representing the path to the input folder

        Outputs:
            (graph, num_buses, size_bus, constraints)
            graph - the graph as a NetworkX object
            num_buses - an integer representing the number of buses you can allocate to
            size_buses - an integer representing the number of students that can fit on a bus
            constraints - a list where each element is a list vertices which represents a single rowdy group
    '''
    graph = nx.read_gml(folder_name + "/graph.gml")
    parameters = open(folder_name + "/parameters.txt")
    num_buses = int(parameters.readline())
    size_bus = int(parameters.readline())
    constraints = []

    for line in parameters:
        line = line[1: -2]
        curr_constraint = [num.replace("'", "") for num in line.split(", ")]
        constraints.append(curr_constraint)

    return graph, num_buses, size_bus, constraints

def solve(graph, num_buses, max_size, constraints, name):
    print('>>> Solving %s...' %name)
    G = graph.copy()
    # rowdy_removed = remove_rowdiest(G, constraints, num_buses)


    print('       assigning edge weights')

    rowdiest = get_rowdiest(G, constraints, num_buses) ##tweak stop cond

    for u, v, d in G.edges(data=True):
        d['weight'] = 0

    lowest = 0
    for g in constraints:
        for i in range(len(g)):
            for j in range(i+1, len(g)):
                u, v = g[i], g[j]
                if G.has_edge(u, v):
                    G[u][v]['weight'] -= max(rowdiest.get(u, 0), rowdiest.get(v, 0))
                    lowest = min(lowest, G[u][v]['weight'])
    for u, v, d in G.edges(data=True):
        d['weight'] += (1 - lowest)

    print('       Lowest: %d' %(-lowest))
    print('       adjusting components')


    components = list(nx.connected_components(G))
    if len(components) < num_buses:
        components = [G.subgraph(c) for c in components]
        while len(components) < num_buses: #or all ones
            cuts = []
            for c in components:
                if len(c) < 2:
                    cuts.append((900000, None))
                else:
                    cuts.append((nx.stoer_wagner(c)))

            index_min = min(enumerate(cuts), key=lambda a: a[1][0])[0]
            mincut = cuts[index_min][1]
            components.pop(index_min)
            components.append(G.subgraph(mincut[0]))
            components.append(G.subgraph(mincut[1]))
        components = [set(c.nodes) for c in components]

    if len(components) > num_buses:
        while len(components) > num_buses:
            components.sort(key=len)
            components.append(set.union(components.pop(0), components.pop(0)))
            #doesnt check when adding yet


    assert len(components) == num_buses
    print('       reducing component sizes')


    #check for bus size/complete rowdy and shuffle by most unpopular
    ind = find_over_limit(components)
    biggest = components[ind]
    while(len(biggest) > max_size):
        n = least_popular(biggest, G)
        for i in range(len(components)):
            # mostConnectionsAdded = 0
            if len(components[i]) < max_size:
                components[i].add(n)
                biggest.remove(n)
                #implement checking for best and not complete later
                break
        biggest = components[find_over_limit(components)]


    assert len(components) == num_buses
    for c in components:
        assert len(c) <= max_size
        assert len(c) > 0
    return components

def find_over_limit(components):
    index_max = max(enumerate(components), key=lambda a: len(a[1]))[0]
    return index_max

def least_popular(component, G):
    lst = []
    best = 0
    minDeg = 9999
    for n in component:
        deg = len(list(G.neighbors(n)))
        if deg == 1:
            return n
        if deg < minDeg:
            minDeg = deg
            best = n
    return best

def get_rowdiest(G, constraints, stop_cond):
    d = defaultdict(int)
    for g in constraints:
        for v in g:
            d[v] += 1
    ordered = sorted(d.items(), key=operator.itemgetter(1), reverse=True)

    ret = {}
    for i in range(len(ordered)):
        p = ordered[i]
        if p[1] <= 2 or len(ret) > stop_cond:
            break
        ret[p[0]] = p[1]
    return ret

    # removed = []
    # for p in ordered:
    #     if p[1] <= 2 or len(removed) > stop_cond:
    #         break
    #     removed.append(p[0])
    #     G.remove_node(p[0])
    # return removed

def main():
    '''
        Main method which iterates over all inputs and calls `solve` on each.
        The student should modify `solve` to return their solution and modify
        the portion which writes it to a file to make sure their output is
        formatted correctly.
    '''
    size_categories = ["small", "medium", "large"]
    if not os.path.isdir(path_to_outputs):
        os.mkdir(path_to_outputs)

    for size in size_categories:
        category_path = path_to_inputs + "/" + size
        output_category_path = path_to_outputs + "/" + size
        category_dir = os.fsencode(category_path)

        if not os.path.isdir(output_category_path):
            os.mkdir(output_category_path)

        for input_folder in os.listdir(category_dir):
            input_name = os.fsdecode(input_folder)
            graph, num_buses, size_bus, constraints = parse_input(category_path + "/" + input_name)
            solution = solve(graph, num_buses, size_bus, constraints, size + input_name)
            output_file = open(output_category_path + "/" + input_name + ".out", "w")

            for component in solution:
                output_file.write("%s\n" % list(component))
            output_file.close()
    
    # size = 'small'
    # input_folder = '98'
    # if not os.path.isdir(path_to_outputs):
    #     os.mkdir(path_to_outputs)

    # category_path = path_to_inputs + "/" + size
    # output_category_path = path_to_outputs + "/" + size
    # category_dir = os.fsencode(category_path)

    # if not os.path.isdir(output_category_path):
    #     os.mkdir(output_category_path)

    # input_name = os.fsdecode(input_folder)
    # graph, num_buses, size_bus, constraints = parse_input(category_path + "/" + input_name)
    # solution = solve(graph, num_buses, size_bus, constraints, size + input_name)
    # output_file = open(output_category_path + "/" + input_name + ".out", "w")

    # for component in solution:
    #     output_file.write("%s\n" % list(component))
    # output_file.close()


if __name__ == '__main__':
    main()
