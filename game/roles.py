"""Werewolf role definitions and role assignments."""

from __future__ import annotations
from enum import Enum


class Team(Enum):
    """Faction alignment."""
    VILLAGE = "village"
    WEREWOLF = "werewolf"


class Role(Enum):
    """All playable roles in a 12-player standard werewolf game."""
    # Village team
    VILLAGER = ("villager", Team.VILLAGE, "No special ability — vote during the day.")
    SEER = ("seer", Team.VILLAGE, "Each night, investigate one player's true identity.")
    WITCH = ("witch", Team.VILLAGE, "Has one healing potion and one poison potion.")
    HUNTER = ("hunter", Team.VILLAGE, "If eliminated, can shoot one player.")
    GUARD = ("guard", Team.VILLAGE, "Each night, protect one player from werewolf attack.")
    # Werewolf team
    WEREWOLF = ("werewolf", Team.WEREWOLF, "Each night, kill one player together.")


    def __init__(self, name_zh: str, team: Team, description: str):
        self.name_zh = name_zh
        self.team = team
        self.description = description

    @property
    def is_werewolf_team(self) -> bool:
        return self.team == Team.WEREWOLF

    @property
    def is_village_team(self) -> bool:
        return self.team == Team.VILLAGE


# Standard 12-player role distribution
ROSTER_12_PLAYER: list[Role] = [
    Role.VILLAGER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER,  # 4 villagers
    Role.SEER,       # 1 seer
    Role.WITCH,      # 1 witch
    Role.HUNTER,     # 1 hunter
    Role.GUARD,      # 1 guard
    Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF,  # 4 werewolves
]
