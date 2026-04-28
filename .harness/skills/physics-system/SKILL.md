---
name: physics-system
description: Use when working with physics bodies, collision shapes, raycasting, areas, rigid bodies, ragdolls, soft bodies, Jolt physics, and physics interpolation in Godot 4.3+
---

# Physics System in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, then C#.

> **Related skills:** **player-controller** for CharacterBody2D/3D movement patterns, **component-system** for hitbox/hurtbox composition, **godot-optimization** for physics performance tuning, **camera-system** for camera follow and interpolation, **multiplayer-sync** for networked physics, **2d-essentials** for tile collision setup and 2D canvas layers.

---

## 1. Physics Body Types

> **Godot 4.4+ recommendation:** Jolt Physics is now the default physics engine for new 3D projects and is built into the engine. For new 3D projects, use Jolt unless you have a specific reason to use GodotPhysics. See Section 8 for Jolt details and differences. 2D physics always uses GodotPhysics.

Godot provides four collision object types. The last three extend `PhysicsBody2D`/`PhysicsBody3D`:

| Type | Moved By | Use For |
|------|----------|---------|
| `Area2D/3D` | Code only | Overlap detection, gravity zones, audio zones |
| `StaticBody2D/3D` | Not moved (or constant velocity) | Walls, floors, conveyor belts, moving platforms |
| `RigidBody2D/3D` | Physics engine | Crates, projectiles, debris, ragdolls |
| `CharacterBody2D/3D` | Code only | Players, enemies, NPCs (see **player-controller** skill) |

Every collision object needs at least one `CollisionShape2D`/`3D` or `CollisionPolygon2D`/`3D` child.

> **Critical rule:** NEVER scale collision shapes or physics bodies via the `scale` property. Always change the shape's own size parameters (radius, extents, height). Scaled shapes produce incorrect collision results.

---

## 2. RigidBody2D/3D

### Forces vs Impulses

```gdscript
extends RigidBody2D

func _physics_process(_delta: float) -> void:
    # Continuous force — applied every physics frame (e.g. thrust)
    if Input.is_action_pressed("thrust"):
        apply_force(Vector2(0, -500).rotated(rotation))

    # Central impulse — instant velocity change (e.g. explosion knockback)
    if Input.is_action_just_pressed("explode"):
        apply_central_impulse(Vector2(0, -800))

    # Torque — continuous rotation force
    var turn: float = Input.get_axis("ui_left", "ui_right")
    apply_torque(turn * 20000.0)
```

```csharp
public partial class Ship : RigidBody2D
{
    public override void _PhysicsProcess(double delta)
    {
        if (Input.IsActionPressed("thrust"))
            ApplyForce(new Vector2(0, -500).Rotated(Rotation));

        if (Input.IsActionJustPressed("explode"))
            ApplyCentralImpulse(new Vector2(0, -800));

        float turn = Input.GetAxis("ui_left", "ui_right");
        ApplyTorque(turn * 20000.0f);
    }
}
```

| Method | Effect | When to Use |
|--------|--------|-------------|
| `apply_force(force, position)` | Continuous acceleration at point | Thrusters, wind, magnets |
| `apply_central_force(force)` | Continuous acceleration at center | Gravity, constant push |
| `apply_impulse(impulse, position)` | Instant velocity change at point | Bullet hit, explosion |
| `apply_central_impulse(impulse)` | Instant velocity change at center | Jump, knockback |
| `apply_torque(torque)` | Continuous angular acceleration | Steering, spinning |
| `apply_torque_impulse(impulse)` | Instant angular velocity change | Impact spin |

### _integrate_forces() — Safe Physics Modification

Use `_integrate_forces()` instead of `_physics_process()` when you need to directly modify a RigidBody's transform, velocity, or angular velocity. Setting `position` or `linear_velocity` directly in `_physics_process()` fights the physics engine.

```gdscript
extends RigidBody2D

var thrust := Vector2(0, -250)
var torque_force := 20000.0

func _integrate_forces(state: PhysicsDirectBodyState2D) -> void:
    if Input.is_action_pressed("ui_up"):
        state.apply_force(thrust.rotated(rotation))
    else:
        state.apply_force(Vector2())

    var rotation_dir: float = Input.get_axis("ui_left", "ui_right")
    state.apply_torque(rotation_dir * torque_force)
```

```csharp
public partial class Ship : RigidBody2D
{
    private Vector2 _thrust = new(0, -250);
    private float _torqueForce = 20000f;

    public override void _IntegrateForces(PhysicsDirectBodyState2D state)
    {
        if (Input.IsActionPressed("ui_up"))
            state.ApplyForce(_thrust.Rotated(Rotation));
        else
            state.ApplyForce(new Vector2());

        float rotDir = Input.GetAxis("ui_left", "ui_right");
        state.ApplyTorque(rotDir * _torqueForce);
    }
}
```

> **Warning:** `_integrate_forces()` is NOT called while the body is sleeping. Enable `can_sleep = false` if you need continuous callbacks, but prefer letting bodies sleep for performance.

### Contact Monitoring

To receive `body_entered`/`body_exited` signals on a RigidBody:

1. Set `contact_monitor = true`
2. Set `max_contacts_reported` to a non-zero value (e.g. 4)

```gdscript
extends RigidBody3D

func _ready() -> void:
    contact_monitor = true
    max_contacts_reported = 4
    body_entered.connect(_on_body_entered)

func _on_body_entered(body: Node) -> void:
    if body.has_method("take_damage"):
        body.take_damage(10)
```

```csharp
public partial class PhysicsCrate : RigidBody3D
{
    public override void _Ready()
    {
        ContactMonitor = true;
        MaxContactsReported = 4;
        BodyEntered += OnBodyEntered;
    }

    private void OnBodyEntered(Node body)
    {
        if (body.HasMethod("TakeDamage"))
            body.Call("TakeDamage", 10);
    }
}
```

### PhysicsMaterial

Attach a `PhysicsMaterial` resource to control surface properties:

| Property | Default | Effect |
|----------|---------|--------|
| `friction` | 1.0 | Resistance to sliding (0 = ice, 1 = rubber) |
| `bounce` | 0.0 | Restitution (0 = no bounce, 1 = full bounce) |
| `rough` | false | If true, uses max friction instead of geometric mean |
| `absorbent` | false | If true, uses min bounce instead of geometric mean |

### Freeze Modes

RigidBody can be frozen to temporarily stop physics simulation:

| Mode | Behavior |
|------|----------|
| `FREEZE_MODE_STATIC` | Acts like a StaticBody (other bodies collide with it) |
| `FREEZE_MODE_KINEMATIC` | Acts like an AnimatableBody (can be moved by code, pushes other bodies) |

```gdscript
# Freeze a crate in place
rigid_body.freeze = true
rigid_body.freeze_mode = RigidBody3D.FREEZE_MODE_STATIC

# Unfreeze
rigid_body.freeze = false
```

### RigidBody3D look_at — Orientation via Physics

You cannot use `look_at()` on a RigidBody3D each frame. Use angular velocity via cross product instead:

```gdscript
extends RigidBody3D

@export var turn_speed: float = 0.1

func _integrate_forces(state: PhysicsDirectBodyState3D) -> void:
    var target_pos: Vector3 = $"../Target".global_position
    var forward: Vector3 = -global_transform.basis.z.normalized()
    var to_target: Vector3 = (target_pos - global_position).normalized()
    var dot: float = clampf(forward.dot(to_target), -1.0, 1.0)
    var angle_to_target: float = acos(dot)
    var turn_angle: float = minf(turn_speed, angle_to_target)
    if angle_to_target > 1e-4:
        state.angular_velocity = forward.cross(to_target).normalized() * turn_angle / state.step
```

```csharp
public partial class HomingBody : RigidBody3D
{
    [Export] public float TurnSpeed { get; set; } = 0.1f;

    public override void _IntegrateForces(PhysicsDirectBodyState3D state)
    {
        var targetPos = GetNode<Node3D>("../Target").GlobalPosition;
        var forward = -GlobalTransform.Basis.Z.Normalized();
        var toTarget = (targetPos - GlobalPosition).Normalized();
        float dot = Mathf.Clamp(forward.Dot(toTarget), -1f, 1f);
        float angleToTarget = Mathf.Acos(dot);
        float turnAngle = Mathf.Min(TurnSpeed, angleToTarget);
        if (angleToTarget > 1e-4f)
            state.AngularVelocity = forward.Cross(toTarget).Normalized() * turnAngle / state.Step;
    }
}
```

---

## 3. StaticBody2D/3D

StaticBodies are not moved by the physics engine but can impart motion to other bodies via constant velocities. They are ideal for walls, floors, and moving platforms.

### Conveyor Belt

```gdscript
extends StaticBody2D

## Speed in pixels/sec — bodies touching this surface slide along it.
@export var belt_speed: float = 100.0

func _ready() -> void:
    constant_linear_velocity = Vector2(belt_speed, 0)
```

### Moving Platform (AnimatableBody)

For platforms that move via code and push other bodies, use `AnimatableBody2D`/`3D` (extends StaticBody):

```gdscript
extends AnimatableBody2D

@export var travel: Vector2 = Vector2(0, -200)
@export var duration: float = 2.0

var _start_position: Vector2

func _ready() -> void:
    _start_position = position
    var tween: Tween = create_tween().set_loops()
    tween.tween_property(self, "position", _start_position + travel, duration)
    tween.tween_property(self, "position", _start_position, duration)
```

```csharp
public partial class MovingPlatform : AnimatableBody2D
{
    [Export] public Vector2 Travel { get; set; } = new(0, -200);
    [Export] public float Duration { get; set; } = 2.0f;

    private Vector2 _startPosition;

    public override void _Ready()
    {
        _startPosition = Position;
        var tween = CreateTween().SetLoops();
        tween.TweenProperty(this, "position", _startPosition + Travel, Duration);
        tween.TweenProperty(this, "position", _startPosition, Duration);
    }
}
```

> **Note:** `AnimatableBody2D`/`3D` is the correct node for moving platforms. A plain `StaticBody` moved by code will not push CharacterBodies reliably.

---

## 4. Area2D/3D

Areas detect overlaps and override physics properties within their bounds. They do NOT produce collision responses — bodies pass through them.

### Overlap Detection

```gdscript
extends Area2D

func _ready() -> void:
    body_entered.connect(_on_body_entered)
    body_exited.connect(_on_body_exited)

func _on_body_entered(body: Node2D) -> void:
    if body.name == "Player":
        print("Player entered the zone")

func _on_body_exited(body: Node2D) -> void:
    if body.name == "Player":
        print("Player left the zone")
```

Use `area_entered`/`area_exited` for Area-to-Area overlap (e.g. hitbox vs hurtbox — see **component-system** skill).

### Gravity Override (Zero-G Zone)

```gdscript
extends Area3D

func _ready() -> void:
    gravity_space_override = Area3D.SPACE_OVERRIDE_REPLACE
    gravity = 0.0
```

```csharp
public partial class ZeroGZone : Area3D
{
    public override void _Ready()
    {
        GravitySpaceOverride = SpaceOverride.Replace;
        Gravity = 0.0f;
    }
}
```

### Point Gravity (Black Hole / Planet)

```gdscript
extends Area2D

func _ready() -> void:
    gravity_space_override = Area2D.SPACE_OVERRIDE_COMBINE
    gravity_point = true
    gravity_point_center = Vector2.ZERO  # Relative to Area2D position
    gravity = 500.0
```

```csharp
public partial class GravityWell : Area2D
{
    public override void _Ready()
    {
        GravitySpaceOverride = SpaceOverride.Combine;
        GravityPoint = true;
        GravityPointCenter = Vector2.Zero;
        Gravity = 500.0f;
    }
}
```

### Space Override Modes

When multiple areas overlap, they're processed by `priority` (highest first):

| Mode | Behavior |
|------|----------|
| `SPACE_OVERRIDE_DISABLED` | No override |
| `SPACE_OVERRIDE_COMBINE` | Adds to running total, continues processing |
| `SPACE_OVERRIDE_REPLACE` | Replaces running total, ignores lower-priority areas |
| `SPACE_OVERRIDE_COMBINE_REPLACE` | Adds to total, then stops processing |
| `SPACE_OVERRIDE_REPLACE_COMBINE` | Replaces total, continues processing |

### Area Properties

Areas can also override `linear_damp` and `angular_damp` (for water zones, slow-mo regions), and redirect audio to a specific `AudioBus`.

---

## 5. Collision Shapes

### 2D Primitive Shapes

| Shape | Use Case |
|-------|----------|
| `RectangleShape2D` | Boxes, platforms, tiles |
| `CircleShape2D` | Balls, coins, simple characters |
| `CapsuleShape2D` | Characters (rounded, slides over edges) |
| `SegmentShape2D` | Thin walls, laser beams |
| `SeparationRayShape2D` | Character ground snapping |
| `WorldBoundaryShape2D` | Infinite floor/wall/ceiling |

### 3D Primitive Shapes

| Shape | Use Case |
|-------|----------|
| `BoxShape3D` | Crates, platforms, rooms |
| `SphereShape3D` | Balls, projectiles, trigger zones |
| `CapsuleShape3D` | Characters, humanoids |
| `CylinderShape3D` | Pillars, barrels |

### Convex vs Concave

| Type | Usable With | Performance | Notes |
|------|-------------|-------------|-------|
| Primitive | All bodies | Fastest | Always prefer for dynamic bodies |
| `ConvexPolygonShape` | All bodies | Fast | No holes or inward curves |
| `ConcavePolygonShape` | StaticBody only | Slowest | Accurate for level geometry; no volume |

### Generating Shapes from Meshes (3D)

Select a `MeshInstance3D` → **Mesh** menu:
- **Create Single Convex Collision Sibling** — Quickhull, one shape (fast, approximate)
- **Create Multiple Convex Collision Siblings** — V-HACD decomposition (more accurate for complex shapes)
- **Create Trimesh Static Body** — ConcavePolygonShape3D for static level geometry
- **Create Trimesh Collision Sibling** — Same, without creating a StaticBody wrapper

### Generating Shapes from Sprites (2D)

Select a `Sprite2D` → **Sprite2D** menu → **Create CollisionPolygon2D Sibling**. Adjust Simplification, Shrink, and Grow in the dialog.

### Performance Rules

1. **Favor primitives** for dynamic bodies (RigidBody, CharacterBody)
2. **Minimize shape count** per body — each shape costs narrow-phase checks
3. **Never translate/rotate/scale** CollisionShape nodes — a single non-transformed shape enables broad-phase optimization
4. **Use concave shapes only on StaticBodies** — they are O(n) triangle checks
5. **Multiple shapes on one body** don't collide with each other (this is correct, not a bug)
6. **Shapes must be direct children** — indirect children are ignored

---

## 6. Collision Layers and Masks

Godot provides 32 physics layers per dimension (2D and 3D separately).

- **collision_layer** — which layers this object **exists on** (others scan for it here)
- **collision_mask** — which layers this object **scans** (what it detects)

> **Mental model:** Layer = "I am", Mask = "I scan for". A collision happens when object A's mask includes object B's layer, OR vice versa.

### Naming Layers

**Project Settings → Layer Names → 2D Physics** (or 3D Physics):

```
Layer 1: Player
Layer 2: Enemy
Layer 3: World
Layer 4: Projectile
Layer 5: Pickup
Layer 6: Trigger
```

### Setting via Code

```gdscript
# Set specific layers by number (1-indexed)
collision_layer = 0   # Clear all
set_collision_layer_value(1, true)   # Add to layer 1 (Player)

collision_mask = 0    # Clear all
set_collision_mask_value(3, true)    # Scan layer 3 (World)
set_collision_mask_value(5, true)    # Scan layer 5 (Pickup)
```

```csharp
CollisionLayer = 0;
SetCollisionLayerValue(1, true);

CollisionMask = 0;
SetCollisionMaskValue(3, true);
SetCollisionMaskValue(5, true);
```

### Bitmask Shorthand

```gdscript
# Layers are bitmasks: layer 1 = bit 0, layer 2 = bit 1, etc.
collision_layer = 1 << 0             # Layer 1 only
collision_mask = (1 << 2) | (1 << 4) # Layers 3 and 5
```

### Export Flags

Expose layer selection in the inspector:

```gdscript
@export_flags_2d_physics var scan_layers: int = 0
```

```csharp
[Export(PropertyHint.Layers2DPhysics)]
public uint ScanLayers { get; set; } = 0;
```

---

## 7. Raycasting and Physics Queries

### RayCast2D/3D Nodes (Simple Per-Frame Rays)

Add a `RayCast2D` or `RayCast3D` as a child node. It casts every physics frame automatically.

```gdscript
@onready var ray: RayCast2D = $RayCast2D

func _physics_process(_delta: float) -> void:
    if ray.is_colliding():
        var collider: Object = ray.get_collider()
        var point: Vector2 = ray.get_collision_point()
        var normal: Vector2 = ray.get_collision_normal()
```

### Code-Based Raycasting (PhysicsDirectSpaceState)

For on-demand queries, access the space state. **Only safe inside `_physics_process()`** — the physics space is locked during rendering.

```gdscript
func _physics_process(_delta: float) -> void:
    var space: PhysicsDirectSpaceState2D = get_world_2d().direct_space_state
    var query := PhysicsRayQueryParameters2D.create(
        global_position,          # from
        global_position + Vector2(0, 100),  # to
    )
    query.exclude = [get_rid()]   # skip self (expects Array[RID])
    query.collision_mask = 0b0100 # only layer 3

    var result: Dictionary = space.intersect_ray(query)
    if result:
        var hit_point: Vector2 = result.position
        var hit_normal: Vector2 = result.normal
        var hit_collider: Object = result.collider
```

```csharp
public override void _PhysicsProcess(double delta)
{
    var space = GetWorld2D().DirectSpaceState;
    var query = PhysicsRayQueryParameters2D.Create(
        GlobalPosition,
        GlobalPosition + new Vector2(0, 100)
    );
    var exclude = new Godot.Collections.Array<Rid>();
    exclude.Add(GetRid());
    query.Exclude = exclude;
    query.CollisionMask = 0b0100;

    var result = space.IntersectRay(query);
    if (result.Count > 0)
    {
        var hitPoint = (Vector2)result["position"];
        var hitNormal = (Vector2)result["normal"];
        var hitCollider = (GodotObject)result["collider"];
    }
}
```

### Ray Result Dictionary

| Key | Type | Description |
|-----|------|-------------|
| `position` | Vector2/3 | World-space hit point |
| `normal` | Vector2/3 | Surface normal at hit |
| `collider` | Object | Hit node |
| `collider_id` | int | Instance ID of collider |
| `rid` | RID | Physics body RID |
| `shape` | int | Shape index on collider |

### 3D Mouse Picking (Ray from Screen)

```gdscript
const RAY_LENGTH := 1000.0

# Store mouse position from input event
var _mouse_pos: Vector2 = Vector2.ZERO

func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventMouseButton and event.pressed:
        _mouse_pos = event.position

func _physics_process(_delta: float) -> void:
    if _mouse_pos == Vector2.ZERO:
        return

    var camera: Camera3D = get_viewport().get_camera_3d()
    var origin: Vector3 = camera.project_ray_origin(_mouse_pos)
    var end: Vector3 = origin + camera.project_ray_normal(_mouse_pos) * RAY_LENGTH

    var space: PhysicsDirectSpaceState3D = get_world_3d().direct_space_state
    var query := PhysicsRayQueryParameters3D.create(origin, end)
    query.collide_with_areas = true  # also detect Area3D nodes

    var result: Dictionary = space.intersect_ray(query)
    if result:
        print("Clicked: ", result.collider.name, " at ", result.position)

    _mouse_pos = Vector2.ZERO
```

```csharp
private const float RayLength = 1000f;
private Vector2 _mousePos;

public override void _UnhandledInput(InputEvent @event)
{
    if (@event is InputEventMouseButton mb && mb.Pressed)
        _mousePos = mb.Position;
}

public override void _PhysicsProcess(double delta)
{
    if (_mousePos == Vector2.Zero) return;

    var camera = GetViewport().GetCamera3D();
    var origin = camera.ProjectRayOrigin(_mousePos);
    var end = origin + camera.ProjectRayNormal(_mousePos) * RayLength;

    var space = GetWorld3D().DirectSpaceState;
    var query = PhysicsRayQueryParameters3D.Create(origin, end);
    query.CollideWithAreas = true;

    var result = space.IntersectRay(query);
    if (result.Count > 0)
        GD.Print($"Clicked: {((Node)result["collider"]).Name} at {result["position"]}");

    _mousePos = Vector2.Zero;
}
```

### Other Query Types

`PhysicsDirectSpaceState` also supports:

| Method | Use |
|--------|-----|
| `intersect_point(params)` | Find all shapes overlapping a point |
| `intersect_shape(params)` | Find all shapes overlapping a shape (area query) |
| `cast_motion(params)` | Shape sweep — find how far a shape can move before hitting something |
| `collide_shape(params)` | Get contact points between shapes |
| `get_rest_info(params)` | Get collision info for a resting shape |

---

## 8. Jolt Physics

Jolt is a built-in alternative physics engine available since Godot 4.4. It is the **default for new 3D projects** starting in 4.4.

### Enabling Jolt

**Project Settings → Physics → 3D → Physics Engine** → set to `Jolt Physics` → Save → Restart editor.

> Jolt is 3D only. 2D always uses GodotPhysics.

### Why Use Jolt

| Advantage | Detail |
|-----------|--------|
| Stability | Better stacking, fewer wobbles |
| Cylinder support | CylinderShape3D works reliably |
| Soft body support | Better SoftBody3D simulation |
| Thread safety | Supports `Physics > 3D > Run On Separate Thread` (experimental) |
| Ghost collision fix | Active edge detection and enhanced internal edge removal |

### Key Differences from GodotPhysics

- **Baumgarte stabilization:** position-only correction (no overshoot, may take longer). Configure: `Physics > Jolt Physics 3D > Simulation > Baumgarte Stabilization Factor`
- **Collision margins:** Jolt uses convex radius (shrinks shape, then applies shell). Configure: `Physics > Jolt Physics 3D > Collisions > Collision Margin Fraction`
- **Single-body joints:** Jolt treats unassigned node as `node_a` (world), opposite of GodotPhysics. Toggle: `Physics > Jolt Physics 3D > Joints > World Node`
- **face_index from raycasts:** returns `-1` by default. Enable: `Physics > Jolt Physics 3D > Queries > Enable Ray Cast Face Index` (increases memory ~25% for ConcavePolygonShape3D)
- **Unsupported joint properties:** `bias`, `softness`, `relaxation`, `damping` on PinJoint3D, HingeJoint3D, SliderJoint3D, ConeTwistJoint3D are ignored

### Migration from Extension

If migrating from the Godot Jolt extension (now maintenance mode), project settings moved from `physics/jolt_3d/` to `physics/jolt_physics_3d/`. Key renames:
- `sleep/enabled` → `simulation/allow_sleep`
- `collisions/use_shape_margins` → `collisions/collision_margin_fraction`
- `solver/velocity_iterations` → `simulation/velocity_steps`
- `solver/position_iterations` → `simulation/position_steps`

---

## 9. Physics Interpolation

Physics interpolation smooths visual motion between physics ticks, eliminating "staircase" jitter when physics tick rate differs from frame rate.

### Enabling

**Project Settings → Physics → Common → Physics Interpolation** → enable.

### Core Rules

1. **Move all game logic to `_physics_process()`** — transforms set outside physics ticks cause jitter
2. **Tweens and AnimationPlayer** that move physics objects must use physics tick timing
3. **Call `reset_physics_interpolation()`** when teleporting or initially placing objects to prevent "streaking" between old and new position

```gdscript
# Teleport a node cleanly
func teleport_to(pos: Vector2) -> void:
    global_position = pos
    reset_physics_interpolation()
```

```csharp
public void TeleportTo(Vector2 pos)
{
    GlobalPosition = pos;
    ResetPhysicsInterpolation();
}
```

### Per-Node Control

```gdscript
# Disable interpolation for a specific node (and children)
node.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
```

Values: `PHYSICS_INTERPOLATION_MODE_INHERIT` (default), `PHYSICS_INTERPOLATION_MODE_ON`, `PHYSICS_INTERPOLATION_MODE_OFF`.

### Choosing Tick Rate

| Rate | Tradeoff |
|------|----------|
| 10–30 TPS | Less CPU, more input delay, simpler physics |
| 30–60 TPS | Good balance for most games (60 is default) |
| 60+ TPS | Fast-paced games, racing, precision platformers |

> **Testing tip:** Temporarily set tick rate to 10 TPS to make interpolation problems obvious during development.

### Camera Interpolation

Cameras often need special handling. For a smooth follow camera with interpolation enabled:

1. Make camera independent (not a child of the followed node) or set `top_level = true`
2. Update camera in `_process()` (not `_physics_process()`)
3. Use `get_global_transform_interpolated()` to read the target's smooth position

```gdscript
extends Camera3D

@onready var _target: Node3D = $"../Player"
var _smooth_pos: Vector3

func _ready() -> void:
    physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF

func _process(delta: float) -> void:
    var target_transform: Transform3D = _target.get_global_transform_interpolated()
    _smooth_pos = _smooth_pos.lerp(target_transform.origin, minf(delta * 5.0, 1.0))
    look_at(_smooth_pos, Vector3.UP)
```

> **Note:** `get_global_transform_interpolated()` should only be used for special cases like cameras (1–2 calls per frame). Regular game logic should use `global_transform` inside `_physics_process()`.

---

## 10. Ragdoll System

Ragdolls replace animation with physics simulation for procedural death animations, explosions, or limp characters.

### Setup (3D)

1. Select `Skeleton3D` node → **Skeleton** menu → **Create Physical Skeleton**
2. This generates `PhysicalBoneSimulator3D` with `PhysicalBone3D` children, each with a collision shape and pin joint
3. **Clean up:** Remove unnecessary bones (master, waist, neck tracker, etc.) — each PhysicalBone3D has a performance cost

### Joint Types

| Joint | Use | Notes |
|-------|-----|-------|
| `PinJoint` | Default, keeps connected | Can cause crumpling — replace with better types |
| `ConeJoint` | Ball-and-socket (shoulders, hips, neck) | Swing Span 20–90°, Twist Span 20–45° |
| `HingeJoint` | Elbows, knees | Enable Angular Limit, set min/max angles |
| `SliderJoint` | Slides on axis | Mechanical joints, pistons |
| `6DOFJoint` | Full control | Linear + angular limits per axis |

> **Tip:** Adjust joints BEFORE collision shapes. Rotating a joint also rotates its child shape.

### Starting Simulation

```gdscript
@onready var sim: PhysicalBoneSimulator3D = $Skeleton3D/PhysicalBoneSimulator3D

# Full ragdoll
func enable_ragdoll() -> void:
    sim.physical_bones_start_simulation()

# Partial ragdoll (e.g. limp arms only)
func enable_partial_ragdoll() -> void:
    sim.physical_bones_start_simulation(["LeftArm", "RightArm"])

# Stop ragdoll and return to animation
func disable_ragdoll() -> void:
    sim.physical_bones_stop_simulation()
```

```csharp
private PhysicalBoneSimulator3D _sim;

public override void _Ready()
{
    _sim = GetNode<PhysicalBoneSimulator3D>("Skeleton3D/PhysicalBoneSimulator3D");
}

public void EnableRagdoll()
{
    _sim.PhysicalBonesStartSimulation();
}

public void EnablePartialRagdoll()
{
    _sim.PhysicalBonesStartSimulation(new StringName[] { "LeftArm", "RightArm" });
}
```

### Blending Animation and Ragdoll

`PhysicalBoneSimulator3D.Influence` (0.0 to 1.0) controls blend between animation and physics. At 0.0 animation dominates, at 1.0 physics dominates.

### Collision Setup

Prevent the character's own CollisionShape from fighting the ragdoll:
- Put the character capsule and ragdoll bones on different collision layers
- Or use `physical_bones_add_collision_exception(character_rid)` to exclude the character body

---

## 11. SoftBody3D

SoftBody3D simulates deformable objects like cloth, capes, and jelly. Jolt Physics is recommended for soft bodies.

### Basic Setup

1. Add `SoftBody3D` node (no CollisionShape child needed — collision is derived from mesh)
2. Assign a mesh with sufficient subdivision (e.g. `PlaneMesh` with subdivide 5×5 for cloth)
3. Set **Simulation Precision** ≥ 5 (prevents collapse)

> **Warning:** `Pressure` > 0.0 on non-closed meshes causes flying behavior. Only use pressure on closed shapes like spheres.

### Cloth / Cape Example

1. Add `SoftBody3D` with `PlaneMesh` (size 0.5×1.0, subdivide width/depth = 5)
2. Position behind character
3. Add `BoneAttachment3D` under Skeleton3D → select Neck bone
4. In SoftBody3D → **Attachments** section: pin top-row vertices → set **Spatial Attachment Path** to the BoneAttachment3D
5. Add character's CollisionShape to **Parent Collision Ignore**
6. Disable backface culling on the mesh material

### Physics Interpolation Note

Physics interpolation does NOT affect SoftBody3D rendering. If soft bodies look choppy, increase **Physics Ticks per Second** instead.

---

## 12. Troubleshooting Physics Issues

### Tunneling (Objects Pass Through at High Speed)

| Solution | How |
|----------|-----|
| Enable Continuous CD | RigidBody → `continuous_cd = true` |
| Thicken static colliders | Make walls/floors thicker |
| Increase tick rate | `Physics Ticks per Second`: 120, 180, or 240 |
| Adjust collision shape | Extend shape in direction of travel based on speed |

### Stacked Objects Wobble

- Increase physics tick rate
- Switch to Jolt (3D) — much better stacking stability

### Scaled Shapes Don't Collide Correctly

- **Never scale** physics bodies or shapes via `scale` property
- Change shape size parameters directly (radius, extents, height)
- If visual and collision need different sizes, make them siblings (not parent-child)
- Remember to **Make Unique** on shared shape resources (`shape.duplicate()`)

### Tile Collision Bumps

Characters snag on edges between adjacent tile colliders:
- Godot 4.5+: `TileMapLayer` auto-merges via **Physics Quadrant Size** (default 16)
- Pre-4.5: Manually create composite colliders (one shape per island of touching tiles)

### CylinderShape3D Unstable

- Switch to Jolt (fully supported)
- With GodotPhysics: substitute CapsuleShape3D or BoxShape3D

### Physics Spiral of Death

Engine can't finish physics simulation within a frame:
- Increase **Max Physics Steps per Frame** (Project Settings)
- Reduce **Physics Ticks per Second**
- Reduce physics body count or collision complexity

### Unreliable Far from Origin

Floating-point precision degrades with distance. Precision thresholds (3D, single precision):

| Distance | Max Step | Suitable For |
|----------|----------|-------------|
| 2048–4096 | ~0.0002 | First-person games |
| 4096–8192 | ~0.0005 | Third-person games |
| 16384–32768 | ~0.002 | Top-down games |
| >32768 | >0.004 | Requires double precision build |

For planetary-scale games, recompile with `precision=double` or implement origin shifting.

---

## 13. Implementation Checklist

- [ ] All dynamic bodies use primitive collision shapes where possible
- [ ] Collision layers are named in Project Settings and bodies use layer/mask correctly
- [ ] RigidBodies use `_integrate_forces()` for direct state modification, not `_physics_process()`
- [ ] RigidBodies that need contact signals have `contact_monitor = true` and `max_contacts_reported > 0`
- [ ] No collision shapes or bodies have non-uniform `scale` values
- [ ] Moving platforms use `AnimatableBody2D/3D`, not manually moved StaticBodies
- [ ] Raycasts via code use `PhysicsDirectSpaceState` inside `_physics_process()` only
- [ ] Physics interpolation is enabled and `reset_physics_interpolation()` is called on teleport
- [ ] Concave collision shapes are only used on StaticBodies
- [ ] Ragdoll bones are on separate collision layers from the character's main collider
