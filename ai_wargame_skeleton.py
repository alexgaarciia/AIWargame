# Import necessary libraries
from __future__ import annotations
import argparse
import copy
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from time import sleep
from typing import Tuple, TypeVar, Type, Iterable, ClassVar, List
import random
import requests
import sys

# maximum and minimum values for our heuristic scores (usually represents an end of game condition)
MAX_HEURISTIC_SCORE = 2000000000
MIN_HEURISTIC_SCORE = -2000000000

fileprint = None


class FileOutput:
    def __init__(self, file_name):
        self.file = open(file_name, 'w')
        self.stdout = sys.stdout
        sys.stdout = self
        self.suppress_output = False  # New flag to control output

    def write(self, text):
        if not self.suppress_output:
            self.file.write(text)
            self.stdout.write(text)

    def flush(self):
        if not self.suppress_output:
            self.file.flush()
            self.stdout.flush()

    def close(self):
        sys.stdout = self.stdout
        self.file.close()


class UnitType(Enum):
    """Every unit type."""
    AI = 0
    Tech = 1
    Virus = 2
    Program = 3
    Firewall = 4


class Player(Enum):
    """The 2 players."""
    Attacker = 0
    Defender = 1

    def next(self) -> Player:
        """The next (other) player."""
        if self is Player.Attacker:
            return Player.Defender
        else:
            return Player.Attacker


class GameType(Enum):
    AttackerVsDefender = 0
    AttackerVsComp = 1
    CompVsDefender = 2
    CompVsComp = 3


##############################################################################################################

@dataclass(slots=True)
class Unit:
    player: Player = Player.Attacker
    type: UnitType = UnitType.Program
    health: int = 9
    # class variable: damage table for units (based on the unit type constants in order)
    damage_table: ClassVar[list[list[int]]] = [
        [3, 3, 3, 3, 1],  # AI
        [1, 1, 6, 1, 1],  # Tech
        [9, 6, 1, 6, 1],  # Virus
        [3, 3, 3, 3, 1],  # Program
        [1, 1, 1, 1, 1],  # Firewall
    ]
    # class variable: repair table for units (based on the unit type constants in order)
    repair_table: ClassVar[list[list[int]]] = [
        [0, 1, 1, 0, 0],  # AI
        [3, 0, 0, 3, 3],  # Tech
        [0, 0, 0, 0, 0],  # Virus
        [0, 0, 0, 0, 0],  # Program
        [0, 0, 0, 0, 0],  # Firewall
    ]

    def is_alive(self) -> bool:
        """Are we alive ?"""
        return self.health > 0

    def mod_health(self, health_delta: int):
        """Modify this unit's health by delta amount."""
        self.health += health_delta
        if self.health < 0:
            self.health = 0
        elif self.health > 9:
            self.health = 9

    def to_string(self) -> str:
        """Text representation of this unit."""
        p = self.player.name.lower()[0]
        t = self.type.name.upper()[0]
        return f"{p}{t}{self.health}"

    def __str__(self) -> str:
        """Text representation of this unit."""
        return self.to_string()

    def damage_amount(self, target: Unit) -> int:
        """How much can this unit damage another unit."""
        amount = self.damage_table[self.type.value][target.type.value]
        if target.health - amount < 0:
            return target.health
        return amount

    def repair_amount(self, target: Unit) -> int:
        """How much can this unit repair another unit."""
        amount = self.repair_table[self.type.value][target.type.value]
        if target.health + amount > 9:
            return 9 - target.health
        return amount


##############################################################################################################

@dataclass(slots=True)
class Coord:
    """Representation of a game cell coordinate (row, col)."""
    row: int = 0
    col: int = 0

    def col_string(self) -> str:
        """Text representation of this Coord's column."""
        coord_char = '?'
        if self.col < 16:
            coord_char = "0123456789abcdef"[self.col]
        return str(coord_char)

    def row_string(self) -> str:
        """Text representation of this Coord's row."""
        coord_char = '?'
        if self.row < 26:
            coord_char = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[self.row]
        return str(coord_char)

    def to_string(self) -> str:
        """Text representation of this Coord."""
        return self.row_string() + self.col_string()

    def __str__(self) -> str:
        """Text representation of this Coord."""
        return self.to_string()

    def clone(self) -> Coord:
        """Clone a Coord."""
        return copy.copy(self)

    def iter_range(self, dist: int) -> Iterable[Coord]:
        """Iterates over Coords inside a rectangle centered on our Coord."""
        for row in range(self.row - dist, self.row + 1 + dist):
            for col in range(self.col - dist, self.col + 1 + dist):
                yield Coord(row, col)

    def iter_adjacent(self) -> Iterable[Coord]:
        """Iterates over adjacent Coords."""
        yield Coord(self.row - 1, self.col)
        yield Coord(self.row, self.col - 1)
        yield Coord(self.row + 1, self.col)
        yield Coord(self.row, self.col + 1)

    @classmethod
    def from_string(cls, s: str) -> Coord | None:
        """Create a Coord from a string. ex: D2."""
        s = s.strip()
        for sep in " ,.:;-_":
            s = s.replace(sep, "")
        if len(s) == 2:
            coord = Coord()
            coord.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[0:1].upper())
            coord.col = "0123456789abcdef".find(s[1:2].lower())
            return coord
        else:
            return None


##############################################################################################################

@dataclass(slots=True)
class CoordPair:
    """Representation of a game move or a rectangular area via 2 Coords."""
    src: Coord = field(default_factory=Coord)
    dst: Coord = field(default_factory=Coord)

    def to_string(self) -> str:
        """Text representation of a CoordPair."""
        return self.src.to_string() + " " + self.dst.to_string()

    def __str__(self) -> str:
        """Text representation of a CoordPair."""
        return self.to_string()

    def clone(self) -> CoordPair:
        """Clones a CoordPair."""
        return copy.deepcopy(self)

    def iter_rectangle(self) -> Iterable[Coord]:
        """Iterates over cells of a rectangular area."""
        for row in range(self.src.row, self.dst.row + 1):
            for col in range(self.src.col, self.dst.col + 1):
                yield Coord(row, col)

    @classmethod
    def from_quad(cls, row0: int, col0: int, row1: int, col1: int) -> CoordPair:
        """Create a CoordPair from 4 integers."""
        return CoordPair(Coord(row0, col0), Coord(row1, col1))

    @classmethod
    def from_dim(cls, dim: int) -> CoordPair:
        """Create a CoordPair based on a dim-sized rectangle."""
        return CoordPair(Coord(0, 0), Coord(dim - 1, dim - 1))

    @classmethod
    def from_string(cls, s: str) -> CoordPair | None:
        """Create a CoordPair from a string. ex: A3 B2"""
        s = s.strip()
        for sep in " ,.:;-_":
            s = s.replace(sep, "")
        if len(s) == 4:
            coords = CoordPair()
            coords.src.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[0:1].upper())
            coords.src.col = "0123456789abcdef".find(s[1:2].lower())
            coords.dst.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[2:3].upper())
            coords.dst.col = "0123456789abcdef".find(s[3:4].lower())
            return coords
        else:
            return None


##############################################################################################################

@dataclass(slots=True)
class Options:
    """Representation of the game options."""
    dim: int = 5
    max_depth: int | None = 4
    min_depth: int | None = 2
    max_time: float | None = 5.0
    game_type: GameType = GameType.CompVsComp
    alpha_beta: bool = True
    max_turns: int | None = 100
    randomize_moves: bool = False
    broker: str | None = None
    heuristic: int | None = 0


##############################################################################################################

@dataclass(slots=True)
class Stats:
    """Representation of the global game statistics."""
    evaluations_per_depth: dict[int, int] = field(default_factory=dict)
    total_seconds: float = 0.0


##############################################################################################################

@dataclass(slots=True)
class Game:
    """Representation of the game state."""
    board: list[list[Unit | None]] = field(default_factory=list)
    next_player: Player = Player.Attacker
    turns_played: int = 0
    options: Options = field(default_factory=Options)
    stats: Stats = field(default_factory=Stats)
    _attacker_has_ai: bool = True
    _defender_has_ai: bool = True

    def __post_init__(self):
        """Automatically called after class init to set up the default board state."""
        dim = self.options.dim
        self.board = [[None for _ in range(dim)] for _ in range(dim)]
        md = dim - 1
        self.set(Coord(0, 0), Unit(player=Player.Defender, type=UnitType.AI))
        self.set(Coord(1, 0), Unit(player=Player.Defender, type=UnitType.Tech))
        self.set(Coord(0, 1), Unit(player=Player.Defender, type=UnitType.Tech))
        self.set(Coord(2, 0), Unit(player=Player.Defender, type=UnitType.Firewall))
        self.set(Coord(0, 2), Unit(player=Player.Defender, type=UnitType.Firewall))
        self.set(Coord(1, 1), Unit(player=Player.Defender, type=UnitType.Program))
        self.set(Coord(md, md), Unit(player=Player.Attacker, type=UnitType.AI))
        self.set(Coord(md - 1, md), Unit(player=Player.Attacker, type=UnitType.Virus))
        self.set(Coord(md, md - 1), Unit(player=Player.Attacker, type=UnitType.Virus))
        self.set(Coord(md - 2, md), Unit(player=Player.Attacker, type=UnitType.Program))
        self.set(Coord(md, md - 2), Unit(player=Player.Attacker, type=UnitType.Program))
        self.set(Coord(md - 1, md - 1), Unit(player=Player.Attacker, type=UnitType.Firewall))

    def clone(self) -> Game:
        """Make a new copy of a game for minimax recursion.

        Shallow copy of everything except the board (options and stats are shared).
        """
        new = copy.deepcopy(self)
        return new

    def is_empty(self, coord: Coord) -> bool:
        """Check if contents of a board cell of the game at Coord is empty (must be valid coord)."""
        return self.board[coord.row][coord.col] is None

    def get(self, coord: Coord) -> Unit | None:
        """Get contents of a board cell of the game at Coord."""
        if self.is_valid_coord(coord):
            return self.board[coord.row][coord.col]
        else:
            return None

    def set(self, coord: Coord, unit: Unit | None):
        """Set contents of a board cell of the game at Coord."""
        if self.is_valid_coord(coord):
            self.board[coord.row][coord.col] = unit

    def remove_dead(self, coord: Coord):
        """Remove unit at Coord if dead."""
        unit = self.get(coord)
        if unit is not None and not unit.is_alive():
            self.set(coord, None)
            if unit.type == UnitType.AI:
                if unit.player == Player.Attacker:
                    self._attacker_has_ai = False
                else:
                    self._defender_has_ai = False

    def mod_health(self, coord: Coord, health_delta: int):
        """Modify health of unit at Coord (positive or negative delta)."""
        target = self.get(coord)
        if target is not None:
            target.mod_health(health_delta)
            self.remove_dead(coord)

    def check_attacker_moves(self, coords: CoordPair):
        """This is a function to check that the attacker's AI, Firewall and Program can only go up or left"""
        if ((coords.src.col - coords.dst.col) == 1 and (coords.src.row == coords.dst.row) or (
                coords.src.row - coords.dst.row) == 1 and (coords.src.col == coords.dst.col)) or (
                coords.src == coords.dst):
            return True
        else:
            print("Warning: You cannot move the Attacker's AI, Firewall and Program down or right")
            return False

    def check_defender_moves(self, coords: CoordPair):
        """This is a function to check that the defender's AI, Firewall and Program can only go down or right"""
        if ((coords.dst.col - coords.src.col == 1) and (coords.dst.row == coords.src.row)) or (
                (coords.dst.row - coords.src.row == 1) and (coords.dst.col == coords.src.col)) or (
                coords.src == coords.dst):
            return True
        else:
            print("Warning: You cannot move the Defender's AI, Firewall and Program up or left")
            return False

    def all_other_conditions(self, coords: CoordPair):
        src_unit = self.get(coords.src)
        dst_unit = self.get(coords.dst)

        if dst_unit is None:
            """ movement conditions --only out of combat for A F P --only 'outwards' for A F P """
            match src_unit.type:
                case UnitType.Virus:
                    return True
                case UnitType.Tech:
                    return True
                case _:
                    """ check outwards, check combat """
                    if src_unit.player == Player.Attacker:
                        if self.check_attacker_moves(coords):
                            for adjacent in coords.src.iter_adjacent():
                                if self.get(adjacent) is not None and self.get(adjacent).player != src_unit.player:
                                    print(
                                        f"Unit locked in Combat, cannot move! {src_unit.to_string()} at {coords.src.to_string()}\n")
                                    return False
                            return True
                        else:
                            return False
                    elif self.check_defender_moves(coords):
                        for adjacent in coords.src.iter_adjacent():
                            if self.get(adjacent) is not None and self.get(adjacent).player != src_unit.player:
                                print(f"Unit locked in Combat, cannot move! {src_unit.to_string()} at {coords.src.to_string()}\n")
                                return False
                        return True
                    else:
                        return False

        if src_unit.player != dst_unit.player:
            """ attack conditions """
            return True
        if src_unit.player == dst_unit.player:
            """ repair conditions --unit.repair_table != 0 && health < 9 """
            if dst_unit.health < 9 and src_unit.repair_amount(dst_unit) != 0:
                return True
            else:
                print(
                    f"Invalid Healing target! from {src_unit.to_string()} to {dst_unit.to_string()} at {coords.dst.to_string()}\n")
        return False

    def is_valid_move(self, coords: CoordPair) -> bool:
        """Validate a move expressed as a CoordPair."""
        # TODO debug fully to make sure this never returns wrong
        unit = self.get(coords.src)
        if unit is None or unit.player != self.next_player:
            print("empty source or enemy unit selected\n")
            return False

        if not self.is_valid_coord(coords.src) or not self.is_valid_coord(coords.dst):
            print(f"coordinates out of bounds {coords.to_string()}\n")
            return False
        elif not (abs(coords.dst.row - coords.src.row) == 1 and abs(coords.dst.col - coords.src.col) == 1):
            """Valid move distance"""
            if coords.dst == coords.src:
                """self destruct"""
                return True
            if not self.all_other_conditions(coords):
                return False
        else:
            print("non specific Invalid move")
            return False
        return True

    def perform_move(self, coords: CoordPair) -> Tuple[bool, str]:
        """Validate and perform a move expressed as a CoordPair."""
        # Definition of general variables:
        source = self.get(coords.src)
        destination = self.get(coords.dst)

        # Check if the current player is the computer based on the game type:
        is_current_player_comp = (
                (self.options.game_type == GameType.AttackerVsComp and self.next_player == Player.Defender) or
                (self.options.game_type == GameType.CompVsDefender and self.next_player == Player.Attacker) or
                (self.options.game_type == GameType.CompVsComp)
        )

        if not self.is_valid_move(coords):
            if is_current_player_comp:
                print(f"AI made invalid move : {coords.to_string()} killing {self.next_player}")
                self.kill_current_player_AI()
            return False, "Player made an invalid move"

        # Conditions to perform damage in attack or heal pieces:
        # If destination is not empty and the destination unit is not yours: damage.
        if destination is not None and source.player != destination.player:
            # First compute how much damage each piece performs on each other.
            resulting_damage_att = source.damage_amount(destination)
            resulting_damage_def = destination.damage_amount(source)

            # Then perform damage:
            source.mod_health(-resulting_damage_att)
            destination.mod_health(-resulting_damage_def)

            # After performing moves, remove possible dead pieces:
            self.remove_dead(coords.src)
            self.remove_dead(coords.dst)

        # If the unit at destination is in your team or destination is empty:
        else:
            # If destination is empty (and the source unit is yours): move.
            if destination is None:
                self.set(coords.dst, self.get(coords.src))  # put in destination the unit in the source coordinates.
                self.set(coords.src, None)  # remove from source the unit.

            # If the destination is not empty and the destination cell = source cell: auto-destruct.
            elif destination is not None and coords.src == coords.dst:
                # Iterate over the adjacent coordinates, get its element and remove 2 points then kill the source:
                for blast in coords.src.iter_range(1):
                    if self.get(blast) is not None:
                        self.get(blast).mod_health(-2)
                source.mod_health(-9)
                self.remove_dead(coords.src)

            # If destination is not empty and the destination unit is yours: heal.
            else:
                # Heal destination.
                healing_amount = source.repair_amount(destination)

                # Necessary condition to check if you cannot heal (two options: either the unit is fully healed or you cannot heal it).
                if healing_amount == 0:
                    return False, "Invalid move: you cannot repair a fully healed unit or you don't have healing power"
                else:
                    destination.mod_health(healing_amount)

        # Conditional statement to end the game if an AI makes an invalid movement (still does not work):

        return True, str(coords)

    def kill_current_player_AI(self):
        for (src, unit) in self.player_units(self.next_player):
            if unit.type == UnitType.AI:
                unit.mod_health(-9)
                self.remove_dead(src)

    def next_turn(self):
        """Transitions game to the next turn."""
        self.next_player = self.next_player.next()
        self.turns_played += 1

    def to_string(self) -> str:
        """Pretty text representation of the game."""
        dim = self.options.dim
        output = ""
        output += f"Next player: {self.next_player.name}\n"
        output += f"Turns played: {self.turns_played}\n"
        coord = Coord()
        output += "\n   "
        for col in range(dim):
            coord.col = col
            label = coord.col_string()
            output += f"{label:^3} "
        output += "\n"
        for row in range(dim):
            coord.row = row
            label = coord.row_string()
            output += f"{label}: "
            for col in range(dim):
                coord.col = col
                unit = self.get(coord)
                if unit is None:
                    output += " .  "
                else:
                    output += f"{str(unit):^3} "
            output += "\n"
        return output

    def __str__(self) -> str:
        """Default string representation of a game."""
        return self.to_string()

    def is_valid_coord(self, coord: Coord) -> bool:
        """Check if a Coord is valid within out board dimensions."""
        dim = self.options.dim
        if coord.row < 0 or coord.row >= dim or coord.col < 0 or coord.col >= dim:
            return False
        return True

    def read_move(self) -> CoordPair:
        """Read a move from keyboard and return as a CoordPair."""
        while True:
            s = input(F'Player {self.next_player.name}, enter your move: ')
            coords = CoordPair.from_string(s)
            if coords is not None and self.is_valid_coord(coords.src) and self.is_valid_coord(coords.dst):
                print(f'{coords}\n')
                return coords
            else:
                print('Invalid coordinates! Try again.')

    def human_turn(self):
        """Human player plays a move (or get via broker)."""
        if self.options.broker is not None:
            print("Getting next move with auto-retry from game broker...")
            while True:
                mv = self.get_move_from_broker()
                if mv is not None:
                    (success, result) = self.perform_move(mv)
                    print(f"Broker {self.next_player.name}: ", end='')
                    print(result)
                    if success:
                        self.next_turn()
                        break
                sleep(0.1)
        else:
            while True:
                mv = self.read_move()
                (success, result) = self.perform_move(mv)
                if success:
                    print(f"Player {self.next_player.name}: ", end='')
                    print(result)
                    self.next_turn()
                    break
                else:
                    print(result)

    def computer_turn(self) -> CoordPair | None:
        """Computer plays a move."""
        mv = self.suggest_move()
        if mv is not None:
            (success, result) = self.perform_move(mv)
            if success:
                print(f"Computer {self.next_player.name}: ", end='')
                print(result)
                self.next_turn()
        return mv

    def player_units(self, player: Player) -> Iterable[Tuple[Coord, Unit]]:
        """Iterates over all units belonging to a player."""
        for coord in CoordPair.from_dim(self.options.dim).iter_rectangle():
            unit = self.get(coord)
            if unit is not None and unit.player == player:
                yield coord, unit

    def is_finished(self) -> bool:
        """Check if the game is over."""
        return self.has_winner() is not None

    def has_winner(self) -> Player | None:
        """Check if the game is over and returns winner"""
        # There was an error in this first if-else statement. There was self.turns_played >= self.options.max_turns,
        # but if the defender decided to auto-destruct in the last round, he would be the winner. That is why
        # we added to the condition "and self._defender_has_ai".
        if self.options.max_turns is not None and self.turns_played >= self.options.max_turns and self._defender_has_ai:
            return Player.Defender
        elif self._attacker_has_ai:
            if self._defender_has_ai:
                return None
            else:
                return Player.Attacker
        elif self._defender_has_ai:
            return Player.Defender

    def move_candidates(self) -> Iterable[CoordPair]:
        """Generate valid move candidates for the next player."""
        move = CoordPair()
        for (src, _) in self.player_units(self.next_player):
            move.src = src
            for dst in src.iter_adjacent():
                move.dst = dst
                if self.is_valid_move(move):
                    yield move.clone()
            move.dst = src
            yield move.clone()

    def random_move(self) -> Tuple[float, CoordPair | None]:
        """Returns a random move."""
        move_candidates = list(self.move_candidates())
        random.shuffle(move_candidates)
        if len(move_candidates) > 0:
            return 0, move_candidates[0]
        else:
            return 0, None

    def chosen_heuristic(self):
        heuristic = self.e0()
        if self.options.heuristic == 1:
            heuristic = self.e1()
        elif self.options.heuristic == 2:
            heuristic = self.e2()
        return heuristic

    def e0(self) -> float:
        count = [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0]]
        # unit count, health sum get counted in the table in relation to their enum value
        for i in range(self.options.dim):
            for j in range(self.options.dim):
                if self.board[i][j] is not None:
                    count[self.board[i][j].player.value][self.board[i][j].type.value] += 1

        heuristic = float(((3 * sum(count[0][1:5]) + 9999 * count[0][0]) - (
                            3 * sum(count[1][1:5]) + 9999 * count[1][0])
                           ) * (-1 if self.next_player.value == 1 else 1))
        return heuristic

    def e1(self) -> float:
        w1, w2, w3, w4, w5 = 10000, 1, 10, 2, 2  # Adjustable Weights
        count = [[(0, 0), (0, 0), (0, 0), (0, 0), (0, 0)], [(0, 0), (0, 0), (0, 0), (0, 0), (0, 0)]]
        # unit count, health sum get counted in the table in relation to their enum value
        for i in range(self.options.dim):
            for j in range(self.options.dim):
                if self.board[i][j] is not None:
                    # using tuple zip unpacking to do element wise addition
                    count[self.board[i][j].player.value][self.board[i][j].type.value] = tuple(
                        a + b for a, b in zip(
                            count[self.board[i][j].player.value][self.board[i][j].type.value],
                            (1, self.board[i][j].health)
                        ))

        ai_health = (count[0][0][1] - count[1][0][1])
        total_health = (sum(unit[1] for unit in count[0]) - sum(unit[1] for unit in count[1]))
        total_units = (sum(unit[0] for unit in count[0]) - sum(unit[0] for unit in count[1]))

        # Initialize damage potential for both players
        player0_damage_potential = 0
        player1_damage_potential = 0

        # Loop through to calculate damage potential
        for unit_type in range(len(count[0])):
            avg_damage = sum(Unit.damage_table[unit_type]) / len(Unit.damage_table[unit_type])
            player0_damage_potential += count[0][unit_type][0] * avg_damage
            player1_damage_potential += count[1][unit_type][0] * avg_damage
        damage_potential = (player0_damage_potential - player1_damage_potential)

        # Initialize damage potential for both players
        player0_repair_potential = 0
        player1_repair_potential = 0

        # Loop through to calculate damage potential
        for unit_type in range(len(count[0])):
            avg_repair = sum(Unit.repair_table[unit_type]) / len(Unit.repair_table[unit_type])
            player0_repair_potential += count[0][unit_type][0] * avg_repair
            player1_repair_potential += count[1][unit_type][0] * avg_repair
        repair_potential = (player0_repair_potential - player1_repair_potential)

        heuristic = float(((w1 * ai_health) + (w2 * total_health) + (w3 * total_units) + (w4 * damage_potential) + (
                w5 * repair_potential)) * (-1 if self.next_player.value == 1 else 1))
        return heuristic

    def e2(self):
        return 0

    def minimax(self, depth=0, maximizing=True) -> Tuple[float | None, CoordPair | None]:
        heuristic_to_use = self.chosen_heuristic()
        if self.has_winner() is not None or depth >= self.options.max_depth:
            return heuristic_to_use, None

        # TODO: USE LAMBDA expression of heuristics to  map to e1, 2, or 3 based on options!!!
        best_move = None
        all_moves = self.move_candidates()
        children: List[tuple[float, CoordPair | None]] = []
        if maximizing:
            children.append((float('-inf'), best_move))
            for move in all_moves:
                new_game = self.clone()
                new_game.perform_move(move.clone())
                new_game.next_turn()
                neweval, _ = new_game.minimax(depth + 1, not maximizing)
                children.append((-neweval, move))  # I think it had to be inverted here because this is the score from the perspective of the other player that just returned
            best_move = max(children, key=lambda x: x[0])
            return best_move
        else:
            children.append((float('inf'), best_move))
            for move in all_moves:
                new_game = self.clone()
                new_game.perform_move(move.clone())
                new_game.next_turn()
                neweval, _ = new_game.minimax(depth + 1, not maximizing)
                children.append((-neweval, move))
            best_move = min(children, key=lambda x: x[0])
            return best_move

    def minimax_with_alpha_beta(self, alpha=float('-inf'), beta=float('inf'), depth=0, maximizing=True) -> Tuple[float, CoordPair | None]:
        heuristic_to_use = self.chosen_heuristic()
        if self.has_winner() is not None or depth >= self.options.max_depth:
            return heuristic_to_use, None
        # TODO: USE LAMBDA expression of heuristics to  map to e1, 2, or 3 based on options!!!

        best_move = None
        all_moves = self.move_candidates()

        if maximizing:
            max_eval = float('-inf')
            for move in all_moves:
                new_game = self.clone()
                new_game.perform_move(move)
                new_game.next_turn()
                neweval, _ = new_game.minimax_with_alpha_beta(depth + 1, alpha, beta, False)
                neweval = -neweval
                # needs an undo move part I think
                max_eval = max(max_eval, neweval)
                if max_eval == neweval:
                    best_move = move.clone()
                alpha = max(alpha, neweval)
                if beta <= alpha:
                    break
            return max_eval, best_move
        else:
            min_eval = float('inf')
            for move in all_moves:
                new_game = self.clone()
                new_game.perform_move(move)
                new_game.next_turn()
                neweval, _ = new_game.minimax_with_alpha_beta(depth + 1, alpha, beta, True)
                neweval = -neweval
                # needs an undo move part I think
                min_eval = min(min_eval, neweval)
                if min_eval == neweval:
                    best_move = move.clone()
                beta = min(beta, neweval)
                if beta <= alpha:
                    break
            return min_eval, best_move

    def suggest_move(self) -> CoordPair | None:
        """Suggest the next move using minimax alpha beta. TODO: REPLACE RANDOM_MOVE WITH PROPER GAME LOGIC!!!"""
        start_time = datetime.now()
        fileprint.suppress_output = True
        fileprint.suppress_output = True
        if self.options.alpha_beta:
            (score, move) = self.minimax_with_alpha_beta()
        else:
            (score, move) = self.minimax()
        fileprint.suppress_output = False
        # reverting invalid move killing from minimax because only board is deepcopied in the game not the other member variables
        elapsed_seconds = (datetime.now() - start_time).total_seconds()
        self.stats.total_seconds += elapsed_seconds
        print(f"Heuristic score: {score:.2f} for move: {move}")
        for k in sorted(self.stats.evaluations_per_depth.keys()):
            print(f"{k}:{self.stats.evaluations_per_depth[k]} ", end='')
        print()
        total_evals = sum(self.stats.evaluations_per_depth.values())
        print("Cumulative evaluations: ", total_evals)
        for k in sorted(self.stats.evaluations_per_depth.keys()):
            print(f"% of cumulative evaluations per depth: {k}:{self.stats.evaluations_per_depth[k]/total_evals*100} ", end='')
        print()

        print("Branching factor: ", total_evals/len(self.stats.evaluations_per_depth))

        if self.stats.total_seconds > 0:
            print(f"Eval perf.: {total_evals / self.stats.total_seconds / 1000:0.1f}k/s")
        print(f"Elapsed time: {elapsed_seconds:0.1f}s")
        return move

    def post_move_to_broker(self, move: CoordPair):
        """Send a move to the game broker."""
        if self.options.broker is None:
            return
        data = {
            "from": {"row": move.src.row, "col": move.src.col},
            "to": {"row": move.dst.row, "col": move.dst.col},
            "turn": self.turns_played
        }
        try:
            r = requests.post(self.options.broker, json=data)
            if r.status_code == 200 and r.json()['success'] and r.json()['data'] == data:
                # print(f"Sent move to broker: {move}")
                pass
            else:
                print(f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            print(f"Broker error: {error}")

    def get_move_from_broker(self) -> CoordPair | None:
        """Get a move from the game broker."""
        if self.options.broker is None:
            return None
        headers = {'Accept': 'application/json'}
        try:
            r = requests.get(self.options.broker, headers=headers)
            if r.status_code == 200 and r.json()['success']:
                data = r.json()['data']
                if data is not None:
                    if data['turn'] == self.turns_played + 1:
                        move = CoordPair(
                            Coord(data['from']['row'], data['from']['col']),
                            Coord(data['to']['row'], data['to']['col'])
                        )
                        print(f"Got move from broker: {move}")
                        return move
                    else:
                        # print("Got broker data for wrong turn.")
                        # print(f"Wanted {self.turns_played+1}, got {data['turn']}")
                        pass
                else:
                    # print("Got no data from broker")
                    pass
            else:
                print(f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            print(f"Broker error: {error}")
        return None


##############################################################################################################

def main():
    # parse command line arguments
    parser = argparse.ArgumentParser(
        prog='ai_wargame',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--heuristic', type=int, help='heuristic mode')
    parser.add_argument('--max_depth', type=int, help='maximum search depth')
    parser.add_argument('--max_time', type=float, help='maximum search time')
    parser.add_argument('--max_turns', type=float, help='maximum number of turns before game ends')
    parser.add_argument('--alpha_beta', type=str, default="True", help='if True alpha-beta is on; otherwise minimax is on')
    parser.add_argument('--game_type', type=str, default="auto", help='game type: auto|attacker|defender|manual')
    parser.add_argument('--broker', type=str, help='play via a game broker')
    args = parser.parse_args()

    # parse the game type
    if args.game_type == "attacker":
        game_type = GameType.AttackerVsComp
    elif args.game_type == "defender":
        game_type = GameType.CompVsDefender
    elif args.game_type == "manual":
        game_type = GameType.AttackerVsDefender
    else:
        game_type = GameType.CompVsComp

    # set up game options
    options = Options(game_type=game_type)

    # override class defaults via command line options
    if args.heuristic is not None:
        options.heuristic = args.heuristic
    if args.max_depth is not None:
        options.max_depth = args.max_depth
    if args.max_time is not None:
        options.max_time = args.max_time
    if args.max_turns is not None:
        options.max_turns = args.max_turns
    if args.broker is not None:
        options.broker = args.broker
    if args.alpha_beta == "True":
        options.alpha_beta = True
    if args.alpha_beta == "False":
        options.alpha_beta = False

    # Create file that stores the output:
    global fileprint
    fileprint = FileOutput(f'gameTrace-{options.alpha_beta}-{options.max_time}-{options.max_turns}.txt')

    # Append the game parameters:
    print("Game Parameters:")
    print(f"\tMaximum number of turns: {options.max_turns}")
    print(f"\tPlayer mode: {options.game_type.name}")
    if args.game_type != "manual":
        print(f"\tTimeout (in seconds): {options.max_time}")
        print(f"\tAlpha-beta: {options.alpha_beta}")
        print(f"\tChosen heuristic: {options.heuristic}")
    print("\n")

    # Create a new game:
    game = Game(options=options)

    # the main game loop
    while True:
        print()
        print(game)

        winner = game.has_winner()
        if winner is not None:
            print(f"{winner.name} wins!")
            break
        if game.options.game_type == GameType.AttackerVsDefender:
            game.human_turn()
        elif game.options.game_type == GameType.AttackerVsComp and game.next_player == Player.Attacker:
            game.human_turn()
        elif game.options.game_type == GameType.CompVsDefender and game.next_player == Player.Defender:
            game.human_turn()
        else:
            player = game.next_player
            move = game.computer_turn()
            if move is not None:
                game.post_move_to_broker(move)
            else:
                print("Computer doesn't know what to do!!!")
                exit(1)
    fileprint.close()


##############################################################################################################
if __name__ == '__main__':
    main()
