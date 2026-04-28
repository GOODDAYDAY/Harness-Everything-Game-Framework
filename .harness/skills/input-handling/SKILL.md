---
name: input-handling
description: Use when implementing input — InputEvent system, Input Map actions, controllers/gamepads, mouse/touch, action rebinding, and input architecture
---

# Input Handling in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, then C#.

> **Related skills:** **player-controller** for movement driven by input, **godot-ui** for UI input focus and navigation, **save-load** for persisting custom key bindings, **responsive-ui** for touch vs desktop input adaptation.

---

## 1. Core Concepts

### Input Flow

```
Hardware Event (key, mouse, gamepad)
    ↓
Engine converts to InputEvent
    ↓
_input()              ← raw input, runs first
    ↓
_shortcut_input()     ← for global shortcuts
    ↓
UI Control nodes      ← buttons, sliders consume events
    ↓
_unhandled_key_input() ← unhandled key-only events
    ↓
_unhandled_input()    ← game input (movement, actions)
```

### Where to Handle Input

| Method                    | Use For                                    | When It Runs     |
|---------------------------|--------------------------------------------|------------------|
| `_input()`                | Camera look, global hotkeys                | First — before everything |
| `_shortcut_input()`       | Global shortcuts (pause, screenshot)       | After `_input`, before UI |
| `_unhandled_key_input()`  | Key-only events that UI didn't consume     | After UI, keys only |
| `_unhandled_input()`      | Gameplay actions (jump, attack, interact)  | Last — after UI consumes |
| `Input.is_action_pressed()` in `_physics_process()` | Continuous movement | N/A — polling, not event-driven |

**Rule of thumb:** Use `_unhandled_input()` for discrete game actions (jump, attack). Use `Input` polling in `_physics_process()` for continuous movement. Use `_input()` only when you need input before UI consumes it (e.g., mouse look).

### InputEvent Hierarchy

```
InputEvent
├── InputEventKey              ← keyboard
├── InputEventMouseButton      ← mouse clicks
├── InputEventMouseMotion      ← mouse movement
├── InputEventJoypadButton     ← gamepad buttons
├── InputEventJoypadMotion     ← gamepad sticks/triggers
├── InputEventScreenTouch      ← touchscreen tap
├── InputEventScreenDrag       ← touchscreen drag
├── InputEventAction           ← synthetic action events
├── InputEventMIDI             ← MIDI devices
└── InputEventGesture          ← pinch, pan gestures
    ├── InputEventMagnifyGesture
    └── InputEventPanGesture
```

---

## 2. Input Map Setup

Define actions in **Project > Project Settings > Input Map** instead of checking raw keycodes. This decouples game logic from specific keys and enables rebinding.

### Default Project Actions

Godot ships with `ui_*` actions: `ui_accept`, `ui_cancel`, `ui_left`, `ui_right`, `ui_up`, `ui_down`, etc. These are used by UI controls for keyboard navigation. You can use them for gameplay but creating custom actions is preferred to avoid conflicts.

### Adding Actions in Code

```gdscript
# Typically done in an autoload _ready(), not every frame
func _ready() -> void:
    if not InputMap.has_action("move_left"):
        InputMap.add_action("move_left")
        var event := InputEventKey.new()
        event.physical_keycode = KEY_A
        InputMap.action_add_event("move_left", event)
```

```csharp
public override void _Ready()
{
    if (!InputMap.HasAction("move_left"))
    {
        InputMap.AddAction("move_left");
        var ev = new InputEventKey();
        ev.PhysicalKeycode = Key.A;
        InputMap.ActionAddEvent("move_left", ev);
    }
}
```

> **Best practice:** Define actions in the editor Input Map. Only add actions in code for dynamically generated bindings or mod support.

### Recommended Action Names

Use descriptive, game-specific names instead of key names:

| Good                | Bad              | Why                                  |
|---------------------|------------------|--------------------------------------|
| `move_left`         | `press_a`        | Decoupled from physical key          |
| `attack`            | `left_click`     | Works for mouse and gamepad          |
| `interact`          | `press_e`        | Rebindable without changing logic    |
| `sprint`            | `hold_shift`     | Input-agnostic                       |
| `pause`             | `press_escape`   | Can map to gamepad Start button too  |

---

## 3. Reading Input — Events vs Polling

### Event-Driven (Discrete Actions)

Use `_unhandled_input()` for one-shot actions: jump, attack, interact, pause.

#### GDScript

```gdscript
func _unhandled_input(event: InputEvent) -> void:
    if event.is_action_pressed("jump"):
        _jump()
        get_viewport().set_input_as_handled()  # prevent further propagation

    if event.is_action_pressed("interact"):
        _interact()

    if event.is_action_pressed("pause"):
        get_tree().paused = not get_tree().paused
        get_viewport().set_input_as_handled()
```

#### C#

```csharp
public override void _UnhandledInput(InputEvent @event)
{
    if (@event.IsActionPressed("jump"))
    {
        Jump();
        GetViewport().SetInputAsHandled();
    }

    if (@event.IsActionPressed("interact"))
        Interact();

    if (@event.IsActionPressed("pause"))
    {
        GetTree().Paused = !GetTree().Paused;
        GetViewport().SetInputAsHandled();
    }
}
```

### Polling (Continuous Input)

Use `Input` singleton in `_physics_process()` for held buttons and analog axes.

#### GDScript

```gdscript
func _physics_process(delta: float) -> void:
    # Movement vector from 4 directional actions
    var direction := Input.get_vector("move_left", "move_right", "move_up", "move_down")
    velocity = direction * speed

    # Check if a button is held
    if Input.is_action_pressed("sprint"):
        velocity *= 1.5

    move_and_slide()
```

#### C#

```csharp
public override void _PhysicsProcess(double delta)
{
    Vector2 direction = Input.GetVector("move_left", "move_right", "move_up", "move_down");
    Velocity = direction * Speed;

    if (Input.IsActionPressed("sprint"))
        Velocity *= 1.5f;

    MoveAndSlide();
}
```

### Key Input Methods

| Method                            | Returns | Use For                              |
|-----------------------------------|---------|--------------------------------------|
| `Input.is_action_pressed()`       | `bool`  | Held buttons (sprint, crouch, fire)  |
| `Input.is_action_just_pressed()`  | `bool`  | One-shot triggers (jump, interact)   |
| `Input.is_action_just_released()` | `bool`  | Release triggers (variable jump cut) |
| `Input.get_action_strength()`     | `float` | Analog pressure (0.0–1.0)           |
| `Input.get_axis()`                | `float` | Single axis (-1.0 to 1.0)           |
| `Input.get_vector()`              | `Vector2` | 2D direction, normalized          |
| `event.is_action_pressed()`       | `bool`  | Check in `_unhandled_input` callback |
| `event.is_action_released()`      | `bool`  | Check in `_unhandled_input` callback |

> **`Input.is_action_just_pressed()` in `_physics_process()` can miss inputs** if the physics framerate is lower than the render framerate. For reliability, catch one-shot actions in `_unhandled_input()` and set a flag, or use the input buffering pattern below.

### Input Buffering

Buffer discrete actions so they aren't lost between physics frames.

```gdscript
var _jump_buffered: bool = false
var _jump_buffer_timer: float = 0.0
const JUMP_BUFFER_TIME: float = 0.1

func _unhandled_input(event: InputEvent) -> void:
    if event.is_action_pressed("jump"):
        _jump_buffered = true
        _jump_buffer_timer = JUMP_BUFFER_TIME

func _physics_process(delta: float) -> void:
    if _jump_buffered:
        _jump_buffer_timer -= delta
        if _jump_buffer_timer <= 0.0:
            _jump_buffered = false

    if _jump_buffered and is_on_floor():
        velocity.y = JUMP_VELOCITY
        _jump_buffered = false
```

```csharp
private bool _jumpBuffered;
private float _jumpBufferTimer;
private const float JumpBufferTime = 0.1f;

public override void _UnhandledInput(InputEvent @event)
{
    if (@event.IsActionPressed("jump"))
    {
        _jumpBuffered = true;
        _jumpBufferTimer = JumpBufferTime;
    }
}

public override void _PhysicsProcess(double delta)
{
    if (_jumpBuffered)
    {
        _jumpBufferTimer -= (float)delta;
        if (_jumpBufferTimer <= 0f)
            _jumpBuffered = false;
    }

    if (_jumpBuffered && IsOnFloor())
    {
        Vector2 vel = Velocity;
        vel.Y = JumpVelocity;
        Velocity = vel;
        _jumpBuffered = false;
    }
}
```

---

## 4. Mouse Input

### Mouse Motion (Camera Look)

Use `_input()` or `_unhandled_input()` depending on whether UI should block the look.

#### GDScript

```gdscript
@export var mouse_sensitivity: float = 0.002

func _ready() -> void:
    Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _input(event: InputEvent) -> void:
    if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
        # Horizontal look (yaw)
        rotate_y(-event.relative.x * mouse_sensitivity)
        # Vertical look (pitch) on a child Head node
        $Head.rotate_x(-event.relative.y * mouse_sensitivity)
        $Head.rotation.x = clamp($Head.rotation.x, -PI / 2.0, PI / 2.0)
```

#### C#

```csharp
[Export] public float MouseSensitivity { get; set; } = 0.002f;

public override void _Ready()
{
    Input.MouseMode = Input.MouseModeEnum.Captured;
}

public override void _Input(InputEvent @event)
{
    if (@event is InputEventMouseMotion motion
        && Input.MouseMode == Input.MouseModeEnum.Captured)
    {
        RotateY(-motion.Relative.X * MouseSensitivity);
        var head = GetNode<Node3D>("Head");
        head.RotateX(-motion.Relative.Y * MouseSensitivity);
        Vector3 rot = head.Rotation;
        rot.X = Mathf.Clamp(rot.X, -Mathf.Pi / 2f, Mathf.Pi / 2f);
        head.Rotation = rot;
    }
}
```

### Mouse Modes

| Mode                         | Cursor Visible | Confined | Use For                    |
|------------------------------|----------------|----------|----------------------------|
| `MOUSE_MODE_VISIBLE`         | Yes            | No       | Menus, strategy games      |
| `MOUSE_MODE_HIDDEN`          | No             | No       | Custom cursor via Sprite2D |
| `MOUSE_MODE_CAPTURED`        | No             | Yes      | FPS camera look            |
| `MOUSE_MODE_CONFINED`        | Yes            | Yes      | RTS, keep cursor in window |
| `MOUSE_MODE_CONFINED_HIDDEN` | No             | Yes      | Hidden + confined          |

```gdscript
# Toggle mouse capture (common pattern for FPS games)
func _unhandled_input(event: InputEvent) -> void:
    if event.is_action_pressed("ui_cancel"):
        if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
            Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
        else:
            Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
```

```csharp
public override void _UnhandledInput(InputEvent @event)
{
    if (@event.IsActionPressed("ui_cancel"))
    {
        Input.MouseMode = Input.MouseMode == Input.MouseModeEnum.Captured
            ? Input.MouseModeEnum.Visible
            : Input.MouseModeEnum.Captured;
    }
}
```

### Mouse Button Events

```gdscript
func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventMouseButton:
        match event.button_index:
            MOUSE_BUTTON_LEFT:
                if event.pressed:
                    _attack()
            MOUSE_BUTTON_RIGHT:
                if event.pressed:
                    _aim_start()
                else:
                    _aim_end()
            MOUSE_BUTTON_WHEEL_UP:
                _next_weapon()
            MOUSE_BUTTON_WHEEL_DOWN:
                _prev_weapon()
```

```csharp
public override void _UnhandledInput(InputEvent @event)
{
    if (@event is InputEventMouseButton mouse)
    {
        switch (mouse.ButtonIndex)
        {
            case MouseButton.Left when mouse.Pressed:
                Attack();
                break;
            case MouseButton.Right:
                if (mouse.Pressed) AimStart(); else AimEnd();
                break;
            case MouseButton.WheelUp:
                NextWeapon();
                break;
            case MouseButton.WheelDown:
                PrevWeapon();
                break;
        }
    }
}
```

### Custom Mouse Cursor

```gdscript
# Set in code
func _ready() -> void:
    var cursor := load("res://assets/ui/crosshair.png")
    Input.set_custom_mouse_cursor(cursor, Input.CURSOR_ARROW, Vector2(16, 16))  # hotspot at center

# Or set in Project Settings:
# Display > Mouse Cursor > Custom Image
# Display > Mouse Cursor > Custom Image Hotspot
```

```csharp
public override void _Ready()
{
    var cursor = GD.Load<Resource>("res://assets/ui/crosshair.png");
    Input.SetCustomMouseCursor(cursor, Input.CursorShape.Arrow, new Vector2(16, 16));
}
```

---

## 5. Controller / Gamepad Support

### Detecting Controllers

```gdscript
func _ready() -> void:
    Input.joy_connection_changed.connect(_on_joy_connection_changed)

func _on_joy_connection_changed(device: int, connected: bool) -> void:
    if connected:
        var name := Input.get_joy_name(device)
        print("Controller connected: %s (device %d)" % [name, device])
    else:
        print("Controller disconnected: device %d" % device)
```

```csharp
public override void _Ready()
{
    Input.JoyConnectionChanged += OnJoyConnectionChanged;
}

private void OnJoyConnectionChanged(long device, bool connected)
{
    if (connected)
        GD.Print($"Controller connected: {Input.GetJoyName((int)device)} (device {device})");
    else
        GD.Print($"Controller disconnected: device {device}");
}
```

### Gamepad Input via Input Map

The best approach: add gamepad events alongside keyboard events to the same Input Map actions. Both inputs trigger the same action — no code changes needed.

In **Project > Project Settings > Input Map**, add to your `move_left` action:
- Key: A
- Joypad Axis: Left Stick Left (Axis 0, negative)

Then `Input.get_vector()` works for both keyboard and gamepad automatically.

### Analog Stick with Deadzone

```gdscript
# Input Map handles deadzones per-action (set in Project Settings)
# For manual deadzone control:
func get_stick_input(deadzone: float = 0.2) -> Vector2:
    var raw := Vector2(
        Input.get_joy_axis(0, JOY_AXIS_LEFT_X),
        Input.get_joy_axis(0, JOY_AXIS_LEFT_Y)
    )
    # Radial deadzone (better than per-axis)
    if raw.length() < deadzone:
        return Vector2.ZERO
    return raw.normalized() * inverse_lerp(deadzone, 1.0, raw.length())
```

```csharp
public Vector2 GetStickInput(float deadzone = 0.2f)
{
    var raw = new Vector2(
        Input.GetJoyAxis(0, JoyAxis.LeftX),
        Input.GetJoyAxis(0, JoyAxis.LeftY)
    );
    if (raw.Length() < deadzone)
        return Vector2.Zero;
    return raw.Normalized() * Mathf.InverseLerp(deadzone, 1.0f, raw.Length());
}
```

> **Prefer Input Map deadzones** over manual deadzone code. The Input Map deadzone is set per-action and works automatically with `Input.get_vector()` / `Input.get_axis()`.

### Gamepad Vibration

```gdscript
# weak motor = low frequency rumble, strong motor = high frequency rumble
# Duration in seconds; 0 = until stopped
Input.start_joy_vibration(0, 0.5, 0.3, 0.2)  # device 0, weak 0.5, strong 0.3, 0.2s

# Stop vibration
Input.stop_joy_vibration(0)
```

```csharp
Input.StartJoyVibration(0, 0.5f, 0.3f, 0.2f);
Input.StopJoyVibration(0);
```

### Detecting Input Device for UI Prompts

Switch between keyboard and gamepad icons based on what the player last used.

```gdscript
# input_icon_manager.gd — autoload
extends Node

signal input_device_changed(is_gamepad: bool)

var is_using_gamepad: bool = false

func _input(event: InputEvent) -> void:
    var was_gamepad := is_using_gamepad

    if event is InputEventJoypadButton or event is InputEventJoypadMotion:
        is_using_gamepad = true
    elif event is InputEventKey or event is InputEventMouseButton or event is InputEventMouseMotion:
        is_using_gamepad = false

    if was_gamepad != is_using_gamepad:
        input_device_changed.emit(is_using_gamepad)
```

```csharp
using Godot;

public partial class InputIconManager : Node
{
    [Signal]
    public delegate void InputDeviceChangedEventHandler(bool isGamepad);

    public bool IsUsingGamepad { get; private set; }

    public override void _Input(InputEvent @event)
    {
        bool wasGamepad = IsUsingGamepad;

        if (@event is InputEventJoypadButton or InputEventJoypadMotion)
            IsUsingGamepad = true;
        else if (@event is InputEventKey or InputEventMouseButton or InputEventMouseMotion)
            IsUsingGamepad = false;

        if (wasGamepad != IsUsingGamepad)
            EmitSignal(SignalName.InputDeviceChanged, IsUsingGamepad);
    }
}
```

---

## 6. Touch Input

### Basic Touch Events

```gdscript
func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventScreenTouch:
        if event.pressed:
            print("Touch at: ", event.position)
        else:
            print("Touch released")

    if event is InputEventScreenDrag:
        print("Drag delta: ", event.relative)
```

```csharp
public override void _UnhandledInput(InputEvent @event)
{
    if (@event is InputEventScreenTouch touch)
    {
        if (touch.Pressed)
            GD.Print($"Touch at: {touch.Position}");
        else
            GD.Print("Touch released");
    }

    if (@event is InputEventScreenDrag drag)
        GD.Print($"Drag delta: {drag.Relative}");
}
```

### Emulate Touch from Mouse

Enable in **Project > Project Settings > Input Devices > Pointing > Emulate Touch From Mouse**. This lets you test touch input on desktop with mouse clicks.

The reverse (**Emulate Mouse From Touch**) is enabled by default — touchscreen taps generate mouse events so UI controls work on mobile without changes.

---

## 7. Action Rebinding at Runtime

Allow players to change their key bindings in-game.

### GDScript

```gdscript
# rebind_button.gd — attach to a Button in a settings menu
extends Button

@export var action_name: String = "jump"

var _is_listening: bool = false


func _ready() -> void:
    _update_label()


func _pressed() -> void:
    _is_listening = true
    text = "Press a key..."


func _unhandled_input(event: InputEvent) -> void:
    if not _is_listening:
        return

    # Accept keyboard, mouse button, and gamepad button events
    if not (event is InputEventKey or event is InputEventMouseButton or event is InputEventJoypadButton):
        return

    # Ignore modifier-only presses (Shift, Ctrl, Alt alone)
    if event is InputEventKey and event.keycode in [KEY_SHIFT, KEY_CTRL, KEY_ALT, KEY_META]:
        return

    # Replace all existing events for this action
    InputMap.action_erase_events(action_name)
    InputMap.action_add_event(action_name, event)

    _is_listening = false
    _update_label()
    get_viewport().set_input_as_handled()


func _update_label() -> void:
    var events := InputMap.action_get_events(action_name)
    if events.size() > 0:
        text = "%s: %s" % [action_name, events[0].as_text()]
    else:
        text = "%s: (unbound)" % action_name
```

### C#

```csharp
using Godot;

public partial class RebindButton : Button
{
    [Export] public string ActionName { get; set; } = "jump";

    private bool _isListening;

    public override void _Ready()
    {
        UpdateLabel();
        Pressed += OnPressed;
    }

    private void OnPressed()
    {
        _isListening = true;
        Text = "Press a key...";
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        if (!_isListening)
            return;

        if (@event is not (InputEventKey or InputEventMouseButton or InputEventJoypadButton))
            return;

        if (@event is InputEventKey keyEvent &&
            keyEvent.Keycode is Key.Shift or Key.Ctrl or Key.Alt or Key.Meta)
            return;

        InputMap.ActionEraseEvents(ActionName);
        InputMap.ActionAddEvent(ActionName, @event);

        _isListening = false;
        UpdateLabel();
        GetViewport().SetInputAsHandled();
    }

    private void UpdateLabel()
    {
        var events = InputMap.ActionGetEvents(ActionName);
        Text = events.Count > 0
            ? $"{ActionName}: {events[0].AsText()}"
            : $"{ActionName}: (unbound)";
    }
}
```

### Saving & Loading Bindings

```gdscript
# Save current bindings to ConfigFile
func save_bindings(config: ConfigFile) -> void:
    for action in InputMap.get_actions():
        # Skip built-in ui_* actions
        if action.begins_with("ui_"):
            continue
        var events := InputMap.action_get_events(action)
        var event_data: Array[Dictionary] = []
        for event in events:
            event_data.append({
                "type": event.get_class(),
                "data": var_to_str(event)
            })
        config.set_value("input", action, event_data)
    config.save("user://input_bindings.cfg")


# Load saved bindings
func load_bindings() -> void:
    var config := ConfigFile.new()
    if config.load("user://input_bindings.cfg") != OK:
        return
    for action in config.get_section_keys("input"):
        if not InputMap.has_action(action):
            continue
        InputMap.action_erase_events(action)
        var event_data: Array = config.get_value("input", action, [])
        for entry in event_data:
            var event: InputEvent = str_to_var(entry["data"])
            if event:
                InputMap.action_add_event(action, event)
```

```csharp
public void SaveBindings()
{
    var config = new ConfigFile();
    foreach (StringName action in InputMap.GetActions())
    {
        if (((string)action).StartsWith("ui_"))
            continue;
        var events = InputMap.ActionGetEvents(action);
        var eventData = new Godot.Collections.Array();
        foreach (var ev in events)
        {
            var dict = new Godot.Collections.Dictionary
            {
                { "type", ev.GetClass() },
                { "data", GD.VarToStr(ev) }
            };
            eventData.Add(dict);
        }
        config.SetValue("input", action, eventData);
    }
    config.Save("user://input_bindings.cfg");
}

public void LoadBindings()
{
    var config = new ConfigFile();
    if (config.Load("user://input_bindings.cfg") != Error.Ok)
        return;
    foreach (string action in config.GetSectionKeys("input"))
    {
        if (!InputMap.HasAction(action))
            continue;
        InputMap.ActionEraseEvents(action);
        var eventData = (Godot.Collections.Array)config.GetValue("input", action, new Godot.Collections.Array());
        foreach (var entry in eventData)
        {
            var dict = (Godot.Collections.Dictionary)entry;
            var ev = GD.StrToVar((string)dict["data"]).As<InputEvent>();
            if (ev != null)
                InputMap.ActionAddEvent(action, ev);
        }
    }
}
```

---

## 8. Consuming and Propagating Input

### Stopping Event Propagation

```gdscript
func _unhandled_input(event: InputEvent) -> void:
    if event.is_action_pressed("interact"):
        _interact()
        # Mark as handled — no other node receives this event
        get_viewport().set_input_as_handled()
```

```csharp
public override void _UnhandledInput(InputEvent @event)
{
    if (@event.IsActionPressed("interact"))
    {
        Interact();
        GetViewport().SetInputAsHandled();
    }
}
```

### Node Processing Order

Input propagates in **reverse scene tree order** (deepest child first, root last). To control which node gets input first:

- Move it deeper in the tree, or
- Use `Node.set_process_input(true/false)` to enable/disable input on specific nodes
- Call `get_viewport().set_input_as_handled()` to stop propagation

### Paused Input

By default, `_unhandled_input()` and `_input()` don't fire when the tree is paused. To receive input during pause (e.g., pause menu):

```gdscript
# On the pause menu node:
func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
```

```csharp
public override void _Ready()
{
    ProcessMode = ProcessModeEnum.Always;
}
```

---

## 9. Common Pitfalls

| Symptom                              | Cause                                           | Fix                                                                |
|--------------------------------------|--------------------------------------------------|--------------------------------------------------------------------|
| Action not recognized               | Action name not defined in Input Map             | Add the action in Project > Project Settings > Input Map           |
| `is_action_just_pressed()` misses input | Called in `_physics_process` at low tick rate  | Catch discrete actions in `_unhandled_input()` instead             |
| Input still fires when UI is open    | Using `_input()` instead of `_unhandled_input()` | Switch to `_unhandled_input()` so UI consumes events first         |
| Mouse look works through menus       | Mouse motion in `_input()` without mode check    | Guard with `if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED`      |
| Gamepad stick drifts                 | Deadzone too low or not set                      | Set deadzone per-action in Input Map (0.2 is a good default)       |
| Controller not detected              | Not connected before game start                  | Connect `joy_connection_changed` signal, handle hot-plug           |
| Key rebinding captures modifier keys | No filter for Shift/Ctrl/Alt alone               | Skip events where keycode is a modifier key                        |
| Touch input doesn't work on desktop  | "Emulate Touch From Mouse" is disabled           | Enable in Project Settings > Input Devices > Pointing              |
| Input fires during pause             | Node `process_mode` is `INHERIT` (pauses with parent) | Set pause menu to `PROCESS_MODE_ALWAYS`                      |
| Action triggers twice per press      | Same action checked in both `_input` and `_unhandled_input` | Pick one callback per action                              |

---

## 10. Implementation Checklist

- [ ] All gameplay actions are defined in the Input Map — no raw keycodes in game logic
- [ ] Discrete actions (jump, attack) use `_unhandled_input()`, not polling in `_physics_process()`
- [ ] Continuous input (movement, sprint) uses `Input.get_vector()` / `Input.is_action_pressed()` in `_physics_process()`
- [ ] Mouse look guards on `Input.mouse_mode == MOUSE_MODE_CAPTURED` to avoid rotating through menus
- [ ] Each Input Map action has both keyboard and gamepad bindings for controller support
- [ ] Gamepad deadzone is set per-action in Input Map (default 0.2)
- [ ] Pause menu node has `process_mode = PROCESS_MODE_ALWAYS` to receive input while paused
- [ ] `get_viewport().set_input_as_handled()` is called after consuming events that shouldn't propagate
- [ ] Input device detection exists if showing keyboard vs gamepad UI prompts
- [ ] Key rebinding saves to and loads from `user://` on game launch
