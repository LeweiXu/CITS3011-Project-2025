The technique used in get_actions() where multiple cases are checked and actions are prioritized is commonly called rule-based action selection or priority-based decision making.

Explanation:
The agent evaluates the current game state and applies a series of rules (cases) in a specific order.
Each rule represents a scenario (e.g., build phase, holding supply centers, attacking, supporting, moving fleets, targeting supply centers).
Higher-priority rules are checked first, and once an action is taken for a unit, it is not reconsidered by lower-priority rules.
This ensures that the most important actions (like holding supply centers or attacking with support) are executed before less critical ones.
Merit:
This approach is simple, interpretable, and effective for encoding expert knowledge or heuristics. It allows the agent to handle complex situations by breaking them into manageable, prioritized steps.

Common Names:

Rule-based system
Priority queue of actions
Hierarchical decision making
Case-based reasoning

----- The Per-Power and the Overall Performance of the Player Agent -----
AUSTRIA: SCs - 10.4±7.78, Wins - 44.0%, Survives - 48.0%, Defeats - 8.0%
ENGLAND: SCs - 11.12±6.04, Wins - 28.0%, Survives - 68.0%, Defeats - 4.0%
FRANCE: SCs - 14.48±5.04, Wins - 60.0%, Survives - 40.0%, Defeats - 0.0%
GERMANY: SCs - 11.48±6.42, Wins - 40.0%, Survives - 56.0%, Defeats - 4.0%
ITALY: SCs - 13.28±5.86, Wins - 48.0%, Survives - 52.0%, Defeats - 0.0%
RUSSIA: SCs - 15.04±5.46, Wins - 76.0%, Survives - 24.0%, Defeats - 0.0%
TURKEY: SCs - 15.76±3.6, Wins - 64.0%, Survives - 36.0%, Defeats - 0.0%
ALL: SCs - 13.08±6.18, Wins - 51.43%, Survives - 46.29%, Defeats - 2.29%
-------------------------------------------------------------------------

