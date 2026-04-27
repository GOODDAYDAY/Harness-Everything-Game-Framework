# PixelArt — Autoload singleton
# Generates all procedural pixel-art textures for Ember Grove.
extends Node

const TILE_SIZE := 32  # pixels per tile (pre-scale)

# ── Public API ───────────────────────────────────────────────────────────────────

func make_tree_texture(tree_type: int) -> ImageTexture:
	"""Returns a 32x32 ImageTexture for the given tree type."""
	var img := Image.create(TILE_SIZE, TILE_SIZE, false, Image.FORMAT_RGBA8)
	_draw_tree(img, tree_type)
	var tex := ImageTexture.create_from_image(img)
	return tex

func make_cell_texture(blocked: bool) -> ImageTexture:
	"""Returns a 32x32 cell background texture."""
	var img := Image.create(TILE_SIZE, TILE_SIZE, false, Image.FORMAT_RGBA8)
	_draw_cell(img, blocked)
	var tex := ImageTexture.create_from_image(img)
	return tex

func make_seed_icon(tree_type: int) -> ImageTexture:
	"""Returns a 16x16 seed icon for the hand/UI."""
	var img := Image.create(16, 16, false, Image.FORMAT_RGBA8)
	_draw_seed_icon(img, tree_type)
	var tex := ImageTexture.create_from_image(img)
	return tex

func make_bond_glow(bond_type: String) -> ImageTexture:
	"""Returns a 32x32 glowing bond overlay."""
	var img := Image.create(TILE_SIZE, TILE_SIZE, false, Image.FORMAT_RGBA8)
	_draw_bond_glow(img, bond_type)
	var tex := ImageTexture.create_from_image(img)
	return tex

# ── Drawing helpers ────────────────────────────────────────────────────────────────

func _fill_rect(img: Image, x: int, y: int, w: int, h: int, c: Color) -> void:
	for py in range(y, y + h):
		for px in range(x, x + w):
			if px >= 0 and py >= 0 and px < img.get_width() and py < img.get_height():
				img.set_pixel(px, py, c)

func _draw_circle(img: Image, cx: int, cy: int, r: int, c: Color) -> void:
	for py in range(cy - r, cy + r + 1):
		for px in range(cx - r, cx + r + 1):
			if (px - cx) * (px - cx) + (py - cy) * (py - cy) <= r * r:
				if px >= 0 and py >= 0 and px < img.get_width() and py < img.get_height():
					img.set_pixel(px, py, c)

func _draw_cell(img: Image, blocked: bool) -> void:
	var bg := Palette.BG_LIGHT if not blocked else Palette.WOOD_DARK
	var border := Palette.WOOD_DARK if not blocked else Palette.BG
	# Fill
	_fill_rect(img, 0, 0, TILE_SIZE, TILE_SIZE, bg)
	# Border (1px inset)
	for x in TILE_SIZE:
		img.set_pixel(x, 0, border)
		img.set_pixel(x, TILE_SIZE - 1, border)
	for y in TILE_SIZE:
		img.set_pixel(0, y, border)
		img.set_pixel(TILE_SIZE - 1, y, border)
	if blocked:
		# Draw an X to indicate blocked
		for i in range(4, TILE_SIZE - 4):
			img.set_pixel(i, i, Palette.DISABLED)
			img.set_pixel(i, TILE_SIZE - 1 - i, Palette.DISABLED)

func _draw_tree(img: Image, tree_type: int) -> void:
	var primary := Palette.tree_primary(tree_type)
	var light   := Palette.tree_light(tree_type)
	var dark    := Palette.tree_dark(tree_type)
	# Ground / soil patch
	_fill_rect(img, 10, 24, 12, 6, Palette.STONE_DK)
	_fill_rect(img, 12, 25, 8, 4, Palette.STONE)

	match tree_type:
		0:  # Ember — pointed flame crown
			_draw_ember_tree(img, primary, light, dark)
		1:  # Frost — crystalline spire
			_draw_frost_tree(img, primary, light, dark)
		2:  # Bloom — round fluffy canopy
			_draw_bloom_tree(img, primary, light, dark)
		3:  # Stone — squat solid trunk with flat top
			_draw_stone_tree(img, primary, light, dark)
		4:  # Wisp — floating orb with trailing sparkles
			_draw_wisp_tree(img, primary, light, dark)

func _draw_ember_tree(img: Image, primary: Color, light: Color, dark: Color) -> void:
	# Trunk
	_fill_rect(img, 14, 17, 4, 8, dark)
	_fill_rect(img, 15, 17, 2, 7, primary)
	# Flame layers (triangle-like, bottom to top gets narrower & lighter)
	_fill_rect(img, 10, 14, 12, 5, primary)   # wide base
	_fill_rect(img, 11, 10, 10, 5, primary)   # mid
	_fill_rect(img, 12, 7,  8,  4, light)     # upper
	_fill_rect(img, 14, 4,  4,  4, light)     # tip
	_fill_rect(img, 15, 3,  2,  2, Color.WHITE) # hottest tip
	# Shading on left side
	for y in range(4, 20):
		if img.get_pixel(10, y).a > 0:
			img.set_pixel(10, y, dark)

func _draw_frost_tree(img: Image, primary: Color, light: Color, dark: Color) -> void:
	# Trunk (thin, icy)
	_fill_rect(img, 15, 18, 2, 7, dark)
	# Spire layers
	_fill_rect(img, 9,  18, 14, 4, primary)   # wide base layer
	_fill_rect(img, 10, 14, 12, 5, primary)
	_fill_rect(img, 12, 10, 8,  5, light)
	_fill_rect(img, 13, 7,  6,  4, light)
	_fill_rect(img, 14, 4,  4,  4, light)
	_fill_rect(img, 15, 2,  2,  3, Color.WHITE) # ice tip
	# Crystal facets (light columns)
	for y in range(7, 22):
		if img.get_pixel(13, y).a > 0:
			img.set_pixel(13, y, light)

func _draw_bloom_tree(img: Image, primary: Color, light: Color, dark: Color) -> void:
	# Trunk
	_fill_rect(img, 14, 18, 4, 8, Palette.WOOD)
	_fill_rect(img, 15, 18, 2, 7, Palette.WOOD_DARK)
	# Fluffy round canopy — three overlapping circles
	_draw_circle(img, 16, 13, 8, dark)     # shadow base
	_draw_circle(img, 16, 12, 7, primary)  # main canopy
	_draw_circle(img, 13, 10, 5, primary)  # left puff
	_draw_circle(img, 19, 10, 5, primary)  # right puff
	_draw_circle(img, 16, 9,  4, light)    # highlight centre
	_draw_circle(img, 13, 8,  3, light)    # highlight left
	# A few flower dots
	img.set_pixel(16, 7, Color.WHITE)
	img.set_pixel(12, 11, Color.WHITE)
	img.set_pixel(20, 11, Color.WHITE)

func _draw_stone_tree(img: Image, primary: Color, light: Color, dark: Color) -> void:
	# Wide squat trunk
	_fill_rect(img, 12, 18, 8, 8, dark)
	_fill_rect(img, 13, 18, 6, 7, primary)
	_fill_rect(img, 14, 18, 4, 6, light)
	# Flat rocky canopy — wide layered slabs
	_fill_rect(img, 8,  15, 16, 4, dark)
	_fill_rect(img, 9,  11, 14, 5, primary)
	_fill_rect(img, 11, 7,  10, 5, primary)
	_fill_rect(img, 12, 5,  8,  3, light)
	# Rock cracks
	for x in [11, 17, 14]:
		for y in range(7, 16):
			if img.get_pixel(x, y).a > 0:
				img.set_pixel(x, y, dark)

func _draw_wisp_tree(img: Image, primary: Color, light: Color, dark: Color) -> void:
	# Ethereal stem (faint)
	_fill_rect(img, 15, 18, 2, 8, dark)
	for y in range(18, 26):
		img.set_pixel(15, y, Color(dark.r, dark.g, dark.b, 0.5))
		img.set_pixel(16, y, Color(dark.r, dark.g, dark.b, 0.5))
	# Main orb
	_draw_circle(img, 16, 13, 8, dark)
	_draw_circle(img, 16, 13, 7, primary)
	_draw_circle(img, 16, 12, 5, light)
	_draw_circle(img, 15, 11, 3, Color(1, 1, 1, 0.8))  # inner glow
	# Orbiting sparkle dots
	var sparkle_pos := [
		Vector2(8, 8), Vector2(24, 8), Vector2(6, 16),
		Vector2(26, 16), Vector2(16, 4)
	]
	for sp in sparkle_pos:
		if sp.x >= 0 and sp.y >= 0 and sp.x < 32 and sp.y < 32:
			img.set_pixel(int(sp.x), int(sp.y), light)

func _draw_seed_icon(img: Image, tree_type: int) -> void:
	var primary := Palette.tree_primary(tree_type)
	var light   := Palette.tree_light(tree_type)
	# Seed shape: small oval
	_draw_circle(img, 8, 9, 5, primary)
	_draw_circle(img, 7, 8, 3, light)
	# tiny sprout on top
	img.set_pixel(8, 3, primary)
	img.set_pixel(7, 4, primary)
	img.set_pixel(9, 4, primary)

func _draw_bond_glow(img: Image, bond_type: String) -> void:
	var c: Color
	match bond_type:
		"steam":      c = Palette.STEAM
		"overgrowth": c = Palette.OVERGROWTH
		"amplify":    c = Palette.AMPLIFY
		_:            c = Palette.HIGHLIGHT
	# Radial soft glow — brighter in centre, transparent at edges
	var cx := TILE_SIZE / 2
	var cy := TILE_SIZE / 2
	var max_r := float(TILE_SIZE) / 2.0
	for y in TILE_SIZE:
		for x in TILE_SIZE:
			var dist := sqrt(float((x - cx) * (x - cx) + (y - cy) * (y - cy)))
			var alpha := clamp(1.0 - dist / max_r, 0.0, 1.0) * 0.5
			if alpha > 0.0:
				img.set_pixel(x, y, Color(c.r, c.g, c.b, alpha))
