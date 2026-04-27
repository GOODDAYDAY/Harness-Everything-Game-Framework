# GameState — Autoload singleton
# Holds all mutable game state. Handles scoring, deck, events.
extends Node

signal state_changed
signal bond_formed(cell_a: Vector2i, cell_b: Vector2i, bond_info: Dictionary)
signal round_started(round_num: int, weather: Dictionary)
signal game_over(final_score: int, threshold: int)

# ── Constants ────────────────────────────────────────────────────────────────────
const GROVE_COLS    := 4
const GROVE_ROWS    := 3
const GROVE_SIZE    := GROVE_COLS * GROVE_ROWS  # 12 cells
const SEEDS_PER_ROUND := 3
const HARMONY_THRESHOLD := 36  # score needed to "harmonise" the grove
const BLOCKED_CELL_COUNT := 2  # how many cells are blocked per run

# ── Weather events ─────────────────────────────────────────────────────────────
# Each event: { name, description, effect_type, value }
const WEATHER_EVENTS := [
	{
		"name": "Gentle Rain",
		"description": "Bloom trees grow stronger this round! +2 score each.",
		"icon": "🌧️",
		"effect_type": "boost_type",
		"target_type": 2,  # BLOOM
		"value": 2,
	},
	{
		"name": "Drought",
		"description": "Frost trees suffer. Frost-Ember Steam bonds weaken by 2.",
		"icon": "☀️",
		"effect_type": "weaken_bond",
		"target_bond": "steam",
		"value": -2,
	},
	{
		"name": "Meteor Shower",
		"description": "A Wisp seed falls from the sky! Added to your hand.",
		"icon": "🌠",
		"effect_type": "gift_seed",
		"target_type": 4,  # WISP
		"value": 1,
	},
	{
		"name": "Morning Mist",
		"description": "Stone trees anchor the grove. Stone bonds give +1 extra.",
		"icon": "🌫️",
		"effect_type": "boost_bond_type",
		"target_type": 3,  # STONE
		"value": 1,
	},
	{
		"name": "Warm Breeze",
		"description": "Nothing special — a perfect peaceful day.",
		"icon": "🍃",
		"effect_type": "none",
		"value": 0,
	},
	{
		"name": "Star Night",
		"description": "Wisp trees glow brightly. All Wisp bonds get +1.",
		"icon": "⭐",
		"effect_type": "boost_bond_type",
		"target_type": 4,  # WISP
		"value": 1,
	},
]

# ── Live state ───────────────────────────────────────────────────────────────────────
var rng := RandomNumberGenerator.new()

# grid: flat array of size GROVE_COLS * GROVE_ROWS
# Each element: { "type": int (-1 = empty), "blocked": bool }
var grid: Array[Dictionary] = []

# player's current seed hand (array of int, tree types)
var hand: Array[int] = []

# seed deck (shuffled pool, refilled when empty)
var deck: Array[int] = []

# selected hand index (-1 = none)
var selected_seed_index: int = -1

# round tracking
var current_round: int = 0
var current_weather: Dictionary = {}

# score tracking
var current_score: int = 0
var total_trees_placed: int = 0

# active bonds: Array of { cell_a: Vector2i, cell_b: Vector2i, bond: Dict }
var active_bonds: Array[Dictionary] = []

# ── Init ─────────────────────────────────────────────────────────────────────────────
func start_new_game() -> void:
	rng.randomize()
	_init_grid()
	_init_deck()
	current_round = 0
	current_score = 0
	total_trees_placed = 0
	active_bonds.clear()
	selected_seed_index = -1
	start_round()

func _init_grid() -> void:
	grid.clear()
	for i in GROVE_SIZE:
		grid.append({"type": TreeTypes.NONE, "blocked": false})
	# Randomly block a few cells
	var blocked := []
	while blocked.size() < BLOCKED_CELL_COUNT:
		var idx := rng.randi_range(0, GROVE_SIZE - 1)
		if idx not in blocked:
			blocked.append(idx)
			grid[idx]["blocked"] = true

func _init_deck() -> void:
	deck.clear()
	hand.clear()
	# Fill deck: 3 copies of each common tree, 1 Wisp
	for t in TreeTypes.DRAW_WEIGHTS.size():
		for _i in range(TreeTypes.DRAW_WEIGHTS[t] * 2):
			deck.append(t)
	# Shuffle
	for i in range(deck.size() - 1, 0, -1):
		var j := rng.randi_range(0, i)
		var tmp := deck[i]
		deck[i] = deck[j]
		deck[j] = tmp

# ── Round management ─────────────────────────────────────────────────────────────────
func start_round() -> void:
	current_round += 1
	# Draw weather event
	current_weather = WEATHER_EVENTS[rng.randi_range(0, WEATHER_EVENTS.size() - 1)]
	# Apply gift_seed weather
	if current_weather.get("effect_type", "") == "gift_seed":
		hand.append(current_weather.get("target_type", 0))
	# Draw seeds up to SEEDS_PER_ROUND
	_draw_seeds()
	emit_signal("round_started", current_round, current_weather)
	emit_signal("state_changed")

func _draw_seeds() -> void:
	"""Fill hand to SEEDS_PER_ROUND from deck."""
	var needed := SEEDS_PER_ROUND - hand.size()
	for _i in range(needed):
		if deck.is_empty():
			_refill_deck()
		if not deck.is_empty():
			hand.append(deck.pop_back())

func _refill_deck() -> void:
	_init_deck()  # reshuffle fresh deck

func end_round() -> void:
	"""Called when player ends round (or hand is empty)."""
	# Check if grove is full
	if _is_grove_full():
		_calculate_final_score()
		emit_signal("game_over", current_score, HARMONY_THRESHOLD)
		return
	start_round()

func _is_grove_full() -> bool:
	for cell in grid:
		if not cell["blocked"] and cell["type"] == TreeTypes.NONE:
			return false
	return true

# ── Placement & scoring ───────────────────────────────────────────────────────────────
func place_seed(col: int, row: int) -> bool:
	"""Place selected seed at (col, row). Returns true on success."""
	if selected_seed_index < 0 or selected_seed_index >= hand.size():
		return false
	var idx := row * GROVE_COLS + col
	if idx < 0 or idx >= grid.size():
		return false
	var cell := grid[idx]
	if cell["blocked"] or cell["type"] != TreeTypes.NONE:
		return false

	var tree_type := hand[selected_seed_index]
	cell["type"] = tree_type
	hand.remove_at(selected_seed_index)
	selected_seed_index = -1
	total_trees_placed += 1

	# Score this placement
	var placement_score := TreeTypes.get_base_score(tree_type)
	# Check bonds with neighbours
	var new_bonds := _check_bonds_at(col, row)
	for bond_data in new_bonds:
		active_bonds.append(bond_data)
		placement_score += bond_data["bond"].get("score_bonus", 0)
		# Apply weather modifier
		placement_score += _weather_bonus_for_bond(bond_data["bond"])
		emit_signal("bond_formed", bond_data["cell_a"], bond_data["cell_b"], bond_data["bond"])

	# Apply weather boost to this tree type
	if current_weather.get("effect_type") == "boost_type":
		if current_weather.get("target_type") == tree_type:
			placement_score += current_weather.get("value", 0)

	current_score += placement_score
	emit_signal("state_changed")

	# Auto-end round when hand empty
	if hand.is_empty():
		end_round()
	return true

func _check_bonds_at(col: int, row: int) -> Array[Dictionary]:
	"""Find all new harmony bonds formed by placing at (col, row)."""
	var bonds: Array[Dictionary] = []
	var placed_type := grid[row * GROVE_COLS + col]["type"]
	var neighbours := _get_neighbours(col, row)
	for n in neighbours:
		var nc: int = n.x
		var nr: int = n.y
		var nidx := nr * GROVE_COLS + nc
		var neighbour_type: int = grid[nidx]["type"]
		if neighbour_type == TreeTypes.NONE:
			continue
		var bond_info := TreeTypes.check_harmony(placed_type, neighbour_type)
		if not bond_info.is_empty():
			bonds.append({
				"cell_a": Vector2i(col, row),
				"cell_b": Vector2i(nc, nr),
				"bond": bond_info,
			})
	return bonds

func _get_neighbours(col: int, row: int) -> Array[Vector2i]:
	var result: Array[Vector2i] = []
	var dirs := [Vector2i(1,0), Vector2i(-1,0), Vector2i(0,1), Vector2i(0,-1)]
	for d in dirs:
		var nc := col + d.x
		var nr := row + d.y
		if nc >= 0 and nc < GROVE_COLS and nr >= 0 and nr < GROVE_ROWS:
			result.append(Vector2i(nc, nr))
	return result

func _weather_bonus_for_bond(bond: Dictionary) -> int:
	var eff := current_weather.get("effect_type", "")
	var val := current_weather.get("value", 0)
	match eff:
		"weaken_bond":
			if bond.get("bond_type") == current_weather.get("target_bond"):
				return val  # negative
		"boost_bond_type":
			if bond.get("a") == current_weather.get("target_type") or \
			   bond.get("b") == current_weather.get("target_type"):
				return val
	return 0

func _calculate_final_score() -> void:
	"""Recalculate score from scratch (bonds may have compounded)."""
	# Score is accumulated live during placement; just ensure it's up to date
	pass

# ── Accessors ───────────────────────────────────────────────────────────────────────────
func get_cell(col: int, row: int) -> Dictionary:
	var idx := row * GROVE_COLS + col
	if idx < 0 or idx >= grid.size():
		return {"type": TreeTypes.NONE, "blocked": true}
	return grid[idx]

func get_bonds_at(col: int, row: int) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	var pos := Vector2i(col, row)
	for b in active_bonds:
		if b["cell_a"] == pos or b["cell_b"] == pos:
			result.append(b)
	return result

func select_seed(index: int) -> void:
	if index >= 0 and index < hand.size():
		selected_seed_index = index
	else:
		selected_seed_index = -1
	emit_signal("state_changed")

func deselect_seed() -> void:
	selected_seed_index = -1
	emit_signal("state_changed")
