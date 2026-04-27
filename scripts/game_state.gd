# GameState — Global autoload for Pixel Werewolf
# Tracks current game phase, day number, villager roster, evidence, and
# win/lose flags. All game systems read from and write to this singleton.
extends Node

# ── Signals ───────────────────────────────────────────────────────────────
signal phase_changed(new_phase: String)
signal villager_died(villager_id: int)
signal evidence_collected(clue: Dictionary)
signal game_over(won: bool)

# ── Enums ────────────────────────────────────────────────────────────────
enum Phase {
	STARTUP,
	NIGHT,
	MORNING_REVEAL,
	DAY_INVESTIGATION,
	DAY_VOTE,
	GAME_OVER
}

enum Role {
	VILLAGER,
	WEREWOLF
}

# ── Villager Definitions ──────────────────────────────────────────────────
# Each entry: name, trait, clothing_color (hex), hat_color (hex)
const VILLAGER_DEFS: Array = [
	{"name": "Aldric",  "trait": "observant", "body_color": 0xC85A3C, "hat_color": 0x8B2010},
	{"name": "Brina",   "trait": "nervous",   "body_color": 0x5A9C40, "hat_color": 0xF0D080},
	{"name": "Corvin",  "trait": "suspicious","body_color": 0x404050, "hat_color": 0x202030},
	{"name": "Dalia",   "trait": "friendly",  "body_color": 0xE880A0, "hat_color": 0x60C840},
	{"name": "Edwin",   "trait": "grumpy",    "body_color": 0x4070A0, "hat_color": 0x202020},
	{"name": "Fenna",   "trait": "calm",      "body_color": 0xE0E0E8, "hat_color": 0xC0C0C8},
	{"name": "Garth",   "trait": "boastful",  "body_color": 0xE87020, "hat_color": 0x6B4010},
	{"name": "Hilde",   "trait": "quiet",     "body_color": 0x7040A0, "hat_color": 0x301860},
]

# ── State ─────────────────────────────────────────────────────────────────
var current_phase: Phase = Phase.STARTUP
var day: int = 1
var werewolf_id: int = -1  # index into villagers array; -1 = not yet assigned

# Array of Dictionaries, one per villager:
# { id, name, trait, body_color, hat_color, role, alive, position, suspicion }
var villagers: Array = []

# Evidence collected by the player:
# { type, description, target_hint, day_collected }
var evidence: Array = []

# Conversation history: { villager_id, day, topic, text }
var dialogue_log: Array = []

# Voting record per day: { day, accused_id, votes_for, votes_against, result }
var vote_history: Array = []

# Quick flags
var game_won: bool = false
var player_id: int = -1  # which villager the player controls (always alive)

# ── Lifecycle ─────────────────────────────────────────────────────────────
func _ready() -> void:
	print("GameState: ready")

# ── Setup ─────────────────────────────────────────────────────────────────
## Initialise a fresh game: pick werewolf, assign starting positions.
func start_new_game() -> void:
	day = 1
	game_won = false
	evidence.clear()
	dialogue_log.clear()
	vote_history.clear()

	# Build villager list from definitions
	villagers.clear()
	for i in range(VILLAGER_DEFS.size()):
		var def = VILLAGER_DEFS[i]
		villagers.append({
			"id": i,
			"name": def.name,
			"trait": def.trait,
			"body_color": def.body_color,
			"hat_color": def.hat_color,
			"role": Role.VILLAGER,
			"alive": true,
			"position": Vector2.ZERO,  # set by village map
			"suspicion": 0,            # 0–100 village suspicion of this person
			"home_tile": Vector2i.ZERO # assigned by village map
		})

	# Randomly assign werewolf
	werewolf_id = randi() % villagers.size()
	villagers[werewolf_id].role = Role.WEREWOLF
	print("GameState: werewolf is ", villagers[werewolf_id].name, " (debug only)")

	# Player is always villager index 0 (Aldric) for now
	player_id = 0

	set_phase(Phase.DAY_INVESTIGATION)

# ── Phase management ──────────────────────────────────────────────────────
func set_phase(new_phase: Phase) -> void:
	if current_phase == new_phase:
		return
	current_phase = new_phase
	var name_str := Phase.keys()[new_phase]
	print("GameState: phase -> ", name_str)
	phase_changed.emit(name_str)

func phase_name() -> String:
	return Phase.keys()[current_phase]

# ── Villager helpers ──────────────────────────────────────────────────────
func alive_villagers() -> Array:
	return villagers.filter(func(v): return v.alive)

func get_villager(id: int) -> Dictionary:
	if id >= 0 and id < villagers.size():
		return villagers[id]
	return {}

func kill_villager(id: int) -> void:
	if id >= 0 and id < villagers.size():
		villagers[id].alive = false
		villager_died.emit(id)
		print("GameState: ", villagers[id].name, " has died")
		_check_lose_condition()

## Called after vote. Reveals role and checks win/lose.
func exile_villager(id: int) -> void:
	if id < 0 or id >= villagers.size():
		return
	var v = villagers[id]
	v.alive = false
	print("GameState: ", v.name, " exiled. Role was: ", Role.keys()[v.role])
	if v.role == Role.WEREWOLF:
		_trigger_win()
	else:
		# Wrong exile — check if player was exiled
		if id == player_id:
			_trigger_lose("You were exiled by the village.")
		else:
			_check_lose_condition()

# ── Evidence ──────────────────────────────────────────────────────────────
func add_evidence(clue: Dictionary) -> void:
	clue["day_collected"] = day
	evidence.append(clue)
	evidence_collected.emit(clue)

func get_evidence_for(villager_id: int) -> Array:
	return evidence.filter(func(e): return e.get("target_hint", -1) == villager_id)

# ── Night phase ───────────────────────────────────────────────────────────
## Werewolf picks a victim. Returns victim id, or -1 if no valid target.
func werewolf_attack() -> int:
	var alive = alive_villagers().filter(func(v): return v.id != werewolf_id and v.id != player_id)
	if alive.is_empty():
		return -1
	# Simple random attack for now; will be smarter in Phase 4
	var target = alive[randi() % alive.size()]
	kill_villager(target.id)
	return target.id

# ── Day advancement ───────────────────────────────────────────────────────
func advance_day() -> void:
	day += 1
	print("GameState: day ", day, " begins")

# ── Win / Lose ────────────────────────────────────────────────────────────
func _trigger_win() -> void:
	game_won = true
	set_phase(Phase.GAME_OVER)
	game_over.emit(true)

func _trigger_lose(reason: String = "") -> void:
	game_won = false
	set_phase(Phase.GAME_OVER)
	print("GameState: game over — ", reason)
	game_over.emit(false)

func _check_lose_condition() -> void:
	var alive = alive_villagers()
	# Lose if player is dead
	var player_alive := alive.any(func(v): return v.id == player_id)
	if not player_alive:
		_trigger_lose("You were killed by the werewolf.")
		return
	# Lose if werewolf equals or outnumbers innocents
	var innocents_alive := alive.filter(func(v): return v.role == Role.VILLAGER).size()
	if innocents_alive <= 1:
		_trigger_lose("The werewolf has overrun the village.")

# ── State export (for TestHarness query) ─────────────────────────────────
func get_state() -> Dictionary:
	return {
		"phase": phase_name(),
		"day": day,
		"villager_count": villagers.size(),
		"alive_count": alive_villagers().size(),
		"evidence_count": evidence.size(),
		"game_won": game_won,
		"werewolf_revealed": current_phase == Phase.GAME_OVER,
		"villagers": villagers.map(func(v): return {
			"id": v.id,
			"name": v.name,
			"alive": v.alive,
			"suspicion": v.suspicion,
			"role": Role.keys()[v.role] if current_phase == Phase.GAME_OVER else "?"
		})
	}
