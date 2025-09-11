import timeout_decorator
from agent_baselines import Agent
import networkx as nx
from collections import deque

class StudentAgent(Agent):
    @timeout_decorator.timeout(1)
    def __init__(self, agent_name='Master Lingwei\'s Agent'):
        super().__init__(agent_name)

    @timeout_decorator.timeout(1)
    def new_game(self, game, power_name):
        self.game = game
        self.power_name = power_name
        self.state_graph = self.build_state_graph()
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
            state_graph.add_node(prov.upper(), type=node_type, units={})

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
            self.state_graph.nodes[node]['units'] = {}
            self.state_graph.nodes[node]['owner'] = None
            self.state_graph.nodes[node]['is_supply'] = False
        
        # Add supply center information
        for prov in self.game.map.scs:
            self.state_graph.nodes[prov.upper()]['is_supply'] = True

        # Add unit information
        for power_name, power in self.game.powers.items():
            for unit in power.units:
                unit_type, prov = unit.split()
                self.state_graph.nodes[prov.upper()]['units'][power_name] = unit_type

        # Add owner information for supply centers
        for owner, provs in self.game.get_centers().items():
            for prov in provs:
                self.state_graph.nodes[prov.upper()]['owner'] = owner

@timeout_decorator.timeout(1)
def get_convoy_options(self):
    """
    Returns a dict mapping 'A {ORIGIN}' -> [DEST,...] where each DEST is a coastal province
    the army can reach via a chain of adjacent fleets in WATER provinces.
    """
    G = self.state_graph
    fleet_nodes = [n for n in G.nodes if G.nodes[n]['type'] == 'WATER' and any(u == 'F' for u in G.nodes[n]['units'].values())]
    visited = set()
    fleet_chains = []

    # Find all chains of adjacent fleets in WATER provinces
    for node in fleet_nodes:
        if node in visited:
            continue
        chain = set()
        q = deque([node])
        while q:
            cur = q.popleft()
            if cur in visited:
                continue
            visited.add(cur)
            chain.add(cur)
            for nbr in G.neighbors(cur):
                if G.nodes[nbr]['type'] == 'WATER' and any(u == 'F' for u in G.nodes[nbr]['units'].values()):
                    if G.get_edge_data(cur, nbr).get('fleet'):
                        q.append(nbr)
        if chain:
            fleet_chains.append(chain)

    convoy_options = {}

    # For each fleet chain, find adjacent armies on COAST provinces and possible convoy destinations
    for chain in fleet_chains:
        # Find armies on COAST provinces adjacent to the chain
        armies = []
        for fleet in chain:
            for nbr in G.neighbors(fleet):
                if G.nodes[nbr]['type'] == 'COAST' and any(u == 'A' for u in G.nodes[nbr]['units'].values()):
                    armies.append(nbr)
        # For each army, find all coastal provinces adjacent to the chain (excluding origin)
        for army_loc in armies:
            destinations = set()
            for fleet in chain:
                for nbr in G.neighbors(fleet):
                    if G.nodes[nbr]['type'] == 'COAST' and nbr != army_loc and G.get_edge_data(fleet, nbr).get('fleet'):
                        destinations.add(nbr)
            if destinations:
                # Find the power name for the army
                for power, unit_type in G.nodes[army_loc]['units'].items():
                    if unit_type == 'A':
                        key = f"A {army_loc}"
                        if key not in convoy_options:
                            convoy_options[key] = []
                        convoy_options[key].extend(sorted(destinations))
    # Remove duplicates in destination lists
    for k in convoy_options:
        convoy_options[k] = sorted(list(set(convoy_options[k])))

    return convoy_options

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
        print(convoy_map)

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
                        
        # Case 1: For every unit that is currently in an unoccupied supply center, hold
        for loc in unit_locs:
            if self.state_graph.nodes[loc.upper()]['owner'] is None and self.state_graph.nodes[loc.upper()]['is_supply']:
                orders.append(f"{unit_types[loc]} {loc} H")
                accounted_locs.add(loc)

        # Case 2: For remaining units, check neighboring nodes for unoccupied supply centers and move there if possible.
        for loc in unit_locs - accounted_locs:
            neighbors = [neighbor for neighbor in self.state_graph.neighbors(loc.upper())]
            neighbors.extend([neighbor for neighbor in convoy_map[loc]])
            for neighbor in neighbors:
                edge_data = self.state_graph.get_edge_data(loc.upper(), neighbor)
                node_data = self.state_graph.nodes[neighbor]
                if unit_types[loc] == 'A' and edge_data.get('army') != True: continue
                elif unit_types[loc] == 'F' and edge_data.get('fleet') != True: continue

                if node_data.get('is_supply') == True and node_data.get('units') == {} and node_data.get('owner') != self.power_name:
                    if neighbor in target_moves: continue
                    orders.append(f"{unit_types[loc]} {loc} - {neighbor}")
                    target_moves.add(neighbor)
                    accounted_locs.add(loc)
                    break

        # Case 3: For remaining units, if 2 units border a location occupied by an enemy unit, move one unit to attack it and support with the other.
        enemy_occupied_locations = [
            n for n in self.state_graph.nodes
            if self.state_graph.nodes[n].get('units') and any(p != my_power for p in self.state_graph.nodes[n]['units'].keys())
        ]
        # For each enemy-occupied node, find friendly units adjacent to it (and ensure edge type matches unit)
        for target in enemy_occupied_locations:
            adjacent_friendly = []
            for loc in unit_locs - accounted_locs:
                if not self.state_graph.has_edge(loc.upper(), target):
                    continue
                edge = self.state_graph.get_edge_data(loc.upper(), target)
                unit_type = unit_types[loc]
                # ensure unit can traverse/support across this edge
                if unit_type == 'A' and not edge.get('army'): continue
                if unit_type == 'F' and not edge.get('fleet'): continue
                adjacent_friendly.append(loc)

            if len(adjacent_friendly) >= 2:
                # Move one unit to attack, others support
                attacker = adjacent_friendly[0]
                attacker_type = unit_types[attacker]

                if target in target_moves: continue
                
                orders.append(f"{attacker_type} {attacker} - {target}")
                target_moves.add(target)
                accounted_locs.add(attacker)
                for supporter in adjacent_friendly[1:]:
                    supporter_type = unit_types[supporter]
                    orders.append(f"{supporter_type} {supporter} S {attacker_type} {attacker} - {target}")
                    accounted_locs.add(supporter)

        # Case 3.5: Any fleets should try move to adjacent sea provinces if possible to vacate space for army units
        for loc in unit_locs - accounted_locs:
            if unit_types[loc] == 'F':
                if self.state_graph.nodes[loc.upper()]['type'] == 'WATER':
                    continue
                for neighbor in self.state_graph.neighbors(loc.upper()):
                    edge_data = self.state_graph.get_edge_data(loc.upper(), neighbor)
                    node_data = self.state_graph.nodes[neighbor]
                    if edge_data.get('fleet') == True and node_data.get('type') == 'WATER' and node_data.get('units') == {}:
                        if neighbor in target_moves:
                            continue
                        orders.append(f"F {loc} - {neighbor}")
                        target_moves.add(neighbor)
                        accounted_locs.add(loc)
                        break

        # Case 4: For remaining units, attempt to move towards the nearest supply center not owned by us.
        for loc in unit_locs - accounted_locs:
            loc_u = loc.upper()
            unit_type = unit_types[loc]

            # BFS from loc to find the first supply center owned by an enemy
            q = deque([loc_u])
            prev = {loc_u: None}
            visited = {loc_u}
            found_path = None

            while q:
                cur = q.popleft()

                # skip the start node when checking target property
                if cur != loc_u:
                    node_data = self.state_graph.nodes[cur]
                    if node_data.get('is_supply') and node_data.get('owner') not in (None, self.power_name):
                        # reconstruct path from loc_u to cur
                        path = []
                        n = cur
                        while n is not None:
                            path.append(n)
                            n = prev.get(n)
                        path.reverse()
                        found_path = path
                        break

                for nbr in self.state_graph.neighbors(cur):
                    if nbr in visited:
                        continue
                    edge = self.state_graph.get_edge_data(cur, nbr) or {}
                    # only traverse edges the unit type can use
                    can_traverse = (unit_type == 'A' and edge.get('army')) or (unit_type == 'F' and edge.get('fleet'))
                    if not can_traverse:
                        continue
                    visited.add(nbr)
                    prev[nbr] = cur
                    q.append(nbr)

            # If no target found or no movement step, hold
            if not found_path or len(found_path) < 2:
                orders.append(f"{unit_type} {loc} H")
                accounted_locs.add(loc)
                continue

            next_step = found_path[1]
            # if next_step is an enemy-occupied supply center and is adjacent, prefer an alternative unoccupied neighbour
            node_data_next = self.state_graph.nodes[next_step]
            occupying_units = node_data_next.get('units', {})
            enemy_occupying = (occupying_units != {} and any(p != self.power_name for p in occupying_units.keys()))
            if node_data_next.get('is_supply') and enemy_occupying:
                # try to find another adjacent unoccupied province to move into
                alt_found = None
                for alt in self.state_graph.neighbors(loc_u):
                    if alt == next_step:
                        continue
                    edge_alt = self.state_graph.get_edge_data(loc_u, alt) or {}
                    can_move_alt = (unit_type == 'A' and edge_alt.get('army')) or (unit_type == 'F' and edge_alt.get('fleet'))
                    if not can_move_alt:
                        continue
                    alt_node = self.state_graph.nodes[alt]
                    if alt_node.get('units', {}) == {} and alt not in target_moves:
                        alt_found = alt
                        break
                if alt_found:
                    orders.append(f"{unit_type} {loc} - {alt_found}")
                    target_moves.add(alt_found)
                    accounted_locs.add(loc)
                    continue
                else:
                    # no suitable alternative, hold
                    orders.append(f"{unit_type} {loc} H")
                    accounted_locs.add(loc)
                    continue

            # avoid collisions
            if next_step in target_moves:
                orders.append(f"{unit_type} {loc} H")
                accounted_locs.add(loc)
                continue

            orders.append(f"{unit_type} {loc} - {next_step}")
            target_moves.add(next_step)
            accounted_locs.add(loc)

        print(orders, self.game.get_current_phase())
        return orders