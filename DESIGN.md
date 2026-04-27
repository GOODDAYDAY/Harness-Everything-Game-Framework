# Pixel Werewolf — Design Document

## Core Concept
A single-player social deduction game set in a cozy pixel village. You are one of the villagers. Each night, a werewolf attacks. Each day, the village votes to exile someone. Figure out who the werewolf is through observation, conversation clues, and deductive reasoning — before the village is overrun.

## Core Fantasy
You're a detective in a tiny pixel village. Read body language, notice who's nervous, track alibis, gather clues, and make accusations. Think Mafia/Werewolf meets Ace Attorney meets cozy pixel RPG.

## What Makes It Unique (as a video game, not a party game)
- **AI-driven villager personalities** — each NPC has traits, secrets, behavioral tells, and relationships
- **Observation mechanics** — watch villagers move around the village, notice suspicious behaviour, track who was where at night
- **Evidence system** — gather clues (footprints, torn fabric, alibis) that build a case, not just random voting
- **Conversation mini-game** — interrogate villagers, catch lies, notice contradictions, build trust or suspicion
- **Adaptive werewolf** — it tries to frame others, build false alibis, and manipulate village opinion

---

## Game Structure

A game round follows classic werewolf phases:

### Night Phase
- Screen darkens, villagers go to their cottages
- The werewolf attacks one villager (shown as shadow event)
- Player can peek out the window / listen for clues
- Morning reveals who was attacked

### Day Phase — Investigation
- Player walks around the village freely
- Talk to villagers (they share observations, rumors, lies)
- Examine the attack scene for evidence
- Check villager locations / routines for alibi gaps
- Open your notebook to review gathered clues

### Day Phase — Vote
- Village gathers at the town square
- Player can accuse someone (present evidence)
- Villagers vote (influenced by evidence, relationships, fear)
- Accused is exiled — reveal if they were the werewolf
- **If wrong**: game continues with fewer villagers, more danger
- **If right**: village is saved!

### Win / Lose
- **Win**: correctly identify and exile the werewolf
- **Lose**: too many villagers attacked (werewolf wins) OR player exiled

---

## Villager Roster (8 characters)

Each playthrough randomly assigns one as werewolf. Roles are hidden from the player.

| Name    | Trait         | Visual                          | Personality                              |
|---------|---------------|---------------------------------|------------------------------------------|
| Aldric  | Observant     | Red cap, brown cloak            | Notices everything, shares gossip freely |
| Brina   | Nervous       | Blonde braid, green dress       | Wrings her hands, avoids eye contact     |
| Corvin  | Suspicious    | Dark hat, long grey coat        | Deflects questions, always has an alibi  |
| Dalia   | Friendly      | Flower crown, pink apron        | Trusts everyone, easy to manipulate      |
| Edwin   | Grumpy        | Bald, bushy beard, blue vest    | Accuses others, hard to read             |
| Fenna   | Calm          | Silver hair, white shawl        | Methodical, gives measured opinions      |
| Garth   | Boastful      | Tall hat, orange jacket         | Over-explains, drops hints accidentally  |
| Hilde   | Quiet         | Dark hood, purple dress         | Says little, but watches closely         |

### Behavioral Tells
- **Werewolf**: wanders near attack site, pauses near victim's cottage, avoids gathering spots
- **Innocents**: mostly follow daily routines with minor variation
- All NPCs accumulate "suspicion weight" that biases voting if not countered by evidence

---

## Evidence System

Clues spawn at the attack scene each morning. Player collects them by walking close:

| Clue            | Description                              | Narrows suspects to...      |
|-----------------|------------------------------------------|-----------------------------|
| Muddy footprint | Large / small boot size                  | Aldric, Garth, Edwin / Brina, Dalia, Hilde |
| Torn fabric     | Colour match to villager clothing        | Specific villager           |
| Dropped item    | Item belonging to a villager             | Specific villager           |
| Overheard words | Fragment of speech heard by a witness    | Villager voice + location   |
| Scorch mark     | Near certain cottage                     | Adjacent cottages           |
| Night window    | Light seen in cottage (awake at night)   | Villager who was awake      |

False clues can be planted by the werewolf to frame others.

---

## Conversation System

Click a villager to open a dialogue. Each day, each villager has up to 3 things to say:
1. **Observation** — what they claim to have seen (may be true, false, or hearsay)
2. **Accusation** — who they're suspicious of and why
3. **Alibi** — where they say they were last night

The player notes contradictions in their journal. Catching a liar in a contradiction builds evidence.

---

## Colour Palette

### Day
- Sky: `#C9E8F0` · Ground: `#8DC66A` · Path: `#C8A87A`
- Cottage: `#E8C888` · Roof: `#C85A3C` · Wood: `#7A5C3A`
- UI parchment: `#F5E6C8` · Ink: `#3A2810`

### Night
- Sky: `#0D1B2A` · Ground: `#1E3040` · Path: `#243850`
- Window glow: `#E8C860` · Moon: `#D4E8F0` · Shadow: `#080F1A`

### Villager Palettes
- Body base: `#F0C8A0` (skin) with clothing per character (see roster)
- Guilty tell highlight: subtle desaturation + slower movement

---

## Village Layout (480×270 viewport)

```
┌──────────────────────────────────────────────────────────┐
│  Forest edge (dark tree line, decorative)                │
│  [Aldric]  [Brina]   [Corvin]   [Dalia]                  │
│   Cottage   Cottage   Cottage   Cottage                  │
│                                                          │
│         [ Town Square / Well ]                           │
│                                                          │
│  [Edwin]  [Fenna]   [Garth]   [Hilde]                   │
│   Cottage  Cottage   Cottage   Cottage                   │
│  Path connecting all cottages                            │
└──────────────────────────────────────────────────────────┘
```

Tile size: 16×16 pixels. Map: 30×17 tiles.

---

## Game State Machine

```
STARTUP → NIGHT → MORNING_REVEAL → DAY_INVESTIGATION → DAY_VOTE → (WIN | LOSE | NIGHT)
```

- `phase`: String — current phase name
- `day`: int — current day number (starts at 1)
- `villagers`: Array[Dictionary] — name, alive, role, position, personality
- `evidence`: Array[Dictionary] — type, description, target_hint
- `accusations`: Dictionary — who has been accused and why
- `werewolf_id`: int — index in villagers array (hidden from player)

---

## Technical Architecture

### Autoloads
- `TestHarness` — test infrastructure (do not modify)
- `GameState` — phase, day, villager data, evidence, game flags

### Scenes
- `scenes/main.tscn` — root scene, orchestrates phase transitions
- `scenes/village.tscn` — the village map, villager sprites, player movement
- `scenes/ui/hud.tscn` — phase banner, day counter, evidence notebook button
- `scenes/ui/dialogue.tscn` — conversation overlay
- `scenes/ui/vote.tscn` — vote panel with villager portraits
- `scenes/ui/notebook.tscn` — clue journal

### Scripts
- `scripts/game_state.gd` — GameState autoload
- `scripts/main.gd` — main scene controller
- `scripts/village_map.gd` — village rendering and villager placement
- `scripts/villager.gd` — individual NPC behaviour
- `scripts/player.gd` — player movement and interaction
- `scripts/art/sprite_gen.gd` — procedural sprite generation

---

## Build Phases

| Phase | Cycles | Goal |
|-------|--------|------|
| 1 — Skeleton | 1 | DESIGN.md, GameState, main scene, village layout |
| 2 — Village + Characters | 2–5 | Tile map, procedural sprites, player movement, NPC placement, day/night visuals |
| 3 — Core Loop | 6–10 | Night attack, morning reveal, dialogue, evidence, vote, win/lose |
| 4 — Deduction Depth | 11–15 | NPC AI routines, behavioral tells, werewolf strategy, alibi system |
| 5 — Juice + Polish | 16+ | Ambient effects, transitions, sound, replay variety |

---

## Design Principles

- **DEDUCTION first** — every mechanic serves figuring out the werewolf
- **RANDOMNESS** — different werewolf, clues, and NPC behaviors each run
- **TENSION** — consequences feel real but failure is dramatic not punishing
- **PERSONALITY** — villagers are characters, not tokens
- **COZY** — warm, charming, gentle. Stardew Valley meets Clue, not Among Us meets horror

## What to Avoid
- Gore, violence, horror imagery
- Pure random voting with no deduction
- Walls of text — show suspicion through behaviour, not exposition
- Making the werewolf too obvious or impossible to find
