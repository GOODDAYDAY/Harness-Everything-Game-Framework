---
name: 2d-essentials
description: Use when working with 2D-specific systems — TileMaps, parallax scrolling, 2D lights and shadows, canvas layers, particles 2D, custom drawing, and 2D meshes in Godot 4.3+
---

# 2D Essentials in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, then C#.

> **Related skills:** **player-controller** for CharacterBody2D movement patterns, **animation-system** for AnimatedSprite2D and sprite animation, **physics-system** for collision shapes and raycasting, **camera-system** for Camera2D follow and shake, **shader-basics** for 2D shaders and post-processing, **godot-optimization** for rendering and draw call tuning.

---

## 1. Canvas Layers and Draw Order

### Draw Order Rules

Within a single canvas layer, nodes draw in **scene tree order** — nodes listed lower in the Scene panel draw **on top**. Use `z_index` to override without rearranging the tree.

```gdscript
# Draw this node above siblings (default z_index is 0)
z_index = 10

# Make z_index relative to parent (default: false = global)
z_as_relative = true
```

### CanvasLayer

`CanvasLayer` creates a separate rendering layer with its own transform, independent of the camera. Higher `layer` values draw on top.

| Layer | Typical Use |
|-------|-------------|
| -1 | Parallax backgrounds |
| 0 | Default game layer (all Node2D without CanvasLayer) |
| 1 | HUD / UI overlay |
| 2 | Pause menu, screen transitions |

```
# Scene tree example
Main
├── ParallaxBackground (CanvasLayer, layer = -1)
│   └── Parallax2D
├── World (Node2D — default layer 0)
│   ├── TileMapLayer
│   └── Player
└── HUD (CanvasLayer, layer = 1)
    └── Control
```

> **Note:** CanvasLayers are NOT required to control draw order. For objects within the same game world, use `z_index` or scene tree ordering. CanvasLayers are for elements that should be independent of the camera (HUD, parallax, transitions).

### Canvas Transform

`Camera2D` works by modifying the viewport's `canvas_transform`. For manual control:

```gdscript
# Scroll the canvas directly (equivalent to camera movement)
get_viewport().canvas_transform = Transform2D(0, Vector2(-200, 0))
```

### Coordinate Conversion

```gdscript
# Local to canvas (world) coordinates
var world_pos: Vector2 = get_global_transform() * local_pos
var local_pos: Vector2 = get_global_transform().affine_inverse() * world_pos

# Local to screen coordinates (accounts for camera, stretch, window)
var screen_pos: Vector2 = get_viewport().get_screen_transform() * get_global_transform_with_canvas() * local_pos
```

```csharp
// Local to canvas (world) coordinates
Vector2 worldPos = GetGlobalTransform() * localPos;
Vector2 localFromWorld = GetGlobalTransform().AffineInverse() * worldPos;

// Local to screen coordinates
Vector2 screenPos = GetViewport().GetScreenTransform() * GetGlobalTransformWithCanvas() * localPos;
```

---

## 2. TileMap System

> **Deprecation notice:** The old `TileMap` node (with in-node layer management) is deprecated as of Godot 4.3. Use individual `TileMapLayer` nodes instead — one node per layer. All examples in this skill use the current `TileMapLayer` approach. If you encounter legacy code using the old `TileMap` node, migrate by replacing it with separate `TileMapLayer` nodes sharing the same `TileSet` resource.

### TileSet Resource Setup

1. Add a `TileMapLayer` node
2. Create a new `TileSet` resource in its inspector
3. Set **Tile Size** (e.g. 16×16) BEFORE creating atlases
4. Drag your tilesheet texture into the TileSet panel → answer "Yes" to auto-create tiles

**Save the TileSet** as an external `.tres` resource (click dropdown → Save) to reuse across levels.

### TileSet Properties

| Property | Purpose |
|----------|---------|
| `Tile Shape` | Square (default), Isometric, Half-Offset Square, Hexagon |
| `Tile Size` | Tile dimensions in pixels |
| `Rendering > UV Clipping` | Clip tiles by their coordinates |

### Atlas Properties

| Property | Purpose |
|----------|---------|
| `Margins` | Edge margins in pixels |
| `Separation` | Gap between tiles in pixels |
| `Texture Region Size` | Size of each tile on the atlas |
| `Use Texture Padding` | 1px transparent border to prevent bleeding (recommended ON) |

### Physics on Tiles

1. TileSet inspector → unfold **Physics Layers** → Add Element
2. In the atlas tile editor, select a tile → press `F` for default rectangle collision
3. Click to add polygon points, right-click to remove, drag edges to insert

### Terrain Autotiling

Terrains automatically select the correct tile based on neighboring tiles.

1. TileSet inspector → **Terrain Sets** → Add Element
2. Choose mode:
   - **Match Corners and Sides** — full 3×3 matching (47 tiles for complete set)
   - **Match Corners** — 2×2 matching (simpler, fewer tiles)
   - **Match Sides** — sides only, ignore corners (minimal set)
3. Add terrains within each set (e.g. "Grass", "Dirt", "Water")
4. Configure **Terrain Peering Bits** on each tile in the atlas editor

### Painting Tiles

| Mode | Shortcut | Notes |
|------|----------|-------|
| Paint | Left-click | `Shift` = line, `Ctrl+Shift` = rectangle |
| Erase | Right-click | Also works with Paint/Line/Rect modes |
| Picker | `Ctrl+click` | Pick tile from placed tiles |
| Bucket Fill | — | Toggle Contiguous checkbox for fill-all behavior |
| Terrain Connect | — | Tiles connect to all neighbors |
| Terrain Path | — | Tiles connect only within current stroke |

### Scattering and Randomization

Enable **randomization** to randomly choose from selected tiles when painting. Set **Scattering** > 0 for a chance of placing no tile (useful for non-repeating detail like grass tufts).

### Multiple Layers

Use multiple `TileMapLayer` nodes for foreground/background separation. Only one tile per layer at a given position — overlap via multiple layers.

```
Level
├── TileMapLayer (Background — behind player)
├── TileMapLayer (Midground — player level)
├── Player
└── TileMapLayer (Foreground — in front of player, higher z_index)
```

### Custom Data on Tiles

1. TileSet inspector → **Custom Data Layers** → Add (e.g. `damage: float`, `destructible: bool`)
2. Set values per tile in the atlas editor

```gdscript
# Read custom data from a tile at runtime
var tile_map: TileMapLayer = $TileMapLayer
var cell: Vector2i = tile_map.local_to_map(global_position)
var tile_data: TileData = tile_map.get_cell_tile_data(cell)
if tile_data:
    var damage: float = tile_data.get_custom_data("damage")
```

```csharp
var tileMap = GetNode<TileMapLayer>("TileMapLayer");
Vector2I cell = tileMap.LocalToMap(GlobalPosition);
TileData tileData = tileMap.GetCellTileData(cell);
if (tileData != null)
{
    float damage = tileData.GetCustomData("damage").AsSingle();
}
```

### Scene Collection Tiles

Place entire scenes as tiles (e.g. doors, chests, spawn points with AudioStreamPlayer2D or particles). Greater performance overhead — each is instanced individually. Use for gameplay elements, not mass terrain.

### Tile Collision Bumps

Characters snagging on edges between adjacent tile colliders is a common issue:
- `TileMapLayer` groups tiles into physics quadrants via **Rendering Quadrant Size** (default 16) which helps reduce edge snagging
- For persistent issues, manually merge adjacent collision polygons into single `StaticBody2D` shapes
- Using `CharacterBody2D` with `floor_snap_length > 0` also reduces edge catching

> See **physics-system** for more collision troubleshooting.

---

## 3. Parallax Scrolling

### Parallax2D Node (Recommended)

`Parallax2D` is the modern replacement for the deprecated `ParallaxBackground`/`ParallaxLayer` nodes.

**Core Properties:**

| Property | Purpose |
|----------|---------|
| `scroll_scale` | Scroll speed multiplier per axis. `1` = camera speed, `<1` = farther, `>1` = closer, `0` = static |
| `repeat_size` | Image size for infinite repeat. Set to texture dimensions for seamless tiling |
| `repeat_times` | Extra repeats behind/in front (increase when zooming out) |
| `scroll_offset` | Offset for the repeat canvas starting point |

### Layer Setup Example (Side-Scroller)

```
Main
├── Camera2D
├── Parallax2D (scroll_scale = 0.1, 0)   ← Sky (slowest)
│   └── Sprite2D (sky texture)
├── Parallax2D (scroll_scale = 0.2, 0)   ← Clouds
│   └── Sprite2D (clouds texture)
├── Parallax2D (scroll_scale = 0.5, 0)   ← Hills
│   └── Sprite2D (hills texture)
├── Parallax2D (scroll_scale = 0.7, 0)   ← Trees
│   └── Sprite2D (trees texture)
└── World (scroll_scale = 1.0 — default)
    ├── TileMapLayer
    └── Player
```

### Infinite Repeat Setup

1. Texture top-left should be at position `(0, 0)` — the repeat canvas starts there and expands down-right
2. Set `repeat_size` to match the texture dimensions
3. Ensure the texture is the same size as or larger than the viewport

```gdscript
extends Parallax2D

func _ready() -> void:
    scroll_scale = Vector2(0.3, 0.0)
    repeat_size = Vector2(1920, 0)  # Match texture width for horizontal repeat
    repeat_times = 3                # Extra repeats for zoom-out safety
```

```csharp
public partial class CloudLayer : Parallax2D
{
    public override void _Ready()
    {
        ScrollScale = new Vector2(0.3f, 0.0f);
        RepeatSize = new Vector2(1920, 0);
        RepeatTimes = 3;
    }
}
```

### Common Mistakes

| Problem | Fix |
|---------|-----|
| Texture centered at (0,0) | Keep top-left at (0,0) — centering breaks infinite repeat |
| Gaps when zooming out | Increase `repeat_times` (e.g. 3) |
| repeat_size doesn't match | Set to actual texture/region size, not viewport size |
| Texture smaller than viewport | Scale the Parallax2D node, or use `texture_repeat = ENABLED` with `region_enabled = true` on Sprite2D |

### Split Screen Parallax

For split-screen games, clone parallax nodes into each `SubViewport`. Use `visibility_layer` on parent nodes and `canvas_cull_mask` on SubViewports to isolate parallax per viewport.

---

## 4. 2D Lights and Shadows

### Node Overview

| Node | Purpose |
|------|---------|
| `CanvasModulate` | Darkens the entire scene (sets ambient color) |
| `PointLight2D` | Omnidirectional/spot light from a point |
| `DirectionalLight2D` | Uniform light from a direction (sun/moon) |
| `LightOccluder2D` | Casts shadows from light sources |

### Basic Setup

1. Add `CanvasModulate` to the scene → set color to dark (e.g. `Color(0.1, 0.1, 0.15)`)
2. Add `PointLight2D` → assign a `Texture` (light shape/gradient) → set `Energy` for intensity
3. For shadows: enable `Shadow > Enabled` on the light, add `LightOccluder2D` nodes to shadow-casting objects

> **Warning:** The background color (Project Settings → Rendering → Environment → Default Clear Color) does NOT receive 2D lighting. Use a full-screen `Sprite2D` or `ColorRect` as your background instead.

### PointLight2D Properties

| Property | Purpose |
|----------|---------|
| `Texture` | Light shape (size determined by texture size) |
| `Texture Scale` | Multiplier for light size (larger = more expensive) |
| `Color` | Light tint |
| `Energy` | Intensity multiplier |
| `Height` | Virtual height for normal mapping (0 = parallel to surface) |
| `Blend Mode` | Add (default), Subtract (negative light), Mix (linear interpolation) |

### Shadow Settings

| Property | Purpose |
|----------|---------|
| `Shadow > Enabled` | Must be enabled for shadows |
| `Shadow > Color` | Shadow tint (default: black) |
| `Shadow > Filter` | None (pixel-art), PCF5 (soft), PCF13 (softest, expensive) |
| `Shadow > Filter Smooth` | Softening amount (higher = softer, may cause banding) |
| `Shadow > Item Cull Mask` | Which LightOccluder2D nodes cast shadows |

### Light Cull Masks

Both lights and occluders have cull masks:
- **Light's Item Cull Mask** → controls which `CanvasItem` nodes receive this light
- **Light's Shadow Item Cull Mask** → controls which `LightOccluder2D` nodes cast shadows for this light
- **LightOccluder2D's Occluder Light Mask** → controls which lights this occluder casts shadows for

### Creating Occluders

- **From Sprite2D:** Select Sprite2D → Sprite2D menu → **Create LightOccluder2D Sibling**
- **Manual:** Add `LightOccluder2D` node → click "+" to create polygon → draw points

### Normal Maps for 2D

Apply per-pixel lighting with normal maps using `CanvasTexture`:

1. Create `CanvasTexture` resource
2. Set `Diffuse > Texture` to the base color sprite
3. Set `Normal Map > Texture` to the normal map
4. Optionally set `Specular > Texture` for reflections
5. Assign the `CanvasTexture` as the Sprite2D's texture

| Property | Purpose |
|----------|---------|
| `Specular > Shininess` | Specular exponent (lower = diffuse, higher = focused) |
| `Specular > Color` | Tint for reflections |

> **Tip:** Use [Laigter](https://azagaya.itch.io/laigter) (free, open source) to generate normal maps from 2D sprites.

### Pixel-Art Lighting

Standard 2D lighting renders at viewport pixel resolution, not texture texel resolution. For pixelated lighting that matches pixel-art aesthetics:

```glsl
shader_type canvas_item;

uniform float pixel_size : hint_range(1.0, 16.0) = 4.0;

void fragment() {
    LIGHT_VERTEX.xy = floor(LIGHT_VERTEX.xy / pixel_size) * pixel_size;
    SHADOW_VERTEX = floor(SHADOW_VERTEX / pixel_size) * pixel_size;
    COLOR = texture(TEXTURE, UV);
}
```

Apply this shader via `ShaderMaterial` on each lit sprite that should have pixelated lighting.

### Additive Sprites as Fake Lights

Set `CanvasItemMaterial > Blend Mode` to **Add** on a Sprite2D for a cheap glow effect. Faster than real lights but no shadows, no normal map support, and inaccurate blending in dark areas.

---

## 5. 2D Particle Systems

### GPUParticles2D vs CPUParticles2D

| Feature | GPUParticles2D | CPUParticles2D |
|---------|----------------|----------------|
| Performance (many particles) | Better | Worse |
| Low-end GPU support | May have issues | More compatible |
| Material | ParticleProcessMaterial | Built-in properties |
| Shader customization | Yes | No |

Use `GPUParticles2D` by default. Convert between types via the toolbar menu.

### Basic Setup

1. Add `GPUParticles2D` node
2. In `Process Material`, create new `ParticleProcessMaterial`
3. Assign a `Texture` (particle sprite)
4. Configure emission, velocity, scale, color

### Key Time Properties

| Property | Purpose |
|----------|---------|
| `Lifetime` | Particle lifespan in seconds |
| `One Shot` | Emit once then stop (explosions, impacts) |
| `Preprocess` | Simulate N seconds before first draw (torches, ambient mist) |
| `Speed Scale` | Global speed multiplier |
| `Explosiveness` | 0 = steady stream, 1 = all particles at once |
| `Randomness` | Random variation on initial values |
| `Local Coords` | On = particles move with node, Off = world space (default) |

### ParticleProcessMaterial Properties

**Emission:**

| Property | Purpose |
|----------|---------|
| `Direction` | Base emission direction (default: right) |
| `Spread` | Angle variance from direction (180 = all directions) |
| `Initial Velocity` | Emission speed (pixels/sec) — must be > 0 for Spread to work |

**Motion:**

| Property | Purpose |
|----------|---------|
| `Gravity` | Applied to all particles |
| `Linear Acceleration` | Per-particle acceleration |
| `Radial Acceleration` | Positive = away from center, negative = toward |
| `Tangential Acceleration` | Perpendicular to radial direction |
| `Damping` | Friction — forces particles to slow down (sparks, explosions) |
| `Angular Velocity` | Rotation speed (degrees/sec) |
| `Orbit Velocity` | Orbital motion around emission center |

**Appearance:**

| Property | Purpose |
|----------|---------|
| `Scale` | Particle scale over lifetime (Min/Max + Curve) |
| `Color` | Static color or gradient (via `Color Ramp`) |
| `Hue Variation` | Randomize hue on spawn |

Most properties support **Min/Max** range (randomized on spawn) and a **Curve** (multiplied over particle lifetime).

### Emission Shapes from Textures

Select GPUParticles2D → **Particles** menu → **Load Emission Mask**:
- **Solid Pixels** — spawn from any non-transparent pixel
- **Border Pixels** — spawn from outer edges only
- **Directed Border Pixels** — border + direction away from center (requires Initial Velocity)
- **Capture from Pixel** — particles inherit color from mask at spawn point

### Flipbook Animation

1. Create `CanvasItemMaterial` in the GPUParticles2D's Material slot
2. Enable `Particle Animation`, set `H Frames` and `V Frames`
3. In ParticleProcessMaterial → Animation: set Speed Min/Max = 1 for linear playback
4. Animation FPS = number of frames / Lifetime

### Visibility Rect

The AABB used for culling. Auto-generate via **Particles** menu → **Generate Visibility Rect**. If particles disappear when the emitter goes offscreen, increase this rect.

### Common Particle Recipes

**Fire:**
```
Direction: (0, -1), Spread: 15°, Initial Velocity: 50-100
Gravity: (0, -20), Damping: 5
Scale: 1.0 → 0.0 (curve), Color Ramp: yellow → orange → transparent
```

**Sparks:**
```
Direction: (0, -1), Spread: 45°, Initial Velocity: 200-400
Gravity: (0, 200), Damping: 10, Explosiveness: 0.8
Scale: 0.5, Lifetime: 0.5, One Shot: true
```

**Dust Trail:**
```
Direction: (0, 0), Spread: 180°, Initial Velocity: 10-30
Gravity: (0, -5), Damping: 3, Local Coords: false
Scale: 0.5 → 1.5 (curve), Color Ramp: white → transparent
```

---

## 6. Custom Drawing

### The _draw() Method

Override `_draw()` on any `CanvasItem`-derived node (Node2D or Control) for custom rendering.

```gdscript
extends Node2D

func _draw() -> void:
    draw_circle(Vector2.ZERO, 50.0, Color.RED)
    draw_rect(Rect2(-25, -25, 50, 50), Color.BLUE, false, 2.0)
    draw_line(Vector2(-100, 0), Vector2(100, 0), Color.WHITE, 2.0, true)
```

```csharp
public partial class CustomDraw : Node2D
{
    public override void _Draw()
    {
        DrawCircle(Vector2.Zero, 50f, Colors.Red);
        DrawRect(new Rect2(-25, -25, 50, 50), Colors.Blue, false, 2f);
        DrawLine(new Vector2(-100, 0), new Vector2(100, 0), Colors.White, 2f, true);
    }
}
```

### Redrawing

`_draw()` is called once and cached. Call `queue_redraw()` to trigger a redraw.

```gdscript
@export var radius: float = 50.0:
    set(value):
        radius = value
        queue_redraw()  # Redraw when property changes

func _draw() -> void:
    draw_circle(Vector2.ZERO, radius, Color.RED)
```

```csharp
private float _radius = 50f;
[Export]
public float Radius
{
    get => _radius;
    set { _radius = value; QueueRedraw(); }
}

public override void _Draw()
{
    DrawCircle(Vector2.Zero, _radius, Colors.Red);
}
```

For per-frame animation, call `queue_redraw()` from `_process()`.

### Drawing Methods Reference

| Method | Description |
|--------|-------------|
| `draw_line(from, to, color, width, antialiased)` | Single line segment |
| `draw_multiline(points, color, width)` | Multiple disconnected lines (better performance) |
| `draw_polyline(points, color, width, antialiased)` | Connected line sequence |
| `draw_polygon(points, colors)` | Filled polygon (auto-closes) |
| `draw_circle(center, radius, color)` | Filled circle |
| `draw_arc(center, radius, start, end, segments, color, width, aa)` | Arc / partial circle |
| `draw_rect(rect, color, filled, width)` | Rectangle (filled or outline) |
| `draw_texture(texture, position)` | Draw a texture |
| `draw_string(font, position, text, alignment, width, font_size)` | Draw text |
| `draw_set_transform(position, rotation, scale)` | Apply transform for subsequent draws (rotation/scale optional) |

### Default Font

```gdscript
var font: Font = ThemeDB.fallback_font

func _draw() -> void:
    draw_string(font, Vector2(10, 30), "Score: 100", HORIZONTAL_ALIGNMENT_LEFT, -1, 16)
```

```csharp
private Font _font = ThemeDB.FallbackFont;

public override void _Draw()
{
    DrawString(_font, new Vector2(10, 30), "Score: 100", HorizontalAlignment.Left, -1, 16);
}
```

### Editor Preview with @tool

Add `@tool` (GDScript) or `[Tool]` (C#) to see custom drawing in the editor. Requires scene reload after adding/removing the annotation.

### Line Width Tip

Odd-width lines (1px, 3px): offset start/end positions by `0.5` to center the line on a pixel boundary and avoid subpixel blurriness.

---

## 7. 2D Meshes

### When to Use

`MeshInstance2D` replaces `Sprite2D` when large transparent areas waste GPU fill rate. The GPU draws the entire texture quad including fully transparent pixels — a mesh eliminates those.

### Converting Sprite2D to MeshInstance2D

1. Select the `Sprite2D`
2. Menu: **Sprite2D → Convert to MeshInstance2D**
3. Adjust growth and simplification parameters
4. Click "Convert 2D Mesh"

Best candidates:
- Screen-sized images with transparency
- Parallax layers with irregular shapes
- Layered images with large transparent borders
- Mobile/low-end GPU targets

---

## 8. 2D Antialiasing

### Per-Node Antialiasing (Recommended)

Many drawing methods support an `antialiased` parameter:

```gdscript
draw_line(Vector2.ZERO, Vector2(100, 50), Color.WHITE, 2.0, true)  # antialiased = true
```

`Line2D` has an `Antialiased` property in the inspector. This works by generating additional geometry — no MSAA needed.

### MSAA 2D

Available in Forward+ and Mobile renderers only (NOT Compatibility).

**Project Settings → Rendering → Anti Aliasing → Quality → MSAA 2D**

Levels: 2x, 4x, 8x.

| MSAA affects | MSAA does NOT affect |
|-------------|---------------------|
| Geometry edges (lines, polygons) | Aliasing within nearest-neighbor textures |
| Sprite edges touching texture edges | Custom 2D shader output |
| | Font rendering |
| | Specular aliasing with Light2D |

> **For pixel art:** Do NOT enable MSAA 2D — it blurs intentionally sharp edges. Use the per-node `antialiased` parameter selectively.

---

## 9. 2D Snapping and Pixel-Perfect

### Editor Snapping

Three-dot menu in the 2D toolbar:
- **Grid Step** — snap to grid (configure Grid Offset and Step)
- **Rotation Step** — snap rotation to degrees
- **Smart Snap** — snap to parent, node anchors, sides, centers, guides

### Runtime Pixel Snap

For pixel-art games, enable pixel snapping to prevent subpixel jitter:

- **Node2D:** Project Settings → Rendering → 2D → Snapping → `Snap 2D Transforms to Pixel`
- **Vertices:** Project Settings → Rendering → 2D → Snapping → `Snap 2D Vertices to Pixel`
- **Controls:** Project Settings → GUI → General → `Snap Controls to Pixels`

---

## 10. Implementation Checklist

- [ ] Background is a Sprite2D or ColorRect (not the default clear color) so it receives 2D lighting
- [ ] TileSet is saved as an external `.tres` resource for reuse across levels
- [ ] TileSet has `Use Texture Padding` enabled to prevent texture bleeding
- [ ] Parallax2D textures have top-left at (0,0), not centered
- [ ] `repeat_size` matches actual texture dimensions
- [ ] `repeat_times` is increased if the camera can zoom out
- [ ] LightOccluder2D nodes are added to shadow-casting objects when shadows are enabled
- [ ] Light and occluder cull masks are configured to avoid unnecessary light calculations
- [ ] GPUParticles2D has a valid Visibility Rect (auto-generate via Particles menu)
- [ ] `queue_redraw()` is called when custom drawing state changes
- [ ] Collision shapes on tiles use the Physics Layer system, not manual CollisionShape2D nodes
- [ ] Large transparent sprites are converted to MeshInstance2D on mobile/low-end targets
