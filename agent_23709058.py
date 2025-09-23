import timeout_decorator
from agent_baselines import Agent
import networkx as nx
from collections import deque
import random

class StudentAgent(Agent):
    RETRY_COUNT = 4
    DEBUG = False

    @timeout_decorator.timeout(1)
    def __init__(self, agent_name='Aggressive Agent'):
        super().__init__(agent_name)

    @timeout_decorator.timeout(1)
    def new_game(self, game, power_name):
        self.game = game
        self.own_power = power_name
        self.state_graph = self.build_state_graph()
        self.target_count = self.RETRY_COUNT
        self.debug = self.DEBUG
        self.target_loc = None
        self.failed_targets = set()
        self.england_wait_fleets = (3, 12)
        self.phase_count = 0
        self.update_state_graph()

    @timeout_decorator.timeout(1)
    def update_game(self, all_power_orders):
        for power_name in all_power_orders.keys():
            self.game.set_orders(power_name, all_power_orders[power_name])
        self.game.process()
        self.phase_count += 1
        self.update_state_graph()

    @timeout_decorator.timeout(1)
    def build_state_graph(self):
        state_graph = nx.Graph()

        # Add nodes for all provinces
        for loc, loc_type in self.game.map.loc_type.items():
            if loc_type == 'LAND':
                node_type = 'LAND'
            elif loc_type == 'WATER':
                node_type = 'WATER'
            elif loc_type == 'COAST':
                node_type = 'COAST'
            state_graph.add_node(loc.upper(), type=node_type, units=(None, None))

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
        # Reset state graph
        for node in self.state_graph.nodes:
            self.state_graph.nodes[node]['units'] = (None, None)
            self.state_graph.nodes[node]['owner'] = None
            self.state_graph.nodes[node]['is_supply'] = False
        
        # Add supply center information
        for loc in self.game.map.scs:
            self.state_graph.nodes[loc.upper()]['is_supply'] = True

        # Add unit information
        for power_name, power in self.game.powers.items():
            for unit in power.units:
                unit_type, loc = unit.split()
                self.state_graph.nodes[loc.upper()]['units'] = (power_name, unit_type)

        # Add owner information for supply centers
        for owner, provs in self.game.get_centers().items():
            for loc in provs:
                self.state_graph.nodes[loc.upper()]['owner'] = owner

    @timeout_decorator.timeout(1)
    def get_convoy_options(self, army_loc, accounted_unit_locs):
        """
        Get dict of possible convoy destinations for an army at army_loc.
        Keys are destination locations, values are lists of fleets involved in the convoy.
        Only the path with the smallest number of fleets is kept for each destination.
        """
        destinations = {}

        # Only proceed if army_loc is a COAST node with our army
        node_data = self.state_graph.nodes.get(army_loc)
        if node_data['type'] != 'COAST' or node_data['units'] != (self.own_power, 'A'):
            return destinations

        # DFS from all adjacent WATER nodes that is occupied by own fleet
        for neighbor in self.state_graph.neighbors(army_loc):
            neighbor_data = self.state_graph.nodes[neighbor]
            if neighbor in accounted_unit_locs: continue
            if neighbor_data['type'] == 'WATER' and neighbor_data['units'] == (self.own_power, 'F') and self.state_graph.get_edge_data(army_loc, neighbor).get('fleet'):
                stack = [(neighbor, [neighbor], set([army_loc, neighbor]))]
                while stack:
                    cur, path, visited = stack.pop()
                    for next_neighbor in self.state_graph.neighbors(cur):
                        next_data = self.state_graph.nodes[next_neighbor]
                        if next_neighbor == army_loc:
                            continue
                        if next_data['type'] == 'COAST' and self.state_graph.get_edge_data(cur, next_neighbor).get('fleet'):
                            # Only keep the path with the smallest number of fleets
                            if next_neighbor not in destinations or len(path) < len(destinations[next_neighbor]):
                                destinations[next_neighbor] = path.copy()
                        elif next_data['type'] == 'WATER' and next_neighbor not in visited and next_data['units'] == (self.own_power, 'F') \
                        and self.state_graph.get_edge_data(cur, next_neighbor).get('fleet'):
                            stack.append((next_neighbor, path + [next_neighbor], visited | set([next_neighbor])))
        
        # Remove EC, WC, SC (not compatible with game engine)
        destinations = {dest[:3]: fleets for dest, fleets in destinations.items()}
        return destinations

    @timeout_decorator.timeout(1)
    def find_closest_unoccupied(self, origin, target, target_locs, accounted_unit_locs):
        """
        Returns a tuple (loc, fleets) where loc is the closest location to 'target' that is unoccupied,
        not in target_locs, and adjacent to (origin). If loc is only reachable via convoy, fleets is a list of fleets involved in the convoy.
        If none found, returns the closest adjacent province (not in target_locs) on the shortest path to target, even if occupied.
        """
        origin_node_data = self.state_graph.nodes[origin]
        origin_unit_type = origin_node_data['units'][1]
        candidates = []
        alt_candidates = []

        # Find all neighbors (direct and convoy) from origin
        neighbors = set(self.state_graph.neighbors(origin))
        convoy_options = self.get_convoy_options(origin, accounted_unit_locs)
        for dest, fleets in convoy_options.items():
            for fleet in fleets:
                if fleet in accounted_unit_locs:
                    break
            else:
                neighbors.add(dest)

        for neighbor in neighbors:
            if neighbor in target_locs: continue
            node_data = self.state_graph.nodes[neighbor]
            fleets = convoy_options[neighbor] if neighbor in convoy_options else None

            # For direct adjacency, check abuts, for convoy, skip abuts check
            if not neighbor in convoy_options and not self.game.map.abuts(origin_unit_type, origin, '-', neighbor):
                continue

            # BFS from neighbor to target to get distance
            visited = {neighbor}
            q = deque([(neighbor, 0)])
            dist = None
            while q:
                cur, d = q.popleft()
                if cur == target:
                    dist = d
                    break
                for nn in self.state_graph.neighbors(cur):
                    if nn not in visited:
                        visited.add(nn)
                        q.append((nn, d + 1))
            if dist is not None:
                if node_data['units'][0] is None:
                    candidates.append((dist, neighbor, fleets))
                else:
                    alt_candidates.append((dist, neighbor, fleets))

        if candidates:
            candidates.sort()
            return candidates[0][1], candidates[0][2]
        if alt_candidates:
            alt_candidates.sort()
            return alt_candidates[0][1], alt_candidates[0][2]
        return None, None

    @timeout_decorator.timeout(1)
    def get_target(self, remaining_units):
        # Pick a random unit and find the closest enemy supply center using BFS
        enemy_supply_centers = [
            n for n in self.state_graph.nodes
            if self.state_graph.nodes[n]['is_supply'] and self.state_graph.nodes[n]['owner'] not in (None, self.own_power)
        ]
        if not remaining_units or not enemy_supply_centers:
            return None
        
        loc = random.choice(list(remaining_units))
        visited = {loc}
        prev = {loc: None}
        q = deque([(loc, 0)])
        min_dist = float('inf')
        target = None
        while q:
            cur, dist = q.popleft()
            if cur in enemy_supply_centers and dist < min_dist and cur not in self.failed_targets:
                target = cur
                min_dist = dist
                break  # Uncomment to pick the first found, not necessarily the closest
            for neighbor in self.state_graph.neighbors(cur):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                prev[neighbor] = cur
                q.append((neighbor, dist + 1))
        return target

    @timeout_decorator.timeout(1)        
    def get_unit_dists(self, remaining_units, target, unit_types):
        unit_distances = []
        for loc in remaining_units:
            unit_type = unit_types[loc]
            # Compute distance from loc to target
            visited = {loc}
            q = deque([(loc, 0)])
            dist_to_target = None
            while q:
                cur, dist = q.popleft()
                if cur == target:
                    dist_to_target = dist
                    break
                for neighbor in self.state_graph.neighbors(cur):
                    if neighbor in visited:
                        continue
                    edge = self.state_graph.get_edge_data(cur, neighbor) or {}
                    can_traverse = (unit_type == 'A' and edge.get('army')) or (unit_type == 'F' and edge.get('fleet'))
                    if not can_traverse:
                        continue
                    visited.add(neighbor)
                    q.append((neighbor, dist + 1))
            unit_distances.append((dist_to_target if dist_to_target is not None else float('inf'), loc))
        
        return unit_distances

    @timeout_decorator.timeout(1)
    def get_actions(self):
        orders = []
        my_power = self.own_power
        my_units = self.game.powers[my_power].units
        unit_types = {unit.split()[1].upper(): unit.split()[0] for unit in my_units}
        unit_locs = set(unit_types.keys())
        accounted_unit_locs = set() # Set of unit locations that have been assigned orders
        accounted_locs = set() # Set of locations that have been targeted by moves/supports
        accounted_fleet_locs = set() # Set of fleet locations that have been assigned orders (subset of accounted_unit_locs)
        
        if self.debug: print(self.game.get_current_phase())

        # Case 0: If in build phase, build in any unoccupied supply center if possible
        if self.game.get_current_phase().endswith('A'):
            all_possible_orders = self.game.get_all_possible_orders()
            for loc in self.game.map.homes[self.own_power]:
                if self.state_graph.nodes[loc.upper()]['is_supply']:
                    possible_builds = all_possible_orders[loc]
                    fleet_count = sum(1 for u in my_units if u.startswith('F'))
                    army_count = sum(1 for u in my_units if u.startswith('A'))
                    total = fleet_count + army_count
                    fleet_ratio = fleet_count / total if total > 0 else 0
                    if self.own_power == "ENGLAND": fleet_ratio_threshold = 0.4
                    else: fleet_ratio_threshold = 0.1

                    if len(possible_builds) == 3:
                        if fleet_ratio < fleet_ratio_threshold:
                            orders.append(f'F {loc} B')
                        else:
                            orders.append(f'A {loc} B')
                    elif len(possible_builds) > 0:
                        orders.append(f'A {loc} B')
            if self.debug: print('\t', orders)
            return orders
        
        # Case 0.5: If in retreat phase, retreat to any unoccupied adjacent location if possible, else disband (no orders needed for disband)
        if self.game.get_current_phase().endswith('R'):
            all_possible_orders = self.game.get_all_possible_orders()
            for loc in all_possible_orders.keys():
                if all_possible_orders[loc] and loc in unit_locs:
                    for order in all_possible_orders[loc]:
                        if order.endswith('R') and not order[-2].isalpha():
                            orders.append(order)
                            break
            if self.debug: print('\t', orders)
            return orders
                        
        # Case 1: For every unit that is currently in a supply center not owned by us, hold 
        for loc in unit_locs:
            node_data = self.state_graph.nodes[loc.upper()]
            if node_data['owner'] != self.own_power and node_data['is_supply']:
                orders.append(f"{unit_types[loc]} {loc} H")
                accounted_unit_locs.add(loc)

        # Case 2: For remaining units, check neighboring nodes for unoccupied supply centers and move there if possible.
        for loc in unit_locs - accounted_unit_locs:
            if self.own_power == "ENGLAND" and unit_types[loc] == 'F' and self.england_wait_fleets[0] < self.phase_count <= self.england_wait_fleets[1]:
                continue
            neighbors = [neighbor for neighbor in self.state_graph.neighbors(loc.upper())]
            for neighbor in neighbors:
                edge_data = self.state_graph.get_edge_data(loc.upper(), neighbor)
                node_data = self.state_graph.nodes[neighbor]
                neighbor_power, neighbor_unit_type = node_data['units']
                if unit_types[loc] == 'A' and edge_data.get('army') != True: continue
                elif unit_types[loc] == 'F' and edge_data.get('fleet') != True: continue

                if node_data.get('is_supply') == True and neighbor_power is None and node_data.get('owner') != self.own_power:
                    if neighbor in accounted_locs: continue
                    orders.append(f"{unit_types[loc]} {loc} - {neighbor}")
                    if self.debug: print('\t', orders[-1])
                    accounted_locs.add(neighbor)
                    accounted_unit_locs.add(loc)
                    break

        # Case 2.5: Check convoy options after checking adjacent army nodes
        for loc in unit_locs - accounted_unit_locs:
            convoy_options = self.get_convoy_options(loc.upper(), accounted_unit_locs)
            if convoy_options == {}: continue
            neighbors = convoy_options.keys()
            for neighbor in neighbors:
                node_data = self.state_graph.nodes[neighbor]
                if node_data.get('is_supply') == True and neighbor_power is None and node_data.get('owner') != self.own_power and not node_data['units'][0]:
                    if neighbor in accounted_locs: continue
                    orders.append(f"A {loc} - {neighbor} VIA")
                    for fleet in convoy_options[neighbor]:
                        orders.append(f"F {fleet} C A {loc} - {neighbor}")
                    accounted_locs.add(neighbor)
                    for fleet in convoy_options[neighbor]:
                        accounted_unit_locs.add(fleet)
                    accounted_unit_locs.add(loc)
                    break

        # Case 3: For remaining units, if 2+ units border a location occupied by an enemy unit, move one unit to attack it and support with all other units
        enemy_occupied_locations = [
            n for n in self.state_graph.nodes
            if self.state_graph.nodes[n]['units'][0] is not None and self.state_graph.nodes[n]['units'][0] != my_power
        ]
        for target in enemy_occupied_locations:
            adjacent_friendly = []
            for loc in unit_locs - accounted_unit_locs:
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
                if target in accounted_locs: continue
                orders.append(f"{attacker_type} {attacker} - {target}")
                accounted_locs.add(target)
                accounted_unit_locs.add(attacker)
                for supporter in adjacent_friendly:
                    if supporter == attacker:
                        continue
                    supporter_type = unit_types[supporter]
                    orders.append(f"{supporter_type} {supporter} S {attacker_type} {attacker} - {target}")
                    accounted_unit_locs.add(supporter)

        # Case 3.5: Any fleets should try move to adjacent sea provinces if possible to vacate space for army units and allow for convoys
        for loc in unit_locs - accounted_unit_locs:
            if unit_types[loc] == 'F':
                if self.state_graph.nodes[loc.upper()]['type'] == 'WATER':
                    accounted_fleet_locs.add(loc)
                    continue
                # Find all adjacent WATER nodes
                water_neighbors = [
                    neighbor for neighbor in self.state_graph.neighbors(loc.upper())
                    if self.state_graph.nodes[neighbor]['type'] == 'WATER'
                    and self.state_graph.get_edge_data(loc.upper(), neighbor).get('fleet') == True
                    and self.state_graph.nodes[neighbor]['units'][0] is None
                ]
                # For each water neighbor, compute distance to closest own army unit
                min_dist = float('inf')
                best_water = None
                for water in water_neighbors:
                    # Find closest own army unit
                    for army_loc in unit_locs:
                        if unit_types[army_loc] != 'A':
                            continue
                        visited = {water}
                        q = deque([(water, 0)])
                        while q:
                            cur, dist = q.popleft()
                            if cur == army_loc.upper():
                                if dist < min_dist:
                                    min_dist = dist
                                    best_water = water
                                break
                            for neighbor in self.state_graph.neighbors(cur):
                                if neighbor not in visited:
                                    visited.add(neighbor)
                                    q.append((neighbor, dist + 1))
                if best_water and best_water not in accounted_locs:
                    orders.append(f"F {loc} - {best_water}")
                    accounted_locs.add(best_water)
                    accounted_unit_locs.add(loc)
                else:
                    accounted_unit_locs.add(loc)

        # Case 4: For remaining units, move as many units as possible to be adjacent to the target
        remaining_units = list(unit_locs - accounted_unit_locs - accounted_fleet_locs)
        # Pick the closest enemy supply center as target every 3 movement phases, or if the target is captured
        if self.target_count == self.RETRY_COUNT or not self.target_loc or \
            (self.target_loc and self.state_graph.nodes[self.target_loc]['owner'] == self.own_power):
            if self.debug: print("\tPicking new target")
            self.target_loc = self.get_target(remaining_units)
            self.target_count = 0
            if self.target_loc:
                self.failed_targets.add(self.target_loc)
        else:
            self.target_count += 1

        target = self.target_loc
        unit_distances = self.get_unit_dists(remaining_units, target, unit_types)
        unit_distances.sort()
        if self.debug: print(f'\tTarget: {target}, no_luck: {self.failed_targets}, target_count: {self.target_count}')
        # Move non-adjacent units first
        for dist, loc in unit_distances:
            unit_type = unit_types[loc]
            if target in self.state_graph.neighbors(loc): continue 
            next_loc, fleets = self.find_closest_unoccupied(loc, target, accounted_locs, accounted_unit_locs)
            if not next_loc: continue
            if fleets:
                orders.append(f"{unit_types[loc]} {loc} - {next_loc} VIA")
                for fleet in fleets:
                    accounted_unit_locs.add(fleet)
                    orders.append(f"F {fleet} C {unit_types[loc]} {loc} - {next_loc}")
            else:
                orders.append(f"{unit_types[loc]} {loc} - {next_loc}")
            accounted_locs.add(next_loc)
            accounted_unit_locs.add(loc)

        # Do adjacent units last
        for dist, loc in unit_distances:
            unit_type = unit_types[loc]
            if target not in self.state_graph.neighbors(loc):
                continue
            next_loc, fleets = self.find_closest_unoccupied(loc, target, accounted_locs, accounted_unit_locs)
            if not next_loc: continue
            if fleets:
                orders.append(f"{unit_types[loc]} {loc} - {next_loc} VIA")
                for fleet in fleets:
                    accounted_unit_locs.add(fleet)
                    orders.append(f"F {fleet} C {unit_types[loc]} {loc} - {next_loc}")
            else:
                orders.append(f"{unit_types[loc]} {loc} - {next_loc}")
            accounted_locs.add(next_loc)
            accounted_unit_locs.add(loc)

        if self.debug: print('\t', orders)
        return orders