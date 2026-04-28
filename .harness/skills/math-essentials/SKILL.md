---
name: math-essentials
description: Use when implementing game math — vectors, transforms, interpolation, curves, random number generation, and common geometric recipes
---

# Game Math in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, then C#.

> **Related skills:** **player-controller** for movement physics, **ai-navigation** for pathfinding math, **camera-system** for camera interpolation, **tween-animation** for easing curves, **physics-system** for collision math.

---

## 1. Vector Operations

### Essential Vector Methods

| Method                  | Returns   | Description                                   |
|-------------------------|-----------|-----------------------------------------------|
| `length()`              | `float`   | Magnitude of the vector                       |
| `length_squared()`      | `float`   | Squared magnitude (faster, skip sqrt)         |
| `normalized()`          | `Vector`  | Unit vector (length 1) in the same direction  |
| `distance_to(b)`        | `float`   | Distance between two points                   |
| `distance_squared_to(b)` | `float` | Squared distance (faster for comparisons)     |
| `direction_to(b)`       | `Vector`  | Normalized direction from this to b           |
| `angle_to(b)`           | `float`   | Angle in radians between two vectors          |
| `angle_to_point(b)`     | `float`   | Angle from this point to b (2D)               |
| `dot(b)`                | `float`   | Dot product                                   |
| `cross(b)`              | `float/Vector3` | Cross product (2D returns float, 3D returns vector) |
| `rotated(angle)`        | `Vector2` | Rotated by radians (2D)                       |
| `move_toward(to, delta)` | `Vector` | Move toward target by at most delta           |
| `clamp(min, max)`       | `Vector`  | Clamp each component                          |
| `snapped(step)`         | `Vector`  | Snap to grid                                  |
| `reflect(normal)`       | `Vector`  | Reflect off a surface                         |
| `bounce(normal)`        | `Vector`  | Bounce off a surface (inverted reflect)       |
| `slide(normal)`         | `Vector`  | Slide along a surface                         |

### Direction and Distance

```gdscript
# Get direction from A to B (normalized)
var dir: Vector2 = global_position.direction_to(target.global_position)

# Get distance
var dist: float = global_position.distance_to(target.global_position)

# Use squared distance for comparisons (faster — avoids sqrt)
if global_position.distance_squared_to(target.global_position) < detection_range * detection_range:
    chase_target()
```

```csharp
Vector2 dir = GlobalPosition.DirectionTo(target.GlobalPosition);
float dist = GlobalPosition.DistanceTo(target.GlobalPosition);

if (GlobalPosition.DistanceSquaredTo(target.GlobalPosition) < detectionRange * detectionRange)
    ChaseTarget();
```

### Dot Product

The dot product tells you how aligned two vectors are.

```gdscript
# Is the target in front of us? (dot > 0 = in front, < 0 = behind)
var forward: Vector2 = Vector2.RIGHT.rotated(rotation)
var to_target: Vector2 = global_position.direction_to(target.global_position)
var dot: float = forward.dot(to_target)

if dot > 0.7:  # roughly within ~45° cone
    print("Target is ahead")
elif dot < -0.7:
    print("Target is behind")
```

```csharp
Vector2 forward = Vector2.Right.Rotated(Rotation);
Vector2 toTarget = GlobalPosition.DirectionTo(target.GlobalPosition);
float dot = forward.Dot(toTarget);

if (dot > 0.7f) GD.Print("Target is ahead");
```

### Cross Product (3D)

The cross product gives a vector perpendicular to two input vectors.

```gdscript
# Get the surface normal from two edge vectors
var edge1: Vector3 = vertex_b - vertex_a
var edge2: Vector3 = vertex_c - vertex_a
var normal: Vector3 = edge1.cross(edge2).normalized()
```

```csharp
Vector3 edge1 = vertexB - vertexA;
Vector3 edge2 = vertexC - vertexA;
Vector3 normal = edge1.Cross(edge2).Normalized();
```

---

## 2. Transforms

### Transform2D

A 2D transform holds position, rotation, and scale.

```gdscript
# Get the global transform
var xform: Transform2D = global_transform

# Convert between local and global space
var local_point: Vector2 = to_local(global_point)
var world_point: Vector2 = to_global(local_point)

# Apply transform to a point
var transformed: Vector2 = xform * Vector2(10, 0)  # point in local space → global

# Inverse transform
var local: Vector2 = xform.affine_inverse() * global_point
```

```csharp
Transform2D xform = GlobalTransform;
Vector2 localPoint = ToLocal(globalPoint);
Vector2 worldPoint = ToGlobal(localPoint);
Vector2 transformed = xform * new Vector2(10, 0);
Vector2 local = xform.AffineInverse() * globalPoint;
```

### Transform3D & Basis

```gdscript
# Basis holds rotation and scale as 3 column vectors
var basis: Basis = global_transform.basis

# Forward direction (looking along -Z in Godot)
var forward: Vector3 = -basis.z
var right: Vector3 = basis.x
var up: Vector3 = basis.y

# Look at a target
look_at(target.global_position, Vector3.UP)

# Rotate around an axis
rotate_y(deg_to_rad(90.0))
rotate_object_local(Vector3.UP, deg_to_rad(45.0))

# Interpolate between two transforms (smooth transition)
var a: Transform3D = $Start.global_transform
var b: Transform3D = $End.global_transform
global_transform = a.interpolate_with(b, 0.5)  # halfway
```

```csharp
Basis basis = GlobalTransform.Basis;
Vector3 forward = -basis.Z;
Vector3 right = basis.X;
Vector3 up = basis.Y;

LookAt(target.GlobalPosition, Vector3.Up);
RotateY(Mathf.DegToRad(90.0f));

Transform3D a = GetNode<Node3D>("Start").GlobalTransform;
Transform3D b = GetNode<Node3D>("End").GlobalTransform;
GlobalTransform = a.InterpolateWith(b, 0.5f);
```

---

## 3. Interpolation

### lerp — Linear Interpolation

```gdscript
# Interpolate between two values (t = 0.0 to 1.0)
var mid: float = lerp(0.0, 100.0, 0.5)   # 50.0
var pos: Vector2 = lerp(start_pos, end_pos, 0.75)  # 75% of the way

# Smooth following — lerp with delta for frame-rate independence
func _process(delta: float) -> void:
    position = position.lerp(target_position, 5.0 * delta)
```

```csharp
float mid = Mathf.Lerp(0.0f, 100.0f, 0.5f);
Vector2 pos = startPos.Lerp(endPos, 0.75f);

public override void _Process(double delta)
{
    Position = Position.Lerp(targetPosition, 5.0f * (float)delta);
}
```

> **Warning:** `lerp(a, b, speed * delta)` is frame-rate dependent and never fully reaches the target. For precise movement, use `move_toward()` instead.

### move_toward — Fixed-Speed Approach

```gdscript
# Move exactly `speed * delta` units toward target each frame
position.x = move_toward(position.x, target_x, speed * delta)

# Vector version
position = position.move_toward(target_position, speed * delta)
```

```csharp
float newX = Mathf.MoveToward(Position.X, targetX, speed * (float)delta);
Position = Position.MoveToward(targetPosition, speed * (float)delta);
```

### slerp — Spherical Interpolation

For smooth rotation interpolation (preserves arc, not straight line).

```gdscript
# Quaternion slerp for smooth 3D rotation
var current_quat: Quaternion = global_transform.basis.get_rotation_quaternion()
var target_quat: Quaternion = target_transform.basis.get_rotation_quaternion()
var result: Quaternion = current_quat.slerp(target_quat, 5.0 * delta)
global_transform.basis = Basis(result)
```

```csharp
Quaternion currentQuat = GlobalTransform.Basis.GetRotationQuaternion();
Quaternion targetQuat = targetTransform.Basis.GetRotationQuaternion();
Quaternion result = currentQuat.Slerp(targetQuat, 5.0f * (float)delta);
GlobalTransform = new Transform3D(new Basis(result), GlobalPosition);
```

### smoothstep — S-Curve Easing

```gdscript
# Returns 0.0 when x <= from, 1.0 when x >= to, smooth curve between
var t: float = smoothstep(0.0, 10.0, distance)  # 0→1 as distance goes 0→10

# Useful for soft thresholds (fog density, volume falloff)
var fog_intensity: float = smoothstep(50.0, 100.0, camera_distance)
```

### cubic_interpolate — Smooth Path Following

```gdscript
# Smooth interpolation using 4 control points (catmull-rom style)
var point: Vector2 = p1.cubic_interpolate(p2, p0, p3, t)
# p0 = before start, p1 = start, p2 = end, p3 = after end
```

### Interpolation Comparison

| Function           | Speed          | Reaches Target | Smooth | Use For                    |
|--------------------|----------------|----------------|--------|----------------------------|
| `lerp(a, b, t)`   | Variable       | Only at t=1    | Yes    | UI transitions, blending   |
| `move_toward()`    | Constant       | Yes            | No     | Movement, timers           |
| `slerp()`          | Variable       | Only at t=1    | Yes    | Rotation blending          |
| `smoothstep()`     | S-curve        | Soft threshold | Yes    | Fog, volume, thresholds    |
| `cubic_interpolate()` | Variable    | Only at t=1    | Very   | Paths, camera rails        |

---

## 4. Curves & Paths

### Curve Resources

```gdscript
# Curve — 1D curve (maps x: 0.0–1.0 to y value)
var curve := Curve.new()
curve.add_point(Vector2(0.0, 0.0))  # start at 0
curve.add_point(Vector2(0.5, 1.0))  # peak at halfway
curve.add_point(Vector2(1.0, 0.0))  # back to 0
var value: float = curve.sample(0.25)  # sample at 25%

# CurveTexture — wrap Curve for use in shaders/particles
var curve_tex := CurveTexture.new()
curve_tex.curve = curve
```

### Path2D / Path3D

Paths define a Curve2D/Curve3D that nodes can follow.

```
Level (Node2D)
├── Path2D
│   └── PathFollow2D
│       └── Enemy (CharacterBody2D)
```

```gdscript
# Move along the path
@onready var path_follow: PathFollow2D = $Path2D/PathFollow2D

func _physics_process(delta: float) -> void:
    path_follow.progress += speed * delta
    # Or use ratio (0.0 to 1.0)
    # path_follow.progress_ratio += 0.1 * delta
```

```csharp
private PathFollow2D _pathFollow;

public override void _Ready()
{
    _pathFollow = GetNode<PathFollow2D>("Path2D/PathFollow2D");
}

public override void _PhysicsProcess(double delta)
{
    _pathFollow.Progress += speed * (float)delta;
}
```

### PathFollow Properties

| Property         | Description                                      |
|------------------|--------------------------------------------------|
| `progress`       | Distance along the curve in pixels/units         |
| `progress_ratio` | 0.0–1.0 position along the curve                |
| `loop`           | Wrap around when reaching the end                |
| `rotates`        | Auto-rotate to face the curve direction          |
| `cubic_interp`   | Use cubic interpolation for smoother following   |

---

## 5. Random Number Generation

### Global Functions

```gdscript
var f: float = randf()                    # 0.0 to 1.0
var i: int = randi()                      # full int range
var ranged: float = randf_range(1.0, 10.0)  # 1.0 to 10.0
var ranged_int: int = randi_range(1, 6)   # 1 to 6 (inclusive)
```

```csharp
float f = GD.Randf();
int i = GD.Randi();
float ranged = GD.RandfRange(1.0f, 10.0f);
int rangedInt = GD.RandiRange(1, 6);
```

### RandomNumberGenerator (Seeded)

For deterministic, reproducible randomness (procedural generation, replays).

```gdscript
var rng := RandomNumberGenerator.new()
rng.seed = 12345  # same seed = same sequence every time

var value: float = rng.randf_range(0.0, 100.0)
var roll: int = rng.randi_range(1, 20)
var normal: float = rng.randfn(0.0, 1.0)  # Gaussian distribution
```

```csharp
var rng = new RandomNumberGenerator();
rng.Seed = 12345;

float value = rng.RandfRange(0.0f, 100.0f);
int roll = rng.RandiRange(1, 20);
float normal = rng.Randfn(0.0f, 1.0f);
```

### Weighted Random Selection

```gdscript
# Weighted random pick from a loot table
func weighted_random(table: Array[Dictionary]) -> Dictionary:
    # table = [{"item": "gold", "weight": 60}, {"item": "gem", "weight": 30}, {"item": "rare", "weight": 10}]
    var total_weight: float = 0.0
    for entry in table:
        total_weight += entry["weight"]

    var roll: float = randf() * total_weight
    var cumulative: float = 0.0
    for entry in table:
        cumulative += entry["weight"]
        if roll <= cumulative:
            return entry

    return table.back()
```

```csharp
public Dictionary WeightedRandom(Godot.Collections.Array<Godot.Collections.Dictionary> table)
{
    float totalWeight = 0.0f;
    foreach (var entry in table)
        totalWeight += (float)entry["weight"];

    float roll = GD.Randf() * totalWeight;
    float cumulative = 0.0f;
    foreach (var entry in table)
    {
        cumulative += (float)entry["weight"];
        if (roll <= cumulative)
            return entry;
    }
    return table[^1];
}
```

### Noise (Procedural Generation)

```gdscript
var noise := FastNoiseLite.new()
noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
noise.frequency = 0.05
noise.seed = randi()

# Sample 2D noise at a position
var height: float = noise.get_noise_2d(x, y)  # returns -1.0 to 1.0
```

```csharp
var noise = new FastNoiseLite();
noise.NoiseType = FastNoiseLite.NoiseTypeEnum.SimplexSmooth;
noise.Frequency = 0.05f;
noise.Seed = (int)GD.Randi();
float height = noise.GetNoise2D(x, y);
```

---

## 6. Common Game Math Recipes

### Look At Target (2D)

```gdscript
# Instant look-at
rotation = global_position.angle_to_point(target.global_position)

# Smooth rotation toward target
var target_angle: float = global_position.angle_to_point(target.global_position)
rotation = lerp_angle(rotation, target_angle, 10.0 * delta)
```

```csharp
Rotation = GlobalPosition.AngleToPoint(target.GlobalPosition);

float targetAngle = GlobalPosition.AngleToPoint(target.GlobalPosition);
Rotation = Mathf.LerpAngle(Rotation, targetAngle, 10.0f * (float)delta);
```

### Orbit Around a Point

```gdscript
func _process(delta: float) -> void:
    var angle: float = Time.get_ticks_msec() / 1000.0 * orbit_speed
    position = center + Vector2(cos(angle), sin(angle)) * orbit_radius
```

```csharp
public override void _Process(double delta)
{
    float angle = Time.GetTicksMsec() / 1000.0f * orbitSpeed;
    Position = center + new Vector2(Mathf.Cos(angle), Mathf.Sin(angle)) * orbitRadius;
}
```

### Sine Wave Bob (Floating Effect)

```gdscript
var _base_y: float

func _ready() -> void:
    _base_y = position.y

func _process(delta: float) -> void:
    position.y = _base_y + sin(Time.get_ticks_msec() / 1000.0 * bob_speed) * bob_amplitude
```

```csharp
private float _baseY;

public override void _Ready() => _baseY = Position.Y;

public override void _Process(double delta)
{
    Vector2 pos = Position;
    pos.Y = _baseY + Mathf.Sin(Time.GetTicksMsec() / 1000.0f * bobSpeed) * bobAmplitude;
    Position = pos;
}
```

### Angle Wrapping

```gdscript
# Wrap angle to -PI..PI range
var wrapped: float = wrapf(angle, -PI, PI)

# Shortest rotation direction between two angles
var diff: float = angle_difference(current_angle, target_angle)
# Returns the shortest path, accounting for wrapping

# Lerp angles correctly (handles wrapping)
rotation = lerp_angle(rotation, target_rotation, 5.0 * delta)
```

```csharp
float wrapped = Mathf.Wrap(angle, -Mathf.Pi, Mathf.Pi);
float diff = Mathf.AngleDifference(currentAngle, targetAngle);
Rotation = Mathf.LerpAngle(Rotation, targetRotation, 5.0f * (float)delta);
```

### Clamped Approach with Deadzone

```gdscript
# Move toward target but stop within a deadzone
func approach_with_deadzone(current: Vector2, target: Vector2, speed: float, deadzone: float, delta: float) -> Vector2:
    var dist: float = current.distance_to(target)
    if dist <= deadzone:
        return current
    return current.move_toward(target, speed * delta)
```

---

## 7. Common Pitfalls

| Symptom                              | Cause                                       | Fix                                                              |
|--------------------------------------|----------------------------------------------|------------------------------------------------------------------|
| `lerp` never reaches target          | Using `lerp(a, b, speed * delta)` each frame | Use `move_toward()` for exact arrival                            |
| Rotation jumps at 180°               | Using `lerp` instead of `lerp_angle`         | Always use `lerp_angle()` for angle interpolation                |
| Object faces wrong direction (3D)    | Forgot Godot uses -Z as forward              | Forward direction is `-global_transform.basis.z`                 |
| Distance check too slow              | Calling `distance_to` on many objects        | Use `distance_squared_to` and compare against `range * range`    |
| Normalized zero vector crashes       | Calling `normalized()` on `Vector2.ZERO`     | Check `length() > 0` first, or use `direction_to()`             |
| Transform interpolation looks wrong  | Lerping euler angles instead of quaternions  | Use `Quaternion.slerp()` or `Transform3D.interpolate_with()`    |
| Random results repeat after restart  | Using `RandomNumberGenerator` with fixed seed | Godot 4.x auto-seeds global RNG; for `RandomNumberGenerator` use `randomize()` or set `seed` |
| Noise values are all ~0              | `frequency` too low                          | Increase `FastNoiseLite.frequency` (try 0.01–0.1)               |

---

## 8. Implementation Checklist

- [ ] Distance comparisons use `distance_squared_to()` for performance
- [ ] Angle interpolation uses `lerp_angle()`, not `lerp()`
- [ ] 3D forward direction is `-transform.basis.z`, not `+z`
- [ ] `move_toward()` is used when exact arrival at target is needed
- [ ] `lerp(a, b, speed * delta)` is understood as frame-rate dependent smooth following, not exact movement
- [ ] `RandomNumberGenerator` is used for deterministic/seeded randomness (procedural generation, replays)
- [ ] Noise-based generation uses `FastNoiseLite` with appropriate frequency and seed
- [ ] Weighted random selection is used for loot tables and probability-based systems
- [ ] Path following uses `PathFollow2D/3D` with `progress` or `progress_ratio`
- [ ] Quaternion slerp is used for 3D rotation interpolation instead of euler angles
