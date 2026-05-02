# GameFlow — Autoload phase machine for Pixel Werewolf
#
# Drives the werewolf game loop through its granular phases:
# SETUP → NIGHT_GUARD → NIGHT_WEREWOLF → NIGHT_WITCH → NIGHT_SEER
# → DAY_ANNOUNCE → DAY_DISCUSSION → DAY_VOTE → DAY_RESULT → (loop).
#
# Delegates state mutations to GameState; coordinates AI decision-making.
# Does NOT define its own phase_changed/game_over signals — uses GameState's.
extends Node

# Signal emitted when a night action is resolved (for UI feedback).
signal night_action_resolved(actor_name: String, action: String)
signal sheriff_elected(player_index: int)
signal day_discussion_line(player_name: String, message: String)

# Reference to GameState autoload (set in _ready).
var game_state: GameState = null

# Discussion timer state
var _discussion_lines: Array[Dictionary] = []
var _discussion_index: int = 0
var _discussion_in_progress: bool = false
var _discussion_done: bool = false
var _discussion_timer: Timer = null

# Discussion line display delay in seconds.
const DISCUSSION_DELAY: float = 2.5


func _init() -> void:
	_discussion_timer = Timer.new()
	_discussion_timer.name = "DiscussionTimer"
	_discussion_timer.one_shot = true
	_discussion_timer.wait_time = DISCUSSION_DELAY
	_discussion_timer.timeout.connect(_on_discussion_timer_timeout)
	add_child(_discussion_timer)


func _ready() -> void:
	print("[GameFlow] _ready() — looking for /root/GameState...")
	var gs = get_node_or_null("/root/GameState")
	if gs and gs.has_method("setup_game"):
		game_state = gs
	else:
		game_state = null
	print("[GameFlow] _ready() — result: ", game_state)
	if not game_state:
		push_error("GameFlow: Could not find GameState autoload!")
	else:
		print("[GameFlow] Found GameState autoload!")


# ---- Public API ----

## Start a new game: reset state, deal roles, begin at SETUP.
func start_new_game(human_seat: int = -1) -> void:
	if not game_state:
		push_error("GameFlow.start_new_game: game_state is null!")
		return
	game_state.setup_game(human_seat)
	print("[GameFlow] setup_game complete. Players: ", game_state.players.size(), " Phase: ", game_state.current_phase)
	# The first advance_phase call goes from SETUP → DAY_SHERIFF_ELECTION.
	# This returns early if human needs to act (sheriff vote), else continues to NIGHT_GUARD.
	advance_phase()
	print("[GameFlow] advance_phase complete. Phase now: ", game_state.current_phase)


## Advance to the next logical phase based on current state.
func advance_phase() -> void:
	if not game_state:
		return
	
	match game_state.current_phase:
		GameState.Phase.SETUP:
			# Day 1: sheriff election before first night
			_enter_phase(GameState.Phase.DAY_SHERIFF_ELECTION)
		
		GameState.Phase.DAY_SHERIFF_ELECTION:
			_execute_sheriff_election()
			game_state.day_number = 1
			_enter_phase(GameState.Phase.NIGHT_GUARD)
			if _waits_for_human_action():
				return
		
		GameState.Phase.NIGHT_GUARD:
			_execute_guard_action()
			_enter_phase(GameState.Phase.NIGHT_WEREWOLF)
			if _waits_for_human_action():
				return
		
		GameState.Phase.NIGHT_WEREWOLF:
			_execute_werewolf_action()
			_enter_phase(GameState.Phase.NIGHT_WITCH)
			if _waits_for_human_action():
				return
		
		GameState.Phase.NIGHT_WITCH:
			_execute_witch_action()
			_enter_phase(GameState.Phase.NIGHT_SEER)
			if _waits_for_human_action():
				return
		
		GameState.Phase.NIGHT_SEER:
			_execute_seer_action()
			_resolve_night_deaths()
			if _check_game_over():
				return
			_enter_phase(GameState.Phase.DAY_ANNOUNCE)
		
		GameState.Phase.DAY_ANNOUNCE:
			# Emit morning report for each night death before proceeding to discussion.
			var night_deaths: Array = game_state.night_deaths
			if night_deaths.size() > 0:
				var report := "☀️ Morning Report — "
				var names: PackedStringArray = []
				for idx in night_deaths:
					var pd: Dictionary = game_state.get_player(idx)
					var pname: String = pd.get("name", "Unknown")
					var role_name: String = PixelTheme.get_role_name(pd.get("role", 0)) if PixelTheme else "??"
					names.append(pname + " (" + role_name + ")")
				report += "Last night, " + ", ".join(names) + " "
				report += "were found dead." if night_deaths.size() > 1 else "was found dead."
				night_action_resolved.emit("🌅 Dawn", report)
			else:
				night_action_resolved.emit("🌅 Dawn", "The night passed peacefully. No one died.")
			_enter_phase(GameState.Phase.DAY_DISCUSSION)
		
		GameState.Phase.DAY_DISCUSSION:
			# First call: start discussion.  Subsequent calls: fast-forward/skip if in progress.
			if not _discussion_done:
				# Only generate discussion lines the first time we enter this phase.
				_execute_day_discussion()
				if _discussion_in_progress:
					# Discussion just started; mark done so we don't re-enter, then return
					# for timer-based emission to begin.
					_discussion_done = true
					return
				# No lines were generated (very unlikely); mark done and fall through.
				_discussion_done = true
			
			if _discussion_in_progress:
				# Player pressed NEXT during discussion — fast-forward: emit all remaining lines
				_skip_discussion()
			
			# All lines have been emitted (naturally or via skip); proceed to vote
			_discussion_done = false
			_enter_phase(GameState.Phase.DAY_VOTE)
			if _waits_for_human_action():
				return
		
		GameState.Phase.DAY_VOTE:
			_simulate_votes()
			_enter_phase(GameState.Phase.DAY_RESULT)
		
		GameState.Phase.DAY_RESULT:
			_resolve_day_elimination()
			if _check_game_over():
				return
			# Start new night.
			game_state.current_round += 1
			game_state.day_number += 1
			game_state._reset_night_actions()
			_enter_phase(GameState.Phase.NIGHT_GUARD)
			if _waits_for_human_action():
				return
		
		GameState.Phase.GAME_OVER:
			# Restart on next advance.
			start_new_game()


# ---- Human Action Check ----

## Returns true if the current phase requires human input AND the human
## hasn't acted yet. When true, the caller should return early so the UI
## can prompt the player before proceeding.
func _waits_for_human_action() -> bool:
	if not game_state or not game_state.has_method("get_player"):
		return false
	var human_idx: int = game_state.human_player_index
	if human_idx < 0 or human_idx >= 12:
		return false
	var hp: Dictionary = game_state.get_player(human_idx)
	if not hp.get("alive", false):
		return false
	
	var phase: int = game_state.current_phase
	match phase:
		GameState.Phase.NIGHT_GUARD:
			return hp.get("role", -1) == GameState.Role.GUARD
		GameState.Phase.NIGHT_WEREWOLF:
			return hp.get("role", -1) == GameState.Role.WEREWOLF
		GameState.Phase.NIGHT_WITCH:
			return hp.get("role", -1) == GameState.Role.WITCH
		GameState.Phase.NIGHT_SEER:
			return hp.get("role", -1) == GameState.Role.SEER
		GameState.Phase.DAY_SHERIFF_ELECTION:
			# Only sheriff election in progress (round 1)
			return game_state.current_round == 0 and not hp.get("has_voted_sheriff", false)
		GameState.Phase.DAY_VOTE:
			return not hp.get("has_voted_day", false)
		_:
			return false

# ---- AI Night Actions ----

func _execute_guard_action() -> void:
	var guards := game_state.get_players_by_role(GameState.Role.GUARD)
	if guards.is_empty():
		return
	
	var guard_idx: int = guards[0]
	var guard_data := game_state.get_player(guard_idx)
	if not guard_data.get("alive", false):
		return
	
	# If the guard is the human player, read the pre-set target (set by MainUI before advancing).
	if guard_idx == game_state.human_player_index and game_state.guard_target >= 0:
		var target: int = game_state.guard_target
		var guard_target_name: String = game_state.get_player(target).get("name", "Player %d" % (target + 1))
		night_action_resolved.emit(guard_data.get("name", "Guard"), "protect " + guard_target_name)
		return
	
	# Pick a random alive player (can't repeat last target).
	var alive := game_state.get_alive_players()
	var candidates: Array[int] = []
	for idx in alive:
		if idx != game_state.guard_last_target:
			candidates.append(idx)
	
	if not candidates.is_empty():
		var target: int = candidates[randi() % candidates.size()]
		game_state.guard_target = target
		var guard_target_name: String = game_state.get_player(target).get("name", "Player %d" % (target + 1))
		night_action_resolved.emit(guard_data.get("name", "Guard"), "protect " + guard_target_name)


func _execute_werewolf_action() -> void:
	var wolves := game_state.get_players_by_role(GameState.Role.WEREWOLF)
	if wolves.is_empty():
		return
	
	# If the human is a werewolf, use their pre-set target.
	if game_state.human_player_index in wolves and game_state.werewolf_target >= 0:
		var target: int = game_state.werewolf_target
		var wolf_target_name: String = game_state.get_player(target).get("name", "Player %d" % (target + 1))
		night_action_resolved.emit("Werewolves", "kill " + wolf_target_name)
		return
	
	# Werewolves target a random non-werewolf alive player.
	var alive := game_state.get_alive_players()
	var candidates: Array[int] = []
	for idx in alive:
		var pd := game_state.get_player(idx)
		if pd.get("role", GameState.Role.NONE) != GameState.Role.WEREWOLF:
			candidates.append(idx)
	
	if not candidates.is_empty():
		var target: int = _ai_select_target(wolves[0] if wolves.size() > 0 else -1, GameState.Role.WEREWOLF, candidates, true, 2)
		if target < 0:
			target = candidates[randi() % candidates.size()]
		game_state.werewolf_target = target
		var wolf_target_name: String = game_state.get_player(target).get("name", "Player %d" % (target + 1))
		night_action_resolved.emit("Werewolves", "kill " + wolf_target_name)


func _execute_witch_action() -> void:
	var witches := game_state.get_players_by_role(GameState.Role.WITCH)
	if witches.is_empty():
		return
	
	var witch_idx: int = witches[0]
	var witch_data := game_state.get_player(witch_idx)
	if not witch_data.get("alive", false):
		return
	
	var witch_name: String = witch_data.get("name", "Witch")
	
	# ── Witch save ──
	# If the human is the witch, their save choice was already recorded by MainUI
	# during the NIGHT_WITCH_SAVE sub-phase. Read it from game_state.
	if witch_idx == game_state.human_player_index:
		if game_state.witch_save_used and game_state.werewolf_target >= 0:
			# Human chose to save
			game_state.witch_save_target = game_state.werewolf_target
			var saved_name: String = game_state.get_player(game_state.werewolf_target).get("name", "Player %d" % (game_state.werewolf_target + 1))
			night_action_resolved.emit(witch_name, "save " + saved_name)
		# Human save was not used — either skipped or no one was attacked.
		# Proceed to poison handling below (both human and AI reach the poison section).
	else:
		# AI witch save: strategic — always save important roles, sometimes save others.
		if not game_state.witch_save_used and game_state.werewolf_target >= 0:
			var save_chance: float = _compute_save_chance(game_state.werewolf_target)
			if randf() < save_chance:
				game_state.witch_save_used = true
				game_state.witch_save_target = game_state.werewolf_target
				var saved_name: String = game_state.get_player(game_state.werewolf_target).get("name", "Player %d" % (game_state.werewolf_target + 1))
				night_action_resolved.emit(witch_name, "save " + saved_name)
				# After saving, still handle poison below.
	
	# ── Witch poison ──
	# If human is witch, use pre-set target from MainUI.
	if witch_idx == game_state.human_player_index:
		if game_state.witch_poison_used:
			# Human already made choice — poison or skip set by MainUI.
			if game_state.witch_poison_target >= 0:
				var poison_name: String = game_state.get_player(game_state.witch_poison_target).get("name", "Player %d" % (game_state.witch_poison_target + 1))
				night_action_resolved.emit(witch_name, "poison " + poison_name)
		return
	
	# AI witch poison
	if not game_state.witch_poison_used:
		var alive := game_state.get_alive_players()
		var candidates: Array[int] = []
		for idx in alive:
			if idx == witch_idx:
				continue
			# Don't poison the person we just saved
			if game_state.witch_save_used and idx == game_state.witch_save_target:
				continue
			candidates.append(idx)
		
		if not candidates.is_empty() and _ai_should_act(witch_idx, 0.33):
			var target: int = _ai_select_target(witch_idx, GameState.Role.WITCH, candidates, true, 3)
			if target < 0:
				target = candidates[randi() % candidates.size()]
			game_state.witch_poison_used = true
			game_state.witch_poison_target = target
			var poison_name: String = game_state.get_player(target).get("name", "Player %d" % (target + 1))
			night_action_resolved.emit(witch_name, "poison " + poison_name)


## Returns the probability [0, 1] that the witch will save a given role.
func _compute_save_chance(werewolf_target: int) -> float:
	var target_role: GameState.Role = game_state.get_player(werewolf_target).get("role", GameState.Role.NONE)
	match target_role:
		GameState.Role.SEER:    return 0.95
		GameState.Role.HUNTER:  return 0.90
		GameState.Role.GUARD:   return 0.60
		GameState.Role.VILLAGER: return 0.40
	
	return 0.30


func _execute_seer_action() -> void:
	var seers := game_state.get_players_by_role(GameState.Role.SEER)
	if seers.is_empty():
		return
	
	var seer_idx: int = seers[0]
	var seer_data := game_state.get_player(seer_idx)
	if not seer_data.get("alive", false):
		return
	
	# If human is seer, use pre-set target.
	if seer_idx == game_state.human_player_index and game_state.seer_target >= 0:
		var target: int = game_state.seer_target
		var target_data := game_state.get_player(target)
		var target_team: GameState.Team = target_data.get("team", GameState.Team.NONE)
		game_state.seer_last_result = target_team
		var target_name: String = target_data.get("name", "Player %d" % (target + 1))
		var result_text := "GOOD" if target_team == GameState.Team.GOOD else "EVIL"
		night_action_resolved.emit(seer_data.get("name", "Seer"), "check " + target_name + " → " + result_text)
		return
	
	# AI: Pick a random alive player to check.
	var alive := game_state.get_alive_players()
	var candidates: Array[int] = []
	for idx in alive:
		if idx != seer_idx:
			candidates.append(idx)
	
	if not candidates.is_empty():
		var target: int = _ai_select_target(seer_idx, GameState.Role.SEER, candidates, false, 4)
		if target < 0:
			target = candidates[randi() % candidates.size()]
		game_state.seer_target = target
		var target_data := game_state.get_player(target)
		var target_team: GameState.Team = target_data.get("team", GameState.Team.NONE)
		game_state.seer_last_result = target_team
		
		var result_str := "EVIL" if target_team == GameState.Team.EVIL else "GOOD"
		var seer_target_name: String = game_state.get_player(target).get("name", "Player %d" % (target + 1))
		night_action_resolved.emit(seer_data.get("name", "Seer"), "check " + seer_target_name + " = " + result_str)


# ---- Sheriff Election ----

func _execute_sheriff_election() -> void:
	"""Day 1 sheriff election: all alive players are candidates.
	Each player votes; winner becomes sheriff (1.5 vote weight)."""
	var alive := game_state.get_alive_players()
	if alive.is_empty():
		return
	
	# All alive players are candidates
	game_state.sheriff_candidates = alive.duplicate()
	
	# Reset vote counters (use float for 1.5 weight consistency)
	for i in 12:
		var pd := game_state.get_player(i)
		if not pd.is_empty():
			pd["votes_against"] = 0.0
	
	# Each alive player votes for another alive player
	for voter_idx in alive:
		var candidates: Array[int] = alive.duplicate()
		candidates.erase(voter_idx)
		if candidates.is_empty():
			continue
		var target_idx: int = -1
		# Human vote: read pre-set target from MainUI.
		if voter_idx == game_state.human_player_index and game_state.human_vote_target >= 0:
			target_idx = game_state.human_vote_target
			game_state.human_vote_target = -1  # consume it
		else:
			target_idx = _ai_sheriff_vote(voter_idx, candidates)
		if target_idx < 0:
			target_idx = candidates[randi() % candidates.size()]
		var target_data := game_state.get_player(target_idx)
		target_data["votes_against"] = target_data.get("votes_against", 0.0) + 1.0
	
	# Find winner (highest votes, random tiebreaker)
	var max_votes: float = -0.01
	var winners: Array[int] = []
	for idx in alive:
		var v: float = game_state.get_player(idx).get("votes_against", 0.0)
		if v > max_votes + 0.001:
			max_votes = v
			winners = [idx]
		elif abs(v - max_votes) <= 0.001:
			winners.append(idx)
	
	if not winners.is_empty():
		# AI-driven tiebreaker
		var sheriff_winner: int = winners[randi() % winners.size()]  # remaining random — tiebreakers are chaotic
		game_state.sheriff_index = sheriff_winner
		game_state.get_player(sheriff_winner)["is_sheriff"] = true


func _sheriff_death_check(dead_idx: int) -> void:
	"""If the sheriff died, transfer badge to a random alive player."""
	if dead_idx != game_state.sheriff_index:
		return
	
	# Remove sheriff status from dead player
	game_state.get_player(dead_idx)["is_sheriff"] = false
	
	# Transfer to a random alive player
	var alive := game_state.get_alive_players()
	alive.erase(dead_idx)
	if alive.is_empty():
		game_state.sheriff_index = -1
		return
	
	# Pick new sheriff — most leadership-aligned alive player
	var new_sheriff: int = alive[0]
	var best_score: float = -1.0
	for a in alive:
		var p := _get_personality(a)
		var s: float = p.leadership + p.rationality * 0.3
		if s > best_score:
			best_score = s
			new_sheriff = a
	game_state.sheriff_index = new_sheriff
	game_state.get_player(new_sheriff)["is_sheriff"] = true


# ---- Night Resolution ----

func _resolve_night_deaths() -> void:
	"""Compute who dies during the night based on all night actions."""
	game_state.night_deaths.clear()
	
	# Werewolf kill (unless saved by guard or witch).
	var wolf_target: int = game_state.werewolf_target
	var saved: bool = false
	
	# Guard protection blocks werewolf kill (but same-target save+guard = death).
	if wolf_target >= 0:
		if game_state.guard_target == wolf_target:
			# Guarded same target wolves attacked.
			if game_state.witch_save_target == wolf_target:
				# Same target saved AND guarded → still dies (rule: 同守同救).
				saved = false
			else:
				# Guard alone saved them.
				saved = true
		elif game_state.witch_save_target == wolf_target:
			# Witch alone saved them.
			saved = true
		
		if not saved:
			game_state.night_deaths.append(wolf_target)
	
	# Witch poison kills separately.
	if game_state.witch_poison_target >= 0:
		if not game_state.night_deaths.has(game_state.witch_poison_target):
			game_state.night_deaths.append(game_state.witch_poison_target)
	
	# Actually kill the players.
	game_state.hunter_was_poisoned = false
	for idx in game_state.night_deaths:
		game_state.kill_player(idx)
		_sheriff_death_check(idx)
		# Track whether hunter was poisoned (blocks revenge).
		var pd_chk := game_state.get_player(idx)
		if pd_chk.get("role", GameState.Role.NONE) == GameState.Role.HUNTER:
			if idx == game_state.witch_poison_target:
				game_state.hunter_was_poisoned = true
	
	# Hunter revenge: if hunter died at night and was NOT poisoned, shoot someone.
	if not game_state.hunter_was_poisoned:
		for night_dead_idx in game_state.night_deaths:
			var pd := game_state.get_player(night_dead_idx)
			if pd.get("role", GameState.Role.NONE) == GameState.Role.HUNTER:
				_execute_hunter_revenge(night_dead_idx)
				break



# ---- Day Discussion ----

func _execute_day_discussion() -> void:
	"""Generate AI discussion lines based on personality and role.
	Each alive player says something in-character."""
	var alive := game_state.get_alive_players()
	if alive.is_empty():
		return

	# Discussion message templates by role
	var templates: Dictionary = {
		GameState.Role.WEREWOLF: [
			"I think we should look at the quieter players.",
			"Player {suspect} seems suspicious to me.",
			"We need to be careful who we trust.",
			"I'm just a regular villager, I swear!",
			"Let's not rush to conclusions.",
			"We should vote for someone who's been defensive.",
			"I noticed Player {suspect} acting strangely last night.",
		],
		GameState.Role.VILLAGER: [
			"I hope we catch a werewolf today.",
			"We need to work together to find them.",
			"Does anyone have useful information?",
			"I trust the seer will guide us.",
			"Let's think this through logically.",
			"Player {suspect} has been very quiet...",
			"I'm not sure who to vote for yet.",
			"We should listen to everyone before deciding.",
		],
		GameState.Role.SEER: [
			"I have some information, but I can't reveal everything yet.",
			"Trust me, we're on the right track.",
			"I've been watching carefully.",
			"Let's see what people say before I share.",
			"Some players are not what they seem.",
			"Pay attention to who deflects questions.",
		],
		GameState.Role.WITCH: [
			"I have my potions ready.",
			"I'll help when the time is right.",
			"We need to be strategic about this.",
			"Let's not waste our resources.",
			"I've seen things that give me pause.",
		],
		GameState.Role.HUNTER: [
			"If I go down, I'm taking someone with me!",
			"I'm not afraid of those wolves.",
			"Let's hunt some werewolves!",
			"I say we vote now and ask questions later.",
			"Cowards hide — I stand my ground.",
			"Someone's going to regret crossing me.",
		],
		GameState.Role.GUARD: [
			"I'll do my best to protect the village.",
			"We need to keep our important roles safe.",
			"I've got a bad feeling about tonight.",
			"Stay alert, everyone.",
			"Let's be smart about this.",
		],
	}

	# Get suspects for each player (a random alive player of opposite team, if known)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(str(game_state.current_round) + "discussion")

	for player_idx in alive:
		var pd := game_state.get_player(player_idx)
		var role: GameState.Role = pd.get("role", GameState.Role.NONE)
		var name: String = pd.get("name", "Player %d" % (player_idx + 1))
		var pers := _get_personality(player_idx)

		# Pick a suspect for werewolves to deflect onto, or villagers to accuse
		var suspect_idx := player_idx
		var other_alive: Array[int] = []
		for a in alive:
			if a != player_idx:
				other_alive.append(a)
		if not other_alive.is_empty():
			suspect_idx = other_alive[rng.randi() % other_alive.size()]
		var suspect_name: String = game_state.get_player(suspect_idx).get("name", "?")

		# Get templates for this role
		var role_templates: Array = templates.get(role, templates[GameState.Role.VILLAGER])
		var template_idx := rng.randi() % role_templates.size()
		var message: String = role_templates[template_idx]

		# Replace {suspect} placeholder
		message = message.replace("{suspect}", suspect_name)

		# Personality influences message styling
		match pers.get("archetype", "Neutral"):
			"Aggressive", "Deceptive":
				message = message.to_upper() if rng.randf() < 0.3 else message + "!"
			"Cautious", "Passive":
				message = "Um... " + message
			"Paranoid":
				message = message + " I have a bad feeling about this."
			"Leader":
				message = message + " Follow my lead on this."
			"Honest":
				message = message + " I'm being completely honest."

		# Store line for timer-based emission instead of emitting now
		_discussion_lines.append({"name": name, "message": message, "player_idx": player_idx})

	# Start emitting lines one at a time via timer
	if _discussion_lines.is_empty():
		# No lines to show; proceed immediately
		_discussion_in_progress = false
	else:
		_discussion_in_progress = true
		_discussion_index = 0
		# Emit first line immediately, timer handles the rest
		_emit_next_discussion_line()

# ---- Discussion Timer Handler ----

func _on_discussion_timer_timeout() -> void:
	"""Timer callback — emit the next discussion line or finish."""
	if not _discussion_in_progress:
		_discussion_timer.stop()
		return
	
	_emit_next_discussion_line()


func _emit_next_discussion_line() -> void:
	"""Emit the next pending discussion line. If no more lines, end discussion."""
	if _discussion_lines.is_empty() or _discussion_index >= _discussion_lines.size():
		# All lines emitted
		_discussion_timer.stop()
		_discussion_in_progress = false
		_discussion_done = true
		_discussion_lines.clear()
		return
	
	var line: Dictionary = _discussion_lines[_discussion_index]
	_discussion_index += 1
	day_discussion_line.emit(line["name"], line["message"])
	
	# Start the timer for the next line (timer is one_shot=true so it stops after each fire).
	_discussion_timer.start()


func _skip_discussion() -> void:
	"""Fast-forward: emit all remaining discussion lines immediately."""
	_discussion_timer.stop()
	while _discussion_index < _discussion_lines.size():
		var line: Dictionary = _discussion_lines[_discussion_index]
		_discussion_index += 1
		day_discussion_line.emit(line["name"], line["message"])
	_discussion_in_progress = false
	_discussion_done = true
	_discussion_lines.clear()

# ---- Day Resolution ----

func _simulate_votes() -> void:
	"""AI-driven voting: each alive player votes for another alive player.
	Sheriff's vote counts as 1.5 (rounded up to 2 for simple int math)."""
	var alive := game_state.get_alive_players()
	
	# Reset vote counters.
	for i in 12:
		var pd := game_state.get_player(i)
		if not pd.is_empty():
			pd["votes_against"] = 0.0
	
	# Each alive player votes.
	for voter_idx in alive:
		var candidates: Array[int] = alive.duplicate()
		candidates.erase(voter_idx)
		if candidates.is_empty():
			continue
		var target_idx: int = -1
		# Human vote: read pre-set target from MainUI.
		if voter_idx == game_state.human_player_index and game_state.human_vote_target >= 0:
			target_idx = game_state.human_vote_target
			game_state.human_vote_target = -1  # consume it
		else:
			target_idx = _ai_day_vote(voter_idx, candidates)
		if target_idx < 0:
			target_idx = candidates[randi() % candidates.size()]
		var target_data := game_state.get_player(target_idx)
		var weight: float = 1.5 if voter_idx == game_state.sheriff_index else 1.0
		target_data["votes_against"] = target_data.get("votes_against", 0.0) + weight


func _resolve_day_elimination() -> void:
	"""Find the player with the most votes and eliminate them.
	Sheriff's 1.5 vote weight can break ties."""
	var alive := game_state.get_alive_players()
	if alive.is_empty():
		return
	
	var max_votes: float = -0.01
	var eliminated_idx: int = -1
	var tie: bool = false
	
	for idx in alive:
		var pd := game_state.get_player(idx)
		var v: float = pd.get("votes_against", 0.0)
		if v > max_votes + 0.001:  # Float tolerance
			max_votes = v
			eliminated_idx = idx
			tie = false
		elif abs(v - max_votes) <= 0.001:
			tie = true
	
	if max_votes > 0.0 and not tie:
		game_state.day_elimination = eliminated_idx
		var pd := game_state.get_player(eliminated_idx)
		var role: GameState.Role = pd.get("role", GameState.Role.NONE)
		game_state.kill_player(eliminated_idx)
		_sheriff_death_check(eliminated_idx)
		game_state.player_eliminated.emit(eliminated_idx)
		
		# Hunter revenge: if hunter was voted out, they always get to shoot.
		if role == GameState.Role.HUNTER:
			_execute_hunter_revenge(eliminated_idx)


# ---- Hunter Revenge ----

func _execute_hunter_revenge(hunter_idx: int) -> void:
	"""Hunter shoots one random alive player upon being eliminated.
	Caller must ensure the hunter was NOT poisoned by witch."""
	var alive := game_state.get_alive_players()
	# Hunter is already dead, so they won't be in alive. Filter just in case.
	var targets: Array[int] = []
	for idx in alive:
		if idx != hunter_idx:
			targets.append(idx)
	
	if targets.is_empty():
		return  # No one left to shoot (edge case)
	
	var shot_target: int = _ai_hunter_shot(hunter_idx, targets)
	if shot_target < 0:
		shot_target = targets[randi() % targets.size()]
	game_state.kill_player(shot_target)
	_sheriff_death_check(shot_target)
	
	print("Hunter (P%d) shot P%d in revenge!" % [hunter_idx + 1, shot_target + 1])
	# Game might end after hunter's shot.
	_check_game_over()


# ---- AI Personality-Driven Decisions ----

## Returns the personality dict for an AI player, or a default neutral personality.
func _get_personality(player_idx: int) -> Dictionary:
	return game_state.ai_personalities.get(player_idx, {
		"archetype": "Neutral",
		"aggressiveness": 0.30,
		"trust_level": 0.30,
		"rationality": 0.50,
		"leadership": 0.30,
		"suspicion": 0.40,
		"loyalty": 0.50,
	})


## AI selects a target from candidates using personality traits.
## - role: the selector's Role (e.g. GUARD, WEREWOLF, WITCH, HUNTER)
## - candidates: array of player indices to choose from
## - prefer_enemy: if true, prefer candidates on the opposite team
## - avoid_self: if true, remove the actor_idx from candidates (caller should handle)
## - seed_offset: vary this per call site so the same selector gets different randomness
func _ai_select_target(actor_idx: int, role: GameState.Role, candidates: Array[int], prefer_enemy: bool = false, seed_offset: int = 0) -> int:
	if candidates.is_empty():
		return -1
	
	var pers := _get_personality(actor_idx)
	var actor_data := game_state.get_player(actor_idx)
	var actor_team: GameState.Team = actor_data.get("team", GameState.Team.NONE)
	
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(str(actor_idx) + str(game_state.current_round) + str(seed_offset))
	
	# Build score for each candidate.
	var scored: Array[Dictionary] = []  # [{idx, score}]
	for c in candidates:
		var score: float = 0.5
		var cdata := game_state.get_player(c)
		var cteam: GameState.Team = cdata.get("team", GameState.Team.NONE)
		var crole: GameState.Role = cdata.get("role", GameState.Role.NONE)
		
		# Prefer opposite team if prefer_enemy is set
		if prefer_enemy:
			if cteam != actor_team and cteam != GameState.Team.NONE:
				score += 0.30 * pers.aggressiveness
			elif cteam == actor_team:
				score -= 0.40 * pers.loyalty
		else:
			# Prefer same team (for guard/witch protect)
			if cteam == actor_team:
				score += 0.25 * pers.loyalty
		
		# Suspicious players are more likely targets for aggressive AI
		score += pers.suspicion * 0.15 * rng.randf()
		
		# Rational AI avoids the sheriff (sheriff is high-profile)
		if cdata.get("is_sheriff", false):
			score -= 0.10 * pers.rationality
		
		# Low-trust AI more likely to target anyone
		score += (1.0 - pers.trust_level) * 0.20 * rng.randf()
		
		# Deceptive/Aggressive AI gains bonus scoring against known enemies
		if prefer_enemy and cteam != actor_team:
			score += pers.aggressiveness * 0.25
		
		# Random jitter to avoid deterministic choice
		score += rng.randf() * 0.25
		
		scored.append({"idx": c, "score": score})
	
	# Sort by score descending and pick the top (with some randomness at the top)
	scored.sort_custom(func(a, b): return a.score > b.score)
	
	# 70% of the time pick the top choice; 30% pick randomly from top 3
	var pick_from_top: int = 3 if scored.size() >= 3 else scored.size()
	if rng.randf() < 0.70:
		return scored[0].idx
	else:
		return scored[rng.randi() % pick_from_top].idx


## AI decides whether to take an action (binary yes/no) based on personality.
## - chance_base: base probability [0.0, 1.0]
## - actor_idx: the deciding player
func _ai_should_act(actor_idx: int, chance_base: float) -> bool:
	var pers := _get_personality(actor_idx)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(str(actor_idx) + str(game_state.current_round) + "should_act")
	
	# Aggressive AI acts more often; cautious AI less often
	var adjusted: float = chance_base + (pers.aggressiveness - 0.30) * 0.30
	adjusted = clampf(adjusted, 0.05, 0.95)
	return rng.randf() < adjusted


## AI chooses a sheriff vote target based on leadership and role alignment.
## Returns the player index to vote for, or -1 if none.
func _ai_sheriff_vote(voter_idx: int, candidates: Array[int]) -> int:
	if candidates.is_empty():
		return -1
	
	var pers := _get_personality(voter_idx)
	var voter_data := game_state.get_player(voter_idx)
	var voter_team: GameState.Team = voter_data.get("team", GameState.Team.NONE)
	var voter_role: GameState.Role = voter_data.get("role", GameState.Role.NONE)
	
	# Werewolves prefer voting for werewolves (to get a wolf sheriff)
	# Good roles prefer voting for trusted-looking players
	var prefer_same_team: bool = (voter_team == GameState.Team.EVIL)
	
	# High-leadership AI votes for themselves
	if pers.leadership > 0.75 and voter_idx in candidates:
		var rng := RandomNumberGenerator.new()
		rng.seed = hash(str(voter_idx) + "self_vote_sheriff")
		if rng.randf() < pers.leadership * 0.7:
			return voter_idx
	
	# Use select_target with sheriff-election weighting
	return _ai_select_target(voter_idx, voter_role, candidates, !prefer_same_team, 100)


## AI chooses a day vote target influenced by personality, role knowledge, and past game info.
func _ai_day_vote(voter_idx: int, candidates: Array[int]) -> int:
	if candidates.is_empty():
		return -1
	
	var pers := _get_personality(voter_idx)
	var voter_data := game_state.get_player(voter_idx)
	var voter_team: GameState.Team = voter_data.get("team", GameState.Team.NONE)
	var voter_role: GameState.Role = voter_data.get("role", GameState.Role.NONE)
	
	# Werewolves coordinate: they prefer to vote for the same player (non-wolf)
	var prefer_enemy: bool = (voter_team == GameState.Team.EVIL)
	
	# If seer has checked someone as EVIL, AI with high rationality might know
	# (Simulated: seer last result influences rational players)
	if pers.rationality > 0.60 and game_state.seer_last_result == GameState.Team.EVIL:
		var seer_target := game_state.seer_target
		if seer_target >= 0 and seer_target in candidates:
			var rng := RandomNumberGenerator.new()
			rng.seed = hash(str(voter_idx) + "seer_knowledge" + str(game_state.current_round))
			if rng.randf() < pers.rationality * 0.50:
				return seer_target
	
	# Leader AI tends to vote with sheriff if sheriff exists
	if pers.leadership > 0.60 and game_state.sheriff_index in candidates and game_state.sheriff_index != voter_idx:
		var rng := RandomNumberGenerator.new()
		rng.seed = hash(str(voter_idx) + "follow_sheriff" + str(game_state.current_round))
		if rng.randf() < pers.leadership * 0.40:
			return game_state.sheriff_index
	
	# Follower AI tends to vote for the player with most existing votes
	if pers.leadership < 0.30:
		var most_voted: int = -1
		var most_count: float = -1.0
		for c in candidates:
			var cv: float = game_state.get_player(c).get("votes_against", 0.0)
			if cv > most_count:
				most_count = cv
				most_voted = c
		if most_voted >= 0 and most_count > 0:
			var rng := RandomNumberGenerator.new()
			rng.seed = hash(str(voter_idx) + "follow_votes" + str(game_state.current_round))
			if rng.randf() < (1.0 - pers.leadership) * 0.60:
				return most_voted
	
	return _ai_select_target(voter_idx, voter_role, candidates, prefer_enemy, 200)


## AI hunter revenge: aggressive hunters shoot randomly; rational hunters target suspects.
func _ai_hunter_shot(hunter_idx: int, targets: Array[int]) -> int:
	if targets.is_empty():
		return -1
	
	var hunter_data := game_state.get_player(hunter_idx)
	return _ai_select_target(hunter_idx, hunter_data.get("role", GameState.Role.HUNTER), targets, true, 300)


# ---- Helpers ----

func _enter_phase(new_phase: GameState.Phase) -> void:
	game_state.set_phase(new_phase)


func _check_game_over() -> bool:
	var winner: GameState.Team = game_state.check_win_condition()
	if winner != GameState.Team.NONE:
		_enter_phase(GameState.Phase.GAME_OVER)
		return true
	return false


func get_phase_display_name(phase: GameState.Phase) -> String:
	match phase:
		GameState.Phase.SETUP:               return "Setup"
		GameState.Phase.DAY_SHERIFF_ELECTION: return "Day - Sheriff Election"
		GameState.Phase.NIGHT_GUARD:          return "Night - Guard"
		GameState.Phase.NIGHT_WEREWOLF:       return "Night - Werewolves"
		GameState.Phase.NIGHT_WITCH:          return "Night - Witch"
		GameState.Phase.NIGHT_SEER:           return "Night - Seer"
		GameState.Phase.DAY_ANNOUNCE:         return "Day - Death Announcement"
		GameState.Phase.DAY_DISCUSSION:       return "Day - Discussion"
		GameState.Phase.DAY_VOTE:             return "Day - Vote"
		GameState.Phase.DAY_RESULT:           return "Day - Result"
		GameState.Phase.GAME_OVER:            return "Game Over"
		_: return "Unknown"


func get_role_display_name(role: GameState.Role) -> String:
	match role:
		GameState.Role.WEREWOLF:  return "Werewolf"
		GameState.Role.VILLAGER:  return "Villager"
		GameState.Role.SEER:      return "Seer"
		GameState.Role.WITCH:     return "Witch"
		GameState.Role.HUNTER:    return "Hunter"
		GameState.Role.GUARD:     return "Guard"
		_: return "Unknown"
