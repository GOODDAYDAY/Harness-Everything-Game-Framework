# Harness Everything Game Framework

A Godot 4.x framework for AI-driven game development. The core harness opens a TCP interface that lets an external AI agent see your game (screenshots), control it (input injection), and query its state — enabling automated testing, self-optimizing gameplay, and iterative AI-assisted development.

## How It Works

```
Godot Game (TestHarness autoload)
    └── TCP server on 127.0.0.1:19840
         ├── ping        — health check + engine info
         ├── screenshot  — capture viewport to PNG
         ├── input_*     — inject mouse/keyboard events
         ├── state       — query game state via GameState
         └── quit        — controlled shutdown

External AI Agent (Python / any TCP client)
    └── connects → observes screenshots → injects input → reads state → iterates
```

## Project Structure

```
Harness-Everything-Game-Framework/   (main branch — framework only)
├── README.md
├── CLAUDE.md
└── scripts/
    └── test_harness.gd              # Core harness autoload

<game-name>/                         (game branches — e.g. werewolf)
├── project.godot                    # Godot project with TestHarness autoload
├── harness.json                     # Game-specific harness config
├── scripts/
│   ├── test_harness.gd              # Copy of the core harness
│   └── ...                          # Game scripts
└── harness_run.py                   # Optimization loop script
```

## Quick Start — Adding Harness to Your Godot Project

1. Copy `scripts/test_harness.gd` into your Godot project's `scripts/` folder.

2. Register it as an autoload in `project.godot`:
```ini
[autoload]
TestHarness="*res://scripts/test_harness.gd"
```

3. Add a project setting to control harness enable/disable:
```ini
[debug]
test_harness/enabled=true   # or false for release builds
```

4. In your GameState autoload, implement a `get_state()` method that returns a Dictionary with your game's current state. The harness calls this for the `state` command.

5. Run your game. The harness listens on `127.0.0.1:19840` and prints a confirmation to the Godot console.

## TCP Protocol

Newline-delimited JSON over raw TCP. Each message is one JSON object followed by `\n`.

### Request
```json
{"cmd": "ping"}
{"cmd": "screenshot", "path": "/tmp/screen.png"}
{"cmd": "input_click", "x": 100, "y": 200, "button": "left"}
{"cmd": "input_key", "key": "space", "pressed": true}
{"cmd": "input_motion", "x": 150, "y": 250}
{"cmd": "state"}
{"cmd": "quit", "exit_code": 0}
```

### Response
```json
{"ok": true, "engine": "godot", "version": "4.2"}
{"ok": false, "error": "unknown command: foo"}
```

The `state` response includes whatever your GameState's `get_state()` returns under the `"state"` key.

## Branch Conventions

- **main** — framework core (this branch). Only harness infrastructure, no game content.
- **game branches** — each game lives on its own branch (e.g. `werewolf`). They carry their own Godot project, scripts, assets, harness config, and optimization scripts.

## License

MIT
