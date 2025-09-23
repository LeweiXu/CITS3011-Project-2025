# CITS3011 Intelligent Agent Project Report

You are required to write a report detailing the techniques you researched/investigated, your reasoning behind your choice of design and technique, and your assessment of the effectiveness of your agent.

**Report Rubrics (22 pts)**:

* **Basic Techniques (14 pts)**
- Considers and describes at least two basic techniques [^4]. Basic techniques can be from those taught in the lectures, or other existing techniques [^8]. (4 pts, 2 for each)
- Discusses the merits/motivations of these basic techniques and justifies the choices. (6 pts, 3 for each)
- Evaluates the effectiveness of these basic techniques and reports experimental results [^7]. (4 pts, 2 for each)

* **New Techniques (8 pts)**
- Creates and describes at least two new techniques [^5] [^6] designed by yourself for improvements. (2 pts, 1 for each)
- Discusses the merits/motivations of these new techniques and justifies the designs. (4 pts, 2 for each)
- Evaluates the effectiveness of these new techniques and reports experimental results [^7]. (2 pts, 1 for each)

## Basic Techniques

**1. Internal State Representation**

This was the first technique/idea that I implemented that is the foundation of all the other techniques described below. Inspired by the internal state graph implemented in `GreedyAgent`, I adapted this graph that uses the `networkx` library to include various other information in its nodes and edges. The implementation of this internal state representation is contained within the lines 36-85 in `agent_23709058.py`, and contains 2 functions: `build_state_graph()` and `update_state_graph()`. 

**`build_state_graph()`**
- This function is used to construct the internal state representation of the diplomacy game, and is called once within `new_game()`.
- We first construct the nodes of the graph using `game.map.loc_type` which is a dictionary of locations and the locations type. With this information, we can initialize each node as a location, with 2 attributes `type` which corresponds to the unit type (WATER, LAND or COAST) and `units` which is a 2-tuple storing the type of unit (A or F) and the power that unit belows to.
    ```python3
    state_graph.add_node(loc.upper(), type=node_type, units=(None, None))
    ```
- Next we use `game.map.abuts()` method to construct the edges between the nodes. For each pair of nodes in the state graph, we test if an army and a fleet can move between the nodes, and if it can, we add the edge and set the corresponding attribute `army` and/or `fleet` to True. For example, to test if an army can move between 2 nodes:
    ```python3
    if self.game.map.abuts('A', i, '-', j):
        state_graph.add_edge(i, j, army=True, fleet=False)
    ```

**`update_state_graph()`**
- This function is used to update the internal state representation every phase, and is called within `update_game()` after the game engine processes the new moves.
- 

**2. Case-Based Reasoning**

## New Techniques

**1. Power-Specific Strategic Variation**

**2. Dynamic Supply Center Targeting**