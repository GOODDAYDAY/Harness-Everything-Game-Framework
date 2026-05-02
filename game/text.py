#!/usr/bin/env python3
"""Multi-language support for Pixel Werewolf.

All user-visible strings are defined here in both Chinese and English.
The active language is controlled by the `LANG` constant ("zh" or "en").
"""

from __future__ import annotations

# Active language: "zh" (Chinese) or "en" (English)
LANG: str = "zh"


def _(key: str, *args, **kwargs) -> str:
    """Look up a string by key and format it with optional args.

    Usage:
        _("game_over")         -> "游戏结束"  (or "Game Over")
        _("day_count", 3)      -> "第 3 天"  (or "Day 3")
    """
    entry = TEXT.get(key)
    if entry is None:
        return key
    val = entry.get(LANG, entry.get("en", key))
    if args or kwargs:
        try:
            return val.format(*args, **kwargs)
        except (KeyError, IndexError):
            return val
    return val


def set_language(lang: str) -> None:
    """Set the active language ("zh" or "en")."""
    global LANG
    if lang in ("zh", "en"):
        LANG = lang


TEXT: dict[str, dict[str, str]] = {
    # ── Game title & menu ──
    "game_title": {"zh": "像素狼人杀", "en": "Pixel Werewolf"},
    "subtitle": {"zh": "秘密之村", "en": "A Village of Secrets"},
    "start_game": {"zh": "开始游戏", "en": "START GAME"},
    "settings": {"zh": "设置", "en": "SETTINGS"},
    "quit": {"zh": "退出", "en": "QUIT"},
    "version_info": {"zh": "v1.0 | 12人局 | 像素艺术", "en": "v1.0  |  12 Players  |  Pixel Art"},
    "how_to_play": {"zh": "白天通过投票淘汰狼人。在狼人找到你之前找到他们。", "en": "Vote during the day to eliminate werewolves. Find them before they find you."},
    "press_to_start": {"zh": "[ 按 ENTER 或点击开始 ]", "en": "[ Press ENTER or click START to begin ]"},
    "click_to_start": {"zh": "[ 点击任意位置开始 ]", "en": "[ Click anywhere to start ]"},

    # ── Role UI ──
    "your_role": {"zh": "你的身份", "en": "Your Role"},
    "team_label": {"zh": "阵营: {}", "en": "Team: {}"},

    # ── Phase indicators ──
    "setup": {"zh": "🔮 准备阶段", "en": "🔮 Setup"},
    "game_over_short": {"zh": "游戏结束", "en": "Game Over"},
    "phase_setup": {"zh": "设置", "en": "Setup"},
    "phase_night_guard": {"zh": "夜晚 — 守卫", "en": "Night — Guard"},
    "phase_night_seer": {"zh": "夜晚 — 预言家", "en": "Night — Seer"},
    "phase_night_werewolf": {"zh": "夜晚 — 狼人", "en": "Night — Werewolves"},
    "phase_night_witch": {"zh": "夜晚 — 女巫", "en": "Night — Witch"},
    "phase_day_announce": {"zh": "白天 — 公告", "en": "Day — Announcement"},
    "phase_day_sheriff": {"zh": "白天 — 警长选举", "en": "Day — Sheriff Election"},
    "phase_day_discussion": {"zh": "白天 — 讨论", "en": "Day — Discussion"},
    "phase_day_vote": {"zh": "白天 — 投票", "en": "Day — Voting"},
    "phase_day_trial": {"zh": "白天 — 辩护", "en": "Day — Defense"},
    "phase_day_pk": {"zh": "白天 — 加票", "en": "Day — Run-off"},
    "phase_day_result": {"zh": "白天 — 结果", "en": "Day — Result"},
    "phase_game_over": {"zh": "游戏结束", "en": "Game Over"},
    "phase_day_prefix": {"zh": "白天", "en": "Day"},
    "phase_night_prefix": {"zh": "夜晚", "en": "Night"},
    "day_count": {"zh": "第 {} 天", "en": "Day {}"},
    "alive_counter": {"zh": "存活: {}/{}", "en": "Alive: {}/{}"},
    "balance_label": {"zh": "狼{}:民{}", "en": "W{}:V{}"},

    # ── Sidebar ──
    "players_header": {"zh": "玩家列表", "en": "Players"},
    "game_log": {"zh": "游戏日志", "en": "Game Log"},
    "unknown_role": {"zh": "???", "en": "???"},
    "you_indicator": {"zh": ">", "en": ">"},

    # ── Sheriff election ──
    "sheriff_nomination_recorded": {"zh": "已提名 — 等待其他人投票...", "en": "Nomination recorded — others voting..."},
    "sheriff_click_to_nominate": {"zh": "点击玩家名字提名警长", "en": "Click a player's name to nominate them for Sheriff"},
    "sheriff_star": {"zh": "[★]", "en": "[★]"},

    # ── Voting ──
    "vote_cast": {"zh": "已投票 — 等待结算...", "en": "Vote cast - awaiting resolution..."},
    "vote_click_player": {"zh": "点击上方玩家名字投出你的票", "en": "Click a villager name above to cast your vote"},
    "vote_count": {"zh": "[{}]", "en": "[{}]"},

    # ── Game over ──
    "game_over": {"zh": "游戏结束 — {} 获胜!", "en": "Game Over - {} wins!"},
    "restart_hint": {"zh": "[ 点击右下角重新开始 ]", "en": "[ Click bottom-right to restart ]"},
    "restart_button": {"zh": "重新开始", "en": "RESTART GAME"},
    "restart_prompt": {"zh": "按 R 重新开始", "en": "Press R to restart"},
    "auto_play_hint": {"zh": "自动进行中 — 观看故事展开...", "en": "Game auto-plays - Watch the story unfold..."},

    # ── Death announcement ──
    "was_killed": {"zh": "在夜晚被杀害了", "en": "was killed during the night"},
    "was_poisoned": {"zh": "被女巫毒杀了", "en": "was poisoned"},
    "they_were": {"zh": "身份是", "en": "They were a"},

    # ── Teams ──
    "team_village": {"zh": "好人阵营", "en": "Village"},
    "team_werewolf": {"zh": "狼人阵营", "en": "Werewolf"},
    "team": {"zh": "阵营", "en": "Team"},
    "village_team": {"zh": "好人阵营", "en": "Village"},
    "werewolf_team": {"zh": "狼人阵营", "en": "Werewolves"},
    "neutral_team": {"zh": "第三方阵营", "en": "Neutral"},

    # ── Role names (already have name_zh/name_en on Role enum, but keep for TEXT pattern) ──
    "role_WEREWOLF": {"zh": "狼人", "en": "Werewolf"},
    "settings_title": {"zh": "设置", "en": "Settings"},
    "settings_language": {"zh": "语言: 中文", "en": "Language: English"},
    "settings_language_zh": {"zh": "切换为英文", "en": "Switch to Chinese"},
    "settings_back": {"zh": "返回主菜单", "en": "Back to Menu"},
    "settings_current_lang": {"zh": "当前语言: 中文", "en": "Current Language: English"},
    "settings_hint": {"zh": "↑↓ 选择  Enter 确认  ESC 返回", "en": "↑↓ Select  Enter Confirm  ESC Back"},
    "role_SEER": {"zh": "预言家", "en": "Seer"},
    "role_WITCH": {"zh": "女巫", "en": "Witch"},
    "role_HUNTER": {"zh": "猎人", "en": "Hunter"},
    "role_GUARD": {"zh": "守卫", "en": "Guard"},
    "role_VILLAGER": {"zh": "村民", "en": "Villager"},

    # ── Night action verbs ──
    "night_kill": {"zh": "击杀", "en": "Kill"},
    "night_save": {"zh": "救活", "en": "Save"},
    "night_poison": {"zh": "毒杀", "en": "Poison"},
    "night_check": {"zh": "查验", "en": "Check"},
    "night_protect": {"zh": "守护", "en": "Guard"},
    "night_skip": {"zh": "跳过", "en": "Skip"},

    # ── Night action UI ──
    "night_wolves_choose": {"zh": "狼人选择目标", "en": "Werewolves choose target"},
    "witch_save_prompt": {"zh": "今晚被杀的玩家是 {}。使用解药吗？", "en": "Player {} was killed tonight. Use antidote?"},
    "witch_save_yes": {"zh": "救活 (Y)", "en": "Save (Y)"},
    "witch_save_no": {"zh": "不救 (N)", "en": "Don't Save (N)"},
    "witch_poison_prompt": {"zh": "使用毒药吗？点击玩家毒杀", "en": "Use poison? Click a player to poison"},
    "witch_poison_skip": {"zh": "不用毒药", "en": "Skip Poison"},
    "seer_check_prompt": {"zh": "点击一名玩家查验身份", "en": "Click a player to check their identity"},
    "guard_protect_prompt": {"zh": "选择今晚要守护的玩家", "en": "Choose a player to protect tonight"},
    "guard_target": {"zh": "🛡 守护目标：{}", "en": "🛡 Guarding: {}"},

    # ── Hunter ──
    "hunter_shot_prompt": {"zh": "你被淘汰了！选择一名玩家带走", "en": "You were eliminated! Choose a player to take with you"},

    # ── Day phase ──
    "morning_report": {"zh": "昨晚 {} 被杀了", "en": "Last night, {} was killed"},
    "peaceful_night": {"zh": "昨晚是平安夜", "en": "Last night was peaceful"},
    "player_died": {"zh": "{} 被淘汰了", "en": "{} was eliminated"},
    "sheriff_elected": {"zh": "{} 成为警长", "en": "{} is now Sheriff"},
    "nobody_sheriff": {"zh": "无人成为警长", "en": "No Sheriff was elected"},

    # ── Vote resolution ──
    "vote_result": {"zh": "{} 被放逐 ({}) 票", "en": "{} was banished with {} votes"},
    "vote_tie": {"zh": "平局 — {}, {} 都需要PK", "en": "Tie — {} and {} need a runoff"},
    "vote_no_one": {"zh": "无人被放逐", "en": "No one was banished"},
    "vote_runoff": {"zh": "⚡ PK轮 — 在 {} 和 {} 之间重新投票", "en": "⚡ Runoff — revote between {} and {}"},
    "vote_runoff_tie": {"zh": "PK仍为平局 — 无人被放逐", "en": "Runoff also tied — no one was banished"},

    # ── Discussion phase ──
    "day_discussion_start_text": {
        "zh": "☀️ 白天讨论开始",
        "en": "☀️ Day discussion begins"
    },

    # ── Log entries ──
    "log_night_start": {"zh": "第 {} 天夜晚开始", "en": "Day {} Night begins"},
    "log_sheriff_nomination": {"zh": "{} 提名 {} 为警长", "en": "{} nominated {} for Sheriff"},
    "log_night_kill": {"zh": "狼人袭击了玩家 {}", "en": "Werewolves attacked Player {}"},

    # ── NPC reaction strings ──
    "npc_reaction_killed": {"zh": "{} 惨叫着倒下了！", "en": "{} screams and falls!"},
    "npc_reaction_no_one_killed": {"zh": "清晨的阳光格外温暖...", "en": "The morning sun feels warm..."},

    # ── Log messages ──
    "log_game_start": {"zh": "游戏开始！第1天夜晚——守卫阶段。", "en": "Game started! Day 1 Night — Guard phase."},
    "log_night_results_announced": {"zh": "第{}天——夜间结果公布。", "en": "Day {} — Night results announced."},
    "log_phase_changed": {"zh": "阶段变更：{}", "en": "Phase changed to {}"},
    "log_pk_phase_changed": {"zh": "PK加赛——阶段变更：{}", "en": "PK Runoff — Phase changed to {}"},
    "log_team_wins": {"zh": "{} 获胜！", "en": "{} wins!"},
    "log_night_begins": {"zh": "第{}天夜晚开始。", "en": "Day {} Night begins."},
    "log_no_sheriff": {"zh": "无人投票。未选出警长。", "en": "No sheriff votes cast. No sheriff elected."},
    "log_sheriff_elected": {"zh": "{}（玩家{}）当选警长！", "en": "{} (Player {}) is elected Sheriff!"},
    "log_sheriff_tie": {"zh": "候选人平票——未选出警长。", "en": "Tie between candidates — no sheriff elected."},
    "log_no_votes": {"zh": "无人投票。无人被放逐。", "en": "No votes cast. No one was eliminated."},
    "log_eliminated_by_vote": {"zh": "{}（玩家{}）被投票放逐。身份是{}。", "en": "{} (Player {}) was eliminated by vote. They were a {}."},
    "log_eliminated_by_pk": {"zh": "{}（玩家{}）在PK中被放逐。身份是{}。", "en": "{} (Player {}) was eliminated by PK vote. They were a {}."},
    "log_hunter_vengeance": {"zh": "{}（猎人）正在发动复仇！", "en": "{} (Hunter) is taking vengeance!"},
    "log_hunter_shot": {"zh": "{}（玩家{}）被猎人的复仇击杀！", "en": "{} (Player {}) was shot by the Hunter's vengeance!"},
    "log_no_hunter_target": {"zh": "猎人没有有效的复仇目标。", "en": "The Hunter has no valid vengeance target."},
    "log_hunter_killed_night": {"zh": "{}（猎人）在夜晚被杀死——发动复仇！", "en": "{} (Hunter) was killed — taking vengeance!"},
    "log_hunter_poisoned": {"zh": "{}（猎人）被毒杀——发动复仇！", "en": "{} (Hunter) was poisoned — taking vengeance!"},
    "log_night_resolved": {"zh": "夜晚结束。遇害者：{}，被救：{}", "en": "Night resolved. Victim: {}, Saved: {}"},

    # ── Phase instructions (used by ui_panels) ──
    "phase_instruction_discussion": {"zh": "💬 讨论时间 —— 交流信息", "en": "💬 Discussion — Share information"},
    "phase_instruction_vote": {"zh": "🗳 投票时间 —— 选择放逐目标", "en": "🗳 Voting — Choose who to banish"},
    "phase_instruction_sheriff": {"zh": "🏛 警长选举 —— 投票选出警长", "en": "🏛 Sheriff Election — Vote for sheriff"},
    "phase_instruction_guard": {"zh": "🛡 守卫请行动 —— 选择守护目标", "en": "🛡 Guard — Choose your target"},
    "phase_instruction_werewolf": {"zh": "🐺 狼人请行动 —— 选择袭击目标", "en": "🐺 Werewolves — Choose your target"},
    "phase_instruction_witch": {"zh": "🧪 女巫请行动 —— 使用解药或毒药", "en": "🧪 Witch — Use heal or poison"},
    "phase_instruction_seer": {"zh": "🔮 预言家请行动 —— 选择查验目标", "en": "🔮 Seer — Choose your target"},
    "phase_instruction_trial": {"zh": "⚖ 最终辩论 —— 被投票者发言辩解", "en": "⚖ Final Trial — The accused speaks"},

    # ── Narration ──
    "narration_day_announce": {"zh": "天亮了，昨晚是平安夜", "en": "Day breaks. A peaceful night."},
    "narration_game_over": {"zh": "游戏结束！", "en": "Game Over!"},
    "narration_generic": {"zh": "发生了某些事情……", "en": "Something happened..."},

    # ── Speaker label ──
    "speaker_label": {"zh": "🎙 玩家 #{}", "en": "🎙 Player #{}"},

    # ── Error / fallback ──
    "error_unknown_phase": {"zh": "未知阶段", "en": "Unknown Phase"},

    # ── Game-over screen ──
    "game_over_sub": {"zh": "—— 点击重新开始 ", "en": "— Click to restart"},
    "game_over_title_village": {"zh": "村民胜利！", "en": "Village Victory!"},
    "game_over_title_werewolf": {"zh": "狼人胜利！", "en": "Werewolf Victory!"},
    "game_over_subtitle_village": {"zh": "所有狼人已被放逐，村庄恢复了和平", "en": "All werewolves have been banished. Peace returns to the village."},
    "game_over_subtitle_werewolf": {"zh": "狼人成功消灭了所有村民，夜色降临", "en": "Werewolves have eliminated all opponents. Darkness falls."},
    "game_over_roles_header": {"zh": "— 角色揭晓 —", "en": "— Role Reveal —"},
    "game_over_click_restart": {"zh": "点击重新开始游戏", "en": "Click to restart"},
    "game_over_team_village": {"zh": "好人阵营 胜利", "en": "Good Team Victory"},
    "game_over_team_wolf": {"zh": "狼人阵营 胜利", "en": "Werewolf Team Victory"},

    # ── Narration / announcement ──
    "announce_header": {"zh": "☀ 死讯公布", "en": "☀ Death Announcement"},
    "game_over_wolf_win": {"zh": "🐺 狼人胜利！", "en": "🐺 Werewolves Win!"},
    "game_over_village_win": {"zh": "🏠 村民胜利！", "en": "🏠 Village Wins!"},
    "game_over_wolf_win_pov": {"zh": "🐺 狼人胜利 —— 干得漂亮！", "en": "🐺 Werewolves Win — Well Hunted!"},
    "werewolf_wins": {"zh": "🐺 狼人胜利！", "en": "🐺 Werewolves Win!"},
    "village_wins": {"zh": "🏠 村民胜利！", "en": "🏠 Village Wins!"},
    "sheriff_election_banner": {"zh": "🏛 警长选举", "en": "🏛 Sheriff Election"},
    "election_banner": {"zh": "🏛 警长选举中", "en": "🏛 Sheriff Election in Progress"},

    # ── Skills / Night abilities ──
    "skill_guard": {"zh": "🛡 守卫 —— 请选择守护目标", "en": "🛡 Guard — Choose a target to protect"},
    "skill_wolves": {"zh": "🐺 狼人 —— 请选择袭击目标", "en": "🐺 Werewolves — Choose a target to attack"},
    "skill_werewolf": {"zh": "🐺 狼人 —— 请选择袭击目标", "en": "🐺 Werewolves — Choose a target to attack"},
    "skill_seer": {"zh": "🔮 预言家 —— 请选择查验目标", "en": "🔮 Seer — Choose a target to investigate"},
    "skill_witch": {"zh": "🧪 女巫 —— 请选择行动", "en": "🧪 Witch — Choose your action"},
    "witch_heal_available": {"zh": "解药可用", "en": "Heal Available"},
    "witch_heal_ready": {"zh": "💚 解药可用", "en": "💚 Heal Available"},
    "witch_heal_used": {"zh": "解药已用", "en": "Heal Used"},
    "witch_poison_available": {"zh": "毒药可用", "en": "Poison Available"},
    "witch_poison_ready": {"zh": "💜 毒药可用", "en": "💜 Poison Available"},
    "witch_poison_used": {"zh": "毒药已用", "en": "Poison Used"},
    "witch_toggle_hint": {"zh": "点击切换解毒/毒杀模式", "en": "Click to toggle heal/poison mode"},

    # ── Wolf vote display ──
    "wolf_vote_header": {"zh": "🐺 狼人投票：", "en": "🐺 Wolf Votes:"},
    "wolf_votes_header": {"zh": "🐺 狼人投票：", "en": "🐺 Wolf Votes:"},
    "wolf_vote_entry": {"zh": "目标 #{} ({} 票)", "en": "Target #{} ({} votes)"},
    "wolf_vote_line": {"zh": "目标 #{} ({} 票)", "en": "Target #{} ({} votes)"},
    "wolf_reveal": {"zh": "🐺 {} 是狼人！", "en": "🐺 {} is a Werewolf!"},

    # ── Discussion ──
    "discussion_speaker": {"zh": "💬 玩家 #{} 发言：", "en": "💬 Player #{} says:"},

    # ── Guard ──
    "guard_no_target": {"zh": "未选择", "en": "None selected"},
    "guard_target_info": {"zh": "🛡 守卫目标: {}", "en": "🛡 Guard Target: {}"},

    # ── Seer ──
    "seer_target": {"zh": "🔮 查验目标：{}", "en": "🔮 Investigating: {}"},
    "seer_result_human": {"zh": "🔮 {} 的身份是：{}！", "en": "🔮 {} is a {}!"},

    # ── Hunter ──
    "hunter_vengeance_info": {"zh": "💀 {} (猎人) 正在选择复仇目标", "en": "💀 {} (Hunter) is taking vengeance"},
    "hunter_vengeance": {"zh": "💀 猎人复仇！", "en": "💀 Hunter's Vengeance!"},

    # ── Spectator ──
    "spectator_mode": {"zh": "👁 观战模式 —— 你已死亡", "en": "👁 Spectator Mode — You are dead"},

    # ── Day banner ──
    "day_banner": {"zh": "☀ 第 {} 天", "en": "☀ Day {}"},

    # ── Vote result ──
    "was_voted_out": {"zh": "被放逐了", "en": "was voted out"},
    "are_tied": {"zh": "平局！需要重投", "en": "are tied! Need runoff"},

    # ── Sheriff result ──
    "sheriff_result_none": {"zh": "无人投票，未选出警长", "en": "No votes — no sheriff elected"},
    "sheriff_result_winner": {"zh": "{} 当选警长！（{} 票）", "en": "{} is Sheriff! ({} votes)"},
    "sheriff_result_tie": {"zh": "平票！{} 与 {} 票数相同", "en": "Tie! {} and {} tied"},
    "sheriff_vote_header": {"zh": "📊 警长选举结果", "en": "📊 Sheriff Election Result"},

    # ── Night narration ──
    "but_was_saved": {"zh": "但被守卫守护了", "en": "but was saved by the guard"},
    "someone_was_attacked": {"zh": "有人昨晚受到了袭击", "en": "Someone was attacked last night"},
    "it_was": {"zh": "是", "en": "It was"},

    # ── Main menu ──
    "tagline": {"zh": "🐺 月圆之夜，谁是人，谁是狼？", "en": "🐺 Under the full moon, who is human, who is wolf?"},
    "footer_tip": {"zh": "按 空格键 开始  |  ESC 返回", "en": "Press SPACE to start  |  ESC to quit"},
    "press_space": {"zh": "按 空格键 继续", "en": "Press SPACE to continue"},
    "quit_prompt": {"zh": "按 Q 退出", "en": "Press Q to quit"},
}
