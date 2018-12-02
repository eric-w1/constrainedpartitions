import networkx as nx
import os
import operator
from collections import defaultdict
from multiprocessing import Pool

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

    # print('       assigning edge weights')

    for u, v, d in G.edges(data=True):
        d['weight'] = 0

    lowest = 0
    for g in constraints:
        for i in range(len(g)):
            for j in range(i+1, len(g)):
                u, v = g[i], g[j]
                if G.has_edge(u, v):
                    G[u][v]['weight'] -= 1
                    lowest = min(lowest, G[u][v]['weight'])
    for u, v, d in G.edges(data=True):
        d['weight'] += (1 - lowest)

    # print('       Lowest: %d' %(-lowest))


    components = list(nx.connected_components(G))

    # print('       adjusting components: %d/%d' %(len(components), num_buses))
    components = adjustNumComponents(components, G, constraints, max_size, num_buses)

    # print('       reducing component sizes:')
    reduceComponentSizes(components, G, constraints, max_size)

    # print('       local improvement:')
    localImprovement(components, G, constraints, max_size)

    assert len(components) == num_buses
    for c in components:
        assert len(c) <= max_size
        assert len(c) > 0
    return components

def score(G, components, constraints):
    graph = nx.compose_all([G.subgraph(c) for c in components])
    bus_assignments = {}
    attendance_count = 0
    assignments = [list(c) for c in components]

    attendance = {student:False for student in graph.nodes()}
    for i in range(len(assignments)):
        for student in assignments[i]:   
            attendance[student] = True
            bus_assignments[student] = i

    total_edges = graph.number_of_edges()
    for i in range(len(constraints)):
        busses = set()
        for student in constraints[i]:
            busses.add(bus_assignments[student])
        if len(busses) <= 1:
            for student in constraints[i]:
                if student in graph:
                    graph.remove_node(student)

    score = 0
    for edge in graph.edges():
        if bus_assignments[edge[0]] == bus_assignments[edge[1]]:
            score += 1
    score = score / total_edges

    return score

def adjustNumComponents(components, G, constraints, max_size, num_buses):
    if len(components) < num_buses:
        components = [G.subgraph(c) for c in components]
        while len(components) < num_buses: #or all ones
            cuts = []
            for c in components:
                if len(c) < 2:
                    cuts.append((90000000000000, None))
                else:
                    cuts.append((nx.stoer_wagner(c)))

            index_min = min(enumerate(cuts), key=lambda a: a[1][0])[0]
            mincut = cuts[index_min][1]
            components.pop(index_min)
            components.append(G.subgraph(mincut[0]))
            components.append(G.subgraph(mincut[1]))

            # print('                             %d/%d' %(len(components), num_buses))
        components = [set(c.nodes) for c in components]

    if len(components) > num_buses:
        while len(components) > num_buses:
            combineComponents(components, constraints, max_size, G)
            # print('                             %d/%d' %(len(components), num_buses))
    return components

def reduceComponentSizes(components, G, constraints, max_size):
    #ALL VERTICES
    # while any([len(c) > max_size for c in components]):
    #     best_node = None
    #     move_from = None
    #     move_to = None
    #     best_score = 0

    #     for c in range(len(components)):
    #         for node in components[c]:
    #             for i in range(len(components)):
    #                 if c == i:
    #                     continue
    #                 if len(components[i]) < max_size and len(components[c]) > max_size:
    #                     comps = components.copy()
    #                     comps[c] = comps[c].copy()
    #                     comps[i] = comps[i].copy()
    #                     comps[i].add(node)
    #                     comps[c].remove(node)
    #                     score_after = score(G, comps, constraints)

    #                 if score_after >= best_score:
    #                     best_score = score_after
    #                     best_node = node
    #                     move_to = i
    #                     move_from = c

    #         components[move_to].add(best_node)
    #         components[move_from].remove(best_node)

        # print('                                 moved one')

    #LEAST POPULAR
    ind = find_over_limit(components)
    biggest = components[ind]

    while(len(biggest) > max_size):
        n = least_popular(biggest, G)
        relocate(n, components, ind, constraints, max_size, G)
        
        ind = find_over_limit(components)
        biggest = components[ind]

        # print('                                 %d/%d' % (len(biggest), max_size))

def localImprovement(components, G, constraints, max_size):
    improved = True
    while improved:
        improved = False
        best_node = None
        move_from = None
        move_to = None
        best_improvement = 0

        for c in range(len(components)):
            for node in components[c]:
                for i in range(len(components)):
                    if c == i:
                        continue
                    if len(components[i]) < max_size:
                        comps = components.copy()
                        score_before = score(G, comps, constraints)
                        comps[c] = comps[c].copy()
                        comps[i] = comps[i].copy()
                        comps[i].add(node)
                        comps[c].remove(node)
                        score_after = score(G, comps, constraints)

                        if score_after - score_before > best_improvement:
                            best_improvement = score_after - score_before
                            best_node = node
                            move_to = i
                            move_from = c
        # print('                          %f' %best_improvement)

        if best_node != None:
            components[move_to].add(best_node)
            components[move_from].remove(best_node)
            improved = True
    return components

def combineComponents(components, constraints, max_size, G):
    least_full = min(enumerate(components), key=lambda a: len(a[1]))[0]
    move_to = None
    best_score = 0
    c = least_full

    for i in range(len(components)):
        if i == least_full or len(components[i]) >= max_size:
            continue
        comps = components.copy()
        comps[least_full] = comps[least_full].copy()
        comps[least_full].update(comps[i])
        comps.pop(i)
        score_after = score(G, comps, constraints)

        if score_after >= best_score:
            best_score = score_after
            move_to = i

    components[least_full].update(components[move_to])
    components.pop(move_to)

def relocate(node, components, move_from, constraints, max_size, G):
    best_node = None
    c = move_from
    move_to = None
    best_score = 0

    for i in range(len(components)):
        if len(components[i]) >= max_size or i == c:
            continue
        comps = components.copy()
        comps[c] = comps[c].copy()
        comps[i] = comps[i].copy()
        comps[i].add(node)
        comps[c].remove(node)
        score_after = score(G, comps, constraints)

        if score_after >= best_score:
            best_score = score_after
            best_node = node
            move_to = i

    components[move_to].add(best_node)
    components[move_from].remove(best_node)

def find_over_limit(components):
    index_max = max(enumerate(components), key=lambda a: len(a[1]))[0]
    return index_max

def least_popular(component, G):
    best = None
    minDeg = 100000
    S = G.subgraph(component)

    for n in component:
        deg = len(list(S.neighbors(n)))
        if deg <= 1:
            return n
        if deg < minDeg:
            minDeg = deg
            best = n
    return best

def process(graph, num_buses, size_bus, constraints, size, output_category_path, input_name):

    solution = solve(graph, num_buses, size_bus, constraints, size + input_name)
    output_file = open(output_category_path + "/" + input_name + ".out", "w")

    for component in solution:
        output_file.write("%s\n" % list(component))
    output_file.close()

def main():
    tasks = []

    size_categories = ["small", "medium", "large"]
    if not os.path.isdir(path_to_outputs):
        os.mkdir(path_to_outputs)

    for size in size_categories:
        category_path = path_to_inputs + "/" + size
        output_category_path = path_to_outputs + "/" + size
        category_dir = os.fsencode(category_path)

        if not os.path.isdir(output_category_path):
            os.mkdir(output_category_path)

        # run = False
        for input_folder in os.listdir(category_dir):
            input_name = os.fsdecode(input_folder)


            # if size == 'medium' and input_name == '11':
            #     run = True

            # if run == False or (size == 'medium' and input_name == '11'):
            #     continue

            graph, num_buses, size_bus, constraints = parse_input(category_path + "/" + input_name)

            print(size, input_name)
            # process(graph, num_buses, size_bus, constraints, size, output_category_path, input_name)
            tasks.append((graph, num_buses, size_bus, constraints, size, output_category_path, input_name))
    
    num_threads = 5
    pool = Pool(num_threads)
    for t in tasks:
        pool.apply_async(process, t)
    # results = [pool.apply_async(process, t) for t in tasks]
    pool.close()
    pool.join()

if __name__ == '__main__':
    main()