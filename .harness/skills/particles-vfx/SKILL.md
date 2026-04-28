---
name: particles-vfx
description: Use when implementing particle effects — GPUParticles2D/3D, ParticleProcessMaterial, emission shapes, subemitters, trails, attractors, collision, and common VFX recipes
---

# Particle Systems in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, then C#.

> **Related skills:** **shader-basics** for custom particle shaders, **3d-essentials** for lighting and environment that affect particles, **2d-essentials** for 2D rendering context, **tween-animation** for code-driven VFX timing, **godot-optimization** for particle performance tuning.

---

## 1. Core Concepts

### GPU vs CPU Particles

| Node                | Processing | Features                                | Use For                        |
|---------------------|------------|-----------------------------------------|--------------------------------|
| `GPUParticles2D`    | GPU        | Full features, high counts, trails      | Most 2D effects                |
| `GPUParticles3D`    | GPU        | Full features, attractors, collision    | Most 3D effects                |
| `CPUParticles2D`    | CPU        | Simpler, no trails/attractors           | Low-end devices, few particles |
| `CPUParticles3D`    | CPU        | Simpler, no trails/attractors           | Low-end devices, few particles |

**Rule of thumb:** Use GPU particles by default. Switch to CPU particles only for low-end/web targets or when you need CPU-side particle positions (e.g., spawning objects at particle locations).

> You can convert between GPU and CPU particles in the editor: select the node → toolbar → **Convert to CPUParticles2D/3D** (or vice versa).

### Particle System Architecture

```
GPUParticles2D/3D
├── Process Material (ParticleProcessMaterial)   ← physics, emission, color
├── Draw Pass 1 (Mesh)                            ← what each particle looks like
└── (Optional) Draw Pass 2-4                      ← additional meshes
```

### Minimal Setup

1. Add a **GPUParticles2D** (or 3D) node
2. In Inspector → Process Material → **New ParticleProcessMaterial**
3. Set **Amount** (number of particles)
4. Configure emission, direction, velocity, gravity
5. (2D) Set **Texture** for particle appearance
6. (3D) Set **Draw Pass 1** mesh (QuadMesh for billboards, or custom mesh)

---

## 2. Key Node Properties

### GPUParticles2D/3D Properties

| Property          | Type     | Description                                         |
|-------------------|----------|-----------------------------------------------------|
| `emitting`        | `bool`   | Start/stop emission                                 |
| `amount`          | `int`    | Total particles alive at once                       |
| `lifetime`        | `float`  | Seconds each particle lives                         |
| `one_shot`        | `bool`   | Emit once then stop                                 |
| `preprocess`      | `float`  | Simulate this many seconds before first frame       |
| `speed_scale`     | `float`  | Time multiplier for particle physics                |
| `explosiveness`   | `float`  | 0.0 = spread over lifetime, 1.0 = all at once      |
| `fixed_fps`       | `int`    | Lock particle update rate (0 = match render FPS)    |
| `local_coords`    | `bool`   | Particles move with the node (true) or stay in world (false) |
| `draw_order`      | `enum`   | Index, Lifetime, or Reverse Lifetime                |
| `amount_ratio`    | `float`  | Fraction of particles to emit (0.0–1.0)             |

### One-Shot vs Continuous

```gdscript
# Continuous emitter (fire, smoke, ambient dust)
$GPUParticles2D.one_shot = false
$GPUParticles2D.emitting = true

# One-shot burst (explosion, impact splash)
$GPUParticles2D.one_shot = true
$GPUParticles2D.emitting = false  # arm it
# Later, trigger:
$GPUParticles2D.restart()
$GPUParticles2D.emitting = true
```

```csharp
// Continuous
var particles = GetNode<GpuParticles2D>("GPUParticles2D");
particles.OneShot = false;
particles.Emitting = true;

// One-shot burst
particles.OneShot = true;
particles.Emitting = false;
// Trigger:
particles.Restart();
particles.Emitting = true;
```

---

## 3. ParticleProcessMaterial — Essential Properties

### Emission Shape

| Shape             | Description                                    |
|-------------------|------------------------------------------------|
| `Point`           | All particles spawn at origin                  |
| `Sphere`          | Random position within a sphere                |
| `Sphere Surface`  | Random position on sphere surface only         |
| `Box`             | Random position within a box                   |
| `Ring`             | Random position on a ring/torus               |
| `Points`          | Spawn at positions from a texture/mesh         |
| `Directed Points` | Spawn at positions with normals from mesh      |

```gdscript
var mat := ParticleProcessMaterial.new()
mat.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
mat.emission_sphere_radius = 2.0
```

```csharp
var mat = new ParticleProcessMaterial();
mat.EmissionShape = ParticleProcessMaterial.EmissionShapeEnum.Sphere;
mat.EmissionSphereRadius = 2.0f;
```

### Direction, Velocity & Gravity

```gdscript
var mat := ParticleProcessMaterial.new()

# Direction particles move (normalized)
mat.direction = Vector3(0.0, 1.0, 0.0)  # upward
mat.spread = 30.0  # degrees of randomness around direction

# Speed
mat.initial_velocity_min = 5.0
mat.initial_velocity_max = 10.0

# Gravity
mat.gravity = Vector3(0.0, -9.8, 0.0)
```

```csharp
var mat = new ParticleProcessMaterial();
mat.Direction = new Vector3(0.0f, 1.0f, 0.0f);
mat.Spread = 30.0f;
mat.InitialVelocityMin = 5.0f;
mat.InitialVelocityMax = 10.0f;
mat.Gravity = new Vector3(0.0f, -9.8f, 0.0f);
```

### Scale Over Lifetime

```gdscript
mat.scale_min = 1.0
mat.scale_max = 1.5

# Scale curve — shrink over lifetime
var curve := CurveTexture.new()
var c := Curve.new()
c.add_point(Vector2(0.0, 1.0))  # full size at birth
c.add_point(Vector2(1.0, 0.0))  # zero at death
curve.curve = c
mat.scale_curve = curve
```

```csharp
var mat = new ParticleProcessMaterial();
mat.ScaleMin = 1.0f;
mat.ScaleMax = 1.5f;

var curve = new CurveTexture();
var c = new Curve();
c.AddPoint(new Vector2(0.0f, 1.0f));
c.AddPoint(new Vector2(1.0f, 0.0f));
curve.Curve = c;
mat.ScaleCurve = curve;
```

### Color Over Lifetime

```gdscript
# Gradient: white → orange → transparent
var grad := GradientTexture1D.new()
var g := Gradient.new()
g.set_color(0, Color(1.0, 1.0, 1.0, 1.0))  # start: white
g.add_point(0.5, Color(1.0, 0.5, 0.0, 0.8))  # middle: orange
g.set_color(1, Color(1.0, 0.2, 0.0, 0.0))  # end: transparent red
grad.gradient = g
mat.color_ramp = grad
```

```csharp
var grad = new GradientTexture1D();
var g = new Gradient();
g.SetColor(0, new Color(1.0f, 1.0f, 1.0f, 1.0f));
g.AddPoint(0.5f, new Color(1.0f, 0.5f, 0.0f, 0.8f));
g.SetColor(1, new Color(1.0f, 0.2f, 0.0f, 0.0f));
grad.Gradient = g;
mat.ColorRamp = grad;
```

### Damping & Acceleration

```gdscript
# Damping — slow particles down over time (smoke deceleration)
mat.damping_min = 2.0
mat.damping_max = 5.0

# Radial acceleration — push away from center (explosion) or pull in (implosion)
mat.radial_accel_min = 5.0   # positive = outward
mat.radial_accel_max = 8.0

# Tangential acceleration — orbit around center
mat.tangential_accel_min = 2.0
mat.tangential_accel_max = 3.0
```

### Angular Velocity (Rotation)

```gdscript
mat.angular_velocity_min = -90.0  # degrees per second
mat.angular_velocity_max = 90.0
```

---

## 4. Common VFX Recipes

### Fire (2D)

```gdscript
func create_fire() -> GPUParticles2D:
    var fire := GPUParticles2D.new()
    fire.amount = 50
    fire.lifetime = 0.8
    fire.local_coords = false

    var mat := ParticleProcessMaterial.new()
    mat.direction = Vector3(0, -1, 0)  # upward in 2D (Y is inverted)
    mat.spread = 15.0
    mat.initial_velocity_min = 40.0
    mat.initial_velocity_max = 80.0
    mat.gravity = Vector3(0, 0, 0)  # no gravity for fire
    mat.scale_min = 0.5
    mat.scale_max = 1.0
    mat.damping_min = 3.0
    mat.damping_max = 5.0

    # Color: bright yellow → orange → transparent
    var grad := GradientTexture1D.new()
    var g := Gradient.new()
    g.set_color(0, Color(1.0, 0.9, 0.3, 1.0))
    g.add_point(0.4, Color(1.0, 0.4, 0.0, 0.8))
    g.set_color(1, Color(0.5, 0.1, 0.0, 0.0))
    grad.gradient = g
    mat.color_ramp = grad

    # Shrink over lifetime
    var curve := CurveTexture.new()
    var c := Curve.new()
    c.add_point(Vector2(0.0, 1.0))
    c.add_point(Vector2(1.0, 0.0))
    curve.curve = c
    mat.scale_curve = curve

    fire.process_material = mat
    fire.texture = preload("res://textures/particles/soft_circle.png")
    return fire
```

### Explosion Burst (One-Shot)

```gdscript
func spawn_explosion(pos: Vector2) -> void:
    var particles := GPUParticles2D.new()
    particles.amount = 30
    particles.lifetime = 0.5
    particles.one_shot = true
    particles.explosiveness = 1.0  # all at once
    particles.position = pos

    var mat := ParticleProcessMaterial.new()
    mat.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
    mat.emission_sphere_radius = 5.0
    mat.direction = Vector3(0, 0, 0)
    mat.spread = 180.0  # full sphere
    mat.initial_velocity_min = 100.0
    mat.initial_velocity_max = 200.0
    mat.damping_min = 5.0
    mat.damping_max = 10.0
    mat.scale_min = 0.5
    mat.scale_max = 1.5

    var grad := GradientTexture1D.new()
    var g := Gradient.new()
    g.set_color(0, Color(1.0, 1.0, 0.5, 1.0))
    g.set_color(1, Color(1.0, 0.3, 0.0, 0.0))
    grad.gradient = g
    mat.color_ramp = grad

    particles.process_material = mat
    particles.texture = preload("res://textures/particles/soft_circle.png")
    add_child(particles)
    particles.emitting = true

    # Auto-cleanup after particles die
    get_tree().create_timer(particles.lifetime + 0.5).timeout.connect(particles.queue_free)
```

```csharp
public void SpawnExplosion(Vector2 pos)
{
    var particles = new GpuParticles2D();
    particles.Amount = 30;
    particles.Lifetime = 0.5f;
    particles.OneShot = true;
    particles.Explosiveness = 1.0f;
    particles.Position = pos;

    var mat = new ParticleProcessMaterial();
    mat.EmissionShape = ParticleProcessMaterial.EmissionShapeEnum.Sphere;
    mat.EmissionSphereRadius = 5.0f;
    mat.Direction = Vector3.Zero;
    mat.Spread = 180.0f;
    mat.InitialVelocityMin = 100.0f;
    mat.InitialVelocityMax = 200.0f;
    mat.DampingMin = 5.0f;
    mat.DampingMax = 10.0f;
    mat.ScaleMin = 0.5f;
    mat.ScaleMax = 1.5f;

    var grad = new GradientTexture1D();
    var g = new Gradient();
    g.SetColor(0, new Color(1.0f, 1.0f, 0.5f, 1.0f));
    g.SetColor(1, new Color(1.0f, 0.3f, 0.0f, 0.0f));
    grad.Gradient = g;
    mat.ColorRamp = grad;

    particles.ProcessMaterial = mat;
    particles.Texture = GD.Load<Texture2D>("res://textures/particles/soft_circle.png");
    AddChild(particles);
    particles.Emitting = true;

    GetTree().CreateTimer(particles.Lifetime + 0.5f).Timeout += particles.QueueFree;
}
```

### Dust / Footstep Puff

```gdscript
func spawn_dust(pos: Vector2) -> void:
    var dust := GPUParticles2D.new()
    dust.amount = 8
    dust.lifetime = 0.4
    dust.one_shot = true
    dust.explosiveness = 0.8
    dust.position = pos

    var mat := ParticleProcessMaterial.new()
    mat.direction = Vector3(0, -1, 0)
    mat.spread = 60.0
    mat.initial_velocity_min = 20.0
    mat.initial_velocity_max = 40.0
    mat.gravity = Vector3(0, 50, 0)  # settle downward in 2D
    mat.scale_min = 0.3
    mat.scale_max = 0.6
    mat.color = Color(0.7, 0.65, 0.55, 0.6)

    var grad := GradientTexture1D.new()
    var g := Gradient.new()
    g.set_color(0, Color(1, 1, 1, 0.6))
    g.set_color(1, Color(1, 1, 1, 0.0))
    grad.gradient = g
    mat.color_ramp = grad

    dust.process_material = mat
    dust.texture = preload("res://textures/particles/soft_circle.png")
    add_child(dust)
    dust.emitting = true
    get_tree().create_timer(1.0).timeout.connect(dust.queue_free)
```

---

## 5. Trails (Forward+ and Mobile only)

Trails create ribbon or tube shapes that follow each particle's path.

### Setup

```
GPUParticles3D
├── Trail Enabled = true
├── Trail Lifetime = 0.3
├── Process Material (ParticleProcessMaterial)
└── Draw Pass 1 (mesh for particle head)
```

The trail mesh is auto-generated. Configure its appearance:

| Property                 | Description                                     |
|--------------------------|--------------------------------------------------|
| `trail_enabled`          | Turn trails on/off                              |
| `trail_lifetime`         | How long the trail lingers (seconds)            |

### Trail Mesh Types

For Draw Pass 1, create a **RibbonTrailMesh** or **TubeTrailMesh**:

| Mesh Type          | Shape                       | Best For               |
|--------------------|-----------------------------|------------------------|
| `RibbonTrailMesh`  | Flat quad strip             | Sword swings, streaks  |
| `TubeTrailMesh`    | Cylindrical                 | Lasers, energy trails  |

```gdscript
var particles := GPUParticles3D.new()
particles.trail_enabled = true
particles.trail_lifetime = 0.3
particles.amount = 20

var trail_mesh := RibbonTrailMesh.new()
trail_mesh.size = 0.2  # trail width
trail_mesh.sections = 4
trail_mesh.section_length = 0.1
particles.draw_pass_1 = trail_mesh
```

```csharp
var particles = new GpuParticles3D();
particles.TrailEnabled = true;
particles.TrailLifetime = 0.3f;
particles.Amount = 20;

var trailMesh = new RibbonTrailMesh();
trailMesh.Size = 0.2f;
trailMesh.Sections = 4;
trailMesh.SectionLength = 0.1f;
particles.DrawPass1 = trailMesh;
```

> **Important:** Trail materials need **Use Particle Trails** enabled in the StandardMaterial3D's Transform section to render correctly.

---

## 6. Subemitters

Subemitters are child particle systems that spawn in response to parent particle events.

### Trigger Modes

| Mode           | Spawns When                          | Key Property            |
|----------------|--------------------------------------|-------------------------|
| `Constant`     | At regular intervals per particle    | `frequency` (per second)|
| `At End`       | When a parent particle dies          | `amount_at_end`         |
| `At Collision` | When a particle hits a collision node| `amount_at_collision`   |

### Setup

1. Create two GPUParticles3D nodes in the same scene
2. On the parent's ParticleProcessMaterial → Sub Emitter → assign the child system
3. Set the sub emitter **Mode** and amount/frequency

```gdscript
# Parent material setup
var parent_mat := ParticleProcessMaterial.new()
parent_mat.sub_emitter_mode = ParticleProcessMaterial.SUB_EMITTER_AT_END
parent_mat.sub_emitter_amount_at_end = 8
parent_mat.sub_emitter_keep_velocity = true

# Assign child particle system as sub-emitter
$ParentParticles.process_material = parent_mat
parent_mat.sub_emitter_node = $ChildParticles.get_path()
```

### Limitations

- Child particle **amount** caps the total active sub-emitter particles
- `explosiveness` has no effect on subemitters
- A system cannot be its own subemitter
- Subemitters can chain (sub-sub-emitters) but watch performance

---

## 7. Attractors & Collision (3D only)

### Attractors

Pull or repel particles. Enable **Attractor Interaction** on the ParticleProcessMaterial first.

| Node                              | Shape       | Notes                     |
|-----------------------------------|-------------|---------------------------|
| `GPUParticlesAttractorBox3D`      | Box         | `size` controls extents   |
| `GPUParticlesAttractorSphere3D`   | Sphere      | `radius` controls size    |
| `GPUParticlesAttractorVectorField3D` | Vector field | Uses 3D texture for directions |

```gdscript
# Create a sphere attractor that pulls particles in
var attractor := GPUParticlesAttractorSphere3D.new()
attractor.radius = 5.0
attractor.strength = 3.0      # positive = pull, negative = repel
attractor.attenuation = 1.0   # falloff curve
attractor.position = Vector3(0, 2, 0)
add_child(attractor)

# Don't forget to enable on the material!
var mat: ParticleProcessMaterial = $GPUParticles3D.process_material
mat.attractor_interaction_enabled = true
```

```csharp
var attractor = new GpuParticlesAttractorSphere3D();
attractor.Radius = 5.0f;
attractor.Strength = 3.0f;
attractor.Attenuation = 1.0f;
attractor.Position = new Vector3(0, 2, 0);
AddChild(attractor);

var mat = GetNode<GpuParticles3D>("GPUParticles3D").ProcessMaterial as ParticleProcessMaterial;
mat.AttractorInteractionEnabled = true;
```

### Collision Nodes

Make particles bounce or stop on surfaces.

| Node                                | Shape         | Notes                          |
|-------------------------------------|---------------|--------------------------------|
| `GPUParticlesCollisionBox3D`        | Box           | Simple, fast                   |
| `GPUParticlesCollisionSphere3D`     | Sphere        | Simple, fast                   |
| `GPUParticlesCollisionHeightField3D`| Height field  | Terrain — auto-updates         |
| `GPUParticlesCollisionSDF3D`        | SDF (baked)   | Complex geometry, Forward+ only |

Configure collision response on the ParticleProcessMaterial:

```gdscript
mat.collision_mode = ParticleProcessMaterial.COLLISION_RIGID  # bounce off
mat.collision_bounce = 0.3   # bounciness
mat.collision_friction = 0.5  # sliding resistance
```

```csharp
mat.CollisionMode = ParticleProcessMaterial.CollisionModeEnum.Rigid;
mat.CollisionBounce = 0.3f;
mat.CollisionFriction = 0.5f;
```

---

## 8. Turbulence

Noise-based movement that adds organic variation. Enable on ParticleProcessMaterial.

```gdscript
mat.turbulence_enabled = true
mat.turbulence_noise_strength = 2.0
mat.turbulence_noise_scale = 1.5
mat.turbulence_noise_speed = Vector3(0.5, 0.0, 0.0)  # pan direction
mat.turbulence_influence_min = 0.3
mat.turbulence_influence_max = 0.8
```

```csharp
mat.TurbulenceEnabled = true;
mat.TurbulenceNoiseStrength = 2.0f;
mat.TurbulenceNoiseScale = 1.5f;
mat.TurbulenceNoiseSpeed = new Vector3(0.5f, 0.0f, 0.0f);
mat.TurbulenceInfluenceMin = 0.3f;
mat.TurbulenceInfluenceMax = 0.8f;
```

> **Performance:** 3D noise is GPU-intensive. Use sparingly on mobile/web targets. Higher `noise_scale` values are cheaper but produce weaker turbulence.

---

## 9. Flipbook Animation (2D)

Animate sprite sheet textures on particles.

### Setup

1. Set the particle **Texture** to a sprite sheet
2. On the GPUParticles2D, set the **CanvasItemMaterial** (not the process material):
   - Material → New CanvasItemMaterial
   - Enable **Particle Animation**
   - Set **H Frames** and **V Frames** to match the sheet layout
3. On the ParticleProcessMaterial, configure Animation:
   - `anim_speed_min` / `anim_speed_max` — playback speed
   - `anim_offset_min` / `anim_offset_max` — random start frame

```gdscript
# Process material animation settings
mat.anim_speed_min = 1.0
mat.anim_speed_max = 1.5
mat.anim_offset_min = 0.0
mat.anim_offset_max = 0.5  # random start position in the animation
```

> Use **Add** blend mode on the CanvasItemMaterial for particles with black backgrounds (fire, sparks, magic).

---

## 10. Performance Tips

| Technique                    | Savings              | When to Use                          |
|------------------------------|----------------------|--------------------------------------|
| Lower `amount`               | Linear GPU savings   | Always — use minimum needed          |
| `fixed_fps = 30`             | Halves particle updates | Background particles, ambient       |
| `amount_ratio` < 1.0         | Scale down dynamically | Quality settings slider              |
| Smaller textures             | Less VRAM + bandwidth | Mobile, many particle systems        |
| `local_coords = true`        | Cheaper transforms   | When particles should move with node |
| Disable `turbulence`         | Removes 3D noise cost | Mobile/web targets                   |
| Fewer `trail_sections`       | Less trail geometry  | When trail smoothness isn't critical |
| `visibility_rect` (2D)       | Skips off-screen     | Always set for 2D particles          |

### Dynamic Quality Scaling

```gdscript
# Adjust particle density based on quality setting
func set_particle_quality(level: float) -> void:
    # level: 0.25 (low) to 1.0 (high)
    for particles in get_tree().get_nodes_in_group("particles"):
        if particles is GPUParticles2D or particles is GPUParticles3D:
            particles.amount_ratio = level
```

```csharp
public void SetParticleQuality(float level)
{
    foreach (var node in GetTree().GetNodesInGroup("particles"))
    {
        if (node is GpuParticles2D p2d)
            p2d.AmountRatio = level;
        else if (node is GpuParticles3D p3d)
            p3d.AmountRatio = level;
    }
}
```

---

## 11. Common Pitfalls

| Symptom                              | Cause                                          | Fix                                                              |
|--------------------------------------|-------------------------------------------------|------------------------------------------------------------------|
| Particles invisible                  | No texture (2D) or no draw pass mesh (3D)       | Set texture or assign a mesh to Draw Pass 1                      |
| Particles appear then vanish immediately | `lifetime` too short                         | Increase `lifetime` (default 1.0s)                               |
| One-shot doesn't re-trigger          | Need to call `restart()` before setting `emitting = true` | Call `restart()` then set `emitting = true`            |
| Particles emit in wrong direction    | `direction` or `gravity` misconfigured          | In 2D, Y is inverted — upward is `Vector3(0, -1, 0)`            |
| Particles don't follow the node      | `local_coords` is `false`                       | Set `local_coords = true` for attached effects                   |
| Particles pop in (no pre-warming)    | No `preprocess` time set                        | Set `preprocess` to 1–2x `lifetime` for ambient effects          |
| Color ramp has no effect             | Using `color` property which overrides ramp      | Clear the base `color` (set to white) when using `color_ramp`    |
| Trails not rendering                 | Missing trail material setup or wrong renderer   | Enable "Use Particle Trails" on material; use Forward+ or Mobile |
| Attractors have no effect            | `attractor_interaction_enabled` is `false`       | Enable on the ParticleProcessMaterial                            |
| Subemitter not spawning              | Child `amount` is too low to accommodate spawns  | Increase child system's `amount`                                 |
| Particles flicker on mobile          | `fixed_fps` not set or too high                  | Set `fixed_fps = 30` for consistency across devices              |

---

## 12. Implementation Checklist

- [ ] Particle `amount` is set to the minimum needed for the visual effect
- [ ] `lifetime` matches the visual duration — not too short or too long
- [ ] `one_shot` is enabled for burst effects (explosions, impacts)
- [ ] `preprocess` is set for always-visible ambient effects (fire, smoke, dust)
- [ ] Emission shape matches the source geometry (sphere for explosions, box for area effects)
- [ ] `color_ramp` fades alpha to 0 at the end so particles don't vanish abruptly
- [ ] `scale_curve` shrinks particles over lifetime for natural fade
- [ ] `local_coords` is set correctly — `true` for attached effects, `false` for world-space
- [ ] One-shot particles are cleaned up with `queue_free` after `lifetime` + margin
- [ ] `visibility_rect` (2D) is set to prevent particles from being culled prematurely
- [ ] Dynamic quality scaling uses `amount_ratio` for player-accessible quality settings
- [ ] Performance-heavy features (turbulence, trails) are disabled on low-end targets
