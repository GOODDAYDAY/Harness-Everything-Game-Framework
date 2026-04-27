# Main — root scene controller for Pixel Werewolf
# Orchestrates phase transitions, HUD updates, and scene loading.
extends Node2D

# ── Child references ─────────────────────────────────────────────────────────────
@onready var village_map: Node2D = $VillageMap
@onready var hud: CanvasLayer = $HUD
@onready var phase_label: Label = $HUD/PhaseLabel
@onready var day_label: Label = $HUD/DayLabel
@onready var status_label: Label = $HUD/StatusLabel

# ── Lifecycle ───────────────────────────────────────────────────────────────
func _ready() -> void:
	# Connect GameState signals
	GameState.phase_changed.connect(_on_phase_changed)
	GameState.game_over.connect(_on_game_over)
	GameState.villager_died.connect(_on_villager_died)

	# Start a new game immediately
	GameState.start_new_game()
	village_map.setup_villagers()
	_update_hud()

func _update_hud() -> void:
	phase_label.text = GameState.phase_name().replace("_", " ")
	day_label.text = "Day " + str(GameState.day)
	status_label.text = str(GameState.alive_villagers().size()) + " villagers alive"

# ── GameState signal handlers ────────────────────────────────────────────────
func _on_phase_changed(new_phase: String) -> void:
	_update_hud()
	match new_phase:
		"DAY_INVESTIGATION":
			_enter_day_investigation()
		"NIGHT":
			_enter_night()
		"MORNING_REVEAL":
			_enter_morning_reveal()
		"DAY_VOTE":
			_enter_day_vote()


func _on_game_over(won: bool) -> void:
	_update_hud()
	if won:
		status_label.text = "Village saved! Werewolf caught!"
	else:
		status_label.text = "The werewolf wins..."


func _on_villager_died(villager_id: int) -> void:
	var name := GameState.get_villager(villager_id).get("name", "Unknown")
	status_label.text = name + " has died!"
	if village_map:
		village_map.refresh_villagers()
	_update_hud()

# ── Phase handlers ─────────────────────────────────────────────────────────────
func _enter_day_investigation() -> void:
	pass  # Village is visible; player can interact

func _enter_night() -> void:
	pass  # Will darken the screen in Phase 2

func _enter_morning_reveal() -> void:
	pass  # Will show attack victim in Phase 3

func _enter_day_vote() -> void:
	pass  # Will open vote panel in Phase 3

# ── Input ────────────────────────────────────────────────────────────────────
func _unhandled_input(event: InputEvent) -> void:
	# Debug: press N to advance to night, D to advance to day, V to vote
	if event is InputEventKey and event.pressed:
		match event.keycode:
			KEY_N:
				GameState.set_phase(GameState.Phase.NIGHT)
			KEY_D:
				GameState.set_phase(GameState.Phase.DAY_INVESTIGATION)
			KEY_V:
				GameState.set_phase(GameState.Phase.DAY_VOTE)
			KEY_SPACE:
				# Debug: trigger werewolf attack
				if GameState.current_phase == GameState.Phase.NIGHT:
					GameState.werewolf_attack()
