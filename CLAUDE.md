# CLAUDE.md — Harness Everything Game Framework

## Branch Structure

```
main          ← Framework core (this branch). Only harness infrastructure.
                 No game-specific content lives here.
<game-name>   ← Each game lives on its own branch (e.g. werewolf).
                 Contains: Godot project, game scripts, assets,
                 harness.json (game config), harness_run.py (optimization loop).
```

## What the Harness Does

`scripts/test_harness.gd` is a Godot autoload that opens a TCP server on `127.0.0.1:19840`. An external AI agent connects to:
- Capture screenshots (PNG via viewport)
- Inject mouse/keyboard input
- Query game state (reads from GameState autoload's `get_state()`)
- Shut down the game cleanly

Protocol: newline-delimited JSON. See README.md for full command reference.

## Working on the Framework (main branch)

- `scripts/test_harness.gd` is the only source file. Marked DO NOT MODIFY in game projects, but here on main it IS the thing being modified.
- Keep it Godot 4.2+ compatible, GL Compatibility renderer.
- The harness must stay self-contained — no dependencies on game code.
- When adding commands, update README.md's protocol table.

## Working on a Game Branch

Game branches contain:
- `harness.json` — paths, game name, harness settings specific to that game
- `harness_run.py` — launches Godot, connects via TCP, runs the AI optimization loop
- Standard Godot project files

When developing on a game branch:
1. The harness (`test_harness.gd`) is a copy — changes to harness should be made on `main` and merged/copied into game branches.
2. `harness.json` configures where the harness binary/tools are, port settings, screenshot paths, etc.
3. `harness_run.py` is the entry point for the AI-driven optimization cycle.

## Setting Up a New Game Branch

```bash
git checkout -b <game-name> main
mkdir -p scripts scenes
# Copy harness into the new project
cp ../main-branch/scripts/test_harness.gd scripts/
# Create project.godot with TestHarness autoload
# Create harness.json with game-specific paths
# Create harness_run.py for the optimization loop
```

## Design Principles

- Harness is infrastructure, not game logic. It stays out of the way.
- GameState autoload is the bridge: games expose state through it, harness reads it.
- Screenshots are resized to viewport logical size (strips HiDPI scaling) for LLM-friendly file sizes.
