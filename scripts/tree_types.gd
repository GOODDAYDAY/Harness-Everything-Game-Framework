# TreeTypes — Autoload singleton
# Defines all tree species, their base scores, and harmony bond rules.
extends Node

# Tree type constants  (used everywhere as integers)
const EMBER := 0
const FROST := 1
const BLOOM := 2
const STONE := 3
const WISP  := 4
const NONE  := -1

const NAMES := ["Ember", "Frost", "Bloom", "Stone", "Wisp"]
const EMOJIS := ["🔥", "❄️", "🌸", "🪨", "✨"]
const DESCRIPTIONS := [
	"Warm and fierce — loves cold neighbours",
	"Cool and calm — pairs beautifully with Ember",
	"Full of life — grows stronger on solid ground",
	"Sturdy and patient — nurtures Bloom nearby",
	"Mysterious — amplifies everything it touches",
]

# Base score each tree contributes (before bonds)
const BASE_SCORES := [2, 2, 2, 2, 3]  # Wisp is inherently rarer / worth more

# ── Harmony bond definitions ──────────────────────────────────────────────────
# Each entry: { a, b, name, description, bond_type }
# bond_type: "steam", "overgrowth", "amplify"
const BONDS := [
	{
		"a": EMBER, "b": FROST,
		"name": "Steam Bond",
		"description": "Fire meets ice — creates billowing steam. ×2 score for both!",
		"bond_type": "steam",
		"score_bonus": 4,
	},
	{
		"a": BLOOM, "b": STONE,
		"name": "Overgrowth Bond",
		"description": "Life roots into stone — spreads +1 to all adjacent cells.",
		"bond_type": "overgrowth",
		"score_bonus": 3,
	},
]

# Wisp amplifies any neighbour
const WISP_AMPLIFY_BONUS := 2

# ── Seed deck weights ─────────────────────────────────────────────────────────
# Probability weight for drawing each seed type
# (Wisp is rarer, Stone/Ember/Frost/Bloom more common)
const DRAW_WEIGHTS := [3, 3, 3, 3, 1]  # Wisp weight = 1

func get_name(t: int) -> String:
	if t < 0 or t >= NAMES.size(): return "Empty"
	return NAMES[t]

func get_base_score(t: int) -> int:
	if t < 0 or t >= BASE_SCORES.size(): return 0
	return BASE_SCORES[t]

func check_harmony(a: int, b: int) -> Dictionary:
	"""Return bond info dict if (a,b) form a harmony pair, else empty dict."""
	for bond in BONDS:
		if (bond.a == a and bond.b == b) or (bond.a == b and bond.b == a):
			return bond
	# Check Wisp amplify
	if a == WISP or b == WISP:
		var other := b if a == WISP else a
		if other != NONE:
			return {
				"a": WISP, "b": other,
				"name": "Wisp Amplify",
				"description": "Wisp magic amplifies its neighbour!",
				"bond_type": "amplify",
				"score_bonus": WISP_AMPLIFY_BONUS,
			}
	return {}

func draw_seed(rng: RandomNumberGenerator) -> int:
	"""Draw a random seed type using weighted probabilities."""
	var total := 0
	for w in DRAW_WEIGHTS:
		total += w
	var roll := rng.randi_range(0, total - 1)
	var acc := 0
	for i in DRAW_WEIGHTS.size():
		acc += DRAW_WEIGHTS[i]
		if roll < acc:
			return i
	return 0
