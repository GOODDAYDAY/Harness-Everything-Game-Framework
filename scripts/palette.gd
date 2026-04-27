# Palette — Autoload singleton
# All colour constants for Ember Grove. Import-free; use Palette.X anywhere.
extends Node

# ─ Background & surfaces ────────────────────────────────────────────────────
const BG         := Color(0.17, 0.12, 0.09, 1.0)   # deep warm dusk
const BG_LIGHT   := Color(0.25, 0.19, 0.14, 1.0)   # lighter cell background
const PARCHMENT  := Color(0.94, 0.87, 0.72, 1.0)   # warm cream
const PARCHMENT2 := Color(0.80, 0.70, 0.55, 1.0)   # muted parchment
const DISABLED   := Color(0.55, 0.52, 0.48, 1.0)   # faded grey-brown

# ─ Wood & soil ──────────────────────────────────────────────────────────────
const WOOD       := Color(0.55, 0.35, 0.18, 1.0)   # warm bark brown
const WOOD_DARK  := Color(0.32, 0.20, 0.10, 1.0)   # dark bark
const SOIL_DARK  := Color(0.24, 0.16, 0.11, 1.0)
const SOIL_MID   := Color(0.35, 0.24, 0.15, 1.0)
const SOIL_LIGHT := Color(0.46, 0.33, 0.20, 1.0)
const GRASS      := Color(0.30, 0.48, 0.20, 1.0)
const GRASS_LT   := Color(0.42, 0.60, 0.28, 1.0)

# ─ Stone (also used as soil patch in tree bases) ──────────────────────────────
const STONE_DK    := Color(0.28, 0.24, 0.20, 1.0)  # used as ground patch dark
const STONE       := Color(0.55, 0.53, 0.50, 1.0)  # mid stone (cell soil)

# ─ Tree colours by type (Dark / Mid / Light) ─────────────────────────────────
# EMBER
const EMBER_DARK  := Color(0.70, 0.22, 0.05, 1.0)
const EMBER_MID   := Color(0.90, 0.45, 0.10, 1.0)
const EMBER_LIGHT := Color(1.00, 0.75, 0.30, 1.0)
# FROST
const FROST_DARK  := Color(0.35, 0.55, 0.75, 1.0)
const FROST_MID   := Color(0.60, 0.80, 0.95, 1.0)
const FROST_LT    := Color(0.85, 0.95, 1.00, 1.0)
# BLOOM
const BLOOM_DARK  := Color(0.55, 0.20, 0.50, 1.0)
const BLOOM_MID   := Color(0.85, 0.42, 0.65, 1.0)
const BLOOM_LIGHT := Color(0.95, 0.75, 0.85, 1.0)
# STONE tree (separate from soil stone above)
const STONE_DARK  := Color(0.35, 0.33, 0.30, 1.0)
const STONE_MID   := Color(0.55, 0.53, 0.50, 1.0)
const STONE_LIGHT := Color(0.72, 0.70, 0.68, 1.0)
# WISP
const WISP_DARK   := Color(0.40, 0.20, 0.60, 1.0)
const WISP_MID    := Color(0.65, 0.45, 0.85, 1.0)
const WISP_LIGHT  := Color(0.85, 0.75, 1.00, 1.0)

# ─ Bond colours ──────────────────────────────────────────────────────────────────
const STEAM      := Color(0.90, 0.92, 1.00, 1.0)   # white-blue steam
const OVERGROWTH := Color(0.25, 0.80, 0.35, 1.0)   # vivid green
const AMPLIFY    := Color(1.00, 0.85, 0.25, 1.0)   # warm gold
const HIGHLIGHT  := Color(1.00, 0.90, 0.50, 1.0)   # soft yellow hover

# ─ Helpers ────────────────────────────────────────────────────────────────────────────

func tree_primary(tree_type: int) -> Color:
	"""Return the primary (mid) colour for a given tree type."""
	match tree_type:
		0: return EMBER_MID
		1: return FROST_MID
		2: return BLOOM_MID
		3: return STONE_MID
		4: return WISP_MID
		_: return PARCHMENT

func tree_light(tree_type: int) -> Color:
	"""Return the light highlight colour for a given tree type."""
	match tree_type:
		0: return EMBER_LIGHT
		1: return FROST_LT
		2: return BLOOM_LIGHT
		3: return STONE_LIGHT
		4: return WISP_LIGHT
		_: return PARCHMENT

func tree_dark(tree_type: int) -> Color:
	"""Return the dark shadow colour for a given tree type."""
	match tree_type:
		0: return EMBER_DARK
		1: return FROST_DARK
		2: return BLOOM_DARK
		3: return STONE_DARK
		4: return WISP_DARK
		_: return WOOD_DARK
