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
- Done in Pycharm, but works for any other Python IDE
  
# Project D1 - Human vs Human mode
- Detection of ilegal actions (diagonals, destinations out of the board, moving the opponent's units, escaping when engaged in combat, possible directions depending on the unit type, ...)
- Attacking rules implemented: Attacks are only allowed to adjacent, adversarial units; attacks are bidirectional and health ranges between 0 and 9.
- Repairing rules implemented: Repairings are only allowed to adjacent, friendly units; each unit has their own repairing power (depending on the unit they want to repair).
- Self-destruct: Any unit can kill itself and penalize the health of its adjacents (including diagonals) in 2 points.
- Health constraints: If health gets to 0, the unit is deleted from board. Health cannot be above 9.
- Input parameters: Number of maximum turns.
