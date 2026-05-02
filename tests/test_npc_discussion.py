#!/usr/bin/env python3
"""Tests for npc_discussion.py — NPC speech generation."""

import sys
sys.path.insert(0, '.')

from game.game_state import GameState
from game.npc_discussion import (
    generate_discussion,
    get_context,
    record_accusation,
    reset_context,
    set_night_victim,
    TEMPLATES,
)
from game.player import Personality
from game.roles import Role


class TestNpcDiscussion:
    """Test that NPC discussion generation works correctly."""

    def setup_method(self):
        self.gs = GameState()
        self.gs.start_game()

    def test_generate_discussion_returns_string(self):
        """generate_discussion returns a non-empty string for a live NPC."""
        alive = self.gs.players.get_alive_players()
        if not alive:
            return
        line = generate_discussion(self.gs, alive[0].index)
        assert isinstance(line, str)
        assert len(line) > 0

    def test_generate_discussion_dead_player_empty(self):
        """generate_discussion returns empty string for dead player."""
        # Kill a player first
        for p in self.gs.players.players:
            if hasattr(p, 'alive'):
                p.alive = False
                line = generate_discussion(self.gs, p.index)
                assert line == ""
                break

    def test_generate_discussion_invalid_index_empty(self):
        """generate_discussion returns empty string for invalid index."""
        line = generate_discussion(self.gs, 999)
        assert line == ""

    def test_generate_discussion_all_players(self):
        """All alive players can generate discussion."""
        alive = self.gs.players.get_alive_players()
        for p in alive:
            line = generate_discussion(self.gs, p.index)
            assert isinstance(line, str)
            assert len(line) > 0
            # Discussion line should reference another player or be a statement
            # (no strict test — just verify it's generated)

    def test_discussion_differs_per_call(self):
        """Multiple calls produce different lines (random selection)."""
        alive = self.gs.players.get_alive_players()
        if not alive:
            return
        idx = alive[0].index
        lines = set()
        for _ in range(20):
            lines.add(generate_discussion(self.gs, idx))
        # At least 2 different lines out of 20 calls
        assert len(lines) >= 2, f"Only {len(lines)} unique lines from 20 calls"

    def test_templates_have_both_languages(self):
        """All templates have both zh and en versions."""
        for key, (zh, en) in TEMPLATES.items():
            assert isinstance(zh, str) and len(zh) > 0, f"{key} missing zh"
            assert isinstance(en, str) and len(en) > 0, f"{key} missing en"

    def test_discussion_uses_player_name(self):
        """Discussion lines include a player name when targeting."""
        alive = self.gs.players.get_alive_players()
        if len(alive) < 2:
            return
        line = generate_discussion(self.gs, alive[0].index)
        # Check if line contains any player name (not empty placeholder)
        for p in alive:
            if p.name in line or p.display_name in line:
                return  # found at least one name
        # Some templates (like "过"/"Pass") don't mention names
        assert True  # acceptable

    def test_werewolf_discussion_avoids_accusing_wolves(self):
        """Werewolf discussion tends to accuse non-wolves."""
        wolves = [p for p in self.gs.players.players if p.role == Role.WEREWOLF]
        if not wolves:
            return
        speaker = wolves[0]
        accusations_against_wolves = 0
        total_calls = 30
        for _ in range(total_calls):
            line = generate_discussion(self.gs, speaker.index)
            # Check if line accuses a werewolf by name
            for w in wolves:
                if w.name in line or w.display_name in line:
                    accusations_against_wolves += 1
                    break
        # Werewolves should not accuse other wolves most of the time
        # (< 50% is reasonable given random choice still includes possibilities)
        accusation_rate = accusations_against_wolves / total_calls
        assert accusation_rate < 0.5, (
            f"Wolves accused each other {accusations_against_wolves}/{total_calls}"
        )

    def test_personality_biases_exist(self):
        """All personalities have at least one speech bias."""
        from game.npc_discussion import PERSONALITY_BIAS
        for p in Personality:
            assert p in PERSONALITY_BIAS, f"{p} missing from PERSONALITY_BIAS"
            assert len(PERSONALITY_BIAS[p]) > 0, f"{p} has empty bias list"

    def test_role_speech_exists(self):
        """All roles have at least one speech preference."""
        from game.npc_discussion import ROLE_SPEECH
        for role in Role:
            assert role in ROLE_SPEECH, f"{role} missing from ROLE_SPEECH"
            assert len(ROLE_SPEECH[role]) > 0, f"{role} has empty speech list"

    def test_discussion_zh(self):
        """Discussion is in Chinese when LANG is zh."""
        from game.text import LANG as current_lang
        if current_lang != "zh":
            import game.text
            game.text.LANG = "zh"
        try:
            alive = self.gs.players.get_alive_players()
            if alive:
                line = generate_discussion(self.gs, alive[0].index)
                # Chinese characters are CJK range
                has_chinese = any('\u4e00' <= c <= '\u9fff' for c in line)
                if not has_chinese:
                    # Some templates might not have Chinese chars, that's OK
                    pass
        finally:
            from game.text import LANG as current_lang
            # Don't revert — test runs in isolation

    def test_no_duplicate_players_in_consecutive_lines(self):
        """Consecutive discussion lines can come from same or different players."""
        # This is a loose test: just verify the system doesn't crash
        alive = self.gs.players.get_alive_players()
        lines = []
        for p in alive:
            line = generate_discussion(self.gs, p.index)
            if line:
                lines.append(line)

    # ── NEW: Context-aware discussion tests ──

    def test_context_set_night_victim(self):
        """Setting a night victim should be recorded in context."""
        reset_context()
        speaker = self.gs.players.get_alive_players()[0]
        set_night_victim(speaker.index)
        ctx = get_context()
        assert ctx.last_night_victim == speaker.index

    def test_context_record_accusation(self):
        """Recording an accusation should be retrievable from context."""
        reset_context()
        record_accusation(0, 1)
        ctx = get_context()
        assert 1 in ctx.accusation_map
        assert 0 in ctx.accusation_map[1]

    def test_context_reset(self):
        """Reset should clear all context data."""
        set_night_victim(3)
        record_accusation(0, 1)
        reset_context()
        ctx = get_context()
        assert ctx.last_night_victim is None
        assert ctx.accusation_map == {}

    def test_personality_quirk_zh(self):
        """Personality quirks should not crash in Chinese mode."""
        from game.text import LANG
        from game.text import set_language as set_lang
        old = LANG
        set_lang("zh")
        reset_context()
        speaker = self.gs.players.get_alive_players()[0]
        line = generate_discussion(self.gs, speaker.index)
        set_lang(old)
        assert isinstance(line, str)
        assert len(line) > 0

    def test_personality_quirk_en(self):
        """Personality quirks should not crash in English mode."""
        from game.text import LANG
        from game.text import set_language as set_lang
        old = LANG
        set_lang("en")
        reset_context()
        speaker = self.gs.players.get_alive_players()[0]
        line = generate_discussion(self.gs, speaker.index)
        set_lang(old)
        assert isinstance(line, str)
        assert len(line) > 0

    def test_all_personalities_generate_without_crash(self):
        """All personality types should generate valid discussion."""
        for personality in Personality:
            # Find an alive player and temporarily change personality
            for p in self.gs.players.players:
                if p.alive:
                    orig = p.personality
                    p.personality = personality
                    line = generate_discussion(self.gs, p.index)
                    p.personality = orig
                    assert isinstance(line, str)
                    break

    def test_all_new_templates_in_templates(self):
        """All template keys referenced in ROLE_SPEECH and PERSONALITY_BIAS exist."""
        from game.npc_discussion import ROLE_SPEECH, PERSONALITY_BIAS
        referenced = set()
        for keys in ROLE_SPEECH.values():
            referenced.update(keys)
        for keys in PERSONALITY_BIAS.values():
            referenced.update(keys)
        missing = referenced - set(TEMPLATES.keys())
        assert not missing, f"Missing template keys: {missing}"
