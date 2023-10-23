# AI Wargame

## Subject: COMP472 Artificial Intelligence
#### Teacher: Leila Kosseim

## Team Members
- Alejandro Leonardo García Navarro - [alexgaarciia](https://github.com/alexgaarciia)
- Lucía Cordero Sánchez - [lucia-corsan](https://github.com/lucia-corsan)
- Simon Dunand - [SquintyG33Rs](https://github.com/SquintyG33Rs)

## URL to the repository (private)
- [https://github.com/alexgaarciia/AIWargame](https://github.com/alexgaarciia/AIWargame)  
  
## Languages and software
- Language used; Python
- Using PiPy interpreter
- Requires the "Request" package
- Done in Pycharm, but works for any other Python IDE
- "grapher.py" requires external Graphvis libraries https://graphviz.org/
  
# Project D1 - Human vs Human mode
- Detection of ilegal actions (diagonals, destinations out of the board, moving the opponent's units, escaping when engaged in combat, possible directions depending on the unit type, ...).
- Attacking rules implemented: Attacks are only allowed to adjacent, adversarial units; attacks are bidirectional and health ranges between 0 and 9.
- Repairing rules implemented: Repairings are only allowed to adjacent, friendly units; each unit has their own repairing power (depending on the unit they want to repair).
- Self-destruct: Any unit can kill itself and penalize the health of its adjacents (including diagonals) in 2 points.
- Health constraints: If health gets to 0, the unit is deleted from board. Health cannot be above 9
- Input parameters: Number of maximum turns.

# Project D2 - Human vs COMP & COMP vs COMP modes
- Implementation of three heuristics for minimax and alpha-beta optimization:
  1. **e0**: Required heuristic in the instructions.
  2. **e1**: Considers the difference in health of both AIs, total health, total units, damage and repair potential.
  3. **e2**: Considers damage potential, repair potential, number of turns, weighted branching factor and AI's health.
     *Note*: All the heuristics consider whether we are maximizing or minimizing at that level of the tree.
- Heuristics as an parameter from Options.
- Implementation of Minimax algorithm.
- Implementation of Minimax with Alpha-Beta pruning algorithm.
- "suggest_move" method.
- Creation of game statistics to measure the quality of our solution: evaluations per depth, elapsed seconds, cumulative evaluations, branching factor, % of cumulative evaluations per depth, ...
