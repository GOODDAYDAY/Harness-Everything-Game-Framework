---
name: 3d-essentials
description: Use when working with 3D-specific systems — materials, lighting, shadows, environment, global illumination, fog, LOD, occlusion culling, and decals in Godot 4.3+
---

# 3D Essentials in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, then C#.

> **Related skills:** **player-controller** for CharacterBody3D movement, **physics-system** for 3D collision shapes and raycasting, **camera-system** for Camera3D follow and transitions, **shader-basics** for spatial shaders and post-processing, **godot-optimization** for 3D performance tuning, **animation-system** for AnimationTree and 3D animation blending.

---

## 1. 3D Coordinate System & Core Nodes

### Coordinate System

Godot uses a **right-handed** coordinate system with metric units (1 unit = 1 meter):

| Axis | Direction | Color  |
|------|-----------|--------|
| X    | Right     | Red    |
| Y    | Up        | Green  |
| Z    | Out of screen (+Z toward viewer) | Blue |

> Cameras and lights point along **-Z** by default. When a character "faces forward," they look along -Z.

### Essential 3D Nodes

| Node               | Purpose                                         |
|--------------------|-------------------------------------------------|
| `Node3D`           | Base transform node — position, rotation, scale |
| `MeshInstance3D`    | Displays a mesh with a material                 |
| `Camera3D`         | Required to render 3D — perspective or orthogonal |
| `DirectionalLight3D` | Sun/moon — parallel rays, cheapest light      |
| `OmniLight3D`      | Point light — emits in all directions           |
| `SpotLight3D`      | Cone light — flashlights, spotlights            |
| `WorldEnvironment` | Sky, fog, tonemap, post-processing              |
| `Decal`            | Projected texture onto surfaces                 |
| `GPUParticles3D`   | GPU-driven particle effects                     |
| `CSGBox3D` etc.    | Constructive Solid Geometry — prototyping       |
| `GridMap`           | 3D tile-based level building                   |

### Minimal 3D Scene

```
World (Node3D)
├── Camera3D
├── DirectionalLight3D
├── WorldEnvironment
├── MeshInstance3D (floor)
└── MeshInstance3D (player model)
```

---

## 2. Materials

### StandardMaterial3D vs ShaderMaterial

| Material             | Use For                                     | Notes                          |
|----------------------|---------------------------------------------|--------------------------------|
| `StandardMaterial3D` | Most 3D objects — PBR workflow              | No code; Inspector-driven      |
| `ORMMaterial3D`      | Same as Standard but with packed ORM texture | Occlusion+Roughness+Metallic in one texture |
| `ShaderMaterial`     | Custom effects — toon, water, dissolve      | Requires spatial shader code   |

### Key StandardMaterial3D Properties

| Property      | Type         | Description                                |
|---------------|--------------|--------------------------------------------|
| `albedo_color` | `Color`     | Base surface color                         |
| `albedo_texture` | `Texture2D` | Diffuse/albedo texture map               |
| `metallic`    | `float`      | 0.0 (dielectric) to 1.0 (metal)           |
| `roughness`   | `float`      | 0.0 (mirror) to 1.0 (matte)               |
| `emission`    | `Color`      | Self-illumination color                    |
| `emission_energy_multiplier` | `float` | Emission brightness             |
| `normal_map`  | `Texture2D`  | Surface detail without extra geometry      |
| `ao_texture`  | `Texture2D`  | Ambient occlusion map                      |
| `heightmap_texture` | `Texture2D` | Ray-marched parallax depth illusion   |
| `rim`         | `float`      | Edge lighting (micro-fur scattering)       |
| `clearcoat`   | `float`      | Transparent secondary coat (car paint)     |

### Transparency Modes

| Mode                | Performance | Shadows | Use For                          |
|---------------------|-------------|---------|----------------------------------|
| Disabled            | Fastest     | Yes     | Fully opaque objects             |
| Alpha               | Slow        | No      | Semi-transparent glass, water    |
| Alpha Scissor       | Fast        | Yes     | Binary cutout (leaves, fences)   |
| Alpha Hash          | Medium      | Yes     | Dithered transparency (hair)     |
| Depth Pre-Pass      | Medium      | Partial | Mostly opaque with transparent edges |

### Setting Materials from Code

#### GDScript

```gdscript
@onready var mesh: MeshInstance3D = $MeshInstance3D

func _ready() -> void:
    var mat := StandardMaterial3D.new()
    mat.albedo_color = Color(0.8, 0.2, 0.2)
    mat.metallic = 0.3
    mat.roughness = 0.7
    mesh.material_override = mat

func flash_emissive() -> void:
    var mat: StandardMaterial3D = mesh.material_override
    mat.emission_enabled = true
    mat.emission = Color.WHITE
    mat.emission_energy_multiplier = 3.0
    var tween := create_tween()
    tween.tween_property(mat, "emission_energy_multiplier", 0.0, 0.3)
    tween.tween_callback(func(): mat.emission_enabled = false)
```

#### C#

```csharp
private MeshInstance3D _mesh;

public override void _Ready()
{
    _mesh = GetNode<MeshInstance3D>("MeshInstance3D");
    var mat = new StandardMaterial3D();
    mat.AlbedoColor = new Color(0.8f, 0.2f, 0.2f);
    mat.Metallic = 0.3f;
    mat.Roughness = 0.7f;
    _mesh.MaterialOverride = mat;
}

public void FlashEmissive()
{
    var mat = _mesh.MaterialOverride as StandardMaterial3D;
    mat.EmissionEnabled = true;
    mat.Emission = Colors.White;
    mat.EmissionEnergyMultiplier = 3.0f;
    var tween = CreateTween();
    tween.TweenProperty(mat, "emission_energy_multiplier", 0.0f, 0.3);
    tween.TweenCallback(Callable.From(() => mat.EmissionEnabled = false));
}
```

### Material Instancing

When multiple MeshInstance3D nodes share the same material, changing one affects all. To make a per-instance copy:

```gdscript
# In _ready() — creates an independent copy of the material
mesh.material_override = mesh.material_override.duplicate()
```

```csharp
_mesh.MaterialOverride = (Material)_mesh.MaterialOverride.Duplicate();
```

---

## 3. Lighting

### Light Types Comparison

| Light               | Shape         | Shadows | Cost    | Max Visible          |
|---------------------|---------------|---------|---------|----------------------|
| `DirectionalLight3D` | Parallel rays | PSSM    | Cheapest | 8 (Forward+)       |
| `OmniLight3D`       | Sphere        | Cube/Dual Paraboloid | Medium | 512 clustered* |
| `SpotLight3D`       | Cone          | Single texture | Cheap | 512 clustered*     |

*Forward+ shares 512 clustered element slots among omni lights, spot lights, decals, and reflection probes.

### Light Properties

#### GDScript

```gdscript
@onready var sun: DirectionalLight3D = $DirectionalLight3D

func _ready() -> void:
    sun.light_color = Color(1.0, 0.95, 0.9)
    sun.light_energy = 1.0
    sun.shadow_enabled = true

    # Directional shadow quality
    sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
    sun.directional_shadow_max_distance = 100.0
```

#### C#

```csharp
private DirectionalLight3D _sun;

public override void _Ready()
{
    _sun = GetNode<DirectionalLight3D>("DirectionalLight3D");
    _sun.LightColor = new Color(1.0f, 0.95f, 0.9f);
    _sun.LightEnergy = 1.0f;
    _sun.ShadowEnabled = true;

    _sun.DirectionalShadowMode = DirectionalLight3D.ShadowMode.Parallel4Splits;
    _sun.DirectionalShadowMaxDistance = 100.0f;
}
```

### Dynamic Point Light

```gdscript
func create_explosion_light(pos: Vector3) -> void:
    var light := OmniLight3D.new()
    light.light_color = Color(1.0, 0.6, 0.2)
    light.light_energy = 4.0
    light.omni_range = 10.0
    light.omni_attenuation = 2.0
    light.position = pos
    add_child(light)

    var tween := create_tween()
    tween.tween_property(light, "light_energy", 0.0, 0.5)
    tween.tween_callback(light.queue_free)
```

```csharp
public void CreateExplosionLight(Vector3 pos)
{
    var light = new OmniLight3D();
    light.LightColor = new Color(1.0f, 0.6f, 0.2f);
    light.LightEnergy = 4.0f;
    light.OmniRange = 10.0f;
    light.OmniAttenuation = 2.0f;
    light.Position = pos;
    AddChild(light);

    var tween = CreateTween();
    tween.TweenProperty(light, "light_energy", 0.0f, 0.5);
    tween.TweenCallback(Callable.From(light.QueueFree));
}
```

### Shadow Configuration Tips

| Setting                     | Effect                                             | Recommendation                       |
|-----------------------------|-----------------------------------------------------|--------------------------------------|
| `shadow_bias`               | Prevents self-shadowing (shadow acne)               | Start at 0.1, increase if acne visible |
| `shadow_normal_bias`        | Better acne fix than regular bias                   | Prefer this over `shadow_bias`       |
| `directional_shadow_max_distance` | Limits shadow range from camera               | Lower = better quality; 50–100m typical |
| Shadow map resolution       | Project Settings > Rendering > Lights and Shadows  | 2048 for perf, 4096 for quality      |
| `shadow_blur`               | Softens shadow edges                                | 1.0–2.0 for gentle softness         |

### Light Bake Modes

| Mode     | Description                                               | Use For                             |
|----------|-----------------------------------------------------------|-------------------------------------|
| Disabled | Not included in lightmap baking; fully real-time (default) | Moving lights, player flashlight    |
| Static   | Fully baked into lightmaps — no runtime cost              | Architecture, terrain, fixed lights |
| Dynamic  | Indirect light baked, direct light stays real-time        | Lights that change color/intensity  |

---

## 4. Environment & Post-Processing

### WorldEnvironment Setup

```
World (Node3D)
├── WorldEnvironment     ← holds Environment + CameraAttributes resources
├── DirectionalLight3D
├── Camera3D
└── ...
```

Set the **Environment** resource on WorldEnvironment and the **Camera Attributes** for exposure/DOF.

### Sky Options

| Sky Material           | Description                              | Use For                    |
|------------------------|------------------------------------------|----------------------------|
| `PanoramaSkyMaterial`  | 360° HDR panorama image                 | Realistic environments     |
| `ProceduralSkyMaterial` | Generated sky with color gradients     | Quick prototyping          |
| `PhysicalSkyMaterial`  | Physics-based atmosphere + sun          | Outdoor day/night cycles   |

#### GDScript

```gdscript
func setup_environment() -> void:
    var env := Environment.new()

    # Sky
    var sky := Sky.new()
    var sky_mat := ProceduralSkyMaterial.new()
    sky_mat.sky_top_color = Color(0.4, 0.6, 1.0)
    sky_mat.sky_horizon_color = Color(0.7, 0.8, 1.0)
    sky_mat.ground_bottom_color = Color(0.2, 0.15, 0.1)
    sky.sky_material = sky_mat
    env.sky = sky
    env.background_mode = Environment.BG_SKY

    # Tonemap
    env.tonemap_mode = Environment.TONE_MAP_FILMIC
    env.tonemap_exposure = 1.0

    # Ambient light from sky
    env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY

    $WorldEnvironment.environment = env
```

#### C#

```csharp
public void SetupEnvironment()
{
    var env = new Godot.Environment();

    var sky = new Sky();
    var skyMat = new ProceduralSkyMaterial();
    skyMat.SkyTopColor = new Color(0.4f, 0.6f, 1.0f);
    skyMat.SkyHorizonColor = new Color(0.7f, 0.8f, 1.0f);
    skyMat.GroundBottomColor = new Color(0.2f, 0.15f, 0.1f);
    sky.SkyMaterial = skyMat;
    env.Sky = sky;
    env.BackgroundMode = Godot.Environment.BGMode.Sky;

    env.TonemapMode = Godot.Environment.ToneMapper.Filmic;
    env.TonemapExposure = 1.0f;

    env.AmbientLightSource = Godot.Environment.AmbientSource.Sky;

    GetNode<WorldEnvironment>("WorldEnvironment").Environment = env;
}
```

### Tonemap Modes

| Mode       | Character                                  | Best For                       |
|------------|---------------------------------------------|--------------------------------|
| Linear     | Clips brights — blown-out look             | Debug, deliberately flat look  |
| Reinhard   | Simple curve, preserves brights            | General use                    |
| Filmic     | Film-like contrast                          | Cinematic games                |
| ACES       | High contrast with desaturation            | Realistic/photographic         |
| AgX        | Maintains hue as brightness increases      | Physically accurate lighting   |

### Post-Processing Effects (Inspector)

Configure these on the Environment resource — no shader code needed:

| Effect    | Description                              | Renderer Support         |
|-----------|------------------------------------------|--------------------------|
| Glow      | Bloom/glow on bright surfaces            | All                      |
| SSAO      | Screen-space ambient occlusion           | Forward+ only            |
| SSIL      | Screen-space indirect lighting           | Forward+ only            |
| SSR       | Screen-space reflections                 | Forward+ only            |
| SDFGI     | Real-time GI for large scenes            | Forward+ only            |
| DOF       | Depth of field blur (via CameraAttributes) | All                   |
| Fog       | Depth and height fog                     | All                      |
| Adjustments | Brightness, contrast, saturation, color correction | All          |
| Auto Exposure | Adaptive exposure (via CameraAttributes) | Forward+, Mobile     |

---

## 5. Global Illumination

### GI Methods Comparison

| Method          | Quality   | Performance | Dynamic | Renderer  | Use For                    |
|-----------------|-----------|-------------|---------|-----------|----------------------------|
| None (ambient)  | Low       | Free        | Yes     | All       | Simple/stylized games      |
| `ReflectionProbe` | Medium  | Low         | Optional | All      | Localized reflections      |
| `LightmapGI`   | High      | Free at runtime | No   | Forward+  | Static scenes (archviz)    |
| `VoxelGI`       | High      | High        | Yes     | Forward+  | Small-medium dynamic scenes |
| `SDFGI`         | Medium-High | Medium    | Yes     | Forward+  | Large open-world scenes    |

### ReflectionProbe

Captures the surrounding environment into a cubemap for reflections on nearby objects.

```
Room (Node3D)
├── ReflectionProbe      ← extents cover the room
├── MeshInstance3D (walls)
└── MeshInstance3D (shiny floor)
```

```gdscript
@onready var probe: ReflectionProbe = $ReflectionProbe

func _ready() -> void:
    probe.size = Vector3(10.0, 4.0, 10.0)  # cover the room
    probe.update_mode = ReflectionProbe.UPDATE_ONCE  # bake once, free at runtime
```

```csharp
public override void _Ready()
{
    var probe = GetNode<ReflectionProbe>("ReflectionProbe");
    probe.Size = new Vector3(10.0f, 4.0f, 10.0f);
    probe.UpdateMode = ReflectionProbe.UpdateModeEnum.Once;
}
```

### LightmapGI (Baked)

Best quality, zero runtime cost. Requires UV2 on meshes (auto-generated on import).

1. Add a **LightmapGI** node to the scene
2. Set all static lights to **Bake Mode: Static**
3. Set all static meshes to **GI Mode: Static** in the GeometryInstance3D section
4. Select LightmapGI → click **Bake Lightmaps** in the toolbar
5. Baked data is saved as a `LightmapGIData` resource — commit it with your project

### SDFGI (Real-Time)

Enable on the Environment resource — no nodes needed:

```gdscript
var env: Environment = $WorldEnvironment.environment
env.sdfgi_enabled = true
env.sdfgi_cascades = 4
env.sdfgi_use_occlusion = true
```

```csharp
var env = GetNode<WorldEnvironment>("WorldEnvironment").Environment;
env.SdfgiEnabled = true;
env.SdfgiCascades = 4;
env.SdfgiUseOcclusion = true;
```

---

## 6. Fog

### Depth & Height Fog (Environment)

Simple fog configured on the Environment resource:

#### GDScript

```gdscript
var env: Environment = $WorldEnvironment.environment

# Depth fog — increases with distance from camera
env.fog_enabled = true
env.fog_light_color = Color(0.7, 0.75, 0.8)
env.fog_density = 0.01

# Height fog — thicker below a certain Y level
env.fog_height = 0.0
env.fog_height_density = 0.5

# Sun scattering — tints fog with directional light color
env.fog_sun_scatter = 0.3
```

#### C#

```csharp
var env = GetNode<WorldEnvironment>("WorldEnvironment").Environment;
env.FogEnabled = true;
env.FogLightColor = new Color(0.7f, 0.75f, 0.8f);
env.FogDensity = 0.01f;
env.FogHeight = 0.0f;
env.FogHeightDensity = 0.5f;
env.FogSunScatter = 0.3f;
```

### Volumetric Fog (Forward+ only)

Realistic fog that interacts with lights and casts volumetric shadows.

Enable on the Environment:

```gdscript
env.volumetric_fog_enabled = true
env.volumetric_fog_density = 0.05
env.volumetric_fog_albedo = Color(0.9, 0.9, 0.9)
env.volumetric_fog_emission = Color(0.0, 0.0, 0.0)
env.volumetric_fog_length = 64.0
env.volumetric_fog_temporal_reprojection_enabled = true
```

```csharp
var env = GetNode<WorldEnvironment>("WorldEnvironment").Environment;
env.VolumetricFogEnabled = true;
env.VolumetricFogDensity = 0.05f;
env.VolumetricFogAlbedo = new Color(0.9f, 0.9f, 0.9f);
env.VolumetricFogEmission = new Color(0.0f, 0.0f, 0.0f);
env.VolumetricFogLength = 64.0f;
env.VolumetricFogTemporalReprojectionEnabled = true;
```

### FogVolume (Localized Fog)

Create fog in specific areas (caves, steam vents, magic effects):

```
Scene
├── WorldEnvironment (volumetric_fog_enabled = true, density = 0.0)
└── FogVolume
    shape = Box
    size = Vector3(5, 3, 5)
    material = FogMaterial (density = 1.0)
```

```gdscript
func create_fog_cloud(pos: Vector3) -> void:
    var fog := FogVolume.new()
    fog.shape = RenderingServer.FOG_VOLUME_SHAPE_ELLIPSOID
    fog.size = Vector3(4.0, 2.0, 4.0)
    fog.position = pos

    var mat := FogMaterial.new()
    mat.density = 0.5
    mat.albedo = Color(0.8, 0.85, 0.9)
    fog.material = mat

    add_child(fog)
```

```csharp
public void CreateFogCloud(Vector3 pos)
{
    var fog = new FogVolume();
    fog.Shape = RenderingServer.FogVolumeShape.Ellipsoid;
    fog.Size = new Vector3(4.0f, 2.0f, 4.0f);
    fog.Position = pos;

    var mat = new FogMaterial();
    mat.Density = 0.5f;
    mat.Albedo = new Color(0.8f, 0.85f, 0.9f);
    fog.Material = mat;

    AddChild(fog);
}
```

> Set global `volumetric_fog_density` to 0.0 and use FogVolume nodes to place fog only where needed. This gives full control without blanket fog everywhere.

---

## 7. Decals

Decals project textures onto surfaces without modifying the underlying mesh. Use for bullet holes, blood splatters, footprints, ground markings.

### Scene Setup

```
World
├── MeshInstance3D (floor)
└── Decal
    size = Vector3(1, 0.5, 1)   ← Y controls projection depth
    texture_albedo = footprint.png
    texture_normal = footprint_normal.png
```

### Spawning Decals from Code

#### GDScript

```gdscript
func spawn_bullet_hole(hit_pos: Vector3, hit_normal: Vector3) -> void:
    var decal := Decal.new()
    decal.size = Vector3(0.3, 0.2, 0.3)
    decal.texture_albedo = preload("res://textures/bullet_hole.png")
    decal.position = hit_pos

    # Orient decal to project along the hit surface normal
    # Decals project along -Y, so rotate to align -Y with -hit_normal
    if hit_normal.abs() != Vector3.UP:
        decal.look_at(hit_pos - hit_normal, Vector3.UP)
        decal.rotate_object_local(Vector3.RIGHT, PI / 2.0)
    # For floor/ceiling hits (normal is UP or DOWN), default orientation works

    # Fade and cleanup
    decal.distance_fade_enabled = true
    decal.distance_fade_begin = 20.0
    decal.distance_fade_length = 5.0

    get_parent().add_child(decal)

    # Remove after 30 seconds
    get_tree().create_timer(30.0).timeout.connect(decal.queue_free)
```

#### C#

```csharp
public void SpawnBulletHole(Vector3 hitPos, Vector3 hitNormal)
{
    var decal = new Decal();
    decal.Size = new Vector3(0.3f, 0.2f, 0.3f);
    decal.TextureAlbedo = GD.Load<Texture2D>("res://textures/bullet_hole.png");
    decal.Position = hitPos;

    if (hitNormal.Abs() != Vector3.Up)
    {
        decal.LookAt(hitPos - hitNormal, Vector3.Up);
        decal.RotateObjectLocal(Vector3.Right, Mathf.Pi / 2.0f);
    }

    decal.DistanceFadeEnabled = true;
    decal.DistanceFadeBegin = 20.0f;
    decal.DistanceFadeLength = 5.0f;

    GetParent().AddChild(decal);

    GetTree().CreateTimer(30.0f).Timeout += decal.QueueFree;
}
```

### Decal Limits

| Renderer     | Max Decals                              |
|--------------|-----------------------------------------|
| Forward+     | 512 clustered elements (shared with lights, probes) |
| Mobile       | 8 per mesh resource                     |
| Compatibility | Limited by max renderable elements     |

---

## 8. Optimization — LOD, Culling, MultiMesh

### Mesh LOD (Automatic)

Godot auto-generates LOD levels on import for glTF, Blend, Collada, and FBX files. No manual setup needed.

Control LOD aggressiveness:

```gdscript
# Per-object LOD bias (GeometryInstance3D property)
# > 1.0 = keep high detail longer, < 1.0 = switch to low detail sooner
$MeshInstance3D.lod_bias = 1.5
```

```csharp
GetNode<MeshInstance3D>("MeshInstance3D").LodBias = 1.5f;
```

Global LOD threshold: **Project Settings > Rendering > Mesh LOD > LOD Change > Threshold Pixels** (default 1.0 — perceptually lossless).

### Visibility Ranges (Manual LOD)

For custom LOD with different meshes at different distances:

```gdscript
# Close-up: full-detail tree (0–30m)
$TreeDetailed.visibility_range_begin = 0.0
$TreeDetailed.visibility_range_end = 30.0
$TreeDetailed.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF

# Far: billboard impostor (25–100m, with crossfade overlap)
$TreeBillboard.visibility_range_begin = 25.0
$TreeBillboard.visibility_range_end = 100.0
$TreeBillboard.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
```

### Occlusion Culling

Prevents rendering objects hidden behind walls/large geometry.

**Setup:**
1. Enable: **Project Settings > Rendering > Occlusion Culling > Use Occlusion Culling**
2. Add an **OccluderInstance3D** node to your scene
3. Select it → click **Bake Occluders** in the 3D toolbar
4. Exclude dynamic objects via **Bake > Cull Mask** (assign them to different visual layers)

> Only bake occluders from static geometry. Moving OccluderInstance3D nodes at runtime forces expensive BVH rebuilds.

### MultiMeshInstance3D

Render thousands of identical meshes (grass, trees, debris) in a single draw call.

#### GDScript

```gdscript
func spawn_grass(positions: PackedVector3Array) -> void:
    var mm := MultiMesh.new()
    mm.transform_format = MultiMesh.TRANSFORM_3D
    mm.mesh = preload("res://meshes/grass_blade.tres")
    mm.instance_count = positions.size()

    for i in positions.size():
        var xform := Transform3D()
        xform.origin = positions[i]
        # Random rotation around Y
        xform = xform.rotated(Vector3.UP, randf() * TAU)
        # Random scale variation
        var s := randf_range(0.8, 1.2)
        xform = xform.scaled(Vector3(s, s, s))
        mm.set_instance_transform(i, xform)

    var mmi := MultiMeshInstance3D.new()
    mmi.multimesh = mm
    add_child(mmi)
```

#### C#

```csharp
public void SpawnGrass(Vector3[] positions)
{
    var mm = new MultiMesh();
    mm.TransformFormat = MultiMesh.TransformFormatEnum.Transform3D;
    mm.Mesh = GD.Load<Mesh>("res://meshes/grass_blade.tres");
    mm.InstanceCount = positions.Length;

    for (int i = 0; i < positions.Length; i++)
    {
        var xform = Transform3D.Identity;
        xform.Origin = positions[i];
        xform = xform.Rotated(Vector3.Up, (float)GD.RandRange(0, Mathf.Tau));
        float s = (float)GD.RandRange(0.8, 1.2);
        xform = xform.Scaled(new Vector3(s, s, s));
        mm.SetInstanceTransform(i, xform);
    }

    var mmi = new MultiMeshInstance3D();
    mmi.Multimesh = mm;
    AddChild(mmi);
}
```

---

## 9. Renderer Comparison

| Feature                | Forward+          | Mobile            | Compatibility     |
|------------------------|-------------------|-------------------|-------------------|
| SSAO / SSIL / SSR      | Yes               | No                | No                 |
| Volumetric Fog          | Yes               | No                | No                |
| SDFGI                   | Yes               | No                | No                |
| LightmapGI              | Yes               | Yes               | Yes               |
| VoxelGI                  | Yes               | No                | No                |
| Glow / Bloom            | Yes               | Yes               | Yes               |
| Max Omni+Spot per mesh  | 512 clustered     | 8+8               | 8+8 (adjustable)  |
| Target Hardware         | Desktop/Console   | Mobile/Mid-range  | Low-end/WebGL     |

Choose in **Project Settings > Rendering > Renderer > Rendering Method**.

> **Rule of thumb:** Start with Forward+ for desktop. Switch to Mobile for mobile targets. Use Compatibility only for web or very low-end hardware.

---

## 10. Common Pitfalls

| Symptom                              | Cause                                          | Fix                                                              |
|--------------------------------------|-------------------------------------------------|------------------------------------------------------------------|
| 3D scene is completely black         | No Camera3D or no lights in scene               | Add Camera3D + DirectionalLight3D + WorldEnvironment             |
| Objects appear dark despite lighting | No ambient light or sky                          | Set Environment ambient_light_source to Sky or Color             |
| Shadow acne (striped shadows)        | Shadow bias too low                              | Increase `shadow_normal_bias` (preferred over `shadow_bias`)     |
| Peter-panning (shadows detached)     | Shadow bias too high                             | Lower `shadow_bias`; use `shadow_normal_bias` instead            |
| Shadows pop in/out                   | `directional_shadow_max_distance` too high       | Lower to 50–100m; quality improves as range shrinks              |
| Material looks flat / no reflections | Missing ReflectionProbe or Sky                   | Add ReflectionProbe or set Environment reflected light to Sky    |
| Decals don't appear                  | Y extent too small or wrong cull mask            | Increase Decal Y size; check cull mask matches target layer      |
| Transparency sorting artifacts       | Overlapping transparent meshes                   | Use Alpha Scissor/Hash where possible; avoid layered transparency |
| SDFGI shows light leaking           | Thin walls or small geometry                     | Thicken walls; increase SDFGI cascade count                      |
| Volumetric fog not visible           | Wrong renderer (Mobile/Compatibility)            | Switch to Forward+ renderer                                      |
| MultiMesh instances invisible         | `instance_count` set after transforms           | Set `instance_count` before calling `set_instance_transform()`   |

---

## 11. Implementation Checklist

- [ ] Scene has Camera3D, at least one light source, and WorldEnvironment
- [ ] Environment has a sky material (procedural or HDR panorama) for ambient and reflected light
- [ ] Tonemap mode is set (Filmic or ACES for realistic look, AgX for physically accurate)
- [ ] DirectionalLight3D has shadows enabled with `shadow_normal_bias` tuned to prevent acne
- [ ] `directional_shadow_max_distance` is set to the minimum needed (50–100m typical)
- [ ] Static geometry uses StandardMaterial3D with appropriate PBR textures (albedo, normal, roughness, metallic)
- [ ] Transparent materials use Alpha Scissor or Alpha Hash instead of Alpha where possible (performance + shadows)
- [ ] ReflectionProbes are placed in rooms/areas with reflective surfaces
- [ ] GI method chosen based on project needs (LightmapGI for static, SDFGI for large dynamic, VoxelGI for small dynamic)
- [ ] Mesh LOD is enabled on import (default for glTF/Blend — verify OBJ files)
- [ ] Occlusion culling is enabled and baked for scenes with heavy occlusion (indoor, urban)
- [ ] MultiMeshInstance3D is used for instanced geometry (grass, trees, props) instead of individual nodes
- [ ] Renderer matches target platform (Forward+ desktop, Mobile mobile, Compatibility web)
