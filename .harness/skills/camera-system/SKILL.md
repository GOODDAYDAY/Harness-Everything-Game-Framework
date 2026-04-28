---
name: camera-system
description: Use when implementing cameras — smooth follow, screen shake, camera zones, and transitions for 2D and 3D
---

# Camera Systems in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, then C#.

> **Related skills:** **player-controller** for first-person camera setup, **state-machine** for camera state transitions, **godot-optimization** for camera culling and performance, **physics-system** for physics interpolation and camera smoothing, **2d-essentials** for canvas layers, parallax scrolling, and coordinate conversion.

---

## 1. Camera2D Basics

### Key Properties

| Property | Type | Description |
|---|---|---|
| `position_smoothing_enabled` | `bool` | Enables built-in position smoothing (lerp toward target) |
| `position_smoothing_speed` | `float` | Speed of built-in smoothing (default `5.0`) |
| `drag_horizontal_enabled` | `bool` | Enables a horizontal drag zone; camera only moves when target exits zone |
| `drag_vertical_enabled` | `bool` | Enables a vertical drag zone |
| `limit_left` | `int` | Left pixel boundary — camera will not scroll past this |
| `limit_right` | `int` | Right pixel boundary |
| `limit_top` | `int` | Top pixel boundary |
| `limit_bottom` | `int` | Bottom pixel boundary |
| `zoom` | `Vector2` | Zoom level; `Vector2(2, 2)` = 2× zoom in, `Vector2(0.5, 0.5)` = zoom out |

Set limits to match your tilemap or level bounds so the camera never shows outside the world. Limits are in world pixels, not tiles.

---

## 2. Smooth Follow

A manual follow camera gives more control than the built-in smoothing — you can add look-ahead, offset, and custom easing.

### GDScript

```gdscript
extends Camera2D

## Target node to follow (assign in Inspector or via code)
@export var target: Node2D

## How quickly the camera catches up to the target (higher = snappier)
@export var follow_speed: float = 8.0

## How far ahead the camera leads in the movement direction
@export var look_ahead_distance: float = 80.0

## How quickly the look-ahead offset responds to direction changes
@export var look_ahead_speed: float = 4.0

var _look_ahead_offset: Vector2 = Vector2.ZERO
var _previous_target_pos: Vector2 = Vector2.ZERO

func _ready() -> void:
    # Disable built-in smoothing — we handle it manually
    position_smoothing_enabled = false
    if target:
        _previous_target_pos = target.global_position
        global_position = target.global_position

func _process(delta: float) -> void:
    if not target:
        return

    # Compute movement direction from last frame
    var move_delta: Vector2 = target.global_position - _previous_target_pos
    _previous_target_pos = target.global_position

    # Smoothly steer look-ahead offset toward movement direction
    var desired_ahead: Vector2 = move_delta.normalized() * look_ahead_distance if move_delta.length() > 0.5 else Vector2.ZERO
    _look_ahead_offset = _look_ahead_offset.lerp(desired_ahead, look_ahead_speed * delta)

    # Lerp camera position toward target + look-ahead
    var desired_pos: Vector2 = target.global_position + _look_ahead_offset
    global_position = global_position.lerp(desired_pos, follow_speed * delta)
```

### C#

```csharp
using Godot;

public partial class SmoothFollowCamera : Camera2D
{
    [Export] public Node2D Target { get; set; }
    [Export] public float FollowSpeed { get; set; } = 8.0f;
    [Export] public float LookAheadDistance { get; set; } = 80.0f;
    [Export] public float LookAheadSpeed { get; set; } = 4.0f;

    private Vector2 _lookAheadOffset = Vector2.Zero;
    private Vector2 _previousTargetPos = Vector2.Zero;

    public override void _Ready()
    {
        PositionSmoothingEnabled = false;
        if (Target != null)
        {
            _previousTargetPos = Target.GlobalPosition;
            GlobalPosition = Target.GlobalPosition;
        }
    }

    public override void _Process(double delta)
    {
        if (Target == null)
            return;

        float dt = (float)delta;

        Vector2 moveDelta = Target.GlobalPosition - _previousTargetPos;
        _previousTargetPos = Target.GlobalPosition;

        Vector2 desiredAhead = moveDelta.Length() > 0.5f
            ? moveDelta.Normalized() * LookAheadDistance
            : Vector2.Zero;

        _lookAheadOffset = _lookAheadOffset.Lerp(desiredAhead, LookAheadSpeed * dt);

        Vector2 desiredPos = Target.GlobalPosition + _lookAheadOffset;
        GlobalPosition = GlobalPosition.Lerp(desiredPos, FollowSpeed * dt);
    }
}
```

---

## 3. Screen Shake

A trauma-based system produces more natural-looking shake than a simple sine wave. High trauma = violent shake; trauma decays over time; offset scales with `trauma^2` so small trauma values feel subtle.

### GDScript

```gdscript
extends Camera2D

## Maximum pixel offset during maximum trauma
@export var max_offset: Vector2 = Vector2(20.0, 15.0)

## Maximum rotation offset in degrees during maximum trauma
@export var max_roll: float = 3.0

## Rate at which trauma decays per second (0–1 range)
@export var decay_rate: float = 1.5

var _trauma: float = 0.0  # 0.0 = no shake, 1.0 = maximum shake

# Optional: use noise for smooth, organic shake
var _noise: FastNoiseLite
var _noise_time: float = 0.0
@export var use_noise: bool = true
@export var noise_speed: float = 60.0

func _ready() -> void:
    _noise = FastNoiseLite.new()
    _noise.noise_type = FastNoiseLite.TYPE_SIMPLEX
    _noise.seed = randi()

## Call this from any node to trigger a shake (amount in 0–1 range; can stack)
func add_trauma(amount: float) -> void:
    _trauma = minf(_trauma + amount, 1.0)

func _process(delta: float) -> void:
    if _trauma <= 0.0:
        offset = Vector2.ZERO
        rotation = 0.0
        return

    # Decay trauma over time
    _trauma = maxf(_trauma - decay_rate * delta, 0.0)
    _noise_time += delta * noise_speed

    var shake: float = _trauma * _trauma  # squaring gives subtle feel at low trauma

    if use_noise:
        offset.x = max_offset.x * shake * _noise.get_noise_2d(_noise_time, 0.0)
        offset.y = max_offset.y * shake * _noise.get_noise_2d(0.0, _noise_time)
        rotation = deg_to_rad(max_roll) * shake * _noise.get_noise_2d(_noise_time, _noise_time)
    else:
        offset.x = max_offset.x * shake * randf_range(-1.0, 1.0)
        offset.y = max_offset.y * shake * randf_range(-1.0, 1.0)
        rotation = deg_to_rad(max_roll) * shake * randf_range(-1.0, 1.0)
```

**Triggering shake from another node:**

```gdscript
# Any node that can reach the camera
func on_explosion() -> void:
    var cam := get_viewport().get_camera_2d() as ScreenShakeCamera
    if cam:
        cam.add_trauma(0.6)
```

### C#

```csharp
using Godot;

public partial class ScreenShakeCamera : Camera2D
{
    [Export] public Vector2 MaxOffset { get; set; } = new Vector2(20f, 15f);
    [Export] public float MaxRoll { get; set; } = 3.0f;
    [Export] public float DecayRate { get; set; } = 1.5f;
    [Export] public bool UseNoise { get; set; } = true;
    [Export] public float NoiseSpeed { get; set; } = 60.0f;

    private float _trauma = 0f;
    private float _noiseTime = 0f;
    private FastNoiseLite _noise;

    public override void _Ready()
    {
        _noise = new FastNoiseLite();
        _noise.NoiseType = FastNoiseLite.NoiseTypeEnum.Simplex;
        _noise.Seed = (int)GD.Randi();
    }

    public void AddTrauma(float amount)
    {
        _trauma = Mathf.Min(_trauma + amount, 1.0f);
    }

    public override void _Process(double delta)
    {
        if (_trauma <= 0f)
        {
            Offset = Vector2.Zero;
            Rotation = 0f;
            return;
        }

        float dt = (float)delta;
        _trauma = Mathf.Max(_trauma - DecayRate * dt, 0f);
        _noiseTime += dt * NoiseSpeed;

        float shake = _trauma * _trauma;

        if (UseNoise)
        {
            Offset = new Vector2(
                MaxOffset.X * shake * _noise.GetNoise2D(_noiseTime, 0f),
                MaxOffset.Y * shake * _noise.GetNoise2D(0f, _noiseTime)
            );
            Rotation = Mathf.DegToRad(MaxRoll) * shake * _noise.GetNoise2D(_noiseTime, _noiseTime);
        }
        else
        {
            Offset = new Vector2(
                MaxOffset.X * shake * (float)GD.RandRange(-1.0, 1.0),
                MaxOffset.Y * shake * (float)GD.RandRange(-1.0, 1.0)
            );
            Rotation = Mathf.DegToRad(MaxRoll) * shake * (float)GD.RandRange(-1.0, 1.0);
        }
    }
}
```

---

## 4. Camera Zones / Rooms

For Metroidvania or Zelda-style games, `Area2D` regions define camera bounds per room. When the player enters a zone, the camera limits tween smoothly to the new room boundaries.

### GDScript

**CameraZone node** — place one per room, sized to fit the room:

```gdscript
## CameraZone.gd — attach to an Area2D
## Set collision layer so only the player can trigger it.
extends Area2D

## Room bounds in world pixels (set via CollisionShape2D or exported values)
@export var limit_left: int = 0
@export var limit_right: int = 320
@export var limit_top: int = 0
@export var limit_bottom: int = 180

## Seconds to tween the camera limits when entering this room
@export var transition_time: float = 0.4

func _ready() -> void:
    body_entered.connect(_on_body_entered)

func _on_body_entered(body: Node2D) -> void:
    # Only react to the player (adjust group name to match your project)
    if not body.is_in_group("player"):
        return

    var cam := body.get_viewport().get_camera_2d()
    if not cam:
        return

    var tween: Tween = create_tween()
    tween.set_parallel(true)
    tween.set_ease(Tween.EASE_IN_OUT)
    tween.set_trans(Tween.TRANS_SINE)

    tween.tween_property(cam, "limit_left",   limit_left,   transition_time)
    tween.tween_property(cam, "limit_right",  limit_right,  transition_time)
    tween.tween_property(cam, "limit_top",    limit_top,    transition_time)
    tween.tween_property(cam, "limit_bottom", limit_bottom, transition_time)
```

### C#

```csharp
// CameraZone.cs — attach to an Area2D
using Godot;

public partial class CameraZone : Area2D
{
    [Export] public int LimitLeft   { get; set; } = 0;
    [Export] public int LimitRight  { get; set; } = 320;
    [Export] public int LimitTop    { get; set; } = 0;
    [Export] public int LimitBottom { get; set; } = 180;
    [Export] public float TransitionTime { get; set; } = 0.4f;

    public override void _Ready()
    {
        BodyEntered += OnBodyEntered;
    }

    private void OnBodyEntered(Node2D body)
    {
        if (!body.IsInGroup("player")) return;
        var cam = body.GetViewport().GetCamera2D();
        if (cam == null) return;

        var tween = CreateTween();
        tween.SetParallel(true);
        tween.SetEase(Tween.EaseType.InOut);
        tween.SetTrans(Tween.TransitionType.Sine);

        tween.TweenProperty(cam, "limit_left",   LimitLeft,   TransitionTime);
        tween.TweenProperty(cam, "limit_right",  LimitRight,  TransitionTime);
        tween.TweenProperty(cam, "limit_top",    LimitTop,    TransitionTime);
        tween.TweenProperty(cam, "limit_bottom", LimitBottom, TransitionTime);
    }
}
```

**Scene setup:**

```
World
├── TileMapLayer
├── Player (CharacterBody2D) — group: "player"
├── Camera2D          ← child of Player or a separate autosnapped node
└── RoomZones
    ├── RoomA (Area2D + CameraZone + CollisionShape2D)
    ├── RoomB (Area2D + CameraZone + CollisionShape2D)
    └── RoomC (Area2D + CameraZone + CollisionShape2D)
```

**Tip:** Size each `CollisionShape2D` to the visible room rectangle. For pixel-art games, align shapes to tile boundaries so there is no overlap between adjacent rooms. If rooms share a wall, a thin 1-pixel gap between shapes avoids double-triggers.

---

## 5. Camera3D Patterns

### Third-Person Follow with SpringArm3D

`SpringArm3D` automatically shortens the arm when something is between the camera and the player, preventing the camera from clipping through walls.

```gdscript
## ThirdPersonCamera.gd — attach to the SpringArm3D node
## Scene: Player (CharacterBody3D) > CameraPivot (Node3D) > SpringArm3D > Camera3D
extends SpringArm3D

@export var target: Node3D          # The player body
@export var follow_speed: float = 10.0
@export var mouse_sensitivity: float = 0.003

# Pitch limits (radians)
@export var min_pitch: float = -0.6
@export var max_pitch: float = 1.0

var _yaw: float = 0.0
var _pitch: float = 0.0

func _ready() -> void:
    Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
    top_level = true  # Detach from player hierarchy so we control position manually

func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
        _yaw   -= event.relative.x * mouse_sensitivity
        _pitch  = clamp(_pitch - event.relative.y * mouse_sensitivity, min_pitch, max_pitch)

func _process(delta: float) -> void:
    if not target:
        return
    # Follow target position
    global_position = global_position.lerp(target.global_position, follow_speed * delta)
    # Apply accumulated mouse rotation
    rotation = Vector3(_pitch, _yaw, 0.0)
```

**Minimum scene tree:**

```
Player (CharacterBody3D)
└── (no camera here — SpringArm is top_level and follows via code)

SpringArm3D  (CameraPivot, top_level = true via code)
└── Camera3D
```

### Orbit Camera (Mouse Drag)

```gdscript
extends Camera3D

@export var target: Node3D
@export var orbit_distance: float = 5.0
@export var orbit_speed: float = 0.005
@export var zoom_speed: float = 0.5
@export var min_distance: float = 1.0
@export var max_distance: float = 20.0

var _yaw: float = 0.0
var _pitch: float = 0.3  # slight downward angle by default

func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
        _yaw   -= event.relative.x * orbit_speed
        _pitch  = clamp(_pitch - event.relative.y * orbit_speed, -1.4, 1.4)

    if event is InputEventMouseButton:
        if event.button_index == MOUSE_BUTTON_WHEEL_UP:
            orbit_distance = maxf(orbit_distance - zoom_speed, min_distance)
        elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
            orbit_distance = minf(orbit_distance + zoom_speed, max_distance)

func _process(_delta: float) -> void:
    if not target:
        return
    # Spherical coordinates → Cartesian offset
    var offset := Vector3(
        orbit_distance * cos(_pitch) * sin(_yaw),
        orbit_distance * sin(_pitch),
        orbit_distance * cos(_pitch) * cos(_yaw)
    )
    global_position = target.global_position + offset
    look_at(target.global_position)
```

### First-Person Camera

First-person camera setup is covered in the **player-controller** skill (section 4). The key points: attach `Camera3D` as a child of a `Head` node on the `CharacterBody3D`, rotate the body for yaw, rotate the head for pitch, and clamp pitch to `±PI/2`.

---

## 6. Camera Transitions

To cut or blend between two cameras (e.g. entering a cutscene, switching player perspective), tween the active camera's position and zoom/FOV toward the second camera's values, then make the switch.

### GDScript

```gdscript
## CameraTransitionManager.gd — Autoload or attach to a scene manager node
extends Node

## Transition the active Camera2D to match the position and zoom of `next_cam`
## over `duration` seconds, then make `next_cam` the active camera.
func transition_2d(next_cam: Camera2D, duration: float = 0.5) -> void:
    var viewport := get_viewport()
    var current_cam := viewport.get_camera_2d()
    if not current_cam or current_cam == next_cam:
        return

    # Temporarily make the current camera a top-level node so it doesn't follow its parent
    current_cam.top_level = true

    var tween: Tween = create_tween()
    tween.set_parallel(true)
    tween.set_ease(Tween.EASE_IN_OUT)
    tween.set_trans(Tween.TRANS_CUBIC)

    tween.tween_property(current_cam, "global_position", next_cam.global_position, duration)
    tween.tween_property(current_cam, "zoom", next_cam.zoom, duration)

    await tween.finished

    # Hand off — make the destination camera active and restore state
    next_cam.make_current()
    current_cam.top_level = false

## Transition between two Camera3D nodes (blends position and FOV)
func transition_3d(next_cam: Camera3D, duration: float = 0.5) -> void:
    var current_cam := get_viewport().get_camera_3d()
    if not current_cam or current_cam == next_cam:
        return

    current_cam.top_level = true

    var tween: Tween = create_tween()
    tween.set_parallel(true)
    tween.set_ease(Tween.EASE_IN_OUT)
    tween.set_trans(Tween.TRANS_CUBIC)

    tween.tween_property(current_cam, "global_position", next_cam.global_position, duration)
    tween.tween_property(current_cam, "global_rotation", next_cam.global_rotation, duration)
    tween.tween_property(current_cam, "fov", next_cam.fov, duration)

    await tween.finished

    next_cam.make_current()
    current_cam.top_level = false
```

**Usage:**

```gdscript
# From anywhere that can reach the manager
CameraTransitionManager.transition_2d($CutsceneCam, 0.6)
```

---

## 7. Split Screen (Local Multiplayer)

Each player gets their own `SubViewport` with a dedicated `Camera2D`/`Camera3D`. A `SubViewportContainer` renders the viewport into the 2D canvas.

### Scene Tree

```
HBoxContainer  (fills the screen — add two children for vertical split)
├── SubViewportContainer  (player 1 side — stretch_shrink = 1)
│   └── SubViewport
│       ├── Player1  (CharacterBody2D)
│       └── Camera2D  (child of Player1)
└── SubViewportContainer  (player 2 side)
    └── SubViewport
        ├── Player2  (CharacterBody2D)
        └── Camera2D  (child of Player2)
```

### GDScript

```gdscript
## SplitScreenSetup.gd — attach to the root node of your split-screen scene
extends Node

@export var player_scene: PackedScene

func _ready() -> void:
    _setup_viewport($HBoxContainer/P1Container/P1Viewport, Vector2i(0, 0))
    _setup_viewport($HBoxContainer/P2Container/P2Viewport, Vector2i(1, 0))

func _setup_viewport(viewport: SubViewport, player_index: Vector2i) -> void:
    # Match viewport size to half the window
    var half_size := Vector2i(
        DisplayServer.window_get_size().x / 2,
        DisplayServer.window_get_size().y
    )
    viewport.size = half_size

    var player: Node = player_scene.instantiate()
    viewport.add_child(player)

    # Each player uses a separate input device (gamepad index via player_index.x)
    # Wire up device index through an exported property on your player script
    if player.has_method("set_device"):
        player.set_device(player_index.x)
```

**Key settings for each `SubViewport`:**

| Property | Value | Reason |
|---|---|---|
| `own_world_3d` | `true` (3D only) | Separate physics world per viewport |
| `audio_listener_enable_2d/3d` | `true` on primary | Only one viewport drives audio |
| `transparent_bg` | `false` | Avoid alpha blending overhead |
| `handle_input_locally` | `false` | Let the root scene handle input routing |

---

## 8. Implementation Checklist

- [ ] `Camera2D` limits match level/tilemap bounds so no out-of-world edges are visible
- [ ] Smooth follow uses `_process` (visual interpolation), not `_physics_process`
- [ ] Screen shake resets `offset` and `rotation` to zero when `_trauma` reaches `0.0`
- [ ] `add_trauma()` clamps to `1.0`; it does not exceed maximum shake
- [ ] Camera zone `Area2D` collision layers are set so only the player triggers them
- [ ] `SpringArm3D` collision mask includes all environment layers for wall avoidance
- [ ] Camera transition awaits tween completion before calling `make_current()`
- [ ] Split screen `SubViewport` sizes are updated on window resize (`get_tree().root.size_changed` signal)
- [ ] Only one `SubViewport` has `audio_listener_enable_2d` or `audio_listener_enable_3d` set to `true`
