"""Player data model and player manager."""

from __future__ import annotations

from enum import Enum
from typing import Optional
from dataclasses import dataclass, field
from game.roles import Role, Team


class Personality(Enum):
    """NPC personality traits that affect decision-making."""
    PARANOID = "paranoid"      # Suspicious of everyone, votes for high-risk targets
    TRUSTING = "trusting"       # Follows sheriff / consensus
    ANALYTICAL = "analytical"   # Spreads votes, avoids bandwagons
    IMPULSIVE = "impulsive"     # Random votes, high variance
    LOYAL = "loyal"             # Always votes with the pack
    RANDOM = "random"           # Truly random — picks any valid target


@dataclass
class Player:
    """A single player in the game."""
    index: int
    role: Role
    name: str = ""
    name_en: str = ""
    alive: bool = True
    is_sheriff: bool = False
    protected: bool = False  # True if guarded this night
    poisoned: bool = False  # True if poisoned by witch
    voted_by: list[int] = field(default_factory=list)  # player indices who voted for this player
    personality: Personality = Personality.RANDOM

    @property
    def idx(self) -> int:
        """Alias for .index for legacy compatibility."""
        return self.index

    @property
    def is_human(self) -> bool:
        """Whether this player is human-controlled (default: index 0)."""
        return self.index == 0

    @property
    def display_name(self) -> str:
        """Return the localized display name based on current LANGUAGE setting."""
        from game.text import LANG
        if LANG == "en" and self.name_en:
            return self.name_en
        return self.name

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "name": self.display_name,
            "role": self.role.value[0],
            "team": self.role.team.value,
            "alive": self.alive,
            "is_sheriff": self.is_sheriff,
            "personality": self.personality.value,
        }


class PlayerManager:
    """Manages all players in the game."""

    def __init__(self, roles: list[Role]):
        self.players: list[Player] = []
        self._assign_roles(roles)

    def _assign_roles(self, roles: list[Role]) -> None:
        """Assign roles and random personalities to players."""
        import random
        shuffled = list(roles)
        random.shuffle(shuffled)
        names_en = [
            "Alice", "Bob", "Charlie", "Diana",
            "Eve", "Frank", "Grace", "Henry",
            "Ivy", "Jack", "Kate", "Leo",
        ]
        names_zh = [
            "小明", "阿花", "阿福", "小红",
            "小美", "大壮", "阿强", "小丽",
            "老王", "阿杰", "安妮", "老李",
        ]
        personalities = list(Personality)
        for i, role in enumerate(shuffled):
            pers = random.choice(personalities)
            self.players.append(Player(index=i, name=names_zh[i], name_en=names_en[i], role=role, personality=pers))

    def get_alive_players(self) -> list[Player]:
        return [p for p in self.players if p.alive]

    def get_dead_players(self) -> list[Player]:
        return [p for p in self.players if not p.alive]

    def get_player(self, index: int) -> Optional[Player]:
        if 0 <= index < len(self.players):
            return self.players[index]
        return None

    def get_players_by_role(self, role: Role) -> list[Player]:
        return [p for p in self.players if p.role == role]

    def get_team_players(self, team: Team) -> list[Player]:
        return [p for p in self.players if p.role.team == team and p.alive]

    def get_werewolf_players(self) -> list[Player]:
        return self.get_team_players(Team.WEREWOLF)

    def kill_player(self, index: int) -> None:
        player = self.get_player(index)
        if player and player.alive:
            player.alive = False


    def is_game_over(self) -> bool:
        """Check win/loss conditions using 屠边 (kill-all-of-one-type) rule.

        Returns True if the game has ended, False otherwise.
        Village wins: all werewolves dead.
        Werewolves win: all villagers (普通村民) dead OR all special roles (神职) dead.
        """
        alive_wolves = len(self.get_team_players(Team.WEREWOLF))
        if alive_wolves == 0:
            return True  # Village wins

        # 屠边 rule: werewolves win if all villagers OR all special roles are dead
        alive_villagers = len([p for p in self.players if p.alive and p.role == Role.VILLAGER])
        special_roles = {Role.SEER, Role.WITCH, Role.HUNTER, Role.GUARD}
        alive_special = len([p for p in self.players if p.alive and p.role in special_roles])

        if alive_villagers == 0 or alive_special == 0:
            return True  # Werewolves win (屠边)
        return False

    def get_winning_team(self) -> Optional[str]:
        """Return the winning team name or None if game not over.

        Uses 屠边 rule: werewolves win if all villagers OR all special roles are dead.
        Village wins if all werewolves are dead.
        """
        alive_wolves = len(self.get_team_players(Team.WEREWOLF))
        if alive_wolves == 0:
            return "village"

        # 屠边: kill all villagers or all special roles
        alive_villagers = len([p for p in self.players if p.alive and p.role == Role.VILLAGER])
        special_roles = {Role.SEER, Role.WITCH, Role.HUNTER, Role.GUARD}
        alive_special = len([p for p in self.players if p.alive and p.role in special_roles])

        if alive_villagers == 0 or alive_special == 0:
            return "werewolf"
        return None

    def get_alive_count_by_team(self) -> dict:
        return {
            "village": len(self.get_team_players(Team.VILLAGE)),
            "werewolf": len(self.get_team_players(Team.WEREWOLF)),
        }

    def to_dict(self) -> dict:
        return {
            "players": [p.to_dict() for p in self.players],
            "alive_count": len(self.get_alive_players()),
            "alive_by_team": self.get_alive_count_by_team(),
        }
