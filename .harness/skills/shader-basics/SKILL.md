---
name: shader-basics
description: Use when implementing shaders — Godot shader language, visual shaders, common visual recipes, and post-processing effects
---

# Shaders in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs.

> **Related skills:** **animation-system** for shader-driven effects like hit flash, **godot-optimization** for shader performance considerations, **camera-system** for post-processing camera effects, **2d-essentials** for 2D lighting, pixel-art shaders, and CanvasTexture normal maps.

---

## 1. Core Concepts

### Shader Types

| Shader Type      | Applied To               | Use For                                          |
|------------------|--------------------------|--------------------------------------------------|
| `canvas_item`    | 2D nodes (Sprite2D, Control, etc.) | 2D effects — outlines, dissolve, color swap |
| `spatial`        | 3D meshes (MeshInstance3D)         | 3D materials — water, terrain, toon shading |
| `particles`      | GPUParticles2D/3D                  | Custom particle behavior                    |
| `sky`            | WorldEnvironment                   | Procedural sky rendering                    |
| `fog`            | FogVolume                          | Volumetric fog effects                      |

### Shader vs ShaderMaterial

```
Shader (.gdshader)        → The code (GLSL-like language)
ShaderMaterial            → Instance of a shader with specific uniform values
CanvasItemMaterial / StandardMaterial3D → Built-in materials (no code needed)
```

Multiple nodes can share the same Shader but have different ShaderMaterial instances with different uniform values (e.g., same dissolve shader but different dissolve progress per enemy).

### Creating a Shader

1. Select a node (e.g., Sprite2D)
2. In Inspector → Material → New ShaderMaterial
3. On the ShaderMaterial → Shader → New Shader
4. Edit the `.gdshader` file in the built-in editor

Or create a `.gdshader` file directly in the FileSystem dock.

---

## 2. Godot Shader Language Basics

Godot uses a GLSL ES 3.0-like language with Godot-specific additions.

### Minimal Canvas Item Shader

```glsl
shader_type canvas_item;

void fragment() {
    // COLOR is the output pixel color
    // TEXTURE is the sprite's texture
    // UV is the texture coordinate (0,0 top-left to 1,1 bottom-right)
    vec4 tex = texture(TEXTURE, UV);
    COLOR = tex;
}
```

### Minimal Spatial Shader

```glsl
shader_type spatial;

void fragment() {
    // ALBEDO is the base color (vec3)
    ALBEDO = vec3(0.8, 0.2, 0.2);
}
```

### Built-in Variables (canvas_item)

| Variable   | Type   | Description                           |
|------------|--------|---------------------------------------|
| `UV`       | `vec2` | Texture coordinates                   |
| `COLOR`    | `vec4` | Output color (set this in `fragment()`) |
| `TEXTURE`  | `sampler2D` | The node's texture                |
| `VERTEX`   | `vec2` | Vertex position (in `vertex()`)       |
| `TIME`     | `float`| Elapsed time in seconds               |
| `SCREEN_UV`| `vec2` | Screen-space UV (for screen effects)  |

> `SCREEN_TEXTURE` was removed in Godot 4.0. To read the screen, declare a uniform: `uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;`

### Built-in Variables (spatial)

| Variable    | Type   | Description                           |
|-------------|--------|---------------------------------------|
| `ALBEDO`    | `vec3` | Base surface color                    |
| `METALLIC`  | `float`| Metallic value (0.0–1.0)             |
| `ROUGHNESS` | `float`| Roughness value (0.0–1.0)            |
| `NORMAL`    | `vec3` | Surface normal (for normal mapping)   |
| `EMISSION`  | `vec3` | Emissive color                        |
| `ALPHA`     | `float`| Transparency (enable in render mode)  |
| `VERTEX`    | `vec3` | Vertex position (in `vertex()`)       |

### Uniforms (Shader Parameters)

Uniforms expose shader values to the Inspector and code.

```glsl
shader_type canvas_item;

uniform float speed : hint_range(0.0, 10.0, 0.1) = 1.0;
uniform vec4 tint_color : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform sampler2D noise_texture : filter_linear_mipmap;

void fragment() {
    vec4 tex = texture(TEXTURE, UV);
    COLOR = tex * tint_color;
}
```

### Common Uniform Hints

| Hint                        | Type         | Description                         |
|-----------------------------|--------------|-------------------------------------|
| `hint_range(min, max, step)` | `float/int` | Slider in Inspector                 |
| `source_color`              | `vec4`       | Color picker in Inspector           |
| `filter_linear_mipmap`      | `sampler2D`  | Texture filtering mode              |
| `repeat_enable`             | `sampler2D`  | Allow texture tiling                |
| `hint_normal`               | `sampler2D`  | Treat as normal map                 |

### Setting Uniforms from Code

#### GDScript

```gdscript
var mat: ShaderMaterial = $Sprite2D.material
mat.set_shader_parameter("speed", 2.0)
mat.set_shader_parameter("tint_color", Color.RED)
```

#### C#

```csharp
var mat = GetNode<Sprite2D>("Sprite2D").Material as ShaderMaterial;
mat.SetShaderParameter("speed", 2.0f);
mat.SetShaderParameter("tint_color", Colors.Red);
```

---

## 3. Common 2D Shader Recipes

### Dissolve Effect

```glsl
shader_type canvas_item;

uniform float dissolve_amount : hint_range(0.0, 1.0) = 0.0;
uniform sampler2D noise_texture : filter_linear_mipmap;
uniform vec4 edge_color : source_color = vec4(1.0, 0.5, 0.0, 1.0);
uniform float edge_width : hint_range(0.0, 0.1) = 0.03;

void fragment() {
    vec4 tex = texture(TEXTURE, UV);
    float noise = texture(noise_texture, UV).r;

    // Discard pixels below the dissolve threshold
    if (noise < dissolve_amount) {
        discard;
    }

    // Glow at the dissolve edge
    float edge = smoothstep(dissolve_amount, dissolve_amount + edge_width, noise);
    COLOR = mix(edge_color, tex, edge);
    COLOR.a = tex.a;
}
```

Animate from code:

```gdscript
func dissolve(duration: float = 1.0) -> void:
    var mat: ShaderMaterial = $Sprite2D.material
    var tween := create_tween()
    tween.tween_property(mat, "shader_parameter/dissolve_amount", 1.0, duration)
    tween.tween_callback(queue_free)
```

```csharp
public void Dissolve(float duration = 1.0f)
{
    var mat = GetNode<Sprite2D>("Sprite2D").Material as ShaderMaterial;
    var tween = CreateTween();
    tween.TweenProperty(mat, "shader_parameter/dissolve_amount", 1.0f, duration);
    tween.TweenCallback(Callable.From(QueueFree));
}
```

### Outline Effect

```glsl
shader_type canvas_item;

uniform vec4 outline_color : source_color = vec4(0.0, 0.0, 0.0, 1.0);
uniform float outline_width : hint_range(0.0, 10.0, 0.5) = 1.0;

void fragment() {
    vec2 size = TEXTURE_PIXEL_SIZE * outline_width;
    vec4 tex = texture(TEXTURE, UV);

    // Sample neighboring pixels
    float alpha_sum = 0.0;
    alpha_sum += texture(TEXTURE, UV + vec2(size.x, 0.0)).a;
    alpha_sum += texture(TEXTURE, UV + vec2(-size.x, 0.0)).a;
    alpha_sum += texture(TEXTURE, UV + vec2(0.0, size.y)).a;
    alpha_sum += texture(TEXTURE, UV + vec2(0.0, -size.y)).a;

    // If any neighbor has alpha but current pixel is transparent → outline
    if (tex.a < 0.5 && alpha_sum > 0.0) {
        COLOR = outline_color;
    } else {
        COLOR = tex;
    }
}
```

### Flash White (Hit Effect)

```glsl
shader_type canvas_item;

uniform float flash_amount : hint_range(0.0, 1.0) = 0.0;

void fragment() {
    vec4 tex = texture(TEXTURE, UV);
    COLOR = mix(tex, vec4(1.0, 1.0, 1.0, tex.a), flash_amount);
}
```

### Color Swap / Palette Shift

```glsl
shader_type canvas_item;

uniform vec4 original_color : source_color = vec4(1.0, 0.0, 0.0, 1.0);
uniform vec4 replacement_color : source_color = vec4(0.0, 0.0, 1.0, 1.0);
uniform float tolerance : hint_range(0.0, 1.0) = 0.1;

void fragment() {
    vec4 tex = texture(TEXTURE, UV);
    float dist = distance(tex.rgb, original_color.rgb);
    if (dist < tolerance) {
        COLOR = vec4(replacement_color.rgb, tex.a);
    } else {
        COLOR = tex;
    }
}
```

### Scrolling UV (Water, Lava, Clouds)

```glsl
shader_type canvas_item;

uniform vec2 scroll_speed = vec2(0.1, 0.05);

void fragment() {
    vec2 scrolled_uv = UV + scroll_speed * TIME;
    COLOR = texture(TEXTURE, scrolled_uv);
}
```

### Wave Distortion

```glsl
shader_type canvas_item;

uniform float wave_amplitude : hint_range(0.0, 0.1) = 0.02;
uniform float wave_frequency : hint_range(0.0, 50.0) = 10.0;
uniform float wave_speed : hint_range(0.0, 10.0) = 2.0;

void fragment() {
    vec2 uv = UV;
    uv.x += sin(uv.y * wave_frequency + TIME * wave_speed) * wave_amplitude;
    COLOR = texture(TEXTURE, uv);
}
```

---

## 4. Common 3D Shader Recipes

### Toon / Cel Shading

```glsl
shader_type spatial;

uniform vec4 base_color : source_color = vec4(0.8, 0.3, 0.3, 1.0);
uniform int shade_levels : hint_range(2, 8) = 3;

void fragment() {
    ALBEDO = base_color.rgb;
}

void light() {
    // Quantize the light to discrete steps
    float NdotL = dot(NORMAL, LIGHT);
    float intensity = clamp(NdotL, 0.0, 1.0);
    float stepped = floor(intensity * float(shade_levels)) / float(shade_levels);
    DIFFUSE_LIGHT += ALBEDO * ATTENUATION * LIGHT_COLOR * stepped;
}
```

### Rim Lighting / Fresnel

```glsl
shader_type spatial;

uniform vec4 rim_color : source_color = vec4(0.5, 0.8, 1.0, 1.0);
uniform float rim_power : hint_range(0.1, 10.0) = 3.0;

void fragment() {
    ALBEDO = vec3(0.3);
    float fresnel = pow(1.0 - dot(NORMAL, VIEW), rim_power);
    EMISSION = rim_color.rgb * fresnel;
}
```

### Simple Water Surface

```glsl
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back;

uniform vec4 water_color : source_color = vec4(0.1, 0.3, 0.6, 0.8);
uniform sampler2D wave_noise : filter_linear_mipmap, repeat_enable;
uniform float wave_speed : hint_range(0.0, 1.0) = 0.05;
uniform float wave_height : hint_range(0.0, 2.0) = 0.3;

void vertex() {
    float wave = texture(wave_noise, VERTEX.xz * 0.1 + TIME * wave_speed).r;
    VERTEX.y += wave * wave_height;
}

void fragment() {
    ALBEDO = water_color.rgb;
    ALPHA = water_color.a;
    METALLIC = 0.6;
    ROUGHNESS = 0.1;
}
```

---

## 5. Visual Shaders

Visual shaders provide a node-based graph editor — no code required.

### When to Use Visual Shaders

| Use Visual Shaders When        | Use Code Shaders When              |
|--------------------------------|------------------------------------|
| Prototyping effects quickly    | Complex math or branching logic    |
| Artists need to tweak values   | Need precise control over every line |
| Learning shader concepts       | Performance-critical shaders       |
| Simple effects (color adjust, UV scroll) | Loops or advanced techniques |

### Creating a Visual Shader

1. Select node → Inspector → Material → New ShaderMaterial
2. Shader → New VisualShader
3. Click the shader to open the Visual Shader editor
4. Add nodes from the palette, connect pins
5. Output nodes (Output, FragmentOutput) are pre-placed

### Key Visual Shader Nodes

| Node                | Purpose                              |
|---------------------|--------------------------------------|
| `Texture2D`         | Sample a texture                     |
| `ColorConstant`     | Solid color value                    |
| `VectorOp`          | Math operations on vectors           |
| `ScalarOp`          | Math operations on floats            |
| `Mix`               | Lerp between two values              |
| `Step` / `SmoothStep` | Threshold / smooth threshold      |
| `Time`              | Current time (for animation)         |
| `UV`                | Texture coordinates                  |
| `Input` (custom)    | Expose a uniform to Inspector        |

> Visual shaders compile to the same GPU code as written shaders. There is no performance difference.

---

## 6. Post-Processing Effects

### Using a ColorRect Overlay

The simplest post-processing setup for 2D:

1. Add a **CanvasLayer** (layer = 100, to render on top)
2. Add a **ColorRect** child set to full screen
3. Assign a ShaderMaterial to the ColorRect

```
Root
├── Game (your scene)
└── CanvasLayer (layer = 100)
    └── ColorRect (full screen, shader material)
```

Set the ColorRect to fill the screen:
- Anchor Preset → Full Rect
- Mouse Filter → Ignore (so it doesn't block input)

### Vignette

```glsl
shader_type canvas_item;

uniform float vignette_intensity : hint_range(0.0, 1.0) = 0.4;
uniform float vignette_opacity : hint_range(0.0, 1.0) = 0.5;

void fragment() {
    float dist = distance(UV, vec2(0.5));
    float vignette = smoothstep(0.2, 0.7, dist * vignette_intensity * 2.0);
    COLOR = vec4(0.0, 0.0, 0.0, vignette * vignette_opacity);
}
```

### CRT / Scanline Effect

> Use this on a **SubViewportContainer** (where `TEXTURE` contains the rendered scene) or replace `TEXTURE` with a `hint_screen_texture` sampler on a ColorRect overlay.

```glsl
shader_type canvas_item;

uniform float scanline_count : hint_range(0.0, 1000.0) = 300.0;
uniform float scanline_opacity : hint_range(0.0, 1.0) = 0.15;
uniform float curvature : hint_range(0.0, 10.0) = 2.0;

void fragment() {
    // Barrel distortion for CRT curve
    vec2 uv = UV * 2.0 - 1.0;
    uv *= 1.0 + pow(length(uv), 2.0) * curvature * 0.01;
    uv = (uv + 1.0) * 0.5;

    if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
        COLOR = vec4(0.0, 0.0, 0.0, 1.0);
    } else {
        vec4 tex = texture(TEXTURE, uv);
        // Scanlines
        float scanline = sin(uv.y * scanline_count * 3.14159) * 0.5 + 0.5;
        tex.rgb -= scanline * scanline_opacity;
        COLOR = tex;
    }
}
```

### Using SubViewport for Post-Processing

For full-scene effects in 2D or 3D:

```
SubViewportContainer (ShaderMaterial with post-process shader)
└── SubViewport (size = window size)
    └── Your Game Scene
```

The SubViewportContainer receives the rendered SubViewport as `TEXTURE`, and the shader processes the entire frame.

### WorldEnvironment (3D Post-Processing)

For 3D, use the built-in Environment resource on WorldEnvironment:
- Tonemap (ACES, Filmic, Reinhard)
- Glow/Bloom
- SSAO, SSIL, SSR
- Depth of Field
- Color correction (brightness, contrast, saturation)
- Fog

These require **no shader code** — configure in Inspector on the Environment resource.

---

## 7. Compositor Effects (Godot 4.3+)

The `Compositor` resource and `CompositorEffect` class let you insert custom render passes into the rendering pipeline. This is the official way to add screen-space effects, custom SSAO, outline passes, or any GPU compute work.

### When to Use Compositor vs Other Approaches

| Approach | Use For |
|----------|---------|
| ShaderMaterial on node | Per-object effects (dissolve, outline on one sprite) |
| CanvasLayer + ColorRect | Simple full-screen 2D post-processing |
| WorldEnvironment | Built-in 3D post-processing (glow, SSAO, DOF) |
| **CompositorEffect** | Custom render passes, compute shaders, effects not available in WorldEnvironment |

### Setup

1. Select your `WorldEnvironment` node (or `Camera3D`)
2. In Inspector → **Compositor** → New `Compositor`
3. In the Compositor → **Effects** → Add Element → New `CompositorEffect`
4. Set `Effect Callback Type` to when the effect runs in the pipeline:
   - `PRE_OPAQUE` — before opaque geometry
   - `POST_OPAQUE` — after opaque, before transparent
   - `POST_SKY` — after sky rendering
   - `PRE_TRANSPARENT` — before transparent geometry
   - `POST_TRANSPARENT` — after all geometry (most common for post-processing)

### Custom CompositorEffect (GDScript)

```gdscript
# custom_outline_effect.gd
@tool
class_name CustomOutlineEffect
extends CompositorEffect

func _init() -> void:
    effect_callback_type = EFFECT_CALLBACK_TYPE_POST_TRANSPARENT
    needs_normal_roughness = true  # request normal buffer access

func _render_callback(effect_callback_type: int, render_data: RenderData) -> void:
    var render_scene_data: RenderSceneData = render_data.get_render_scene_data()
    var render_scene_buffers: RenderSceneBuffers = render_data.get_render_scene_buffers()

    if not render_scene_buffers:
        return

    # Access render buffers for custom processing
    var size: Vector2i = render_scene_buffers.get_internal_size()
    # Custom rendering logic using RenderingDevice
    var rd: RenderingDevice = RenderingServer.get_rendering_device()
    # ... dispatch compute shaders or draw commands
```

> **Note:** CompositorEffect uses the low-level `RenderingDevice` API. This is an advanced feature — for most post-processing needs, use WorldEnvironment built-in effects or a SubViewport + shader approach.

### Built-in Compositor Uses

Godot uses the Compositor internally for:
- **SDFGI** (Signed Distance Field Global Illumination)
- **VoxelGI** probes
- **Screen-space reflections**

You can stack multiple CompositorEffects in order. Lower array indices execute first.

---

## 8. Render Modes

Render modes go on the first line after `shader_type` and control how the shader interacts with the rendering pipeline.

### Canvas Item Render Modes

```glsl
shader_type canvas_item;
render_mode unshaded;           // Ignore all lighting
render_mode light_only;         // Only visible where lit
render_mode blend_add;          // Additive blending (glow, fire)
render_mode blend_mix;          // Standard alpha blending (default)
render_mode blend_premul_alpha; // Pre-multiplied alpha
```

### Spatial Render Modes

```glsl
shader_type spatial;
render_mode unshaded;              // No lighting calculations
render_mode cull_disabled;         // Render both sides of faces
render_mode depth_draw_always;     // Always write to depth buffer
render_mode specular_toon;         // Toon specular model
render_mode diffuse_toon;          // Toon diffuse model
render_mode blend_add;             // Additive blending
```

---

## 9. Common Pitfalls

| Symptom                             | Cause                                             | Fix                                                              |
|-------------------------------------|----------------------------------------------------|------------------------------------------------------------------|
| Shader has no visible effect        | Material not assigned or shader not saved           | Check node's Material property in Inspector                      |
| Transparent parts render as black   | Alpha not handled in shader                        | Set `COLOR.a = tex.a;` and use appropriate blend mode            |
| Uniform doesn't appear in Inspector | Typo in uniform name or wrong type                 | Re-save the shader; check for compilation errors                 |
| Texture appears stretched/tiled     | Missing `repeat_enable` or wrong UV scale          | Add `repeat_enable` hint to sampler2D uniform                    |
| Shader works in editor but not in game | Screen texture uniform needs backbuffer          | Use `hint_screen_texture` on a `sampler2D` uniform (Godot 4.x)  |
| Performance drops with many shaders | Each unique shader = draw call break               | Share ShaderMaterial instances; use uniforms for variation        |
| Screen-space UV is wrong            | `SCREEN_UV` not available in some contexts         | Ensure the node is rendered in the correct viewport              |
| Visual shader node missing          | Node was renamed or removed in newer Godot version | Check Godot docs for the current node name                       |

---

## 10. Implementation Checklist

- [ ] Shader type matches the node type (`canvas_item` for 2D, `spatial` for 3D)
- [ ] Uniforms use appropriate hints (`hint_range`, `source_color`, `filter_linear_mipmap`)
- [ ] Shared visual effects use the same Shader resource with separate ShaderMaterial instances
- [ ] Post-processing shaders are on a CanvasLayer (2D) or WorldEnvironment (3D), not on game objects
- [ ] `TEXTURE` is sampled in canvas_item shaders (otherwise sprite content is lost)
- [ ] Alpha-transparent shaders set `COLOR.a` correctly and use `blend_mix` render mode
- [ ] Animated shader parameters (dissolve, flash) are driven by Tweens or AnimationPlayer, not `_process`
- [ ] Screen-reading shaders use `hint_screen_texture` on a `sampler2D` uniform (Godot 4.x approach)
- [ ] Complex shaders are profiled with the Godot profiler to check GPU frame time
