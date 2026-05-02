#!/usr/bin/env python3
"""harness_run.py — AI-driven game development loop for Pixel Werewolf (Python)."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

_HARNESS_DIR = Path(__file__).resolve().parent.parent / "Harness-Everything"
if _HARNESS_DIR.exists() and str(_HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(_HARNESS_DIR))


def main():
    parser = argparse.ArgumentParser(description="Harness agent for Pixel Werewolf")
    parser.add_argument("--cycles", type=int, default=0,
                        help="Override max_cycles (0 = use config value)")
    args = parser.parse_args()

    project_dir = Path(__file__).resolve().parent
    config_path = project_dir / "harness.json"
    with open(config_path, encoding="utf-8") as f:
        raw = json.load(f)

    # Resolve API key from env
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if api_key and not raw["harness"].get("api_key"):
        raw["harness"]["api_key"] = api_key

    # Extract game config
    game_cfg = raw.pop("game", {})
    game_type = game_cfg.get("game_type", "python")
    entry = game_cfg.get("entry_point", "main.py")
    os.environ.setdefault("HARNESS_GAME_TYPE", game_type)
    os.environ.setdefault("HARNESS_GAME_ENTRY", entry)
    os.environ.setdefault(
        "HARNESS_GAME_PATH",
        str(project_dir.resolve()),
    )
    os.environ.setdefault("HARNESS_GAME_PORT", "19840")

    # Build agent config
    from harness.agent import AgentConfig, AgentLoop
    agent_cfg = AgentConfig.from_dict(raw)
    if args.cycles > 0:
        agent_cfg.max_cycles = args.cycles

    print("=" * 60)
    print("  Pixel Werewolf — Harness Agent (Python)")
    print(f"  model     = {agent_cfg.harness.model}")
    print(f"  workspace = {agent_cfg.harness.workspace}")
    print(f"  max_cycles= {agent_cfg.max_cycles}")
    print(f"  game      = {game_type} ({entry}, port={os.environ['HARNESS_GAME_PORT']})")
    print("=" * 60)

    loop = AgentLoop(agent_cfg)
    result = asyncio.run(loop.run())
    print(f"\n[harness_run] {result.cycles_run} cycles, "
          f"status={result.mission_status}, "
          f"tool_calls={result.total_tool_calls}")
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
