import timeout_decorator
from agent_baselines import Agent
import networkx as nx
from collections import deque

RETRY_COUNT = 3

class AggressiveAgent(Agent):
    @timeout_decorator.timeout(1)
    def __init__(self, agent_name='Master Lingwei\'s aggressive agent that somehow works'):
        super().__init__(agent_name)

    @timeout_decorator.timeout(1)
    def new_game(self, game, power_name):
        self.game = game
        self.power_name = power_name
        self.state_graph = self.build_state_graph()
        self.target_count = RETRY_COUNT
        self.target = None
        self.no_luck = set()
        self.update_state_graph()

    @timeout_decorator.timeout(1)
    def update_game(self, all_power_orders):
        # do not make changes to the following codes
        for power_name in all_power_orders.keys():
            self.game.set_orders(power_name, all_power_orders[power_name])
        self.game.process()
        self.update_state_graph()

    @timeout_decorator.timeout(1)
    def build_state_graph(self):
        # TODO: does not take into account convoys for armies
        state_graph = nx.Graph()

        # Add nodes for all provinces
        for prov, prov_type in self.game.map.loc_type.items():
            if prov_type == 'LAND':
                node_type = 'LAND'
            elif prov_type == 'WATER':
                node_type = 'WATER'
            elif prov_type == 'COAST':
                node_type = 'COAST'
            state_graph.add_node(prov.upper(), type=node_type, units=(None, None))

        # Add edges for army/fleet adjacency
        locations = list(state_graph.nodes)
        for i in locations:
            for j in locations:
                if self.game.map.abuts('A', i, '-', j):
                    state_graph.add_edge(i, j, army=True, fleet=False)
                if self.game.map.abuts('F', i, '-', j):
                    if state_graph.has_edge(i, j):
                        state_graph[i][j]['fleet'] = True
                    else:
                        state_graph.add_edge(i, j, army=False, fleet=True)

        return state_graph

    @timeout_decorator.timeout(1)
    def update_state_graph(self):
        # Reset units and owner information for all nodes
        for node in self.state_graph.nodes:
            self.state_graph.nodes[node]['units'] = (None, None)
            self.state_graph.nodes[node]['owner'] = None
            self.state_graph.nodes[node]['is_supply'] = False
        
        # Add supply center information
        for prov in self.game.map.scs:
            self.state_graph.nodes[prov.upper()]['is_supply'] = True

        # Add unit information
        for power_name, power in self.game.powers.items():
            for unit in power.units:
                unit_type, prov = unit.split()
                self.state_graph.nodes[prov.upper()]['units'] = (power_name, unit_type)

        # Add owner information for supply centers
        for owner, provs in self.game.get_centers().items():
            for prov in provs:
                self.state_graph.nodes[prov.upper()]['owner'] = owner

    @timeout_decorator.timeout(1)
    def get_convoy_options(self):
        """
        For each army of self.power_name on a COAST node, finds all paths via fleets on WATER nodes to other COAST nodes.
        Returns a dict mapping '{ORIGIN}' -> {DEST: [fleet1, fleet2, ...], ...}
        """
        # TODO: account for EC/SC coasts
        G = self.state_graph
        convoy_options = {}
        coast_nodes = [n for n in G.nodes if G.nodes[n]['type'] == 'COAST' and G.nodes[n]['units'] == (self.power_name, 'A')]

        for origin in coast_nodes:
            destinations = {}
            # Start DFS from all adjacent WATER nodes with a fleet
            for nbr in G.neighbors(origin):
                nbr_data = G.nodes[nbr]
                if nbr_data['type'] == 'WATER' and nbr_data['units'] == (self.power_name, 'F') and G.get_edge_data(origin, nbr).get('fleet'):
                    stack = [(nbr, [nbr], set([origin, nbr]))]
                    while stack:
                        cur, path, visited = stack.pop()
                        # Explore neighbors of current WATER node
                        for next_nbr in G.neighbors(cur):
                            next_data = G.nodes[next_nbr]
                            if next_nbr == origin:
                                continue
                            # If adjacent COAST node (not origin), record as destination
                            if next_data['type'] == 'COAST' and G.get_edge_data(cur, next_nbr).get('fleet'):
                                if next_nbr not in destinations:
                                    destinations[next_nbr] = path.copy()
                            # Continue DFS through WATER nodes with fleets
                            elif next_data['type'] == 'WATER' and next_nbr not in visited and next_data['units'] == (self.power_name, 'F') and G.get_edge_data(cur, next_nbr).get('fleet'):
                                stack.append((next_nbr, path + [next_nbr], visited | set([next_nbr])))
            convoy_options[origin] = destinations
        return convoy_options

    @timeout_decorator.timeout(1)
    def find_closest_unoccupied(self, origin, target, target_locs):
        """
        Returns the closest location to 'target' that is unoccupied, not in target_locs, and adjacent to 'origin'.
        If none found, returns the closest adjacent province (not in target_locs) on the shortest path to target, even if occupied.
        """
        G = self.state_graph
        candidates = []
        origin_node_data = G.nodes[origin]
        origin_unit_type = origin_node_data['units'][1]
        for nbr in G.neighbors(origin):
            if nbr in target_locs: continue
            node_data = G.nodes[nbr]
            if node_data['units'][0] is not None: continue
            if not self.game.map.abuts(origin_unit_type, origin, '-', nbr): continue
            # BFS from nbr to target to get distance
            visited = {nbr}
            q = deque([(nbr, 0)])
            dist = None
            while q:
                cur, d = q.popleft()
                if cur == target:
                    dist = d
                    break
                for nn in G.neighbors(cur):
                    if nn not in visited:
                        visited.add(nn)
                        q.append((nn, d + 1))
            if dist is not None:
                candidates.append((dist, nbr))
        if candidates:
            candidates.sort()
            return candidates[0][1]
        # If no unoccupied adjacent province, pick the closest adjacent province on shortest path to target (even if occupied)
        alt_candidates = []
        for nbr in G.neighbors(origin):
            if nbr in target_locs: continue
            if not self.game.map.abuts(origin_unit_type, origin, '-', nbr): continue
            # BFS from nbr to target to get distance
            visited = {nbr}
            q = deque([(nbr, 0)])
            dist = None
            while q:
                cur, d = q.popleft()
                if cur == target:
                    dist = d
                    break
                for nn in G.neighbors(cur):
                    if nn not in visited:
                        visited.add(nn)
                        q.append((nn, d + 1))
            if dist is not None:
                alt_candidates.append((dist, nbr))
        if alt_candidates:
            alt_candidates.sort()
            return alt_candidates[0][1]
        return None

    @timeout_decorator.timeout(1)
    def get_target(self, remaining_units, unit_types):
        enemy_supply_centers = [
            n for n in self.state_graph.nodes
            if self.state_graph.nodes[n]['is_supply'] and self.state_graph.nodes[n]['owner'] not in (None, self.power_name)
        ]
        target = None
        min_dist = float('inf')
        for loc in remaining_units:
            loc_u = loc.upper()
            unit_type = unit_types[loc]
            visited = {loc_u}
            prev = {loc_u: None}
            q = deque([(loc_u, 0)])
            while q:
                cur, dist = q.popleft()
                if cur in enemy_supply_centers and dist < min_dist and cur not in self.no_luck:
                    target = cur
                    min_dist = dist
                for nbr in self.state_graph.neighbors(cur):
                    if nbr in visited:
                        continue
                    edge = self.state_graph.get_edge_data(cur, nbr) or {}
                    can_traverse = (unit_type == 'A' and edge.get('army')) or (unit_type == 'F' and edge.get('fleet'))
                    if not can_traverse:
                        continue
                    visited.add(nbr)
                    prev[nbr] = cur
                    q.append((nbr, dist + 1))
        return target
            
    def get_unit_dists(self, remaining_units, target, unit_types):
        unit_distances = []
        for loc in remaining_units:
            loc_u = loc.upper()
            unit_type = unit_types[loc]
            # Compute distance from loc to target
            visited = {loc_u}
            q = deque([(loc_u, 0)])
            dist_to_target = None
            while q:
                cur, dist = q.popleft()
                if cur == target:
                    dist_to_target = dist
                    break
                for nbr in self.state_graph.neighbors(cur):
                    if nbr in visited:
                        continue
                    edge = self.state_graph.get_edge_data(cur, nbr) or {}
                    can_traverse = (unit_type == 'A' and edge.get('army')) or (unit_type == 'F' and edge.get('fleet'))
                    if not can_traverse:
                        continue
                    visited.add(nbr)
                    q.append((nbr, dist + 1))
            unit_distances.append((dist_to_target if dist_to_target is not None else float('inf'), loc))
        
        return unit_distances

    @timeout_decorator.timeout(1)
    def get_actions(self):
        orders = []
        my_power = self.power_name
        my_units = self.game.powers[my_power].units
        unit_types = {unit.split()[1].upper(): unit.split()[0] for unit in my_units}
        unit_locs = set(unit_types.keys())
        accounted_locs = set()
        target_moves = set()
        convoy_map = self.get_convoy_options()

        # Case 0: If in build phase, build in any unoccupied supply center if possible
        if self.game.get_current_phase().endswith('A'):
            all_possible_orders = self.game.get_all_possible_orders()
            for loc in self.game.map.homes[self.power_name]:
                if self.state_graph.nodes[loc.upper()]['is_supply']:
                    possible_builds = all_possible_orders[loc]
                    if len(possible_builds) == 3:
                        orders.append(f'A {loc} B')
                    elif len(possible_builds) > 0:
                        orders.append(all_possible_orders[loc][0])
            return orders
        
        # Case 0.5: If in retreat phase, return empty list (only when vsing static agents)
        if self.game.get_current_phase().endswith('R'):
            return []
                        
        # Case 1: For every unit that is currently in a supply center not owned by us, hold
        for loc in unit_locs:
            node_data = self.state_graph.nodes[loc.upper()]
            if node_data['owner'] != self.power_name and node_data['is_supply']:
                orders.append(f"{unit_types[loc]} {loc} H")
                accounted_locs.add(loc)

        # Case 2: For remaining units, check neighboring nodes for unoccupied supply centers and move there if possible.
        for loc in unit_locs - accounted_locs:
            neighbors = [neighbor for neighbor in self.state_graph.neighbors(loc.upper())]
            for neighbor in neighbors:
                edge_data = self.state_graph.get_edge_data(loc.upper(), neighbor)
                node_data = self.state_graph.nodes[neighbor]
                neighbor_power, neighbor_unit_type = node_data['units']
                if unit_types[loc] == 'A' and edge_data.get('army') != True: continue
                elif unit_types[loc] == 'F' and edge_data.get('fleet') != True: continue

                if node_data.get('is_supply') == True and neighbor_power is None and node_data.get('owner') != self.power_name:
                    if neighbor in target_moves: continue
                    orders.append(f"{unit_types[loc]} {loc} - {neighbor}")
                    target_moves.add(neighbor)
                    accounted_locs.add(loc)
                    break

        # Case 2.5: Check convoy options after checking adjacent army nodes
        for loc in unit_locs - accounted_locs:
            if loc in convoy_map:
                neighbors = convoy_map[loc].keys()
                for neighbor in neighbors:
                    node_data = self.state_graph.nodes[neighbor]
                    if node_data.get('is_supply') == True and neighbor_power is None and node_data.get('owner') != self.power_name:
                        if neighbor in target_moves: continue
                        orders.append(f"A {loc} - {neighbor} VIA")
                        target_moves.add(neighbor)
                        accounted_locs.add(tuple(convoy_map[loc][neighbor]))  # Add all fleets involved in convoy to accounted_locs
                        accounted_locs.add(loc)
                        break

        # Case 3: For remaining units, if 2+ units border a location occupied by an enemy unit, move one unit to attack it and support with all other units
        enemy_occupied_locations = [
            n for n in self.state_graph.nodes
            if self.state_graph.nodes[n]['units'][0] is not None and self.state_graph.nodes[n]['units'][0] != my_power
        ]
        for target in enemy_occupied_locations:
            adjacent_friendly = []
            for loc in unit_locs - accounted_locs:
                if not self.state_graph.has_edge(loc.upper(), target):
                    continue
                edge = self.state_graph.get_edge_data(loc.upper(), target)
                unit_type = unit_types[loc]
                if unit_type == 'A' and not edge.get('army'): continue
                if unit_type == 'F' and not edge.get('fleet'): continue
                adjacent_friendly.append(loc)

            if len(adjacent_friendly) >= 2:
                target_type = self.state_graph.nodes[target]['type']
                attacker = None
                if target_type in ('COAST', 'LAND'):
                    for loc in adjacent_friendly:
                        if unit_types[loc] == 'A':
                            attacker = loc
                            break
                if attacker is None:
                    for loc in adjacent_friendly:
                        if unit_types[loc] == 'F':
                            attacker = loc
                            break
                if attacker is None:
                    attacker = adjacent_friendly[0]  # fallback to first

                attacker_type = unit_types[attacker]
                if target in target_moves: continue
                orders.append(f"{attacker_type} {attacker} - {target}")
                target_moves.add(target)
                accounted_locs.add(attacker)
                for supporter in adjacent_friendly:
                    if supporter == attacker:
                        continue
                    supporter_type = unit_types[supporter]
                    orders.append(f"{supporter_type} {supporter} S {attacker_type} {attacker} - {target}")
                    accounted_locs.add(supporter)

        # Case 3.5: Any fleets should try move to adjacent sea provinces if possible to vacate space for army units and allow for convoys
        for loc in unit_locs - accounted_locs:
            if unit_types[loc] == 'F':
                if self.state_graph.nodes[loc.upper()]['type'] == 'WATER':
                    continue
                for neighbor in self.state_graph.neighbors(loc.upper()):
                    edge_data = self.state_graph.get_edge_data(loc.upper(), neighbor)
                    node_data = self.state_graph.nodes[neighbor]
                    neighbor_power, neighbor_unit_type = node_data['units']
                    if edge_data.get('fleet') == True and node_data.get('type') == 'WATER' and neighbor_power is None:
                        if neighbor in target_moves:
                            continue
                        orders.append(f"F {loc} - {neighbor}")
                        target_moves.add(neighbor)
                        accounted_locs.add(loc)
                        break

        # Case 4: For remaining units, move as many units as possible to be adjacent to the closest enemy supply center.
        remaining_units = list(unit_locs - accounted_locs)
        # Pick the closest enemy supply center as target
        if self.target_count == RETRY_COUNT:
            target = self.get_target(remaining_units, unit_types)
            self.target_count = 0
            self.no_luck.add(target)
        else:
            self.target_count += 1

        unit_distances = self.get_unit_dists(remaining_units, target, unit_types)

        # Sort units by distance to target (closest first)
        unit_distances.sort()
        # Move non-adjacent units first
        for dist, loc in unit_distances:
            loc_u = loc.upper()
            unit_type = unit_types[loc]
            if target in self.state_graph.neighbors(loc_u): continue 
            next_loc = self.find_closest_unoccupied(loc_u, target, target_moves)
            if not next_loc: continue
            orders.append(f"{unit_types[loc]} {loc} - {next_loc}")
            target_moves.add(next_loc)
            accounted_locs.add(loc)

        # Do adjacent units last
        for dist, loc in unit_distances:
            loc_u = loc.upper()
            unit_type = unit_types[loc]
            if target not in self.state_graph.neighbors(loc_u):
                continue
            next_loc = self.find_closest_unoccupied(loc_u, target, target_moves)
            if not next_loc: continue
            if next_loc is not None:
                orders.append(f"{unit_types[loc]} {loc} - {next_loc}")
                target_moves.add(next_loc)
                accounted_locs.add(loc)
            else:
                orders.append(f"{unit_types[loc]} {loc} H")
                accounted_locs.add(loc)

        # print(orders, self.game.get_current_phase())
        return orders