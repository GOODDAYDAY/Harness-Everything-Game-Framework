---
name: xr-development
description: Use when building VR/AR/XR applications — OpenXR setup, XROrigin3D, hand tracking, controllers, passthrough, and Meta Quest deployment in Godot 4.3+
---

# XR Development in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, then C#.

> **Related skills:** **3d-essentials** for 3D rendering and environment, **physics-system** for 3D physics interactions, **input-handling** for non-XR input patterns, **export-pipeline** for platform exports.

---

## 1. XR Setup

### Enabling OpenXR

1. **Project Settings → Plugins → Enable:** `OpenXR` (or `OpenXR Plugin` depending on version)
2. **Project Settings → XR → OpenXR → Enabled** → `true`
3. **Project Settings → XR → Shaders → Enabled** → `true` (for XR shader support)
4. **Rendering:**
   - Use **Forward+** or **Mobile** renderer (Compatibility also works for simpler scenes)
   - Set **Project Settings → Display → Window → VSync Mode** to `Disabled` (the XR runtime controls frame timing)

### Core Scene Structure

```
Main (Node3D)
├── XROrigin3D                    ← Player's physical space origin
│   ├── XRCamera3D                ← Head-mounted display
│   ├── XRController3D (left)     ← Left controller
│   │   └── LeftHandModel (MeshInstance3D or hand tracking)
│   ├── XRController3D (right)    ← Right controller
│   │   └── RightHandModel
│   └── (XRBodyTracker via XRServer — optional full body tracking)
├── WorldEnvironment
└── GameWorld (Node3D)
    └── ... level geometry
```

### Starting XR Session

```gdscript
extends Node3D

func _ready() -> void:
    var xr_interface: XRInterface = XRServer.find_interface("OpenXR")
    if xr_interface and xr_interface.is_initialized():
        get_viewport().use_xr = true
    else:
        push_error("OpenXR not available")
```

```csharp
public partial class XRMain : Node3D
{
    public override void _Ready()
    {
        var xrInterface = XRServer.FindInterface("OpenXR");
        if (xrInterface != null && xrInterface.IsInitialized())
            GetViewport().UseXr = true;
        else
            GD.PushError("OpenXR not available");
    }
}
```

---

## 2. Controllers and Input

### XRController3D

`XRController3D` automatically tracks the physical controller's position and rotation.

```gdscript
extends XRController3D

func _ready() -> void:
    button_pressed.connect(_on_button_pressed)
    button_released.connect(_on_button_released)
    input_float_changed.connect(_on_float_changed)

func _on_button_pressed(button_name: String) -> void:
    match button_name:
        "trigger_click":
            shoot()
        "grip_click":
            grab()
        "ax_button":  # A or X depending on hand
            jump()
        "by_button":  # B or Y depending on hand
            open_menu()

func _on_button_released(button_name: String) -> void:
    if button_name == "grip_click":
        release()

func _on_float_changed(float_name: String, value: float) -> void:
    if float_name == "trigger":
        # Analog trigger value 0.0–1.0
        update_trigger_visual(value)
```

```csharp
public partial class XRControllerHandler : XRController3D
{
    public override void _Ready()
    {
        ButtonPressed += OnButtonPressed;
        ButtonReleased += OnButtonReleased;
        InputFloatChanged += OnFloatChanged;
    }

    private void OnButtonPressed(string buttonName)
    {
        switch (buttonName)
        {
            case "trigger_click": Shoot(); break;
            case "grip_click": Grab(); break;
            case "ax_button": Jump(); break;
        }
    }

    private void OnButtonReleased(string buttonName)
    {
        if (buttonName == "grip_click") Release();
    }

    private void OnFloatChanged(string floatName, double value)
    {
        if (floatName == "trigger") UpdateTriggerVisual((float)value);
    }
}
```

### Common Controller Buttons (OpenXR)

| Signal Name | Physical Button |
|-------------|----------------|
| `trigger_click` | Index finger trigger (digital) |
| `trigger` | Index finger trigger (analog float) |
| `grip_click` | Side grip |
| `grip` | Side grip (analog float) |
| `ax_button` | A (right) or X (left) |
| `by_button` | B (right) or Y (left) |
| `primary` | Thumbstick click |
| `primary_x/y` | Thumbstick axes (-1 to 1) |

### Thumbstick Locomotion

```gdscript
extends XROrigin3D

@export var move_speed: float = 2.0
@export var turn_speed: float = 2.0
@export var snap_turn_degrees: float = 30.0

@onready var left_controller: XRController3D = $LeftController
@onready var camera: XRCamera3D = $XRCamera3D

func _physics_process(delta: float) -> void:
    # Smooth locomotion from left thumbstick
    var input := Vector2(
        left_controller.get_float("primary_x"),
        left_controller.get_float("primary_y")
    )

    if input.length() > 0.1:
        # Move in camera's forward direction (ignore vertical)
        var forward := -camera.global_basis.z
        forward.y = 0.0
        forward = forward.normalized()
        var right := camera.global_basis.x
        right.y = 0.0
        right = right.normalized()

        var movement: Vector3 = (forward * input.y + right * input.x) * move_speed * delta
        global_position += movement
```

---

## 3. Hand Tracking

OpenXR hand tracking provides skeletal hand data without controllers.

```gdscript
extends XROrigin3D

@onready var left_hand: XRController3D = $LeftController
@onready var right_hand: XRController3D = $RightController

func _process(_delta: float) -> void:
    # Check if hand tracking is active (vs controller tracking)
    var xr_interface: XRInterface = XRServer.find_interface("OpenXR")
    if not xr_interface:
        return

    # Hand tracking data is accessed through the XRHandTracker
    var left_tracker: XRHandTracker = XRServer.get_tracker("left_hand") as XRHandTracker
    if left_tracker:
        # Check for pinch gesture
        if left_tracker.get_hand_joint_flags(XRHandTracker.HAND_JOINT_INDEX_TIP) & XRHandTracker.HAND_JOINT_FLAG_POSITION_TRACKED:
            var thumb_tip: Vector3 = left_tracker.get_hand_joint_transform(XRHandTracker.HAND_JOINT_THUMB_TIP).origin
            var index_tip: Vector3 = left_tracker.get_hand_joint_transform(XRHandTracker.HAND_JOINT_INDEX_TIP).origin
            var pinch_distance: float = thumb_tip.distance_to(index_tip)
            if pinch_distance < 0.02:  # 2cm threshold
                _on_pinch_detected()
```

```csharp
public partial class XRHandTrackingOrigin : XROrigin3D
{
    public override void _Process(double delta)
    {
        var xrInterface = XRServer.FindInterface("OpenXR");
        if (xrInterface == null)
            return;

        var leftTracker = XRServer.GetTracker("left_hand") as XRHandTracker;
        if (leftTracker != null)
        {
            var flags = leftTracker.GetHandJointFlags(XRHandTracker.HandJoint.IndexTip);
            if (flags.HasFlag(XRHandTracker.HandJointFlags.PositionTracked))
            {
                Vector3 thumbTip = leftTracker.GetHandJointTransform(XRHandTracker.HandJoint.ThumbTip).Origin;
                Vector3 indexTip = leftTracker.GetHandJointTransform(XRHandTracker.HandJoint.IndexTip).Origin;
                float pinchDistance = thumbTip.DistanceTo(indexTip);
                if (pinchDistance < 0.02f) // 2cm threshold
                    OnPinchDetected();
            }
        }
    }
}
```

> **Note:** Hand tracking availability depends on the XR headset. Meta Quest, Apple Vision Pro, and some SteamVR setups support it. Always fall back to controller input.

---

## 4. Grabbing Objects

### Physics-Based Grabbing

```gdscript
extends XRController3D

var _held_object: RigidBody3D = null
var _grab_joint: Generic6DOFJoint3D = null

@onready var grab_area: Area3D = $GrabArea  # small Area3D at controller position

func _ready() -> void:
    button_pressed.connect(_on_button_pressed)
    button_released.connect(_on_button_released)

func _on_button_pressed(button_name: String) -> void:
    if button_name == "grip_click" and _held_object == null:
        _try_grab()

func _on_button_released(button_name: String) -> void:
    if button_name == "grip_click" and _held_object != null:
        _release()

func _try_grab() -> void:
    var bodies: Array[Node3D] = grab_area.get_overlapping_bodies()
    for body in bodies:
        if body is RigidBody3D:
            _held_object = body
            # Create a joint to attach object to controller
            _grab_joint = Generic6DOFJoint3D.new()
            add_child(_grab_joint)
            _grab_joint.node_a = get_path()
            _grab_joint.node_b = _held_object.get_path()
            break

func _release() -> void:
    if _grab_joint:
        _grab_joint.queue_free()
        _grab_joint = null
    if _held_object:
        # Apply controller velocity to thrown object
        _held_object.linear_velocity = get_pose().linear_velocity
        _held_object.angular_velocity = get_pose().angular_velocity
        _held_object = null
```

```csharp
public partial class XRGrabController : XRController3D
{
    private RigidBody3D _heldObject = null;
    private Generic6DOFJoint3D _grabJoint = null;

    [Export] public Area3D GrabArea { get; set; }

    public override void _Ready()
    {
        ButtonPressed += OnButtonPressed;
        ButtonReleased += OnButtonReleased;
    }

    private void OnButtonPressed(string buttonName)
    {
        if (buttonName == "grip_click" && _heldObject == null)
            TryGrab();
    }

    private void OnButtonReleased(string buttonName)
    {
        if (buttonName == "grip_click" && _heldObject != null)
            Release();
    }

    private void TryGrab()
    {
        foreach (var body in GrabArea.GetOverlappingBodies())
        {
            if (body is RigidBody3D rigidBody)
            {
                _heldObject = rigidBody;
                _grabJoint = new Generic6DOFJoint3D();
                AddChild(_grabJoint);
                _grabJoint.NodeA = GetPath();
                _grabJoint.NodeB = _heldObject.GetPath();
                break;
            }
        }
    }

    private void Release()
    {
        if (_grabJoint != null)
        {
            _grabJoint.QueueFree();
            _grabJoint = null;
        }
        if (_heldObject != null)
        {
            var pose = GetPose();
            _heldObject.LinearVelocity = pose.LinearVelocity;
            _heldObject.AngularVelocity = pose.AngularVelocity;
            _heldObject = null;
        }
    }
}
```

---

## 5. XR UI Interaction

### In-World UI Panels

Standard Godot `Control` nodes don't work directly in 3D XR. Use a `SubViewport` rendered onto a `MeshInstance3D`:

```
UIPanel (StaticBody3D)
├── MeshInstance3D (QuadMesh, material with SubViewport texture)
├── CollisionShape3D (for ray interaction)
└── SubViewport (size = 1024x768)
    └── Control (your UI scene)
```

### Pointer/Ray Interaction

```gdscript
extends XRController3D

@onready var ray: RayCast3D = $RayCast3D  # pointing forward from controller

func _physics_process(_delta: float) -> void:
    if ray.is_colliding():
        var collider: Object = ray.get_collider()
        if collider.has_method("xr_hover"):
            collider.xr_hover(ray.get_collision_point())

        if get_float("trigger") > 0.8:
            if collider.has_method("xr_click"):
                collider.xr_click(ray.get_collision_point())
```

```csharp
public partial class XRPointerController : XRController3D
{
    [Export] public RayCast3D Ray { get; set; }

    public override void _PhysicsProcess(double delta)
    {
        if (Ray.IsColliding())
        {
            var collider = Ray.GetCollider();
            if (collider is GodotObject obj)
            {
                if (obj.HasMethod("xr_hover"))
                    obj.Call("xr_hover", Ray.GetCollisionPoint());

                if (GetFloat("trigger") > 0.8f)
                {
                    if (obj.HasMethod("xr_click"))
                        obj.Call("xr_click", Ray.GetCollisionPoint());
                }
            }
        }
    }
}
```

> **Tip:** Use the community addon [Godot XR Tools](https://github.com/GodotVR/godot-xr-tools) for production-ready interaction systems, locomotion, and UI helpers.

---

## 6. Passthrough (Mixed Reality)

Passthrough blends the real world with virtual content (AR/MR).

```gdscript
func enable_passthrough() -> void:
    var xr_interface: XRInterface = XRServer.find_interface("OpenXR")
    if xr_interface:
        # Request passthrough blend mode
        xr_interface.environment_blend_mode = XRInterface.XR_ENV_BLEND_MODE_ALPHA_BLEND
        # Make the background transparent
        get_viewport().transparent_bg = true
        RenderingServer.set_default_clear_color(Color(0, 0, 0, 0))
```

```csharp
private void EnablePassthrough()
{
    var xrInterface = XRServer.FindInterface("OpenXR");
    if (xrInterface != null)
    {
        // Request passthrough blend mode
        xrInterface.EnvironmentBlendMode = XRInterface.EnvironmentBlendModeEnum.AlphaBlend;
        // Make the background transparent
        GetViewport().TransparentBg = true;
        RenderingServer.SetDefaultClearColor(new Color(0, 0, 0, 0));
    }
}
```

> **Passthrough support:** Meta Quest 3/Pro, Apple Vision Pro, Varjo XR-4. Not all headsets support it.

---

## 7. Meta Quest Export

### Setup

1. Install Android Build Template: **Project → Install Android Build Template**
2. Install OpenXR Vendors plugin: **Project → Project Settings → Plugins → Enable `Godot OpenXR Vendors`** (or install from AssetLib)
3. **Export → Add → Android**
4. In the Android export preset:
   - **XR Features → XR Mode** → `OpenXR`
   - **XR Features → Hand Tracking** → `Optional` or `Required`
   - **XR Features → Passthrough** → `Optional` (if needed)
   - **Architectures → arm64** → enabled (Quest is ARM)
5. Set minimum API level to 29+

### Performance Settings for Quest

| Setting | Recommended Value |
|---------|-------------------|
| Renderer | Mobile |
| MSAA | 2x or 4x (VR needs antialiasing) |
| Texture Compression | ETC2/ASTC |
| Target FPS | 72 (Quest 2) or 90 (Quest 3) |

> **Critical:** VR must maintain consistent frame rate. Dropped frames cause nausea. Profile aggressively and keep draw calls low.

---

## 8. Common Pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| Black screen in headset | `use_xr = true` not set on viewport | Set in `_ready()` after checking XR interface |
| Controller input not firing | Wrong signal name for the platform | Check OpenXR action map bindings in Project Settings |
| Objects scale wrong in VR | Scene not built at real-world scale | Use 1 unit = 1 meter throughout the scene |
| Motion sickness from locomotion | Smooth rotation | Use snap turning (30° increments) or add a vignette during movement |
| UI unreadable in VR | Panel too far away or too small | Place UI at 1–2m distance, use SubViewport at 1024+ resolution |
| Hand tracking jittery | Raw joint data used directly | Apply smoothing (lerp toward new position each frame) |
| Export fails on Quest | Missing Android build template or wrong architecture | Install Android Build Template; enable arm64; set API level 29+ |

---

## 9. Implementation Checklist

- [ ] OpenXR is enabled in Project Settings
- [ ] Scene uses `XROrigin3D` → `XRCamera3D` + `XRController3D` hierarchy
- [ ] XR session is started with `get_viewport().use_xr = true` after interface check
- [ ] World is built at 1 unit = 1 meter scale
- [ ] Controller input uses OpenXR action names (`trigger_click`, `grip_click`, etc.)
- [ ] Fallback exists for hand tracking → controller tracking
- [ ] UI panels use SubViewport rendered on a 3D mesh
- [ ] Locomotion includes comfort options (snap turn, vignette)
- [ ] VSync is disabled (XR runtime handles frame timing)
- [ ] Quest export uses Mobile renderer, arm64 architecture, API level 29+
