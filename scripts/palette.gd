# Palette — Autoload singleton
# Provides the canonical colour palette and helper functions for Ember Grove.
extends Node

# ── Background & UI ────────────────────────────────────────────────────────────
const BG          := Color("#2C1810")   # warm dark brown
const BG_LIGHT    := Color("#3D2B1F")   # dark wood (grid lines)
const PARCHMENT   := Color("#F5E6D3")   # light cream text / UI
const PARCHMENT2  := Color("#EDD9BE")   # slightly darker parchment
const WOOD        := Color("#6B4226")   # medium wood tone
const WOOD_DARK   := Color("#4A2C14")   # dark wood border

# ── Tree primary colours ───────────────────────────────────────────────────────
const EMBER       := Color("#E8762C")   # fire orange
const EMBER_LT    := Color("#F4A261")   # ember highlight
const EMBER_DK    := Color("#C0501A")   # ember shadow

const FROST       := Color("#74B9D8")   # ice blue
const FROST_LT    := Color("#B8DCF0")   # frost highlight
const FROST_DK    := Color("#4A8AAA")   # frost shadow

const BLOOM       := Color("#E8A0BF")   # life pink
const BLOOM_LT    := Color("#F4C2D4")   # bloom highlight
const BLOOM_DK    := Color("#C06090")   # bloom shadow

const STONE       := Color("#8B7355")   # earth brown
const STONE_LT    := Color("#A89070")   # stone highlight
const STONE_DK    := Color("#5C4A30")   # stone shadow

const WISP        := Color("#9B72CF")   # magic purple
const WISP_LT     := Color("#C4A8E8")   # wisp highlight
const WISP_DK     := Color("#6A48A0")   # wisp shadow

# ── Bond / effect colours ─────────────────────────────────────────────────────
const STEAM       := Color("#DDEEFF")   # steam white-blue
const OVERGROWTH  := Color("#7EC850")   # vivid green
const AMPLIFY     := Color("#FFD966")   # golden yellow

# ── UI accents ────────────────────────────────────────────────────────────────
const HIGHLIGHT   := Color("#FFE08A")   # hover / selected yellow
const DISABLED    := Color("#7A6855")   # greyed out
const SUCCESS     := Color("#90E0A0")   # positive feedback green
const WARNING     := Color("#F4A261")   # caution orange (same as EMBER_LT)

# ── Helper ────────────────────────────────────────────────────────────────────
func tree_primary(tree_type: int) -> Color:
	match tree_type:
		0: return EMBER
		1: return FROST
		2: return BLOOM
		3: return STONE
		4: return WISP
	_: return PARCHMENT

func tree_light(tree_type: int) -> Color:
	match tree_type:
		0: return EMBER_LT
		1: return FROST_LT
		2: return BLOOM_LT
		3: return STONE_LT
		4: return WISP_LT
	_: return PARCHMENT

func tree_dark(tree_type: int) -> Color:
	match tree_type:
		0: return EMBER_DK
		1: return FROST_DK
		2: return BLOOM_DK
		3: return STONE_DK
		4: return WISP_DK
	_: return WOOD_DARK
