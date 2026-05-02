#!/usr/bin/env python3
"""NPC Discussion generation for Pixel Werewolf.

Generates personality-driven discussion content for NPCs during the
DAY_DISCUSSION phase, adding narrative depth to the game.

Each NPC has a distinct personality that shapes:
- Template selection (what kind of thing they say)
- Emotional modifiers (how they say it — tone, urgency, hesitation)
- Game event reactivity (responding to deaths, accusations, votes)
"""

from __future__ import annotations

import random
from typing import Optional

from game.game_state import GameState
from game.player import Personality
from game.roles import Role

# ── Discussion templates ──
# Each template is a (zh_str, en_str) tuple
# {p} is replaced with a target player name
# {s} is replaced with the speaker's own name (rare)

TEMPLATES: dict[str, tuple[str, str]] = {
    # ── Sheriff ──
    "sheriff_callout": (
        "我认为{p}很可疑，大家注意他。",
        "I think {p} is suspicious, everyone watch them.",
    ),
    "sheriff_defend": (
        "大家冷静，我是警长，我会找出狼人。",
        "Everyone calm down, I'm the sheriff. I'll find the werewolves.",
    ),
    "sheriff_question": (
        "{p}，你昨晚在哪里？",
        "{p}, where were you last night?",
    ),
    "sheriff_pressure": (
        "{p}，你的发言漏洞太多了，解释一下。",
        "{p}, your story has too many holes. Explain yourself.",
    ),
    "sheriff_order_vote": (
        "大家都投{p}，听我指挥。",
        "Everyone vote {p}, follow my lead.",
    ),
    "sheriff_protect": (
        "{p}是好人，我保他。",
        "{p} is good, I vouch for them.",
    ),
    # ── Seer ──
    "seer_hint_good": (
        "我验了{p}，他是好人。",
        "I checked {p}, they are good.",
    ),
    "seer_hint_bad": (
        "我怀疑{p}有问题，先投他。",
        "I suspect {p} has issues, vote them first.",
    ),
    "seer_vague": (
        "昨晚我得到了重要信息，先不公布。",
        "I got important info last night, not revealing yet.",
    ),
    "seer_claim": (
        "我是预言家，昨晚我查了人。",
        "I'm the Seer. I checked someone last night.",
    ),
    "seer_counterclaim": (
        "{p}在假跳预言家，我是真预言家！",
        "{p} is a fake Seer! I'm the real Seer!",
    ),
    # ── Villager ──
    "villager_random_1": (
        "我觉得{p}很可疑，你们觉得呢？",
        "I find {p} suspicious, what do you think?",
    ),
    "villager_random_2": (
        "昨晚没发生什么特别的事。",
        "Nothing special happened last night.",
    ),
    "villager_random_3": (
        "我没什么信息，跟着警长投票。",
        "I have no info, I'll follow the sheriff.",
    ),
    "villager_random_4": (
        "我们先投{p}吧，看看反应。",
        "Let's vote {p} first and see the reaction.",
    ),
    "villager_afraid": (
        "我不知道该信谁了……",
        "I don't know who to trust anymore...",
    ),
    "villager_confident": (
        "我敢肯定{p}有问题，信我一次。",
        "I'm sure {p} is trouble, trust me on this.",
    ),
    "villager_waffle": (
        "嗯……也可能是我想多了。",
        "Hmm... maybe I'm overthinking it.",
    ),
    # ── Werewolf ──
    "werewolf_blame_good": (
        "我怀疑{p}，他昨晚行为很奇怪。",
        "I suspect {p}, their behavior last night was strange.",
    ),
    "werewolf_blame_other_ww": (
        "大家不要怀疑{p}，他是好人。",
        "Don't suspect {p}, they are good.",
    ),
    "werewolf_act_confused": (
        "我什么都不知道，你们说的都有道理。",
        "I don't know anything, you all make good points.",
    ),
    "werewolf_accuse_seer": (
        "我觉得{p}假跳预言家，先投他。",
        "I think {p} is a fake seer, vote them first.",
    ),
    "werewolf_bandwagon": (
        "对，{p}确实有问题！",
        "Yes, {p} is definitely suspicious!",
    ),
    "werewolf_deflect": (
        "等等，我们是不是该看看{p}？",
        "Wait, shouldn't we be looking at {p}?",
    ),
    "werewolf_fake_hint": (
        "我有内部消息，{p}有问题。",
        "I have inside info, {p} is not clean.",
    ),
    "werewolf_sacrifice": (
        "好吧，如果大家要投，那就投{p}吧。",
        "Fine, if everyone wants to vote, let's vote {p}.",
    ),
    # ── Guard ──
    "guard_hint": (
        "我保护了一个重要的人，不多说了。",
        "I protected someone important, that's all I'll say.",
    ),
    "guard_quiet": (
        "昨晚平安，大家放心。",
        "Last night was peaceful, rest assured.",
    ),
    "guard_warning": (
        "{p}，我会盯着你的。",
        "{p}, I'll be watching you.",
    ),
    "guard_hint_save": (
        "昨晚有人想搞事，但我挡住了。",
        "Someone tried something last night, but I stopped it.",
    ),
    # ── Witch ──
    "witch_hint_save": (
        "昨晚我救了人。",
        "I saved someone last night.",
    ),
    "witch_hint_poison": (
        "我用毒药解决了一个可疑的人。",
        "I poisoned someone suspicious.",
    ),
    "witch_vague": (
        "昨晚的事我不方便说。",
        "I'd rather not talk about last night.",
    ),
    "witch_warning": (
        "别逼我，我有毒药。",
        "Don't push me, I have poison.",
    ),
    "witch_regret": (
        "我可能做了个错误的决定……",
        "I might have made a wrong decision...",
    ),
    # ── Hunter ──
    "hunter_bravado": (
        "我猎人，谁敢投我？",
        "I'm the Hunter, who dares vote me?",
    ),
    "hunter_suspicious": (
        "我觉得{p}有问题，大家注意。",
        "I think {p} is trouble, everyone watch out.",
    ),
    "hunter_threat": (
        "投我的人，我死了也会带走一个。",
        "Vote me and I'll take someone with me.",
    ),
    "hunter_vengeance": (
        "如果我死了，{p}就是我要带走的人。",
        "If I die, {p} is coming with me.",
    ),
    # ── Generic / Reaction ──
    "generic_follow": (
        "我跟着{p}投票。",
        "I'll vote with {p}.",
    ),
    "generic_pass": (
        "过。",
        "Pass.",
    ),
    "generic_accuse": (
        "我怀疑{p}。",
        "I suspect {p}.",
    ),
    "generic_agree": (
        "同意。",
        "Agreed.",
    ),
    "generic_disagree": (
        "我不这么认为。",
        "I don't think so.",
    ),
    "generic_think": (
        "让我想想……",
        "Let me think...",
    ),
    # ── Reaction to deaths ──
    "reaction_shock_death": (
        "天哪，{p}死了……",
        "Oh no, {p} is dead...",
    ),
    "reaction_sad_death": (
        "{p}是个好人，我们会记住他。",
        "{p} was a good person, we'll remember them.",
    ),
    "reaction_suspicious_death": (
        "{p}死了？这很奇怪……",
        "{p} is dead? That's strange...",
    ),
    "reaction_fear": (
        "下一个可能就是我……",
        "I might be next...",
    ),
    "reaction_anger": (
        "谁干的？！一定要找出凶手。",
        "Who did this?! We must find the killer.",
    ),
    # ── Accusation response ──
    "defend_innocent": (
        "冤枉啊，我是好人！",
        "I'm innocent, I'm a good person!",
    ),
    "defend_confident": (
        "你怀疑我？你才可疑。",
        "You suspect ME? You're the suspicious one.",
    ),
    "defend_quiet": (
        "……清者自清。",
        "...innocence speaks for itself.",
    ),
    "defend_plead": (
        "别投我，我真的不是狼。",
        "Don't vote me, I'm really not a wolf.",
    ),
    "defend_counter": (
        "{p}一直在带节奏，大家注意。",
        "{p} has been leading the charge, watch out.",
    ),
}


# ── Template keys that count as accusations ──
_ACCUSATION_KEYS: set[str] = {
    "generic_accuse",
    "sheriff_callout", "sheriff_question", "sheriff_pressure",
    "sheriff_investigate", "sheriff_suspect",
    "seer_vague", "seer_accuse",
    "hunter_suspicious", "hunter_bravado",
    "werewolf_blame", "werewolf_bandwagon",
    "villager_confident", "villager_random_1",
    "defend_counter",
}


def _is_accusation_like(template_key: str) -> bool:
    """Check if a template key sounds like an accusation."""
    # Keys containing 'accuse', 'blame', 'suspect', 'pressure', 'callout' are accusatory
    for part in ("accuse", "blame", "suspect", "callout", "pressure"):
        if part in template_key:
            return True
    return False


# ── Personality-specific speech biases ──
# Each personality favours certain template keywords
PERSONALITY_BIAS: dict[Personality, list[str]] = {
    Personality.PARANOID: [
        "sheriff_callout", "sheriff_question", "generic_accuse",
        "villager_random_1", "reaction_suspicious_death",
        "defend_counter", "sheriff_pressure",
    ],
    Personality.TRUSTING: [
        "villager_random_3", "generic_follow", "sheriff_defend",
        "villager_random_2", "generic_agree", "sheriff_protect",
    ],
    Personality.ANALYTICAL: [
        "villager_random_4", "sheriff_question", "seer_vague",
        "villager_random_1", "generic_think", "villager_waffle",
        "sheriff_pressure",
    ],
    Personality.IMPULSIVE: [
        "villager_random_1", "villager_random_4", "generic_accuse",
        "hunter_bravado", "hunter_suspicious", "werewolf_bandwagon",
        "reaction_anger", "villager_confident",
    ],
    Personality.LOYAL: [
        "sheriff_defend", "villager_random_3", "generic_follow",
        "witch_vague", "guard_quiet", "sheriff_protect",
        "reaction_sad_death",
    ],
    Personality.RANDOM: [
        "villager_random_1", "villager_random_2", "villager_random_3",
        "villager_random_4", "generic_pass", "generic_accuse",
        "generic_agree", "generic_disagree", "generic_think",
        "villager_afraid", "villager_confident",
    ],
}


# ── Role-specific speech preferences ──
ROLE_SPEECH: dict[Role, list[str]] = {
    Role.WEREWOLF: [
        "werewolf_blame_good", "werewolf_blame_other_ww",
        "werewolf_act_confused", "werewolf_accuse_seer",
        "werewolf_bandwagon", "werewolf_deflect", "werewolf_fake_hint",
        "werewolf_sacrifice", "generic_accuse", "villager_random_1",
    ],
    Role.SEER: [
        "seer_hint_good", "seer_hint_bad", "seer_vague",
        "seer_claim", "seer_counterclaim",
        "sheriff_question", "generic_accuse",
    ],
    Role.WITCH: [
        "witch_hint_save", "witch_hint_poison", "witch_vague",
        "witch_warning", "witch_regret",
        "sheriff_question", "guard_quiet",
    ],
    Role.GUARD: [
        "guard_hint", "guard_quiet", "guard_warning", "guard_hint_save",
        "sheriff_defend", "sheriff_question",
    ],
    Role.HUNTER: [
        "hunter_bravado", "hunter_suspicious", "hunter_threat",
        "hunter_vengeance", "generic_accuse", "villager_random_1",
    ],
    Role.VILLAGER: [
        "villager_random_1", "villager_random_2", "villager_random_3",
        "villager_random_4", "villager_afraid", "villager_confident",
        "villager_waffle", "generic_pass", "generic_accuse",
    ],
}


# ── Personality speech quirks ──
# These modify the raw template text to add emotional texture
PERSONALITY_QUIRKS: dict[Personality, dict[str, tuple[str, str]]] = {
    Personality.PARANOID: {
        "prefix": ("等等，", "Wait, "),
        "suffix": ("……你不觉得吗？", "...don't you think?",),
        "hesitation": ("嗯……", "Hmm..."),
    },
    Personality.TRUSTING: {
        "prefix": ("我觉得，", "I feel like "),
        "suffix": ("，我相信大家。", ", I trust everyone."),
        "hesitation": ("嗯……", "Well..."),
    },
    Personality.ANALYTICAL: {
        "prefix": ("根据目前的信息，", "Based on current info, "),
        "suffix": ("，这是我分析的结论。", ", that's my analysis."),
        "hesitation": ("让我分析一下……", "Let me analyze..."),
    },
    Personality.IMPULSIVE: {
        "prefix": ("我直觉告诉我——", "My gut tells me—"),
        "suffix": ("！肯定是这样！", "! It has to be!"),
        "hesitation": ("快说快说，", "Come on, "),
    },
    Personality.LOYAL: {
        "prefix": ("我相信组织，", "I trust the group, "),
        "suffix": ("，我听大家的。", ", I'll go with the group."),
        "hesitation": ("这个……", "Well..."),
    },
    Personality.RANDOM: {
        "prefix": ("哈！", "Ha! "),
        "suffix": ("哦，随便啦。", "Oh, whatever."),
        "hesitation": ("唔……", "Umm..."),
    },
}


# ── Game event context ──
class DiscussionContext:
    """Context about recent game events for contextual dialogue generation."""

    def __init__(self) -> None:
        self.last_night_victim: Optional[int] = None
        self.last_voted_out: Optional[int] = None
        self.accusation_map: dict[int, list[int]] = {}  # target -> [accusers]
        self.recent_events: list[str] = []

    def record_accusation(self, accuser_idx: int, target_idx: int) -> None:
        if target_idx not in self.accusation_map:
            self.accusation_map[target_idx] = []
        self.accusation_map[target_idx].append(accuser_idx)

    def clear(self) -> None:
        self.last_night_victim = None
        self.last_voted_out = None
        self.accusation_map.clear()
        self.recent_events.clear()


# Global discussion context — persists across phases
_global_context = DiscussionContext()


def get_context() -> DiscussionContext:
    """Get the shared discussion context."""
    return _global_context


def reset_context() -> None:
    """Reset discussion context at start of a new discussion round."""
    _global_context.clear()


# ── Template categories for contextual selection ──
DEATH_REACTION_KEYS = [
    "reaction_shock_death", "reaction_sad_death",
    "reaction_suspicious_death", "reaction_fear", "reaction_anger",
]
ACCUSED_RESPONSE_KEYS = [
    "defend_innocent", "defend_confident", "defend_quiet",
    "defend_plead", "defend_counter",
]


def _has_sheriff(state: GameState) -> bool:
    """Check if the game has a sheriff."""
    for p in state.players.get_alive_players():
        if p.is_sheriff:
            return True
    return False


def _get_sheriff_idx(state: GameState) -> Optional[int]:
    """Return the index of the current sheriff, if any."""
    for p in state.players.get_alive_players():
        if p.is_sheriff:
            return p.index
    return None


def generate_discussion(state: GameState, speaker_idx: int) -> str:
    """Generate a discussion line for an NPC.

    Takes into account:
    - The speaker's role
    - The speaker's personality (template bias + quirks)
    - Recent game events (who died last night, who was just voted out)
    - Whether the speaker has been accused
    - The current game phase (day discussion vs voting)

    Args:
        state: The current game state.
        speaker_idx: Index of the NPC speaking.

    Returns:
        A formatted discussion string in the active language.
    """
    speaker = state.players.get_player(speaker_idx)
    if not speaker or not speaker.alive:
        return ""

    role = speaker.role
    personality = speaker.personality
    from game.text import LANG
    is_zh = LANG == "zh"

    # ── Context-aware template selection ──
    template_key = _choose_contextual_template(
        state, speaker_idx, role, personality
    )

    # ── Pick a target player ──
    target_idx = _pick_target(state, speaker_idx, role, template_key)
    target_name = _get_player_name(state, target_idx, speaker_idx)

    # ── Format the template ─-
    template_data = TEMPLATES.get(template_key, TEMPLATES["generic_pass"])
    template_str = template_data[0] if is_zh else template_data[1]
    result = template_str.replace("{p}", target_name)

    # ── Auto-record accusation if this is an accusatory template ──
    if target_idx is not None and target_idx != speaker_idx:
        ctx = _global_context
        # Accusation templates include: generic_accuse, sheriff_* (accusatory variants),
        # villager_* (accusatory variants), and wolf accusation templates
        if template_key in _ACCUSATION_KEYS or _is_accusation_like(template_key):
            ctx.record_accusation(speaker_idx, target_idx)

    # ── Apply personality quirks (30% chance for minor modification) ──
    result = _apply_personality_quirk(result, personality, is_zh)

    return result


def _choose_contextual_template(
    state: GameState,
    speaker_idx: int,
    role: Role,
    personality: Personality,
) -> str:
    """Choose a template key based on game context.

    Priority order:
    1. Just had a night death → react to death
    2. Speaker was just accused → defend
    3. Sheriff speaking → lead discussion
    4. Role-specific + personality preferences
    """
    ctx = _global_context

    # Priority 1: Someone died last night (first discussion after night)
    if ctx.last_night_victim is not None and random.random() < 0.6:
        return random.choice(DEATH_REACTION_KEYS)

    # Priority 2: Speaker was accused recently
    if speaker_idx in ctx.accusation_map and random.random() < 0.5:
        return random.choice(ACCUSED_RESPONSE_KEYS)

    # Priority 3: Build candidate pool from role + personality
    candidates: list[str] = []

    # Add role-specific templates (higher weight)
    if role in ROLE_SPEECH:
        candidates.extend(ROLE_SPEECH[role])

    # Add personality-biased templates
    if personality in PERSONALITY_BIAS:
        candidates.extend(PERSONALITY_BIAS[personality])

    # Add generic templates for variety
    candidates.extend([
        "generic_follow", "generic_pass", "generic_accuse",
        "generic_agree", "generic_disagree", "generic_think",
    ])

    # If there's a sheriff and we're not the sheriff, occasionally follow
    sheriff_idx = _get_sheriff_idx(state)
    if sheriff_idx is not None and speaker_idx != sheriff_idx:
        if random.random() < 0.15:
            return "generic_follow"

    # Fallback
    if not candidates:
        return "generic_pass"

    return random.choice(candidates)


def _apply_personality_quirk(
    text: str, personality: Personality, is_zh: bool
) -> str:
    """Apply personality-specific speech quirks.

    Adds prefixes, suffixes, or hesitation markers 30% of the time
    to add emotional texture without overwhelming.
    """
    quirks = PERSONALITY_QUIRKS.get(personality)
    if not quirks:
        return text

    # Short templates (≤3 chars in Chinese, ≤4 chars in English) — don't modify
    if (is_zh and len(text) <= 3) or (not is_zh and len(text) <= 4):
        return text

    roll = random.random()

    if roll < 0.10:
        # Add prefix
        prefix_data = quirks.get("prefix", ("", ""))
        prefix = prefix_data[0] if is_zh else prefix_data[1]
        return prefix + text
    elif roll < 0.20:
        # Add suffix
        suffix_data = quirks.get("suffix", ("", ""))
        suffix = suffix_data[0] if is_zh else suffix_data[1]
        return text + suffix
    elif roll < 0.30:
        # Add hesitation at start
        hes_data = quirks.get("hesitation", ("", ""))
        hes = hes_data[0] if is_zh else hes_data[1]
        return hes + text

    # 70% chance: return as-is
    return text


def _pick_target(
    state: GameState, speaker_idx: int, role: Role, template_key: str
) -> Optional[int]:
    """Pick a target player for accusation-style discussion.

    Context-aware: if the template is a defence response, target
    the accuser. If death reaction, target the victim.
    """
    alive = state.players.get_alive_players()
    others = [p for p in alive if p.index != speaker_idx]
    if not others:
        return None

    ctx = _global_context

    # Defence template → target the first accuser
    if template_key in ACCUSED_RESPONSE_KEYS:
        accusers = ctx.accusation_map.get(speaker_idx, [])
        if accusers:
            # Find alive accuser
            alive_accusers = [
                a for a in accusers
                if state.players.get_player(a)
                and state.players.get_player(a).alive
            ]
            if alive_accusers:
                return random.choice(alive_accusers)

    # Death reaction → target the victim (for sympathy/anger)
    if template_key in DEATH_REACTION_KEYS:
        if ctx.last_night_victim is not None:
            victim = state.players.get_player(ctx.last_night_victim)
            if victim:
                return ctx.last_night_victim

    # Werewolves: prefer accusing non-wolves or protecting fellow wolves
    if role == Role.WEREWOLF:
        non_ww = [p for p in others if p.role != Role.WEREWOLF]
        if non_ww and random.random() < 0.7:
            return random.choice(non_ww).index
        return random.choice(others).index

    return random.choice(others).index


def _get_player_name(
    state: GameState, target_idx: Optional[int], speaker_idx: int
) -> str:
    """Get a display name for the target player."""
    if target_idx is None:
        alive = state.players.get_alive_players()
        others = [p for p in alive if p.index != speaker_idx]
        if others:
            return random.choice(others).name
        return "..."

    p = state.players.get_player(target_idx)
    if p:
        return p.name
    return str(target_idx)


def record_accusation(accuser_idx: int, target_idx: int) -> None:
    """Record that accuser_idx accused target_idx.

    Called by the game loop when a player votes or speaks against another.
    """
    _global_context.record_accusation(accuser_idx, target_idx)


def set_night_victim(victim_idx: int) -> None:
    """Record who died last night for contextual reactions."""
    _global_context.last_night_victim = victim_idx


def set_voted_out(voted_idx: int) -> None:
    """Record who was voted out for contextual reactions."""
    _global_context.last_voted_out = voted_idx
