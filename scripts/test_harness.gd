# TestHarness — Autoload for external test automation
#
# Provides a TCP server on port 19840 that accepts JSON commands from the
# Python GameBridge. Handles: ping, screenshot, input injection, state
# query, and controlled shutdown.
#
# DO NOT MODIFY THIS FILE — it is test infrastructure, not game code.
extends Node

const PORT := 19840
const HOST := "127.0.0.1"

var _server: TCPServer = null
var _peer: StreamPeerTCP = null
var _buffer: String = ""

# ── Lifecycle ─────────────────────────────────────────────────────────────

func _ready() -> void:
	_server = TCPServer.new()
	var err := _server.listen(PORT, HOST)
	if err != OK:
		push_warning("TestHarness: failed to listen on %s:%d (err=%d)" % [HOST, PORT, err])
		return
	print("TestHarness: listening on %s:%d" % [HOST, PORT])


func _process(_delta: float) -> void:
	if _server == null:
		return

	# Accept new connection (only one client at a time)
	if _server.is_connection_available():
		if _peer != null:
			_peer.disconnect_from_host()
		_peer = _server.take_connection()
		_buffer = ""

	if _peer == null:
		return

	# Check connection status
	_peer.poll()
	var status := _peer.get_status()
	if status != StreamPeerTCP.STATUS_CONNECTED:
		if status == StreamPeerTCP.STATUS_NONE or status == StreamPeerTCP.STATUS_ERROR:
			_peer = null
			_buffer = ""
		return

	# Read available data
	var available := _peer.get_available_bytes()
	if available <= 0:
		return

	var data := _peer.get_data(available)
	if data[0] != OK:
		return
	_buffer += data[1].get_string_from_utf8()

	# Process complete lines (newline-delimited JSON)
	while "\n" in _buffer:
		var newline_pos := _buffer.find("\n")
		var line := _buffer.substr(0, newline_pos).strip_edges()
		_buffer = _buffer.substr(newline_pos + 1)
		if line.length() > 0:
			_handle_message(line)


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_PREDELETE:
		_cleanup()


func _cleanup() -> void:
	if _peer != null:
		_peer.disconnect_from_host()
		_peer = null
	if _server != null:
		_server.stop()
		_server = null

# ── Message dispatch ──────────────────────────────────────────────────────

func _handle_message(raw: String) -> void:
	var json := JSON.new()
	var parse_err := json.parse(raw)
	if parse_err != OK:
		_send_error("JSON parse error: %s" % json.get_error_message())
		return

	var msg: Dictionary = json.data
	if not msg.has("cmd"):
		_send_error("missing 'cmd' field")
		return

	var cmd: String = msg.get("cmd", "")
	match cmd:
		"ping":
			_cmd_ping()
		"screenshot":
			_cmd_screenshot(msg)
		"input_click":
			_cmd_input_click(msg)
		"input_key":
			_cmd_input_key(msg)
		"input_motion":
			_cmd_input_motion(msg)
		"state":
			_cmd_state()
		"quit":
			_cmd_quit(msg)
		_:
			_send_error("unknown command: %s" % cmd)

# ── Commands ──────────────────────────────────────────────────────────────

func _cmd_ping() -> void:
	_send_response({"ok": true, "engine": "godot", "version": Engine.get_version_info()["string"]})


func _cmd_screenshot(msg: Dictionary) -> void:
	var path: String = msg.get("path", "/tmp/game_screenshot.png")
	# Wait for the current frame to finish rendering
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	if image == null:
		_send_error("failed to capture viewport image")
		return
	var err := image.save_png(path)
	if err != OK:
		_send_error("failed to save screenshot: error %d" % err)
		return
	_send_response({
		"ok": true,
		"path": path,
		"size": [image.get_width(), image.get_height()],
	})


func _cmd_input_click(msg: Dictionary) -> void:
	var x: float = msg.get("x", 0.0)
	var y: float = msg.get("y", 0.0)
	var button_name: String = msg.get("button", "left")
	var button_index := MOUSE_BUTTON_LEFT
	match button_name:
		"right":
			button_index = MOUSE_BUTTON_RIGHT
		"middle":
			button_index = MOUSE_BUTTON_MIDDLE

	# Move mouse first so hover state updates
	var motion := InputEventMouseMotion.new()
	motion.position = Vector2(x, y)
	motion.global_position = Vector2(x, y)
	Input.parse_input_event(motion)

	# Press
	var press := InputEventMouseButton.new()
	press.position = Vector2(x, y)
	press.global_position = Vector2(x, y)
	press.button_index = button_index
	press.pressed = true
	Input.parse_input_event(press)

	# Release (next frame for realistic input)
	await get_tree().process_frame
	var release := InputEventMouseButton.new()
	release.position = Vector2(x, y)
	release.global_position = Vector2(x, y)
	release.button_index = button_index
	release.pressed = false
	Input.parse_input_event(release)

	_send_response({"ok": true})


func _cmd_input_key(msg: Dictionary) -> void:
	var key_name: String = msg.get("key", "")
	var pressed: bool = msg.get("pressed", true)
	var keycode := _key_name_to_code(key_name)
	if keycode == KEY_NONE:
		_send_error("unknown key: %s" % key_name)
		return

	var event := InputEventKey.new()
	event.keycode = keycode
	event.pressed = pressed
	event.physical_keycode = keycode
	Input.parse_input_event(event)

	# If pressed=true and no explicit release, auto-release next frame
	if pressed and not msg.has("no_release"):
		await get_tree().process_frame
		var release := InputEventKey.new()
		release.keycode = keycode
		release.pressed = false
		release.physical_keycode = keycode
		Input.parse_input_event(release)

	_send_response({"ok": true})


func _cmd_input_motion(msg: Dictionary) -> void:
	var x: float = msg.get("x", 0.0)
	var y: float = msg.get("y", 0.0)
	var event := InputEventMouseMotion.new()
	event.position = Vector2(x, y)
	event.global_position = Vector2(x, y)
	Input.parse_input_event(event)
	_send_response({"ok": true})


func _cmd_state() -> void:
	# Read from GameState autoload
	var gs = get_node_or_null("/root/GameState")
	if gs == null:
		_send_error("GameState autoload not found")
		return

	# Serialize grid
	var grid_data := []
	for cell in gs.grid:
		grid_data.append({"type": cell["type"], "blocked": cell["blocked"]})

	# Serialize hand
	var hand_data := []
	for seed_type in gs.hand:
		hand_data.append(seed_type)

	# Serialize bonds
	var bonds_data := []
	for bond in gs.active_bonds:
		bonds_data.append({
			"cell_a": [bond["cell_a"].x, bond["cell_a"].y],
			"cell_b": [bond["cell_b"].x, bond["cell_b"].y],
			"bond_type": bond["bond"].get("bond_type", ""),
			"bond_name": bond["bond"].get("name", ""),
		})

	_send_response({
		"ok": true,
		"state": {
			"score": gs.current_score,
			"round": gs.current_round,
			"selected_seed": gs.selected_seed_index,
			"total_trees": gs.total_trees_placed,
			"grid_cols": gs.GROVE_COLS,
			"grid_rows": gs.GROVE_ROWS,
			"grid": grid_data,
			"hand": hand_data,
			"bonds": bonds_data,
			"weather": {
				"name": gs.current_weather.get("name", ""),
				"icon": gs.current_weather.get("icon", ""),
				"description": gs.current_weather.get("description", ""),
			},
		},
	})


func _cmd_quit(msg: Dictionary) -> void:
	var exit_code: int = msg.get("exit_code", 0)
	_send_response({"ok": true})
	# Give time for the response to be sent
	await get_tree().create_timer(0.1).timeout
	get_tree().quit(exit_code)

# ── Helpers ───────────────────────────────────────────────────────────────

func _send_response(data: Dictionary) -> void:
	if _peer == null or _peer.get_status() != StreamPeerTCP.STATUS_CONNECTED:
		return
	var json_str := JSON.stringify(data) + "\n"
	_peer.put_data(json_str.to_utf8_buffer())


func _send_error(message: String) -> void:
	_send_response({"ok": false, "error": message})


func _key_name_to_code(name: String) -> Key:
	match name.to_lower():
		"space": return KEY_SPACE
		"enter", "return": return KEY_ENTER
		"escape", "esc": return KEY_ESCAPE
		"tab": return KEY_TAB
		"backspace": return KEY_BACKSPACE
		"delete", "del": return KEY_DELETE
		"up": return KEY_UP
		"down": return KEY_DOWN
		"left": return KEY_LEFT
		"right": return KEY_RIGHT
		"shift": return KEY_SHIFT
		"ctrl", "control": return KEY_CTRL
		"alt": return KEY_ALT
		"a": return KEY_A
		"b": return KEY_B
		"c": return KEY_C
		"d": return KEY_D
		"e": return KEY_E
		"f": return KEY_F
		"g": return KEY_G
		"h": return KEY_H
		"i": return KEY_I
		"j": return KEY_J
		"k": return KEY_K
		"l": return KEY_L
		"m": return KEY_M
		"n": return KEY_N
		"o": return KEY_O
		"p": return KEY_P
		"q": return KEY_Q
		"r": return KEY_R
		"s": return KEY_S
		"t": return KEY_T
		"u": return KEY_U
		"v": return KEY_V
		"w": return KEY_W
		"x": return KEY_X
		"y": return KEY_Y
		"z": return KEY_Z
		"0": return KEY_0
		"1": return KEY_1
		"2": return KEY_2
		"3": return KEY_3
		"4": return KEY_4
		"5": return KEY_5
		"6": return KEY_6
		"7": return KEY_7
		"8": return KEY_8
		"9": return KEY_9
		"f1": return KEY_F1
		"f2": return KEY_F2
		"f3": return KEY_F3
		"f4": return KEY_F4
		"f5": return KEY_F5
		"f6": return KEY_F6
		"f7": return KEY_F7
		"f8": return KEY_F8
		"f9": return KEY_F9
		"f10": return KEY_F10
		"f11": return KEY_F11
		"f12": return KEY_F12
	return KEY_NONE
