# VillageMap — Renders the pixel village and places villager sprites
# Attached to the VillageMap Node2D in scenes/main.tscn
# Handles: background tiles, cottages, paths, town square, villager tokens
extends Node2D

# ── Constants ─────────────────────────────────────────────────────────────────
const TILE_SIZE := 16
const MAP_W := 30
const MAP_H := 17

# ── Day palette ─────────────────────────────────────────────────────────────
const C_SKY       := Color(0.788, 0.910, 0.941)  # #C9E8F0
const C_GRASS     := Color(0.553, 0.776, 0.416)  # #8DC66A
const C_PATH      := Color(0.784, 0.659, 0.478)  # #C8A87A
const C_COTTAGE   := Color(0.910, 0.784, 0.533)  # #E8C888
const C_ROOF      := Color(0.784, 0.353, 0.235)  # #C85A3C
const C_WOOD      := Color(0.478, 0.361, 0.227)  # #7A5C3A
const C_WELL      := Color(0.600, 0.450, 0.300)  # stone grey-brown
const C_TREE_DARK := Color(0.118, 0.235, 0.157)  # dark forest green
const C_TREE_MID  := Color(0.180, 0.380, 0.200)  # mid forest green
const C_DOOR      := Color(0.350, 0.220, 0.100)  # dark wood door
const C_WINDOW    := Color(0.980, 0.930, 0.750)  # warm window glass

# ── Night palette (blended in during night phase) ───────────────────────────
const C_NIGHT_SKY    := Color(0.051, 0.106, 0.165)  # #0D1B2A
const C_NIGHT_GROUND := Color(0.118, 0.188, 0.251)  # #1E3040
const C_WINDOW_GLOW  := Color(0.910, 0.784, 0.376)  # #E8C860

# ── Cottage home tiles (tile-space coords, top-left of cottage) ─────────────────
# 8 cottages: 4 top row, 4 bottom row
const COTTAGE_TILES: Array = [
	Vector2i(2,  2),   # Aldric
	Vector2i(8,  2),   # Brina
	Vector2i(14, 2),   # Corvin
	Vector2i(20, 2),   # Dalia
	Vector2i(2,  11),  # Edwin
	Vector2i(8,  11),  # Fenna
	Vector2i(14, 11),  # Garth
	Vector2i(20, 11),  # Hilde
]

# Town square centre tile
const SQUARE_TILE := Vector2i(13, 7)

# ── Internal refs ──────────────────────────────────────────────────────────────
var _bg_image: Image
var _bg_texture: ImageTexture
var _bg_sprite: Sprite2D

var _villager_sprites: Array = []  # Array of Sprite2D

# ── Lifecycle ───────────────────────────────────────────────────────────────
func _ready() -> void:
	_build_background()
	# Villager tokens are spawned by main.gd after GameState.start_new_game()

func setup_villagers() -> void:
	_spawn_villager_tokens()

# ── Background drawing ───────────────────────────────────────────────────────
func _build_background() -> void:
	var w := MAP_W * TILE_SIZE  # 480
	var h := MAP_H * TILE_SIZE  # 272 (slightly taller than viewport, crops nicely)
	_bg_image = Image.create(w, h, false, Image.FORMAT_RGB8)

	# 1. Fill grass
	_bg_image.fill(C_GRASS)

	# 2. Forest edge — top two rows of tiles
	for tx in range(MAP_W):
		_draw_tree(tx, 0)
		if tx % 2 == 0:
			_draw_tree(tx, 1)

	# 3. Paths — horizontal corridor mid-map
	for tx in range(MAP_W):
		_fill_tile(tx, 7, C_PATH)
		_fill_tile(tx, 8, C_PATH)

	# 4. Vertical paths connecting cottages to horizontal path
	for pair in [[3, 2, 6], [9, 2, 6], [15, 2, 6], [21, 2, 6],
				 [3, 9, 11], [9, 9, 11], [15, 9, 11], [21, 9, 11]]:
		for ty in range(pair[1], pair[2]):
			_fill_tile(pair[0], ty, C_PATH)

	# 5. Cottages
	for i in range(COTTAGE_TILES.size()):
		var ct := COTTAGE_TILES[i]
		_draw_cottage(ct.x, ct.y)

	# 6. Town square / well
	_draw_well(SQUARE_TILE.x, SQUARE_TILE.y)

	# 7. Create texture and sprite
	_bg_texture = ImageTexture.create_from_image(_bg_image)
	_bg_sprite = Sprite2D.new()
	_bg_sprite.texture = _bg_texture
	_bg_sprite.position = Vector2(w / 2.0, h / 2.0)
	_bg_sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	add_child(_bg_sprite)

# Utility: fill a tile with a solid color
func _fill_tile(tx: int, ty: int, color: Color) -> void:
	for px in range(TILE_SIZE):
		for py in range(TILE_SIZE):
			_bg_image.set_pixel(tx * TILE_SIZE + px, ty * TILE_SIZE + py, color)

# Utility: fill a rectangle within pixel space
func _fill_rect_px(x: int, y: int, w: int, h: int, color: Color) -> void:
	for px in range(w):
		for py in range(h):
			var ix := x + px
			var iy := y + py
			if ix >= 0 and iy >= 0 and ix < _bg_image.get_width() and iy < _bg_image.get_height():
				_bg_image.set_pixel(ix, iy, color)

func _draw_tree(tx: int, ty: int) -> void:
	# Dark background tile
	_fill_tile(tx, ty, C_TREE_DARK)
	# Mid-color blob in centre
	var ox := tx * TILE_SIZE + 4
	var oy := ty * TILE_SIZE + 2
	_fill_rect_px(ox, oy, 8, 12, C_TREE_MID)

func _draw_cottage(tx: int, ty: int) -> void:
	# Cottage body: 4x3 tiles — body 4 wide, 2 tall; roof 4 wide, 1 tall
	var bx := tx * TILE_SIZE
	var by := ty * TILE_SIZE
	# Roof (2 tile rows, 4 tiles wide => 64x32 px, pitched)
	_fill_rect_px(bx, by, 4 * TILE_SIZE, TILE_SIZE, C_ROOF)
	# Slanted roof shadow
	_fill_rect_px(bx, by + TILE_SIZE, 4 * TILE_SIZE, TILE_SIZE // 2, C_ROOF)
	# Body
	_fill_rect_px(bx, by + TILE_SIZE + TILE_SIZE // 2, 4 * TILE_SIZE, 2 * TILE_SIZE - TILE_SIZE // 2, C_COTTAGE)
	# Door (centre of body)
	_fill_rect_px(bx + TILE_SIZE + 4, by + 2 * TILE_SIZE, 8, TILE_SIZE, C_DOOR)
	# Window left
	_fill_rect_px(bx + 4, by + TILE_SIZE + 6, 8, 6, C_WINDOW)
	# Window right
	_fill_rect_px(bx + 2 * TILE_SIZE + 4, by + TILE_SIZE + 6, 8, 6, C_WINDOW)
	# Wood frame outline (top and sides, 1px)
	for px in range(4 * TILE_SIZE):
		_bg_image.set_pixel(bx + px, by, C_WOOD)
		_bg_image.set_pixel(bx + px, by + 3 * TILE_SIZE - 1, C_WOOD)
	for py in range(3 * TILE_SIZE):
		_bg_image.set_pixel(bx, by + py, C_WOOD)
		_bg_image.set_pixel(bx + 4 * TILE_SIZE - 1, by + py, C_WOOD)

func _draw_well(tx: int, ty: int) -> void:
	# Stone circle well in centre of town square
	var cx := tx * TILE_SIZE + TILE_SIZE // 2
	var cy := ty * TILE_SIZE + TILE_SIZE // 2
	# 3x3 tile base area, draw paving stones
	_fill_rect_px(tx * TILE_SIZE - TILE_SIZE, ty * TILE_SIZE - TILE_SIZE, 3 * TILE_SIZE, 3 * TILE_SIZE, C_PATH)
	# Well circle (approximate with 3 concentric fills)
	_fill_rect_px(cx - 8, cy - 8, 16, 16, C_WELL)
	_fill_rect_px(cx - 5, cy - 5, 10, 10, C_NIGHT_GROUND)  # dark water inside
	# Crossbar
	_fill_rect_px(cx - 9, cy - 10, 18, 3, C_WOOD)

# ── Villager token sprites ────────────────────────────────────────────────────────
func _spawn_villager_tokens() -> void:
	_villager_sprites.clear()
	for v in GameState.villagers:
		var sprite := _make_villager_sprite(v)
		# Place in front of their cottage
		var home := COTTAGE_TILES[v.id]
		var world_pos := Vector2(
			(home.x + 2) * TILE_SIZE,  # centre of 4-tile-wide cottage
			(home.y + 3) * TILE_SIZE + 4  # just below cottage
		)
		sprite.position = world_pos
		GameState.villagers[v.id].position = world_pos
		GameState.villagers[v.id].home_tile = home
		add_child(sprite)
		_villager_sprites.append(sprite)

func _make_villager_sprite(v: Dictionary) -> Sprite2D:
	# 8x12 pixel character: hat(4px) + head(4px) + body(4px)
	var img := Image.create(8, 12, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))  # transparent

	var skin  := Color(0.941, 0.784, 0.627)  # #F0C8A0
	var body_c := Color(((v.body_color >> 16) & 0xFF) / 255.0, ((v.body_color >> 8) & 0xFF) / 255.0, (v.body_color & 0xFF) / 255.0)
	var hat_c  := Color(((v.hat_color  >> 16) & 0xFF) / 255.0, ((v.hat_color  >> 8) & 0xFF) / 255.0, (v.hat_color  & 0xFF) / 255.0)

	# Hat row 0: 6 wide centred
	for px in range(1, 7):
		img.set_pixel(px, 0, hat_c)
	# Hat row 1: 8 wide brim
	for px in range(0, 8):
		img.set_pixel(px, 1, hat_c)
	# Head rows 2-5: 6 wide centred, skin color
	for py in range(2, 6):
		for px in range(1, 7):
			img.set_pixel(px, py, skin)
	# Eyes row 3
	img.set_pixel(2, 3, Color(0.2, 0.15, 0.1))
	img.set_pixel(5, 3, Color(0.2, 0.15, 0.1))
	# Body rows 6-11
	for py in range(6, 12):
		for px in range(1, 7):
			img.set_pixel(px, py, body_c)
	# Arms (sides of body)
	for py in range(6, 10):
		img.set_pixel(0, py, body_c)
		img.set_pixel(7, py, body_c)

	var tex := ImageTexture.create_from_image(img)
	var sprite := Sprite2D.new()
	sprite.texture = tex
	sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	sprite.name = "Villager_" + v.name
	# Scale up 2x so characters read clearly at village scale
	sprite.scale = Vector2(2, 2)
	return sprite

# ── Public API ────────────────────────────────────────────────────────────────
func refresh_villagers() -> void:
	"""Refresh visibility of all villager sprites (e.g. after death)."""
	for i in range(_villager_sprites.size()):
		if i < GameState.villagers.size():
			_villager_sprites[i].visible = GameState.villagers[i].alive
