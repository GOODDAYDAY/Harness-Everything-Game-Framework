---
name: tween-animation
description: Use when implementing tweens — property animation, method tweening, chaining, parallel sequences, easing, and common UI/gameplay motion recipes
---

# Tweens in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, then C#.

> **Related skills:** **animation-system** for AnimationPlayer/AnimationTree (keyframe-based), **godot-ui** for UI transitions, **shader-basics** for tweening shader parameters, **camera-system** for camera shake and transitions.

---

## 1. Core Concepts

### Tween vs AnimationPlayer

| Feature         | Tween (code-driven)                        | AnimationPlayer (data-driven)              |
|-----------------|--------------------------------------------|--------------------------------------------|
| Setup           | Code only — no editor needed               | Animation panel with keyframes             |
| Best for        | Procedural motion, UI transitions, VFX     | Complex multi-track, artist-driven clips   |
| Reusability     | Recreated per use — lightweight            | Saved as resources, reusable across scenes |
| Blending        | No — one tween per property at a time      | Yes — AnimationTree supports blending      |
| Method calls    | `tween_callback()` at any point            | Call Method tracks at keyframed times      |

**Rule of thumb:** Use Tweens for one-off procedural animations (fade in, bounce, slide). Use AnimationPlayer for repeating, artist-tuned animations (walk cycle, attack sequence).

### Creating a Tween

Tweens are created from any `Node` and auto-bind to it. When the node is freed, the tween stops automatically.

```gdscript
# Creates a tween bound to this node
var tween := create_tween()
tween.tween_property(self, "position", Vector2(400, 300), 1.0)
```

```csharp
var tween = CreateTween();
tween.TweenProperty(this, "position", new Vector2(400, 300), 1.0f);
```

> **Important:** Each call to `create_tween()` creates a new tween. Previous tweens on the same property are **not** automatically killed — they compete. Kill old tweens before creating new ones on the same property if you don't want conflicts.

---

## 2. Tweener Types

### tween_property() — Animate any property

```gdscript
var tween := create_tween()
# Animate position over 0.5 seconds
tween.tween_property($Sprite2D, "position", Vector2(200, 100), 0.5)
# Animate modulate alpha (fade out)
tween.tween_property($Sprite2D, "modulate:a", 0.0, 0.3)
```

```csharp
var tween = CreateTween();
tween.TweenProperty(GetNode("Sprite2D"), "position", new Vector2(200, 100), 0.5);
tween.TweenProperty(GetNode("Sprite2D"), "modulate:a", 0.0f, 0.3);
```

**Sub-property access:** Use `:` to target individual components — `"position:x"`, `"modulate:a"`, `"scale:y"`.

### tween_callback() — Call a method at a point in the sequence

```gdscript
var tween := create_tween()
tween.tween_property(self, "position", Vector2.ZERO, 0.5)
tween.tween_callback(func(): print("Arrived!"))
tween.tween_callback(queue_free)
```

```csharp
var tween = CreateTween();
tween.TweenProperty(this, "position", Vector2.Zero, 0.5f);
tween.TweenCallback(Callable.From(() => GD.Print("Arrived!")));
tween.TweenCallback(Callable.From(QueueFree));
```

### tween_interval() — Wait/delay between steps

```gdscript
var tween := create_tween()
tween.tween_property(self, "modulate:a", 0.0, 0.3)  # fade out
tween.tween_interval(1.0)                             # wait 1 second
tween.tween_property(self, "modulate:a", 1.0, 0.3)  # fade back in
```

```csharp
var tween = CreateTween();
tween.TweenProperty(this, "modulate:a", 0.0f, 0.3);
tween.TweenInterval(1.0f);
tween.TweenProperty(this, "modulate:a", 1.0f, 0.3);
```

### tween_method() — Animate a custom method with interpolated values

```gdscript
# Animate a method that receives interpolated float values
func _ready() -> void:
    var tween := create_tween()
    tween.tween_method(_set_health_bar, 100.0, 0.0, 2.0)

func _set_health_bar(value: float) -> void:
    $HealthBar.value = value
    $HealthLabel.text = "%d%%" % int(value)
```

```csharp
public override void _Ready()
{
    var tween = CreateTween();
    tween.TweenMethod(Callable.From<float>(SetHealthBar), 100.0f, 0.0f, 2.0f);
}

private void SetHealthBar(float value)
{
    GetNode<ProgressBar>("HealthBar").Value = value;
    GetNode<Label>("HealthLabel").Text = $"{(int)value}%";
}
```

---

## 3. Sequencing — Chain vs Parallel

### Sequential (Default)

By default, tweeners run **sequentially** — each waits for the previous to finish.

```gdscript
var tween := create_tween()
tween.tween_property(self, "position:x", 300.0, 0.5)   # Step 1
tween.tween_property(self, "position:y", 200.0, 0.5)   # Step 2 (after Step 1)
tween.tween_property(self, "rotation", PI, 0.3)         # Step 3 (after Step 2)
```

### Parallel — Run tweeners simultaneously

#### Option 1: `set_parallel(true)` — All tweeners run at once

```gdscript
var tween := create_tween().set_parallel(true)
tween.tween_property(self, "position", Vector2(300, 200), 0.5)
tween.tween_property(self, "rotation", PI, 0.5)
tween.tween_property(self, "modulate:a", 0.5, 0.5)
```

```csharp
var tween = CreateTween().SetParallel(true);
tween.TweenProperty(this, "position", new Vector2(300, 200), 0.5f);
tween.TweenProperty(this, "rotation", Mathf.Pi, 0.5f);
tween.TweenProperty(this, "modulate:a", 0.5f, 0.5f);
```

#### Option 2: `chain()` — Switch back to sequential mid-tween

```gdscript
var tween := create_tween().set_parallel(true)
# These two run at the same time
tween.tween_property(self, "position", Vector2(300, 200), 0.5)
tween.tween_property(self, "scale", Vector2(2, 2), 0.5)
# Switch back to sequential for the next step
tween.chain().tween_property(self, "modulate:a", 0.0, 0.3)
tween.tween_callback(queue_free)
```

```csharp
var tween = CreateTween().SetParallel(true);
tween.TweenProperty(this, "position", new Vector2(300, 200), 0.5f);
tween.TweenProperty(this, "scale", new Vector2(2, 2), 0.5f);
tween.Chain().TweenProperty(this, "modulate:a", 0.0f, 0.3f);
tween.TweenCallback(Callable.From(QueueFree));
```

#### Option 3: `parallel()` — Make the next tweener parallel with the previous

```gdscript
var tween := create_tween()
tween.tween_property(self, "position", Vector2(300, 200), 0.5)
# This runs at the same time as position, not after
tween.parallel().tween_property(self, "rotation", PI, 0.5)
# This runs after both finish (back to sequential)
tween.tween_callback(func(): print("done"))
```

---

## 4. Easing & Transitions

### Setting Easing

```gdscript
var tween := create_tween()
# Set defaults for the entire tween
tween.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
tween.tween_property(self, "position", Vector2(400, 300), 0.6)
```

```csharp
var tween = CreateTween();
tween.SetTrans(Tween.TransitionType.Cubic).SetEase(Tween.EaseType.Out);
tween.TweenProperty(this, "position", new Vector2(400, 300), 0.6f);
```

### Per-Tweener Override

```gdscript
var tween := create_tween()
# This tweener uses bounce, overriding the tween default
tween.tween_property(self, "position:y", 0.0, 0.5) \
    .set_trans(Tween.TRANS_BOUNCE).set_ease(Tween.EASE_OUT)
```

```csharp
var tween = CreateTween();
tween.TweenProperty(this, "position:y", 0.0f, 0.5f)
    .SetTrans(Tween.TransitionType.Bounce)
    .SetEase(Tween.EaseType.Out);
```

### Transition Types

| Transition       | Character                              | Common Use                          |
|------------------|----------------------------------------|-------------------------------------|
| `TRANS_LINEAR`   | Constant speed                         | Progress bars, timers               |
| `TRANS_SINE`     | Gentle acceleration                    | Subtle UI animations                |
| `TRANS_QUAD`     | Moderate curve                         | General movement                    |
| `TRANS_CUBIC`    | Smooth curve                           | Most UI transitions                 |
| `TRANS_QUART`    | Strong curve                           | Dramatic entrances                  |
| `TRANS_QUINT`    | Very strong curve                      | Emphasis effects                    |
| `TRANS_EXPO`     | Exponential — sharp start/stop         | Snap-to-position                    |
| `TRANS_CIRC`     | Circular — smooth deceleration         | Natural motion                      |
| `TRANS_BACK`     | Overshoots target slightly             | Bouncy UI buttons                   |
| `TRANS_ELASTIC`  | Spring oscillation                     | Playful/cartoon effects             |
| `TRANS_BOUNCE`   | Bounces at the end                     | Dropping objects, landing           |

### Ease Types

| Ease          | Behavior                                |
|---------------|-----------------------------------------|
| `EASE_IN`     | Slow start, fast end                    |
| `EASE_OUT`    | Fast start, slow end (most natural)     |
| `EASE_IN_OUT` | Slow at both ends                       |
| `EASE_OUT_IN` | Fast at both ends (rarely used)         |

> **Most common combo:** `TRANS_CUBIC` + `EASE_OUT` for natural-feeling UI transitions. `TRANS_BACK` + `EASE_OUT` for playful bounce-in effects.

---

## 5. PropertyTweener Modifiers

### from() — Set custom start value

```gdscript
# Slide in from off-screen (starts at x=-200, animates to current position)
var tween := create_tween()
tween.tween_property($Panel, "position:x", $Panel.position.x, 0.4) \
    .from(-200.0)
```

```csharp
var panel = GetNode<Control>("Panel");
var tween = CreateTween();
tween.TweenProperty(panel, "position:x", panel.Position.X, 0.4f)
    .From(-200.0f);
```

### from_current() — Capture current value as start

```gdscript
# Ensure tween starts from wherever the property is right now
tween.tween_property(self, "position", target_pos, 0.5).from_current()
```

```csharp
tween.TweenProperty(this, "position", targetPos, 0.5f).FromCurrent();
```

### as_relative() — Final value is added to current

```gdscript
# Move 100 pixels right from wherever the node currently is
tween.tween_property(self, "position:x", 100.0, 0.3).as_relative()
```

```csharp
tween.TweenProperty(this, "position:x", 100.0f, 0.3f).AsRelative();
```

### set_delay() — Delay before this tweener starts

```gdscript
var tween := create_tween().set_parallel(true)
tween.tween_property($Label1, "modulate:a", 1.0, 0.3).from(0.0)
tween.tween_property($Label2, "modulate:a", 1.0, 0.3).from(0.0).set_delay(0.1)
tween.tween_property($Label3, "modulate:a", 1.0, 0.3).from(0.0).set_delay(0.2)
# Staggered fade-in: Label1, then Label2, then Label3
```

---

## 6. Looping & Signals

### Looping

```gdscript
# Loop forever (0 = infinite)
var tween := create_tween().set_loops()
tween.tween_property($Icon, "rotation", TAU, 2.0).as_relative()

# Loop 3 times
var tween2 := create_tween().set_loops(3)
tween2.tween_property($Sprite, "modulate:a", 0.3, 0.5)
tween2.tween_property($Sprite, "modulate:a", 1.0, 0.5)
```

```csharp
// Loop forever
var tween = CreateTween().SetLoops();
tween.TweenProperty(GetNode("Icon"), "rotation", Mathf.Tau, 2.0f).AsRelative();

// Loop 3 times
var tween2 = CreateTween().SetLoops(3);
tween2.TweenProperty(GetNode("Sprite"), "modulate:a", 0.3f, 0.5f);
tween2.TweenProperty(GetNode("Sprite"), "modulate:a", 1.0f, 0.5f);
```

### Signals

```gdscript
var tween := create_tween()
tween.tween_property(self, "position", Vector2(300, 200), 0.5)
tween.finished.connect(_on_tween_finished)

func _on_tween_finished() -> void:
    print("Tween complete!")
```

```csharp
var tween = CreateTween();
tween.TweenProperty(this, "position", new Vector2(300, 200), 0.5f);
tween.Finished += OnTweenFinished;

private void OnTweenFinished()
{
    GD.Print("Tween complete!");
}
```

| Signal                       | Fires When                                   |
|------------------------------|----------------------------------------------|
| `finished`                   | All tweeners complete (after final loop)     |
| `loop_finished(loop_count)`  | Each loop iteration completes                |
| `step_finished(idx)`         | Each individual tweener completes            |

---

## 7. Tween Lifecycle

### Killing and Replacing Tweens

```gdscript
var _move_tween: Tween

func move_to(target: Vector2) -> void:
    # Kill the previous tween if still running
    if _move_tween and _move_tween.is_valid():
        _move_tween.kill()

    _move_tween = create_tween()
    _move_tween.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
    _move_tween.tween_property(self, "position", target, 0.4)
```

```csharp
private Tween _moveTween;

public void MoveTo(Vector2 target)
{
    if (_moveTween != null && _moveTween.IsValid())
        _moveTween.Kill();

    _moveTween = CreateTween();
    _moveTween.SetTrans(Tween.TransitionType.Cubic).SetEase(Tween.EaseType.Out);
    _moveTween.TweenProperty(this, "position", target, 0.4f);
}
```

### Pause Mode

```gdscript
# Tween continues during SceneTree pause (for pause menu animations)
var tween := create_tween()
tween.set_pause_mode(Tween.TWEEN_PAUSE_PROCESS)

# Tween pauses when bound node's process_mode stops it (default)
tween.set_pause_mode(Tween.TWEEN_PAUSE_BOUND)
```

### Speed Scale

```gdscript
# Slow motion tween (half speed)
var tween := create_tween()
tween.set_speed_scale(0.5)

# Double speed
tween.set_speed_scale(2.0)
```

### Ignore Time Scale

```gdscript
# Tween runs at normal speed even when Engine.time_scale is changed
var tween := create_tween()
tween.set_ignore_time_scale()
```

---

## 8. Common Recipes

### Fade In / Fade Out

```gdscript
func fade_in(node: CanvasItem, duration: float = 0.3) -> Tween:
    node.modulate.a = 0.0
    var tween := node.create_tween()
    tween.tween_property(node, "modulate:a", 1.0, duration)
    return tween

func fade_out_and_free(node: CanvasItem, duration: float = 0.3) -> void:
    var tween := node.create_tween()
    tween.tween_property(node, "modulate:a", 0.0, duration)
    tween.tween_callback(node.queue_free)
```

```csharp
public Tween FadeIn(CanvasItem node, float duration = 0.3f)
{
    node.Modulate = new Color(node.Modulate, 0.0f);
    var tween = node.CreateTween();
    tween.TweenProperty(node, "modulate:a", 1.0f, duration);
    return tween;
}

public void FadeOutAndFree(CanvasItem node, float duration = 0.3f)
{
    var tween = node.CreateTween();
    tween.TweenProperty(node, "modulate:a", 0.0f, duration);
    tween.TweenCallback(Callable.From(node.QueueFree));
}
```

### UI Panel Slide In / Out

```gdscript
func slide_in(panel: Control) -> void:
    var target_x := panel.position.x
    var tween := create_tween()
    tween.tween_property(panel, "position:x", target_x, 0.4) \
        .from(target_x - 300.0) \
        .set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)

func slide_out(panel: Control) -> void:
    var tween := create_tween()
    tween.tween_property(panel, "position:x", panel.position.x - 300.0, 0.3) \
        .set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
    tween.tween_callback(func(): panel.visible = false)
```

### Button Press Feedback (Scale Bounce)

```gdscript
func bounce_press(button: Control) -> void:
    var tween := button.create_tween()
    tween.tween_property(button, "scale", Vector2(0.9, 0.9), 0.05)
    tween.tween_property(button, "scale", Vector2(1.05, 1.05), 0.1) \
        .set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
    tween.tween_property(button, "scale", Vector2.ONE, 0.1)
```

```csharp
public void BouncePress(Control button)
{
    var tween = button.CreateTween();
    tween.TweenProperty(button, "scale", new Vector2(0.9f, 0.9f), 0.05f);
    tween.TweenProperty(button, "scale", new Vector2(1.05f, 1.05f), 0.1f)
        .SetTrans(Tween.TransitionType.Back).SetEase(Tween.EaseType.Out);
    tween.TweenProperty(button, "scale", Vector2.One, 0.1f);
}
```

### Damage Number Popup

```gdscript
func spawn_damage_number(value: int, pos: Vector2) -> void:
    var label := Label.new()
    label.text = str(value)
    label.position = pos
    label.z_index = 100
    add_child(label)

    var tween := label.create_tween().set_parallel(true)
    tween.tween_property(label, "position:y", pos.y - 50.0, 0.6) \
        .set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
    tween.tween_property(label, "modulate:a", 0.0, 0.4) \
        .set_delay(0.3)
    tween.chain().tween_callback(label.queue_free)
```

```csharp
public void SpawnDamageNumber(int value, Vector2 pos)
{
    var label = new Label();
    label.Text = value.ToString();
    label.Position = pos;
    label.ZIndex = 100;
    AddChild(label);

    var tween = label.CreateTween().SetParallel(true);
    tween.TweenProperty(label, "position:y", pos.Y - 50.0f, 0.6f)
        .SetTrans(Tween.TransitionType.Quad).SetEase(Tween.EaseType.Out);
    tween.TweenProperty(label, "modulate:a", 0.0f, 0.4f)
        .SetDelay(0.3f);
    tween.Chain().TweenCallback(Callable.From(label.QueueFree));
}
```

### Pulsing / Breathing Effect

```gdscript
func start_pulse(node: CanvasItem) -> void:
    var tween := node.create_tween().set_loops()
    tween.tween_property(node, "modulate:a", 0.4, 0.8) \
        .set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
    tween.tween_property(node, "modulate:a", 1.0, 0.8) \
        .set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
```

```csharp
public void StartPulse(CanvasItem node)
{
    var tween = node.CreateTween().SetLoops();
    tween.TweenProperty(node, "modulate:a", 0.4f, 0.8f)
        .SetTrans(Tween.TransitionType.Sine).SetEase(Tween.EaseType.InOut);
    tween.TweenProperty(node, "modulate:a", 1.0f, 0.8f)
        .SetTrans(Tween.TransitionType.Sine).SetEase(Tween.EaseType.InOut);
}
```

### Screen Shake

```gdscript
# On Camera2D
func shake(intensity: float = 8.0, duration: float = 0.3) -> void:
    var tween := create_tween().set_loops(int(duration / 0.04))
    tween.tween_property(self, "offset",
        Vector2(randf_range(-intensity, intensity), randf_range(-intensity, intensity)), 0.02)
    tween.tween_property(self, "offset",
        Vector2(randf_range(-intensity, intensity), randf_range(-intensity, intensity)), 0.02)
    tween.finished.connect(func(): offset = Vector2.ZERO)
```

> **Note:** Tween offsets are fixed at creation time, so each loop shakes to the same positions. For truly random per-frame shake, use `_process()` with a timer instead.

### Shader Parameter Animation

```gdscript
func dissolve(sprite: Sprite2D, duration: float = 1.0) -> void:
    var mat: ShaderMaterial = sprite.material
    var tween := create_tween()
    tween.tween_property(mat, "shader_parameter/dissolve_amount", 1.0, duration)
    tween.tween_callback(sprite.queue_free)
```

```csharp
public void Dissolve(Sprite2D sprite, float duration = 1.0f)
{
    var mat = sprite.Material as ShaderMaterial;
    var tween = CreateTween();
    tween.TweenProperty(mat, "shader_parameter/dissolve_amount", 1.0f, duration);
    tween.TweenCallback(Callable.From(sprite.QueueFree));
}
```

---

## 9. Common Pitfalls

| Symptom                             | Cause                                            | Fix                                                                |
|-------------------------------------|---------------------------------------------------|--------------------------------------------------------------------|
| Tween jumps or jitters              | Multiple tweens competing on the same property    | Kill the old tween before creating a new one                       |
| Tween does nothing                  | Node was freed before tween finished              | Check `is_valid()` or use `tween_callback` instead of `await`      |
| Tween runs during pause             | Default pause mode doesn't match expectation      | Set `set_pause_mode(TWEEN_PAUSE_PROCESS)` for pause-immune tweens  |
| `from()` value ignored              | Called after `set_parallel()` changed ordering    | Call `from()` directly on the PropertyTweener, not on the Tween    |
| Tween doesn't loop smoothly         | End value doesn't match start for seamless loop   | Use `as_relative()` for rotation, or match start/end values        |
| Relative tween drifts over loops    | `as_relative()` accumulates each loop             | Use absolute values for looping; relative for one-shot moves       |
| Callback fires at wrong time        | Callback added to parallel section                | Use `chain()` to switch back to sequential before the callback     |
| Tween property path not found       | Typo or wrong path format                         | Use `"property:component"` — e.g., `"position:x"`, `"modulate:a"` |
| Tween faster/slower than expected   | `Engine.time_scale` affects tween                 | Use `set_ignore_time_scale()` for UI tweens during slow-mo         |

---

## 10. Implementation Checklist

- [ ] Old tweens are killed before creating new ones on the same property
- [ ] Tween references are stored in variables when they need to be killed later
- [ ] Easing is set (`TRANS_CUBIC` + `EASE_OUT` for natural motion, not default `TRANS_LINEAR`)
- [ ] `set_parallel(true)` is used when multiple properties should animate simultaneously
- [ ] `chain()` is used to switch back to sequential after parallel sections
- [ ] `from()` or `from_current()` is used when the start value matters (not just the end value)
- [ ] `as_relative()` is used for incremental movement instead of computing absolute targets
- [ ] Looping tweens use `set_loops()` — not manual recreation
- [ ] Tweens that must run during pause use `set_pause_mode(TWEEN_PAUSE_PROCESS)`
- [ ] `tween_callback(queue_free)` is used at the end of fire-and-forget sequences (damage numbers, particles)
