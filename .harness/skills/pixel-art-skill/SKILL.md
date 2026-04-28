---
name: pixel-art-character
description: Guide for creating pixel art characters, sprites, and game assets. Activates when user mentions pixel art, sprite, sprite sheet, pixel animation, retro game art, 8-bit characters, pixel character design, game sprites, canvas pixel drawing, tileset, or game assets.
---

# Pixel Art & Game Asset Creation

Generate production-quality pixel art using AI tools (PixelLab, SpriteCook) and render/animate them in HTML5 Canvas.

---

## Approach: Choose the Right Tool for the Job

| Goal | Best Approach |
|------|---------------|
| Production-quality sprites, characters, tilesets | **PixelLab or SpriteCook via MCP** — AI generates art indistinguishable from professional pixel artists |
| Simple animated character demo | **Code-only (Buffer Canvas + hLine)** — good for prototypes, chibi-style characters |
| Rendering & animating AI-generated sprites | **Canvas engine** — load sprite sheets, handle animation frames, input, particles |
| Full game scene with multiple assets | **PixelLab/SpriteCook** for asset generation → **Canvas engine** for assembly and interaction |

> **Key insight**: Code-only pixel art (hLine row-by-row) works for simple stylized characters but cannot match the quality of AI-generated sprites for detailed characters, environments, and tilesets. Use AI tools for asset generation and code for rendering/animation.

---

## 1. AI Asset Generation (Production Quality)

### PixelLab — MCP Integration

PixelLab generates pixel art characters, animations, and tilesets from text descriptions.

**Setup with Claude Code:**

```json
// Add to .claude/settings.json or .mcp.json
{
  "mcpServers": {
    "pixellab": {
      "url": "https://api.pixellab.ai/mcp",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer YOUR_API_TOKEN"
      }
    }
  }
}
```

Get your API token at [pixellab.ai](https://www.pixellab.ai). Interactive setup at [pixellab.ai/vibe-coding](https://www.pixellab.ai/vibe-coding).

**Available tools:**

```
create_character(description, n_directions)
  → Generate character with 4 or 8 directional views
  → Example: create_character("mushroom druid with staff", n_directions=4)

animate_character(character_id, animation)
  → Add walk/run/idle/attack animations to existing character
  → Example: animate_character("abc123", "walk")

create_tileset(lower, upper)
  → Generate Wang tilesets for seamless terrain
  → Example: create_tileset("grass", "dirt path")

create_isometric_tile(description, size)
  → Individual isometric tiles
  → Example: create_isometric_tile("grass on top of dirt", 32)
```

**Workflow:**
1. Generate character → returns job ID (processes in 2-5 min)
2. Check job status → download sprite sheet when ready
3. Animate character → generates walk/run/idle frames
4. Export to sprite sheet → ready for game engine

**Supported formats:** 32x32, 32x40, custom sizes. Styles: bipedal-realistic, quadrupedal-tiny, bipedal-semi-chibi.

### SpriteCook — MCP Integration

SpriteCook generates pixel art and HD game assets with style consistency.

**Setup with Claude Code:**

```bash
# Automatic installer (Mac/Linux)
bash -c "$(curl -fsSL https://spritecook.ai/install.sh)"

# Windows PowerShell
iwr -useb https://spritecook.ai/install.ps1 | iex
```

Or manual config:

```json
{
  "mcpServers": {
    "spritecook": {
      "url": "https://api.spritecook.ai/mcp/",
      "headers": { "Authorization": "Bearer YOUR_API_KEY" }
    }
  }
}
```

Get your API key at [app.spritecook.ai/api-keys](https://app.spritecook.ai/api-keys).

**Key workflow — Style Consistency:**
1. Generate ONE hero asset first (e.g., the main character)
2. Use that asset's ID as style reference for all other assets
3. This keeps art consistent across characters, items, props, and tilesets

**Example prompt flow:**
```
"Generate a pixel art cow for a cozy farming game"
→ Creates cow sprite with unique asset ID

"Generate a barn in the same style as [cow asset ID]"
→ Creates barn matching the cow's art style

"Generate tree sprites in the same style"
→ Consistent trees matching the whole set
```

**Capabilities:** Sprites, characters, items, tilesets, UI, backgrounds. Both pixel art and HD styles.

### Other AI Tools

| Tool | Best For |
|------|----------|
| **PixelBox** (llamagen.ai) | Free browser-based pixel art sprite animation |
| **pixel-plugin** (Claude Code plugin) | Aseprite integration for natural language pixel art |
| **Stable Diffusion + PixelArt LoRA** | Bulk generation with local GPU, then manual refinement |

---

## 2. Canvas Rendering Engine (Code Patterns)

For rendering AI-generated sprites or building simple pixel art in code. Based on the mushroom druid reference implementation.

### Buffer Canvas Pattern (Critical)

Draw at 1:1 pixel scale on offscreen canvas, scale to display. This produces crisp, non-blurry pixels.

```javascript
// Offscreen buffer at sprite resolution
const W = 56, H = 64;
const buf = document.createElement('canvas');
buf.width = W; buf.height = H;
const bc = buf.getContext('2d');

// Display canvas — with HiDPI/Retina fix
const display = document.getElementById('display');
const DPR = window.devicePixelRatio || 1;
const CSS_W = 460, CSS_H = 310;
display.width = CSS_W * DPR;
display.height = CSS_H * DPR;
display.style.width = CSS_W + 'px';
display.style.height = CSS_H + 'px';

const dctx = display.getContext('2d');
dctx.scale(DPR, DPR);
dctx.imageSmoothingEnabled = false; // CRITICAL

// CSS: canvas { image-rendering: pixelated; image-rendering: crisp-edges; }

// IMPORTANT: use CSS_W/CSS_H (not display.width) for coordinates after DPR scaling
const SCALE = 5;
dctx.drawImage(buf, x, y, W * SCALE, H * SCALE);
```

**HiDPI/Retina fix**: On screens with `devicePixelRatio > 1`, the canvas backing store must be scaled up to match device pixels. Without this, the browser interpolates between CSS pixels causing blurry sprites. After `dctx.scale(DPR, DPR)`, all coordinates stay in CSS pixels but render at native resolution.

**Critical**: After this fix, always use `CSS_W`/`CSS_H` instead of `display.width`/`display.height` for coordinate math (translate, clearRect, bounds checks). `display.width` is now the DPR-scaled physical size.

**Re-enforce smoothing**: `imageSmoothingEnabled` can reset after `save/restore` or `scale`. Re-set it before every `drawImage`:

```javascript
dctx.imageSmoothingEnabled = false; // re-enforce before blit
dctx.drawImage(buf, x, y, W * SCALE, H * SCALE);
```

### Loading & Rendering Sprite Sheets

When using AI-generated sprite sheets:

```javascript
const sheet = new Image();
sheet.src = 'character-spritesheet.png';
sheet.onload = () => {
  // Each frame is FRAME_W x FRAME_H in the sheet
  const FRAME_W = 32, FRAME_H = 40;
  const COLS = sheet.width / FRAME_W;

  function drawFrame(frameIndex) {
    const col = frameIndex % COLS;
    const row = Math.floor(frameIndex / COLS);
    dctx.drawImage(sheet,
      col * FRAME_W, row * FRAME_H, FRAME_W, FRAME_H,  // source
      x, y, FRAME_W * SCALE, FRAME_H * SCALE            // dest
    );
  }
};
```

### Hue-Shifted Palette (for code-only sprites)

When drawing sprites manually, use hue-shifted color ramps:

```javascript
const P = {
  // Shadows → cool (blue/purple), highlights → warm (yellow/orange)
  // Example: red mushroom cap
  C0: '#4a1018',  // darkest (purple-shifted)
  C3: '#c03830',  // base red
  C7: '#f88868',  // brightest (orange-shifted)

  // Example: green cloak
  G0: '#102810',  // darkest (blue-shifted)
  G4: '#489830',  // base green
  G8: '#98e870',  // brightest (yellow-shifted)
};
```

**Rule**: 8-12 tones per material, never pure value darkening.

### Advanced Technique: Selective Outlining (Selout)

Replace pure black outlines with **colored outlines** that match nearby hues. This is the single biggest quality improvement for pixel art sprites.

```javascript
const P = {
  // SELOUT OUTLINES — one per material region
  OC: '#3a1014',  // cap outline (dark red, not black)
  OB: '#2a1810',  // brim outline (dark brown)
  OF: '#2a1810',  // face outline (warm dark)
  OG: '#0c1c0c',  // cloak outline (dark green)
  OW: '#1a1008',  // staff/feet outline (dark wood)
  OL: '#10080a',  // high-contrast areas only (near-black)
};
```

**Rules:**
- Light-facing edges → lighter outline (1 shade darker than fill)
- Shadow-facing edges → darker outline
- Internal lines → selout color matching the darker fill nearby
- Only keep near-black outline where maximum contrast is needed

### Advanced Technique: Anti-Aliasing (AA)

Add intermediate color pixels on curved edges (>1px staircase patterns). Do NOT AA straight lines or 45-degree diagonals.

```javascript
// AA row above cap dome — soften edge against background
hL(ox+10, oy-1, [AA_dark, AA_dark, AA_dark, AA_dark]);

// Cap dome with AA at edges
hL(ox+9, oy, [AA_dark, OUTLINE, OUTLINE, ..., OUTLINE, AA_dark]);
```

**Rules:**
- AA halftone = value halfway between outline and background
- Only on staircase steps >1px long
- Horizontal slopes get horizontal AA, vertical slopes get vertical AA
- Less is more — too much AA = blurry

### Advanced Technique: Dithering

Checkerboard pattern between two adjacent tones to create texture and smooth gradients:

```javascript
// Dithered fill for texture
function dither(x, y, w, h, c1, c2) {
  for (let dy = 0; dy < h; dy++)
    for (let dx = 0; dx < w; dx++) {
      bc.fillStyle = (dx+dy) % 2 === 0 ? c1 : c2;
      bc.fillRect(x+dx, y+dy, 1, 1);
    }
}
```

**Use for:** metal armor transitions, fabric folds, wood grain, stone surfaces. Avoid on skin and smooth surfaces.

### Drawing Helpers

```javascript
function px(x, y, col) {
  bc.fillStyle = col;
  bc.fillRect(x, y, 1, 1);
}

function hLine(x, y, colors) {
  for (let i = 0; i < colors.length; i++)
    if (colors[i]) { bc.fillStyle = colors[i]; bc.fillRect(x+i, y, 1, 1); }
}
```

### Modular Body Parts

Split character into functions that animate independently:

```javascript
function drawCharacter(bob, blink, walkStep) {
  bc.clearRect(0, 0, W, H);
  const baseY = 6 + bob + walkBounce;  // body moves

  drawStaff(baseX + 21, baseY + 2);
  drawCap(baseX - 2, baseY);
  drawFace(baseX + 5, baseY + 14, blink);
  drawCloak(baseX + 5, baseY + 20, cloakSway);

  // FEET: fixed Y — anchored to ground, no bob
  drawFeet(baseX + 6, FIXED_FEET_Y, walkStep);
}
```

---

## 3. Animation System

### State Machine

```javascript
const st = {
  x: 180, dir: 1,
  walking: false, walkDir: 0, walkFrame: -1,
  animFrame: 0,
  blinkTimer: 0, blink: false,
  attackTimer: -1,
  particles: [],
};
```

### Grounding (Feet on Floor)

```javascript
const GROUND_Y = 290;

// CRITICAL: Calculate CHAR_DRAW_Y from the ACTUAL bottom row of feet/boots
// in the buffer, NOT a guess. Count the exact buffer row where the last
// boot pixel is drawn, then anchor that to GROUND_Y.
//
// Example: if bootsY = 32 and boots are 2 rows tall → bottom = row 34
const BOOTS_BOTTOM_ROW = 34; // measure this from your drawBoots function!
const CHAR_DRAW_Y = GROUND_Y - BOOTS_BOTTOM_ROW * RENDER_SCALE;

// Shadow follows character direction (CSS_W, not display.width after DPR fix)
const shadowX = st.dir === 1 ? st.x + 68 : st.x + W * SCALE - 68;
dctx.fillStyle = 'rgba(0,0,0,0.30)';
dctx.beginPath();
dctx.ellipse(shadowX, GROUND_Y, 32, 6, 0, 0, Math.PI * 2);
dctx.fill();
```

**Common bug**: Setting `CHAR_DRAW_Y` with a wrong row number causes the character to float above ground. Always trace the exact buffer row of the lowest pixel in `drawBoots`/`drawFeet` and use that value.

### Walk Cycle (4 Frames)

```
Step 0: Contact — both feet down
Step 1: Left forward — body dips 1px, cloak sways left
Step 2: Passing — feet close
Step 3: Right forward — body dips 1px, cloak sways right
```

### Direction Flipping

```javascript
// IMPORTANT: use CSS_W (not display.width) after DPR fix
if (st.dir === -1) {
  dctx.save();
  dctx.translate(CSS_W, 0);
  dctx.scale(-1, 1);
  dctx.imageSmoothingEnabled = false; // re-enforce after scale
  dctx.drawImage(buf, CSS_W - st.x - W*SCALE, CHAR_DRAW_Y, W*SCALE, H*SCALE);
  dctx.restore();
}
// ALL offsets must mirror: particles, shadow, effects
const footX = st.dir === 1 ? st.x + 70 : st.x + W * SCALE - 70;
```

### Game Loop

```javascript
// Animation ticks at ~7 FPS (pixel art frames)
// Movement at 60 FPS (smooth sliding)
let lastTick = 0;
function loop(ts) {
  if (ts - lastTick > 150) { lastTick = ts; st.animFrame++; updateAnimations(); }
  if (st.walking) { st.x += st.walkDir * 2; st.dir = st.walkDir; }
  render();
  requestAnimationFrame(loop);
}
```

### Particle System

```javascript
function spawnParticle(x, y, type) {
  const colors = type === 'magic'
    ? ['#78e050','#50c038','#a0f070','#ccffcc']
    : ['#68c848','#489830','#80d858'];
  st.particles.push({
    x: x + (Math.random()-0.5) * 20,
    y: y - Math.random() * 10,
    vx: (Math.random()-0.5) * 2,
    vy: -Math.random() * 1.5 - 0.5,
    life: 40 + Math.random() * 40, maxLife: 80,
    color: colors[Math.floor(Math.random() * colors.length)],
    size: RENDER_SCALE,
  });
}
```

---

## 4. Common Pitfalls

| Mistake | Symptom | Fix |
|---------|---------|-----|
| No `imageSmoothingEnabled = false` | Blurry pixels when scaled | Set before every `drawImage`, re-set after `save/restore` |
| No HiDPI/DPR fix | Blurry on Retina/4K screens | `canvas.width = CSS_W * DPR` + `ctx.scale(DPR, DPR)` |
| Using `display.width` after DPR fix | Wrong coordinates (2x too large) | Use `CSS_W`/`CSS_H` for all coordinate math |
| Bob applied to feet | Character floats off ground | Fixed feetY, only bob the body/head |
| Wrong `CHAR_DRAW_Y` calculation | Character floats above ground | Trace exact boot bottom row in buffer, anchor to `GROUND_Y` |
| Shadow/particles don't flip | Effects on wrong side facing left | Mirror X: `st.x + W*SCALE - offset` |
| Eyes asymmetric | Eyes look cross-eyed/diverging | Ensure shine/iris px() positions are same relative column in each eye |
| Pillow shading | Character looks inflated/flat | Pick ONE light direction, commit to it |
| Pure black outlines | Chunky, unprofessional look | Use **selout**: colored outlines per material region |
| Pure value shading | Muddy, lifeless colors | Hue shift: shadows→cool, highlights→warm |
| No AA on curves | Jagged dome/circle edges | Add 1px intermediate color on staircase steps >1px |
| `O` undefined in draw function | ReferenceError crash | Each draw function must define `const O = P.XX` locally, or use `P.XX` directly |
| Weapon drawn on wrong side in buffer | Attack goes backward when sprite is flipped | Sprite faces RIGHT in buffer. Draw weapon attacks to the RIGHT (positive X). The `scale(-1,1)` flip will mirror it correctly |
| Weapon/effects not passed attack state | Sprites stay in idle pose during attack | Pass `attacking` boolean to draw functions: `drawSprite(bc, bob, walkStep, attacking)` |
| Shadow drawn after character | Shadow overlaps character's feet | Draw order: background → ground → shadows → character sprites → effects → particles → UI |
