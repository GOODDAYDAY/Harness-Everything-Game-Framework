"""Player data model and player manager."""

from __future__ import annotations

from typing import Optional
from dataclasses import dataclass, field
from game.roles import Role, Team


@dataclass
class Player:
    """A single player in the game."""
    index: int
    name: str
    role: Role
    alive: bool = True
    is_sheriff: bool = False
    protected: bool = False  # True if guarded this night
    poisoned: bool = False  # True if poisoned by witch
    voted_by: list[int] = field(default_factory=list)  # player indices who voted for this player

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "name": self.name,
            "role": self.role.value[0],
            "team": self.role.team.value,
            "alive": self.alive,
            "is_sheriff": self.is_sheriff,
        }


class PlayerManager:
    """Manages all players in the game."""

    def __init__(self, roles: list[Role]):
        self.players: list[Player] = []
        self._town_crier_won: bool = False
        self._assign_roles(roles)

    def _assign_roles(self, roles: list[Role]) -> None:
        """Assign roles to players. For now, sequential assignment.
        In a real game, roles would be assigned randomly.
        """
        import random
        shuffled = list(roles)
        random.shuffle(shuffled)
        names = [
            "Alice", "Bob", "Charlie", "Diana",
            "Eve", "Frank", "Grace", "Henry",
            "Ivy", "Jack", "Kate", "Leo",
        ]
        for i, role in enumerate(shuffled):
            self.players.append(Player(index=i, name=names[i], role=role))

    def get_alive_players(self) -> list[Player]:
        return [p for p in self.players if p.alive]

    def get_dead_players(self) -> list[Player]:
        return [p for p in self.players if not p.alive]

    def get_player(self, index: int) -> Optional[Player]:
        if 0 <= index < len(self.players):
            return self.players[index]
        return None

    def get_team_players(self, team: Team) -> list[Player]:
        return [p for p in self.players if p.role.team == team and p.alive]

    def get_werewolf_players(self) -> list[Player]:
        return self.get_team_players(Team.WEREWOLF)

    def kill_player(self, index: int) -> None:
        player = self.get_player(index)
        if player and player.alive:
            player.alive = False

    @property
    def town_crier_won(self) -> bool:
        """Check if the Town Crier (independent) has achieved their win condition.
        The Town Crier wins if they were voted out during a day phase.
        This is set by game state when a town crier is eliminated by vote."""
        return self._town_crier_won

    def set_town_crier_won(self) -> None:
        self._town_crier_won = True

    def is_game_over(self) -> bool:
        """Check win/loss conditions."""
        # Town Crier independent win takes priority
        if self._town_crier_won:
            return True
        alive_village = len(self.get_team_players(Team.VILLAGE))
        alive_wolves = len(self.get_team_players(Team.WEREWOLF))
        # Werewolves win if they equal or outnumber village
        if alive_wolves == 0:
            return True  # Village wins
        if alive_wolves >= alive_village:
            return True  # Werewolves win
        return False

    def get_winning_team(self) -> Optional[str]:
        """Return the winning team name or None if game not over."""
        if self._town_crier_won:
            return "town_crier"
        alive_village = len(self.get_team_players(Team.VILLAGE))
        alive_wolves = len(self.get_team_players(Team.WEREWOLF))
        if alive_wolves == 0:
            return "village"
        if alive_wolves >= alive_village:
            return "werewolf"
        return None

    def get_alive_count_by_team(self) -> dict:
        return {
            "village": len(self.get_team_players(Team.VILLAGE)),
            "werewolf": len(self.get_team_players(Team.WEREWOLF)),
            "independent": len(self.get_team_players(Team.INDEPENDENT)),
        }

    def to_dict(self) -> dict:
        return {
            "players": [p.to_dict() for p in self.players],
            "alive_count": len(self.get_alive_players()),
            "alive_by_team": self.get_alive_count_by_team(),
        }
