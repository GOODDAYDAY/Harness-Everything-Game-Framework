# Game — Main game scene controller
# Handles rendering the grove grid, hand, UI overlays, and player input.
extends Node2D

# ── Layout constants ────────────────────────────────────────────────────────────
const TILE      := 32           # px per tile (matches PixelArt.TILE_SIZE)
const GAP       := 4            # gap between tiles
const TILE_STEP := TILE + GAP   # step per cell = 36

# Grove grid top-left origin (centred in viewport)
const GROVE_X   := 28
const GROVE_Y   := 40

# Hand area y-position
const HAND_Y    := 220
const HAND_X    := 40
const HAND_STEP := 52

# UI text positions
const SCORE_POS   := Vector2(310, 50)
const ROUND_POS   := Vector2(310, 70)
const WEATHER_POS := Vector2(310, 95)
const HELP_POS    := Vector2(310, 160)

# ── Animation constants ─────────────────────────────────────────────────────────
const BOND_FLASH_DURATION := 1.2
const SWAY_AMPLITUDE      := 1.2   # pixels of vertical sway
const SWAY_SPEED          := 1.6   # radians/sec base speed
const POPUP_RISE_SPEED    := 22.0  # px/s upward drift
const POPUP_DURATION      := 1.8   # seconds a popup lives

# ── Child nodes (created programmatically) ─────────────────────────────────────
var _grid_sprites:   Array[Sprite2D]   = []  # one per cell
var _tree_sprites:   Array[Sprite2D]   = []  # one per cell (tree on top)
var _bond_sprites:   Array[Sprite2D]   = []  # flashing bond overlays (per bond event)
var _bond_lines:     Array[Node]       = []  # persistent bond line nodes (Line2D + Labels)
var _hand_sprites:   Array[Sprite2D]   = []  # one per seed in hand
var _hand_labels:    Array[Label]      = []  # name label under each seed
var _select_rect:    ColorRect                # selection highlight
var _hover_rect:     ColorRect                # hover highlight
var _ui_layer:       CanvasLayer
var _score_label:    Label
var _round_label:    Label
var _weather_label:  Label
var _help_label:     Label
var _end_round_btn:  Button
var _end_panel:      PanelContainer           # game-over panel

# ── Animation state ─────────────────────────────────────────────────────────────
var _hover_cell := Vector2i(-1, -1)          # cell under mouse
var _bond_flash_timers: Array[float] = []    # countdown per bond overlay sprite
var _sway_phases:       Array[float] = []    # per-tree sway phase (radians)
var _sway_speeds:       Array[float] = []    # per-tree sway speed multiplier

# Floating score popups: each { label: Label, timer: float, vel_y: float }
var _popups: Array[Dictionary] = []

# ── Ready ───────────────────────────────────────────────────────────────────────
func _ready() -> void:
	_build_scene()
	GameState.state_changed.connect(_on_state_changed)
	GameState.bond_formed.connect(_on_bond_formed)
	GameState.round_started.connect(_on_round_started)
	GameState.game_over.connect(_on_game_over)
	GameState.score_gained.connect(_on_score_gained)
	GameState.start_new_game()

func _build_scene() -> void:
	# Background
	var bg := ColorRect.new()
	bg.color = Palette.BG
	bg.size = Vector2(480, 270)
	add_child(bg)

	# Build cell sprites (grid)
	for row in GameState.GROVE_ROWS:
		for col in GameState.GROVE_COLS:
			var cell_sprite := Sprite2D.new()
			cell_sprite.centered = false
			cell_sprite.position = _cell_pos(col, row)
			add_child(cell_sprite)
			_grid_sprites.append(cell_sprite)

			var tree_sprite := Sprite2D.new()
			tree_sprite.centered = false
			tree_sprite.position = _cell_pos(col, row)
			tree_sprite.visible = false
			add_child(tree_sprite)
			_tree_sprites.append(tree_sprite)

			# Per-tree sway (random phase so they don't all move identically)
			_sway_phases.append(randf() * TAU)
			_sway_speeds.append(randf_range(0.8, 1.2))

	# Hover rect (drawn above grid)
	_hover_rect = ColorRect.new()
	_hover_rect.size = Vector2(TILE, TILE)
	_hover_rect.color = Color(Palette.HIGHLIGHT.r, Palette.HIGHLIGHT.g, Palette.HIGHLIGHT.b, 0.35)
	_hover_rect.visible = false
	add_child(_hover_rect)

	# Selection rect (shown around selected hand seed)
	_select_rect = ColorRect.new()
	_select_rect.size = Vector2(TILE, TILE)
	_select_rect.color = Color(Palette.HIGHLIGHT.r, Palette.HIGHLIGHT.g, Palette.HIGHLIGHT.b, 0.5)
	_select_rect.visible = false
	add_child(_select_rect)

	# Title label above grove
	var title := Label.new()
	title.text = "Ember Grove"
	title.position = Vector2(GROVE_X, 8)
	title.add_theme_color_override("font_color", Palette.PARCHMENT)
	add_child(title)

	# Hand label
	var hand_lbl := Label.new()
	hand_lbl.text = "Your Seeds:"
	hand_lbl.position = Vector2(HAND_X, HAND_Y - 18)
	hand_lbl.add_theme_color_override("font_color", Palette.PARCHMENT2)
	add_child(hand_lbl)

	# UI layer for score etc.
	_ui_layer = CanvasLayer.new()
	_ui_layer.layer = 10
	add_child(_ui_layer)

	_score_label = Label.new()
	_score_label.position = SCORE_POS
	_score_label.add_theme_color_override("font_color", Palette.AMPLIFY)
	_ui_layer.add_child(_score_label)

	_round_label = Label.new()
	_round_label.position = ROUND_POS
	_round_label.add_theme_color_override("font_color", Palette.PARCHMENT2)
	_ui_layer.add_child(_round_label)

	_weather_label = Label.new()
	_weather_label.position = WEATHER_POS
	_weather_label.add_theme_color_override("font_color", Palette.FROST_LT)
	_weather_label.autowrap_mode = TextServer.AUTOWRAP_WORD
	_weather_label.custom_minimum_size = Vector2(160, 60)
	_ui_layer.add_child(_weather_label)

	_help_label = Label.new()
	_help_label.position = HELP_POS
	_help_label.add_theme_color_override("font_color", Palette.DISABLED)
	_help_label.text = "Click a seed,\nthen click the grove.\nRight-click to deselect."
	_help_label.autowrap_mode = TextServer.AUTOWRAP_WORD
	_help_label.custom_minimum_size = Vector2(160, 60)
	_ui_layer.add_child(_help_label)

	# End Round button
	_end_round_btn = Button.new()
	_end_round_btn.text = "End Round"
	_end_round_btn.position = Vector2(SCORE_POS.x, 225)
	_end_round_btn.size = Vector2(140, 24)
	_end_round_btn.pressed.connect(_on_end_round_pressed)
	_ui_layer.add_child(_end_round_btn)

	# End-game panel (hidden until game over)
	_end_panel = PanelContainer.new()
	_end_panel.visible = false
	_end_panel.position = Vector2(80, 80)
	_end_panel.size = Vector2(320, 120)
	_ui_layer.add_child(_end_panel)
	var end_vbox := VBoxContainer.new()
	_end_panel.add_child(end_vbox)
	var end_title := Label.new()
	end_title.name = "EndTitle"
	end_title.add_theme_color_override("font_color", Palette.AMPLIFY)
	end_vbox.add_child(end_title)
	var end_score_lbl := Label.new()
	end_score_lbl.name = "EndScore"
	end_score_lbl.add_theme_color_override("font_color", Palette.PARCHMENT)
	end_vbox.add_child(end_score_lbl)
	var restart_btn := Button.new()
	restart_btn.text = "Play Again"
	restart_btn.pressed.connect(_on_restart_pressed)
	end_vbox.add_child(restart_btn)

# ── Coordinate helpers ──────────────────────────────────────────────────────────
func _cell_pos(col: int, row: int) -> Vector2:
	return Vector2(GROVE_X + col * TILE_STEP, GROVE_Y + row * TILE_STEP)

func _cell_center(col: int, row: int) -> Vector2:
	return _cell_pos(col, row) + Vector2(TILE / 2.0, TILE / 2.0)

func _pos_to_cell(pos: Vector2) -> Vector2i:
	"""Convert screen position to grid cell. Returns (-1,-1) if outside grid."""
	var rel := pos - Vector2(GROVE_X, GROVE_Y)
	var col := int(rel.x / TILE_STEP)
	var row := int(rel.y / TILE_STEP)
	# Verify it's within the tile (not in the gap)
	var local_x := int(rel.x) % TILE_STEP
	var local_y := int(rel.y) % TILE_STEP
	if local_x >= TILE or local_y >= TILE:
		return Vector2i(-1, -1)
	if col < 0 or col >= GameState.GROVE_COLS or row < 0 or row >= GameState.GROVE_ROWS:
		return Vector2i(-1, -1)
	return Vector2i(col, row)

func _hand_index_at(pos: Vector2) -> int:
	"""Return hand index if pos is over a seed, else -1."""
	for i in _hand_sprites.size():
		var sp := _hand_sprites[i]
		var r := Rect2(sp.position, Vector2(TILE, TILE))
		if r.has_point(pos):
			return i
	return -1

# ── Input ───────────────────────────────────────────────────────────────────────

func _input(event: InputEvent) -> void:
	if _end_panel.visible:
		return  # block input during game-over

	if event is InputEventMouseMotion:
		_on_mouse_move(event.position)
	elif event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
			_on_left_click(event.position)
		elif event.button_index == MOUSE_BUTTON_RIGHT and event.pressed:
			GameState.deselect_seed()


func _on_mouse_move(pos: Vector2) -> void:
	var cell := _pos_to_cell(pos)
	if cell != _hover_cell:
		_hover_cell = cell
		if cell.x >= 0:
			_hover_rect.position = _cell_pos(cell.x, cell.y)
			_hover_rect.visible = true
		else:
			_hover_rect.visible = false

func _on_left_click(pos: Vector2) -> void:
	# Check hand click first
	var hand_idx := _hand_index_at(pos)
	if hand_idx >= 0:
		GameState.select_seed(hand_idx)
		return
	# Check grove click
	var cell := _pos_to_cell(pos)
	if cell.x >= 0 and GameState.selected_seed_index >= 0:
		GameState.place_seed(cell.x, cell.y)

func _on_end_round_pressed() -> void:
	if not _end_panel.visible:
		GameState.end_round()

# ── State refresh ────────────────────────────────────────────────────────────────

func _on_state_changed() -> void:
	_refresh_grid()
	_refresh_hand()
	_refresh_ui()

func _on_round_started(_round: int, _weather: Dictionary) -> void:
	_refresh_ui()

func _on_bond_formed(cell_a: Vector2i, cell_b: Vector2i, bond_info: Dictionary) -> void:
	_spawn_bond_overlay(cell_a, cell_b, bond_info)
	_spawn_bond_line(cell_a, cell_b, bond_info)

func _on_game_over(final_score: int, threshold: int) -> void:
	_show_end_panel(final_score, threshold)
	_end_round_btn.visible = false

func _on_restart_pressed() -> void:
	_end_panel.visible = false
	_end_round_btn.visible = true
	_clear_bond_sprites()
	_clear_bond_lines()
	_clear_popups()
	GameState.start_new_game()

func _on_score_gained(amount: int, label_text: String, col: int, row: int) -> void:
	"""Spawn a floating score popup at the given cell position."""
	var center := _cell_center(col, row)
	_spawn_popup(label_text if label_text != "" else "+%d" % amount, center)

# ── Grid / hand refresh ─────────────────────────────────────────────────────────

func _refresh_grid() -> void:
	for row in GameState.GROVE_ROWS:
		for col in GameState.GROVE_COLS:
			var idx := row * GameState.GROVE_COLS + col
			var cell := GameState.get_cell(col, row)
			var gs := _grid_sprites[idx]
			var ts := _tree_sprites[idx]

			# Cell background
			gs.texture = PixelArt.make_cell_texture(cell["blocked"])

			# Tree sprite
			var tree_type: int = cell["type"]
			if not cell["blocked"] and tree_type != TreeTypes.NONE:
				ts.texture = PixelArt.make_tree_texture(tree_type)
				ts.visible = true
			else:
				ts.visible = false

func _refresh_hand() -> void:
	# Remove old hand sprites
	for sp in _hand_sprites:
		sp.queue_free()
	for lbl in _hand_labels:
		lbl.queue_free()
	_hand_sprites.clear()
	_hand_labels.clear()

	for i in GameState.hand.size():
		var tree_type: int = GameState.hand[i]
		var sp := Sprite2D.new()
		sp.centered = false
		sp.position = Vector2(HAND_X + i * HAND_STEP, HAND_Y)
		sp.texture = PixelArt.make_tree_texture(tree_type)
		add_child(sp)
		_hand_sprites.append(sp)

		# Selection glow
		if i == GameState.selected_seed_index:
			_select_rect.position = sp.position
			_select_rect.visible = true

		# Name label below seed
		var lbl := Label.new()
		lbl.text = TreeTypes.get_name(tree_type)
		lbl.position = Vector2(HAND_X + i * HAND_STEP - 4, HAND_Y + TILE + 2)
		lbl.add_theme_color_override("font_color", Palette.tree_primary(tree_type))
		add_child(lbl)
		_hand_labels.append(lbl)

	if GameState.selected_seed_index < 0:
		_select_rect.visible = false

func _refresh_ui() -> void:
	var score     := GameState.current_score
	var threshold := GameState.HARMONY_THRESHOLD
	_score_label.text = "Score: %d / %d" % [score, threshold]
	_round_label.text = "Round %d" % GameState.current_round

	var w := GameState.current_weather
	if w.is_empty():
		_weather_label.text = ""
	else:
		_weather_label.text = "%s %s\n%s" % [
			w.get("icon", ""),
			w.get("name", ""),
			w.get("description", ""),
		]

# ── Bond overlay (flashing on bond event) ──────────────────────────────────────

func _spawn_bond_overlay(cell_a: Vector2i, cell_b: Vector2i, bond_info: Dictionary) -> void:
	"""Flash a glowing overlay on both cells when a bond forms."""
	var bond_type: String = bond_info.get("bond_type", "amplify")
	for cell in [cell_a, cell_b]:
		var ov := Sprite2D.new()
		ov.centered = false
		ov.position = _cell_pos(cell.x, cell.y)
		ov.texture = PixelArt.make_bond_glow(bond_type)
		add_child(ov)
		_bond_sprites.append(ov)
		_bond_flash_timers.append(BOND_FLASH_DURATION)

func _clear_bond_sprites() -> void:
	for sp in _bond_sprites:
		sp.queue_free()
	_bond_sprites.clear()
	_bond_flash_timers.clear()

# ── Persistent bond lines ──────────────────────────────────────────────────────

func _spawn_bond_line(cell_a: Vector2i, cell_b: Vector2i, bond_info: Dictionary) -> void:
	"""Draw a thin persistent coloured line connecting the two bonded cell centres."""
	var bond_type: String = bond_info.get("bond_type", "amplify")
	var line_color: Color
	match bond_type:
		"steam":      line_color = Palette.STEAM
		"overgrowth": line_color = Palette.OVERGROWTH
		"amplify":    line_color = Palette.AMPLIFY
		_:            line_color = Palette.HIGHLIGHT
	line_color.a = 0.6

	var from_pt := _cell_center(cell_a.x, cell_a.y)
	var to_pt   := _cell_center(cell_b.x, cell_b.y)

	# Use a Line2D node for a clean bond line
	var line := Line2D.new()
	line.width = 2.0
	line.default_color = line_color
	line.add_point(from_pt)
	line.add_point(to_pt)
	# Gently pulse the line by animating width in _process via a small marker
	line.set_meta("bond_type", bond_type)
	line.set_meta("phase", randf() * TAU)
	add_child(line)
	_bond_lines.append(line)

	# Also place a small icon Label at the midpoint showing bond name
	var mid := (from_pt + to_pt) / 2.0 - Vector2(0, 8)
	var name_lbl := Label.new()
	name_lbl.text = bond_info.get("name", "")
	name_lbl.position = mid
	name_lbl.add_theme_color_override("font_color", line_color)
	name_lbl.set_meta("is_bond_label", true)
	add_child(name_lbl)
	_bond_lines.append(name_lbl)  # store so we can clear it

func _clear_bond_lines() -> void:
	for n in _bond_lines:
		n.queue_free()
	_bond_lines.clear()

# ── Floating score popups ──────────────────────────────────────────────────────

func _spawn_popup(text: String, world_pos: Vector2) -> void:
	"""Create a floating label that drifts upward and fades."""
	var lbl := Label.new()
	lbl.text = text
	lbl.position = world_pos - Vector2(16, 8)
	lbl.add_theme_color_override("font_color", Palette.AMPLIFY)
	add_child(lbl)
	_popups.append({
		"label": lbl,
		"timer": POPUP_DURATION,
	})

func _clear_popups() -> void:
	for p in _popups:
		if is_instance_valid(p["label"]):
			p["label"].queue_free()
	_popups.clear()

# ── End game panel ──────────────────────────────────────────────────────────────

func _show_end_panel(final_score: int, threshold: int) -> void:
	var harmonised := final_score >= threshold
	var title_node := _end_panel.find_child("EndTitle")
	var score_node := _end_panel.find_child("EndScore")
	if title_node:
		title_node.text = "✨ Grove Harmonised! ✨" if harmonised else "Grove Unfinished..."
	if score_node:
		var pct := int(float(final_score) / float(threshold) * 100.0)
		score_node.text = "Final Score: %d / %d (%d%%)" % [final_score, threshold, pct]
	_end_panel.visible = true

# ── Per-frame ───────────────────────────────────────────────────────────────────

func _process(delta: float) -> void:
	_update_bond_flashes(delta)
	_update_tree_sway(delta)
	_update_popups(delta)
	_update_bond_line_pulse(delta)

func _update_bond_flashes(delta: float) -> void:
	"""Fade out bond overlay sprites over time."""
	var to_remove: Array[int] = []
	for i in _bond_flash_timers.size():
		_bond_flash_timers[i] -= delta
		if i < _bond_sprites.size():
			var alpha := clamp(_bond_flash_timers[i] / BOND_FLASH_DURATION, 0.0, 1.0)
			_bond_sprites[i].modulate = Color(1, 1, 1, alpha)
			if _bond_flash_timers[i] <= 0.0:
				to_remove.append(i)
	# Remove expired (in reverse order)
	for i in to_remove.size():
		var idx := to_remove[to_remove.size() - 1 - i]
		_bond_sprites[idx].queue_free()
		_bond_sprites.remove_at(idx)
		_bond_flash_timers.remove_at(idx)

func _update_tree_sway(delta: float) -> void:
	"""Gently oscillate planted tree sprites for a living-forest feel."""
	for row in GameState.GROVE_ROWS:
		for col in GameState.GROVE_COLS:
			var idx := row * GameState.GROVE_COLS + col
			var ts := _tree_sprites[idx]
			if not ts.visible:
				continue
			_sway_phases[idx] += delta * SWAY_SPEED * _sway_speeds[idx]
			var offset_y := sin(_sway_phases[idx]) * SWAY_AMPLITUDE
			ts.position = _cell_pos(col, row) + Vector2(0, offset_y)

func _update_popups(delta: float) -> void:
	"""Drift floating score labels upward and fade them out."""
	var to_remove: Array[int] = []
	for i in _popups.size():
		var p: Dictionary = _popups[i]
		p["timer"] -= delta
		var lbl: Label = p["label"]
		if not is_instance_valid(lbl):
			to_remove.append(i)
			continue
		# Drift upward
		lbl.position.y -= POPUP_RISE_SPEED * delta
		# Fade
		var alpha := clamp(p["timer"] / POPUP_DURATION, 0.0, 1.0)
		lbl.modulate = Color(1, 1, 1, alpha)
		if p["timer"] <= 0.0:
			to_remove.append(i)
	for i in to_remove.size():
		var idx := to_remove[to_remove.size() - 1 - i]
		if is_instance_valid(_popups[idx]["label"]):
			_popups[idx]["label"].queue_free()
		_popups.remove_at(idx)

func _update_bond_line_pulse(delta: float) -> void:
	"""Gently pulse bond line widths so they feel alive."""
	for node in _bond_lines:
		if node is Line2D and is_instance_valid(node):
			var phase: float = node.get_meta("phase", 0.0)
			phase += delta * 1.4
			node.set_meta("phase", phase)
			node.width = 1.5 + sin(phase) * 0.7
