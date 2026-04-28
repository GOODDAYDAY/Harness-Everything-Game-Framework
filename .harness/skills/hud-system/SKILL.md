---
name: hud-system
description: Use when building in-game HUDs — health bars, score displays, minimap, notifications, and damage numbers
---

# HUD Systems in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, then C#.

> **Related skills:** **godot-ui** for Control node layout and themes, **component-system** for HealthComponent integration, **event-bus** for score/notification signals, **inventory-system** for inventory UI patterns, **2d-essentials** for CanvasLayer setup and draw order.

---

## 1. HUD Architecture

### Why CanvasLayer

A `CanvasLayer` renders its children in a fixed screen-space layer that is completely independent of any `Camera2D` or `Camera3D` transform. Without it, HUD nodes attached to the scene root still move with the camera when you pan or zoom. Wrapping all HUD nodes in a `CanvasLayer` (layer `≥ 1`) ensures the HUD always stays in place regardless of camera movement.

### Scene Tree

```
World (Node2D / Node3D)
├── TileMapLayer          ← game world
├── Player (CharacterBody2D)
│   ├── Camera2D
│   ├── HealthComponent
│   └── HurtboxComponent
├── Enemies
└── HUD (CanvasLayer — layer: 1)
    ├── MarginContainer (anchor: Full Rect — provides edge padding)
    │   ├── TopBar (HBoxContainer)
    │   │   ├── HealthBarPanel (PanelContainer)
    │   │   │   └── HealthBar (TextureProgressBar or ProgressBar)
    │   │   └── ScoreLabel (Label)
    │   └── BottomBar (HBoxContainer)
    │       └── InteractionPrompt (Label — hidden by default)
    ├── DamageNumbersLayer (Node2D — world-space spawning point)
    ├── MinimapContainer (SubViewportContainer)
    │   └── MinimapViewport (SubViewport)
    │       ├── MinimapCamera (Camera2D)
    │       └── MinimapWorld (mirrors or references world nodes)
    └── NotificationStack (VBoxContainer — anchored top-right)
```

**Key rules:**
- Keep all HUD scenes under a single `CanvasLayer`. Do not mix HUD nodes into the game world tree.
- Use `layer = 1` for the main HUD. Use higher values (e.g. `10`) for overlays or pause menus that must appear above the HUD.
- Damage numbers are an exception — they can live in a `Node2D` child of the `CanvasLayer` and use `get_viewport().get_screen_transform()` to convert world positions to screen positions.

---

## 2. Health Bar

### ProgressBar vs TextureProgressBar

| Node | When to use |
|---|---|
| `ProgressBar` | Prototyping, plain-colour bars |
| `TextureProgressBar` | Pixel-art or stylised bars using sprite sheets |

Both expose `min_value`, `max_value`, and `value`. Set `step = 0` so tweening produces a smooth animation rather than snapping to integer steps.

### GDScript

```gdscript
## health_bar.gd — attach to a ProgressBar or TextureProgressBar
class_name HealthBar
extends ProgressBar

## Reference to the HealthComponent this bar tracks.
## Assign in the Inspector or connect programmatically from the HUD root.
@export var health_component: HealthComponent

## Duration (seconds) for the smooth tween on health change.
@export var tween_duration: float = 0.25

var _tween: Tween


func _ready() -> void:
    step = 0.0  # allow fractional values for smooth animation
    if health_component:
        _connect_component(health_component)


## Call this if the HealthComponent is not available at _ready time
## (e.g. the player spawns after the HUD).
func bind(component: HealthComponent) -> void:
    if health_component:
        health_component.health_changed.disconnect(_on_health_changed)
    health_component = component
    _connect_component(component)


func _connect_component(component: HealthComponent) -> void:
    max_value = component.max_health
    value     = component.current_health
    component.health_changed.connect(_on_health_changed)


func _on_health_changed(current: int, maximum: int) -> void:
    max_value = maximum
    _animate_to(current)


func _animate_to(target_value: float) -> void:
    if _tween:
        _tween.kill()
    _tween = create_tween()
    _tween.set_ease(Tween.EASE_OUT)
    _tween.set_trans(Tween.TRANS_QUAD)
    _tween.tween_property(self, "value", target_value, tween_duration)
```

### C#

```csharp
// HealthBar.cs — attach to a ProgressBar or TextureProgressBar
using Godot;

public partial class HealthBar : ProgressBar
{
    [Export] public HealthComponent HealthComponent { get; set; }
    [Export] public float TweenDuration { get; set; } = 0.25f;

    private Tween _tween;

    public override void _Ready()
    {
        Step = 0.0;
        if (HealthComponent != null)
            ConnectComponent(HealthComponent);
    }

    /// <summary>Call this when the HealthComponent is not available at _Ready time.</summary>
    public void Bind(HealthComponent component)
    {
        if (HealthComponent != null)
            HealthComponent.HealthChanged -= OnHealthChanged;
        HealthComponent = component;
        ConnectComponent(component);
    }

    private void ConnectComponent(HealthComponent component)
    {
        MaxValue = component.MaxHealth;
        Value    = component.CurrentHealth;
        component.HealthChanged += OnHealthChanged;
    }

    private void OnHealthChanged(int current, int maximum)
    {
        MaxValue = maximum;
        AnimateTo(current);
    }

    private void AnimateTo(float targetValue)
    {
        _tween?.Kill();
        _tween = CreateTween();
        _tween.SetEase(Tween.EaseType.Out);
        _tween.SetTrans(Tween.TransitionType.Quad);
        _tween.TweenProperty(this, "value", targetValue, TweenDuration);
    }
}
```

**Tip:** If you use `TextureProgressBar`, set `fill_mode` to `FILL_LEFT_TO_RIGHT` and assign your bar texture to `texture_progress`. The `value` / `max_value` ratio drives how much of the texture is revealed.

---

## 3. Score / Label Display

### GDScript

```gdscript
## score_display.gd — attach to a Label
class_name ScoreDisplay
extends Label

## Duration (seconds) to count from old to new score value.
@export var count_duration: float = 0.4

var _displayed_score: int = 0
var _tween: Tween


func _ready() -> void:
    EventBus.score_changed.connect(_on_score_changed)
    text = "0"


func _on_score_changed(new_score: int) -> void:
    _animate_counter(_displayed_score, new_score)


func _animate_counter(from: int, to: int) -> void:
    if _tween:
        _tween.kill()

    _tween = create_tween()
    _tween.set_ease(Tween.EASE_OUT)
    _tween.set_trans(Tween.TRANS_QUAD)
    # Tween an intermediate float; update the label text each step.
    _tween.tween_method(_set_counter_value, float(from), float(to), count_duration)


func _set_counter_value(value: float) -> void:
    _displayed_score = int(value)
    text = str(_displayed_score)
```

### C#

```csharp
// ScoreDisplay.cs — attach to a Label
using Godot;

public partial class ScoreDisplay : Label
{
    [Export] public float CountDuration { get; set; } = 0.4f;

    private int _displayedScore = 0;
    private Tween _tween;

    public override void _Ready()
    {
        EventBus.Instance.ScoreChanged += OnScoreChanged;
        Text = "0";
    }

    private void OnScoreChanged(int newScore)
    {
        AnimateCounter(_displayedScore, newScore);
    }

    private void AnimateCounter(int from, int to)
    {
        _tween?.Kill();
        _tween = CreateTween();
        _tween.SetEase(Tween.EaseType.Out);
        _tween.SetTrans(Tween.TransitionType.Quad);
        _tween.TweenMethod(
            Callable.From<double>(SetCounterValue),
            (double)from,
            (double)to,
            CountDuration
        );
    }

    private void SetCounterValue(double value)
    {
        _displayedScore = (int)value;
        Text = _displayedScore.ToString();
    }
}
```

**EventBus signals needed:**

```gdscript
# autoloads/event_bus.gd
signal score_changed(new_score: int)
```

```csharp
// EventBus.cs (partial — score signal)
[Signal] public delegate void ScoreChangedEventHandler(int newScore);
```

Emit from wherever points are awarded:

```gdscript
# Inside a collectible or enemy death handler
EventBus.score_changed.emit(GameState.score)
```

```csharp
// Inside a collectible or enemy death handler
EventBus.Instance.EmitSignal(EventBus.SignalName.ScoreChanged, GameState.Score);
```

---

## 4. Damage Numbers

Damage numbers are short-lived `Label` nodes that float upward and fade out. Spawn one per damage event; release it after the tween completes. For high-frequency damage (e.g. rapid-fire weapons) a simple manual pool avoids per-hit allocation.

### GDScript — DamageNumber scene (single instance)

```gdscript
## damage_number.gd — attach to a Label; root of a small PackedScene
class_name DamageNumber
extends Label

## Pixels to travel upward during the animation.
@export var rise_distance: float = 40.0

## Duration (seconds) for the full rise-and-fade.
@export var lifetime: float = 0.7

## Optional: tint critical hits differently before spawning.
@export var critical_color: Color = Color(1.0, 0.3, 0.1)
@export var normal_color: Color   = Color(1.0, 1.0, 1.0)


func show_damage(amount: int, is_critical: bool = false) -> void:
    text           = str(amount) if not is_critical else "!" + str(amount)
    modulate.a     = 1.0
    add_theme_font_size_override("font_size", 24 if not is_critical else 32)
    modulate       = critical_color if is_critical else normal_color
    _play_animation()


func _play_animation() -> void:
    var tween := create_tween()
    tween.set_parallel(true)

    # Rise upward
    tween.tween_property(self, "position:y", position.y - rise_distance, lifetime) \
        .set_ease(Tween.EASE_OUT) \
        .set_trans(Tween.TRANS_QUAD)

    # Fade out (start fading at halfway point)
    tween.tween_property(self, "modulate:a", 0.0, lifetime * 0.5) \
        .set_delay(lifetime * 0.5) \
        .set_ease(Tween.EASE_IN)

    tween.finished.connect(queue_free)
```

### C# — DamageNumber scene (single instance)

```csharp
// DamageNumber.cs — attach to a Label; root of a small PackedScene
using Godot;

public partial class DamageNumber : Label
{
    [Export] public float RiseDistance { get; set; } = 40.0f;
    [Export] public float Lifetime { get; set; } = 0.7f;
    [Export] public Color CriticalColor { get; set; } = new(1.0f, 0.3f, 0.1f);
    [Export] public Color NormalColor { get; set; } = new(1.0f, 1.0f, 1.0f);

    public void ShowDamage(int amount, bool isCritical = false)
    {
        Text = isCritical ? $"!{amount}" : amount.ToString();
        Modulate = new Color(Modulate, 1.0f);
        AddThemeFontSizeOverride("font_size", isCritical ? 32 : 24);
        Modulate = isCritical ? CriticalColor : NormalColor;
        PlayAnimation();
    }

    private void PlayAnimation()
    {
        var tween = CreateTween();
        tween.SetParallel(true);

        // Rise upward
        tween.TweenProperty(this, "position:y", Position.Y - RiseDistance, Lifetime)
            .SetEase(Tween.EaseType.Out)
            .SetTrans(Tween.TransitionType.Quad);

        // Fade out (start fading at halfway point)
        tween.TweenProperty(this, "modulate:a", 0.0f, Lifetime * 0.5f)
            .SetDelay(Lifetime * 0.5f)
            .SetEase(Tween.EaseType.In);

        tween.Finished += QueueFree;
    }
}
```

### GDScript — Spawner (attach to the HUD or a DamageNumbersLayer Node2D)

```gdscript
## damage_number_spawner.gd
extends Node

@export var damage_number_scene: PackedScene

## Simple pool: pre-instantiate a fixed number and recycle them.
## For low-frequency damage, omit pooling and just instantiate directly.
const POOL_SIZE := 20
var _pool: Array[DamageNumber] = []
var _pool_index: int = 0


func _ready() -> void:
    for i in POOL_SIZE:
        var dn: DamageNumber = damage_number_scene.instantiate()
        dn.visible = false
        add_child(dn)
        _pool.append(dn)


## Call this from any node that receives damage events.
## `world_position` is the attacker or victim's global position in world space.
func spawn(world_position: Vector2, amount: int, is_critical: bool = false) -> void:
    # Convert world position to screen space so the label sits above the entity
    var screen_pos: Vector2 = get_viewport().get_canvas_transform() * world_position

    # Wraps around — if POOL_SIZE is too small, older labels get recycled mid-animation.
    var dn := _pool[_pool_index % POOL_SIZE]
    _pool_index += 1

    dn.position = screen_pos
    dn.visible  = true
    dn.show_damage(amount, is_critical)
```

### C# — Spawner (attach to the HUD or a DamageNumbersLayer Node2D)

```csharp
// DamageNumberSpawner.cs
using Godot;

public partial class DamageNumberSpawner : Node
{
    [Export] public PackedScene DamageNumberScene { get; set; }

    private const int PoolSize = 20;
    private readonly DamageNumber[] _pool = new DamageNumber[PoolSize];
    private int _poolIndex = 0;

    public override void _Ready()
    {
        for (int i = 0; i < PoolSize; i++)
        {
            var dn = DamageNumberScene.Instantiate<DamageNumber>();
            dn.Visible = false;
            AddChild(dn);
            _pool[i] = dn;
        }
    }

    /// <summary>
    /// Call from any node that receives damage events.
    /// <paramref name="worldPosition"/> is the attacker or victim's global position.
    /// </summary>
    public void Spawn(Vector2 worldPosition, int amount, bool isCritical = false)
    {
        var screenPos = GetViewport().GetCanvasTransform() * worldPosition;

        var dn = _pool[_poolIndex % PoolSize];
        _poolIndex++;

        dn.Position = screenPos;
        dn.Visible = true;
        dn.ShowDamage(amount, isCritical);
    }
}
```

**Connecting to a damage event (GDScript):**

```gdscript
# In the HUD root or the DamageNumberSpawner's _ready:
EventBus.damage_dealt.connect(func(pos: Vector2, amount: int, crit: bool) -> void:
    $DamageNumbersLayer/DamageNumberSpawner.spawn(pos, amount, crit)
)
```

**Connecting to a damage event (C#):**

```csharp
// In the HUD root or the DamageNumberSpawner's _Ready:
EventBus.Instance.DamageDealt += (Vector2 pos, int amount, bool crit) =>
{
    GetNode<DamageNumberSpawner>("DamageNumbersLayer/DamageNumberSpawner")
        .Spawn(pos, amount, crit);
};
```

**Pool notes:** The simple modular pool above recycles labels before they finish animating if POOL_SIZE is too small. Increase the pool size or skip pooling entirely for games with infrequent hits. A more robust pool tracks which instances are free using a `free_list` array.

---

## 5. Notification System

Toast-style notifications appear for a short time then auto-dismiss. A `VBoxContainer` holds all visible toasts; a max-visible cap drops the oldest when the queue overflows.

### GDScript

```gdscript
## notification_stack.gd — attach to a VBoxContainer anchored to top-right corner
class_name NotificationStack
extends VBoxContainer

@export var notification_scene: PackedScene
@export var max_visible: int = 5
@export var auto_dismiss_time: float = 3.0

var _queue: Array[String] = []
var _active: Array[Control] = []


func _ready() -> void:
    # Connect to an EventBus signal, or call push() directly from code.
    EventBus.notification_requested.connect(push)


## Enqueue a new notification message.
func push(message: String) -> void:
    _queue.append(message)
    _flush_queue()


func _flush_queue() -> void:
    while _queue.size() > 0 and _active.size() < max_visible:
        _show_next()


func _show_next() -> void:
    var message: String = _queue.pop_front()
    var toast: Control = notification_scene.instantiate()

    # Expect the toast scene to have a child Label named "MessageLabel"
    toast.get_node("MessageLabel").text = message
    toast.modulate.a = 0.0
    add_child(toast)
    _active.append(toast)

    # Fade in
    var tween: Tween = create_tween()
    tween.tween_property(toast, "modulate:a", 1.0, 0.2)

    # Auto-dismiss timer
    var timer: Timer = Timer.new()
    timer.wait_time = auto_dismiss_time
    timer.one_shot  = true
    toast.add_child(timer)
    timer.timeout.connect(_dismiss.bind(toast))
    timer.start()


func _dismiss(toast: Control) -> void:
    _active.erase(toast)

    var tween: Tween = toast.create_tween()
    tween.tween_property(toast, "modulate:a", 0.0, 0.2)
    tween.finished.connect(func() -> void:
        toast.queue_free()
        _flush_queue()  # Show next queued message if any
    )
```

### C#

```csharp
// NotificationStack.cs — attach to a VBoxContainer
using Godot;
using System.Collections.Generic;

public partial class NotificationStack : VBoxContainer
{
    [Export] public PackedScene NotificationScene { get; set; }
    [Export] public int MaxVisible { get; set; } = 5;
    [Export] public float AutoDismissTime { get; set; } = 3.0f;

    private readonly Queue<string> _queue  = new();
    private readonly List<Control> _active = new();

    public override void _Ready()
    {
        EventBus.Instance.NotificationRequested += Push;
    }

    public void Push(string message)
    {
        _queue.Enqueue(message);
        FlushQueue();
    }

    private void FlushQueue()
    {
        while (_queue.Count > 0 && _active.Count < MaxVisible)
            ShowNext();
    }

    private void ShowNext()
    {
        string message = _queue.Dequeue();
        var toast = NotificationScene.Instantiate<Control>();
        toast.GetNode<Label>("MessageLabel").Text = message;
        toast.Modulate = new Color(1, 1, 1, 0);
        AddChild(toast);
        _active.Add(toast);

        var tween = CreateTween();
        tween.TweenProperty(toast, "modulate:a", 1.0f, 0.2f);

        var timer = new Timer { WaitTime = AutoDismissTime, OneShot = true };
        toast.AddChild(timer);
        timer.Timeout += () => Dismiss(toast);
        timer.Start();
    }

    private void Dismiss(Control toast)
    {
        _active.Remove(toast);

        var tween = toast.CreateTween();
        tween.TweenProperty(toast, "modulate:a", 0.0f, 0.2f);
        tween.Finished += () =>
        {
            toast.QueueFree();
            FlushQueue();
        };
    }
}
```

**Toast scene structure:**

```
ToastNotification (PanelContainer)
└── MarginContainer
    └── MessageLabel (Label)
```

**EventBus signal needed:**

```gdscript
# autoloads/event_bus.gd
signal notification_requested(message: String)
```

```csharp
// EventBus.cs (partial — notification signal)
[Signal] public delegate void NotificationRequestedEventHandler(string message);
```

---

## 6. Minimap Concept

A minimap renders a simplified view of the world using a second `Camera2D` inside a `SubViewport`. The `SubViewportContainer` displays the result as a texture anywhere in the HUD.

### Scene Tree

```
HUD (CanvasLayer)
└── MinimapContainer (SubViewportContainer — custom_minimum_size: 128x128)
    └── MinimapViewport (SubViewport — size: 256x256, disable_3d: true)
        ├── MinimapCamera (Camera2D — zoom: Vector2(0.15, 0.15))
        └── (world nodes are rendered via visibility layers — see below)
```

### How it Works

The `SubViewport` renders a completely separate view of the world. Rather than duplicating nodes, use Godot's **visibility layers** to control what each camera sees:

1. Assign your world `TileMapLayer`, environment, and entities to a **world layer** (e.g. layer 1).
2. Assign minimap-specific indicator sprites (player dot, enemy dots) to a **minimap layer** (e.g. layer 2).
3. Set the main `Camera2D`'s `cull_mask` to show only layer 1.
4. Set the `MinimapCamera`'s `cull_mask` to show layers 1 + 2, or only layer 2 if you want an abstract minimap.

### GDScript — MinimapCamera

```gdscript
## minimap_camera.gd — attach to the Camera2D inside the SubViewport
extends Camera2D

## The target node the minimap camera tracks (usually the player).
@export var follow_target: Node2D

## How tightly the minimap tracks the target (0 = no follow, 1 = instant snap).
@export var follow_speed: float = 10.0


func _process(delta: float) -> void:
    if not follow_target:
        return
    global_position = global_position.lerp(follow_target.global_position, follow_speed * delta)
```

### C# — MinimapCamera

```csharp
// MinimapCamera.cs — attach to the Camera2D inside the SubViewport
using Godot;

public partial class MinimapCamera : Camera2D
{
    /// <summary>The target node the minimap camera tracks (usually the player).</summary>
    [Export] public Node2D FollowTarget { get; set; }

    /// <summary>How tightly the minimap tracks the target (0 = no follow, 1 = instant snap).</summary>
    [Export] public float FollowSpeed { get; set; } = 10.0f;

    public override void _Process(double delta)
    {
        if (FollowTarget == null)
            return;
        GlobalPosition = GlobalPosition.Lerp(FollowTarget.GlobalPosition, FollowSpeed * (float)delta);
    }
}
```

### SubViewport Settings

| Property | Recommended value | Reason |
|---|---|---|
| `size` | `Vector2i(256, 256)` | Internal render resolution; `SubViewportContainer` scales to display size |
| `render_target_update_mode` | `UPDATE_ALWAYS` | Keeps the minimap live every frame |
| `disable_3d` | `true` | Skip 3D rendering overhead for a 2D minimap |
| `canvas_item_default_texture_filter` | `TEXTURE_FILTER_NEAREST` | Preserves pixel art crispness |

### Circular Mask (Optional)

To clip the minimap to a circle, wrap the `SubViewportContainer` in a `TextureRect` using a circular mask texture, or apply a shader to the `SubViewportContainer`:

```gdscript
# Assign a circular mask shader to the SubViewportContainer's material
# Shader (res://shaders/circle_mask.gdshader):
# shader_type canvas_item;
# void fragment() {
#     vec2 uv = UV - 0.5;
#     float dist = length(uv);
#     COLOR = texture(TEXTURE, UV);
#     COLOR.a *= step(dist, 0.5);
# }
```

---

## 7. Interaction Prompts

Show a "Press E to interact" prompt near interactable objects. The prompt can be placed in screen space (always a fixed distance from the actor on screen) or in world space (floats above the object in the game world, moves with camera).

### GDScript — Screen-Space Prompt (recommended for most games)

The prompt lives in the HUD `CanvasLayer`. Its position is updated each frame by converting the interactable's world position to screen coordinates.

```gdscript
## interaction_prompt.gd — attach to a Label or Control inside the HUD CanvasLayer
extends Label

## Pixel offset above the interactable's screen position.
@export var offset: Vector2 = Vector2(0.0, -48.0)

var _target: Node2D = null


func _ready() -> void:
    hide()


## Call this when the player enters an interactable's Area2D.
func show_for(target: Node2D, action_name: String = "interact") -> void:
    _target = target
    var key: String = _get_key_label(action_name)
    text = "Press %s to interact" % key
    show()


## Call this when the player exits the Area2D.
func hide_prompt() -> void:
    _target = null
    hide()


func _process(_delta: float) -> void:
    if not _target or not visible:
        return
    # Convert world position → screen position
    var screen_pos: Vector2 = get_viewport().get_canvas_transform() * _target.global_position
    global_position = screen_pos + offset


func _get_key_label(action_name: String) -> String:
    var events: Array[InputEvent] = InputMap.action_get_events(action_name)
    for event in events:
        if event is InputEventKey:
            return event.as_text_physical_keycode()
        if event is InputEventJoypadButton:
            return event.as_text()
    return "[%s]" % action_name
```

### C# — Screen-Space Prompt

```csharp
// InteractionPrompt.cs — attach to a Label or Control inside the HUD CanvasLayer
using Godot;

public partial class InteractionPrompt : Label
{
    /// <summary>Pixel offset above the interactable's screen position.</summary>
    [Export] public Vector2 Offset { get; set; } = new(0.0f, -48.0f);

    private Node2D _target;

    public override void _Ready()
    {
        Hide();
    }

    /// <summary>Call when the player enters an interactable's Area2D.</summary>
    public void ShowFor(Node2D target, string actionName = "interact")
    {
        _target = target;
        string key = GetKeyLabel(actionName);
        Text = $"Press {key} to interact";
        Show();
    }

    /// <summary>Call when the player exits the Area2D.</summary>
    public void HidePrompt()
    {
        _target = null;
        Hide();
    }

    public override void _Process(double delta)
    {
        if (_target == null || !Visible)
            return;
        var screenPos = GetViewport().GetCanvasTransform() * _target.GlobalPosition;
        GlobalPosition = screenPos + Offset;
    }

    private static string GetKeyLabel(string actionName)
    {
        var events = InputMap.ActionGetEvents(actionName);
        foreach (var ev in events)
        {
            if (ev is InputEventKey key)
                return key.AsTextPhysicalKeycode();
            if (ev is InputEventJoypadButton btn)
                return btn.AsText();
        }
        return $"[{actionName}]";
    }
}
```

### Interactable Area2D (GDScript)

```gdscript
## interactable.gd — attach to an Area2D on the interactable object
extends Area2D

## Group used to find the HUD interaction prompt — set on the Label in the HUD.
const PROMPT_GROUP := "interaction_prompt"


func _ready() -> void:
    body_entered.connect(_on_body_entered)
    body_exited.connect(_on_body_exited)


func _on_body_entered(body: Node2D) -> void:
    if not body.is_in_group("player"):
        return
    _get_prompt().show_for(self)


func _on_body_exited(body: Node2D) -> void:
    if not body.is_in_group("player"):
        return
    _get_prompt().hide_prompt()


func _get_prompt() -> InteractionPrompt:
    return get_tree().get_first_node_in_group(PROMPT_GROUP) as InteractionPrompt
```

### Interactable Area2D (C#)

```csharp
// Interactable.cs — attach to an Area2D on the interactable object
using Godot;

public partial class Interactable : Area2D
{
    private const string PromptGroup = "interaction_prompt";

    public override void _Ready()
    {
        BodyEntered += OnBodyEntered;
        BodyExited += OnBodyExited;
    }

    private void OnBodyEntered(Node2D body)
    {
        if (!body.IsInGroup("player"))
            return;
        GetPrompt()?.ShowFor(this);
    }

    private void OnBodyExited(Node2D body)
    {
        if (!body.IsInGroup("player"))
            return;
        GetPrompt()?.HidePrompt();
    }

    private InteractionPrompt GetPrompt()
    {
        return GetTree().GetFirstNodeInGroup(PromptGroup) as InteractionPrompt;
    }
}
```

**World-space alternative:** Instead of a HUD Label, add a `Label3D` (3D) or a `Label` with `top_level = true` (2D) directly to the interactable scene. This floats above the object in world space and is naturally occluded by camera zoom or rotation. The trade-off is that it requires a `CanvasItem` in the world tree rather than the HUD layer, and does not automatically stay in screen bounds.

---

## 8. Checklist

- [ ] All HUD nodes are children of a `CanvasLayer` with `layer >= 1` so they are unaffected by camera transforms
- [ ] `ProgressBar.step` is set to `0.0` for smooth tween animation rather than integer snapping
- [ ] Health bar binds to `HealthComponent.health_changed` signal — does not poll in `_process`
- [ ] Tween is killed (`_tween.kill()`) before starting a new one so rapid damage does not stack animations
- [ ] Score counter uses `tween_method` to interpolate the displayed integer — not a jump cut
- [ ] Damage number positions are converted from world space to screen space using `get_viewport().get_canvas_transform()`
- [ ] Damage number pool size is large enough that labels are not recycled before their tween completes
- [ ] Notification stack enforces `max_visible` and re-checks the queue after each dismissal
- [ ] Toast auto-dismiss uses a `Timer` node — not `await get_tree().create_timer()`
- [ ] `SubViewport` for minimap has `render_target_update_mode = UPDATE_ALWAYS`
- [ ] Minimap `Camera2D` zoom and cull mask are configured so only the intended layers are visible
- [ ] Interaction prompt converts the interactable's world position each frame — not cached at spawn time
- [ ] `InputMap.action_get_events()` is used to display the correct key for the player's current binding
- [ ] HUD nodes that do not need input set `mouse_filter = MOUSE_FILTER_IGNORE` to avoid blocking game clicks
