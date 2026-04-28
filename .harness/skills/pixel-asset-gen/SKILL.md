---
name: pixel-asset-gen
description: >
  Generate pixel art game assets (characters, weapons, tiles, UI, items, backgrounds, animations)
  using ByteDance's Seedream image generation API via Volcengine. Use this skill whenever the user
  wants to create pixel art images, game sprites, pixel-style illustrations, or any game asset
  for their project. Trigger on phrases like "生成像素素材", "pixel art", "generate sprite",
  "帮我生成游戏图片", "draw a pixel character", "make a tileset", or any request to create
  visual game assets. Also trigger when the user describes what a game object should look like
  and wants an image of it. Even if the user just says something like "帮我画个角色" or
  "I need a sword icon for my game", this skill should kick in.
---

# Pixel Art Game Asset Generator

You help game developers generate pixel art assets by calling the Volcengine Seedream image generation API.

## Environment Setup

The user must have `ARK_API_KEY` set (Volcengine Ark API key from https://www.volcengine.com).
If it's not set, tell them to run: `export ARK_API_KEY=your_key_here`

## Core Workflow

1. Understand what asset the user needs
2. Build an optimized pixel art prompt using the guidelines below
3. Run the generation script to call the API
4. Show the user the result (URL + saved file path)

## Prompt Engineering for Pixel Art

Good pixel art prompts have this structure:
```
[style descriptor], [subject], [details], [color palette], [background], [quality tags]
```

**Always include these style anchors** (pick the right tier):
- 8-bit: `8-bit pixel art, NES style, limited color palette, chunky pixels`
- 16-bit: `16-bit pixel art, SNES style, retro game sprite, detailed pixels`
- Modern pixel: `pixel art, indie game style, clean pixels, vibrant colors`

**Asset-type templates** — the user is making a **pixel art board game (桌游)**. Adapt these to their description:

| Asset Type | Chinese | Key prompt additions |
|------------|---------|----------------------|
| Card illustration | 卡牌插图 | `card art, portrait orientation, centered composition, detailed illustration` |
| Card back | 卡背 | `card back design, symmetrical pattern, decorative border` |
| Character portrait | 角色肖像 | `character portrait, bust shot, detailed face, RPG character` |
| Board tile | 棋盘格/地图格 | `board game tile, top-down, seamless, hex tile or square tile` |
| Token / marker | 棋子/标记 | `game token, top-down view, circular icon, small marker` |
| Resource icon | 资源图标 | `resource icon, small badge, gold/wood/stone/food style` |
| Terrain tile | 地形 | `terrain tile, board game map tile, forest/mountain/water/plains` |
| Enemy/creature | 怪物/生物 | `monster portrait, creature art, board game enemy card art` |
| Item / relic | 道具/遗物 | `item card art, relic icon, equipment illustration` |
| Board background | 棋盘背景 | `game board background, parchment texture, aged map style` |
| UI / HUD frame | 卡框/UI框 | `card frame, ornate border, UI frame, decorative panel` |
| Dice / die face | 骰子 | `dice face, pixel art die, D6 face, game dice icon` |

**Always end the prompt with:**
`white background, pixel perfect, game asset, clean edges, no anti-aliasing`

**Example transformations:**

User says: "一个手持火焰剑的骑士角色"
→ `16-bit pixel art, SNES style, knight character holding a flaming sword, full armor, red and gold color scheme, character sprite, front-facing pose, white background, pixel perfect, game asset, clean edges, no anti-aliasing`

User says: "草地瓦片"
→ `8-bit pixel art, NES style, grass terrain tile, green color palette, seamless tileset tile, top-down view, white background, pixel perfect, game asset, clean edges, no anti-aliasing`

## Running the Generation Script

Use the bundled script to call the API. The script handles API calls, saves the image locally, and prints the result.

**Important:** Always run with proxy bypassed (Volcengine is a Chinese domestic service):
```bash
NO_PROXY="ark.cn-beijing.volces.com" http_proxy="" https_proxy="" \
python /Users/relivelin/.claude/skills/pixel-asset-gen/scripts/generate.py \
  --prompt "YOUR_OPTIMIZED_PROMPT" \
  --output-dir "./assets" \
  --filename "descriptive_name.png"
```

**Parameters:**
- `--prompt`: The full optimized pixel art prompt
- `--output-dir`: Where to save the image (default: `./assets`, creates if missing)
- `--filename`: Output filename (use snake_case descriptive name, e.g. `knight_sprite.png`)
- `--model`: Model ID (default: `doubao-seedream-4-0-250828`; use `doubao-seedream-3-0-t2i-250415` for budget/quick drafts, `doubao-seedream-4-5-251128` for high-res final assets, `doubao-seedream-5-0-260128` for the latest quality)
- `--size`: Image size (default: `1024x1024`, options: `512x512`, `1024x1024`)

The script prints the saved file path and image URL on success.

## After Generation

1. Tell the user where the file was saved
2. Show them the image URL so they can preview it in a browser
3. Ask if they want adjustments — common tweaks:
   - "更大的像素颗粒感" → add `large pixel blocks, very chunky pixels` to prompt
   - "更丰富的细节" → switch from 8-bit to 16-bit in prompt
   - "不同的配色" → specify a concrete palette (e.g., `earth tones`, `cool blues and purples`)
   - "动画帧" → add `animation frames, sprite sheet, multiple poses`

## Batch Generation

If the user wants multiple assets at once (e.g., "帮我生成整套RPG素材"), generate them one by one using the script in a loop, giving each a clear descriptive filename. After all are done, list all saved paths together.

## Troubleshooting

- **API key error**: Remind user to set `ARK_API_KEY`
- **Model not found**: Try `doubao-seedream-3-0` as fallback model name
- **Poor quality results**: Refine the prompt — add more specific color and style details, or switch to a higher-tier model
- **Image looks blurry**: Add `pixel perfect, sharp edges, no blur, no anti-aliasing` to the prompt
