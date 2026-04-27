# Ember Grove — Design Document

## Core Concept
Tend a magical forest by placing five types of enchanted trees on a hex-like grid. Trees don't just grow — they **resonate**. Adjacent trees of complementary types form glowing "harmony bonds" that score big and unlock visual chain reactions.

## What Makes It Unique
You're not farming — you're **composing**. Every tree placement is like placing a musical note. The right neighbour creates harmony; the wrong one creates discord. The satisfying "click" when a harmony bond lights up is the core dopamine hit.

## The Five Tree Types
| Tree | Element | Colour |
|------|---------|--------|
| Ember | Fire | Warm orange |
| Frost | Ice | Soft blue |
| Bloom | Life | Blush pink |
| Stone | Earth | Muted brown |
| Wisp | Magic | Soft purple |

## Harmony Pairs (the twist)
- **Ember + Frost** → Steam Bond: ×2 score multiplier, glowing white pulse
- **Bloom + Stone** → Overgrowth Bond: spreads bonus to all 4 adjacent cells
- **Wisp + Any** → Amplify Bond: doubles that tree's harmony score

## Randomness
- Grove layout is procedurally generated (blocked/open cells vary each run)
- Starting hand of 5 seeds is random from weighted pool
- Each round brings a random Weather Event: Rain (Bloom ×1.5), Drought (Frost –1 bond), Meteor (free Wisp seed), Fog (hides 3 cells)
- Seed draws between rounds shuffle with a deck mechanic — guaranteed variety

## Player Decisions
- **Where** to place a seed (positioning for future bonds)
- **Which** seed to play now vs save for later
- **When** to trigger a Wisp amplify chain vs place it for zone coverage
- Risk/reward: place Ember next to Frost for Steam (great!) or next to Bloom (wasted slot?)

## Win Condition
Fill the grove (12 cells on a 4×3 grid). Score each tree + bonds. Beat the threshold (scales by difficulty) to "harmonise" the grove. Gentle — no hard failure, just aim higher next time.

## Colour Palette
`#2C1810` bg · `#E8762C` ember · `#74B9D8` frost · `#E8A0BF` bloom · `#8B7355` stone · `#9B72CF` wisp · `#F5E6D3` parchment

## Moment-to-Moment Loop
1. Draw seeds (3 per round, random from deck)
2. See weather event for this round
3. Place 1–3 seeds into grove
4. Watch harmony bonds light up with chain animations
5. Draw next round — repeat until grove full
6. Final harmony score + sparkle celebration
