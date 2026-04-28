---
name: godot-debugging
description: Use when debugging Godot projects — remote debugger, print techniques, signal tracing, common error patterns and fixes
---

# Godot Debugging

This skill covers systematic debugging for Godot 4.3+ projects in both GDScript and C#. It covers print techniques, breakpoints, signal tracing, the built-in profiler, scene tree inspection, common error patterns, and a step-by-step debugging checklist.

> **Related skills:** **godot-optimization** for performance profiling, **godot-testing** for regression tests after fixes, **csharp-signals** for C# signal debugging patterns.

---

## 1. Print Debugging

### GDScript

Godot provides several print functions with different purposes. Choose based on the severity and context of what you are logging.

```gdscript
# print() — general output, space-separated values
print("Player position: ", position)
print("Health: ", health, " / ", max_health)

# print_rich() — BBCode-formatted output in the Output panel
print_rich("[color=yellow]WARNING:[/color] Enemy count exceeded limit: ", enemy_count)
print_rich("[b]State:[/b] [color=green]", current_state, "[/color]")

# push_error() — logs an error with a full stack trace; does NOT stop execution
push_error("save_game: file path is empty")

# push_warning() — logs a warning with stack trace; use for recoverable issues
push_warning("AudioStreamPlayer: bus '%s' not found, using Master" % bus_name)

# print_debug() — only prints in debug builds; stripped from release exports
print_debug("Frame delta: ", delta, " | FPS: ", Engine.get_frames_per_second())

# printerr() — prints to stderr; visible in external terminals and CI logs
printerr("Critical: physics state corrupted at frame ", Engine.get_process_frames())
```

**Formatted output patterns:**

```gdscript
# String formatting with % operator
print("Actor [%s] dealt %d damage to [%s]" % [name, damage, target.name])

# String.format() with named placeholders
var msg := "Position: ({x}, {y}) at speed {spd}"
print(msg.format({"x": position.x, "y": position.y, "spd": velocity.length()}))

# Printing arrays and dictionaries — use str() for clean output
var inventory := {"sword": 1, "potion": 3}
print("Inventory: ", str(inventory))

# Conditional verbose logging using a project-level constant or autoload flag
if DebugConfig.verbose_ai:
    print_rich("[color=cyan][AI][/color] ", agent.name, " chose action: ", chosen_action)
```

```csharp
// String interpolation
GD.Print($"Actor [{Name}] dealt {damage} damage to [{target.Name}]");

// Printing collections
var inventory = new Godot.Collections.Dictionary { { "sword", 1 }, { "potion", 3 } };
GD.Print("Inventory: ", inventory);

// Conditional verbose logging
if (DebugConfig.VerboseAi)
    GD.PrintRich($"[color=cyan][AI][/color] {agent.Name} chose action: {chosenAction}");
```

**When to use each function:**

| Function | Visible in Release | Stack Trace | Use For |
|---|---|---|---|
| `print()` | Yes (if not stripped) | No | General value inspection |
| `print_rich()` | Yes | No | Categorised, colour-coded logs |
| `push_error()` | Yes | Yes | Invalid state, programmer errors |
| `push_warning()` | Yes | Yes | Recoverable problems |
| `print_debug()` | No | No | Verbose frame-level output |
| `printerr()` | Yes | No | External terminal / CI output |

### C\#

```csharp
using Godot;

public partial class Player : CharacterBody3D
{
    public override void _Ready()
    {
        // GD.Print — equivalent to GDScript print()
        GD.Print("Player position: ", Position);

        // GD.PrintRich — BBCode formatted
        GD.PrintRich("[color=yellow]Ready called on[/color] ", Name);

        // GD.PushError — logs error with stack trace
        GD.PushError("_Ready: required child node missing");

        // GD.PushWarning — logs warning with stack trace
        GD.PushWarning("AudioBus not found, falling back to Master");

        // GD.PrintErr — writes to stderr
        GD.PrintErr("Critical failure in _Ready");
    }

    private void HandleDamage(int amount)
    {
        // Formatted string output
        GD.Print($"[{Name}] took {amount} damage. HP: {_health}/{_maxHealth}");
    }
}
```

---

## 2. Breakpoints and the Remote Debugger

### Setting Breakpoints

- Click the gutter (left of line numbers) in the Script editor to toggle a breakpoint. A red dot appears.
- Use `F9` to toggle a breakpoint on the current line.
- Use `breakpoint` as a statement in GDScript to trigger a programmatic breakpoint:

```gdscript
func _physics_process(delta: float) -> void:
    if velocity.length() > MAX_SPEED:
        breakpoint  # execution pauses here during debug runs
    move_and_slide()
```

- In C#, use `System.Diagnostics.Debugger.Break()` or attach a .NET debugger (e.g. JetBrains Rider or VS Code with the Godot extension).

```csharp
public override void _PhysicsProcess(double delta)
{
    if (Velocity.Length() > MaxSpeed)
    {
        System.Diagnostics.Debugger.Break(); // pause if .NET debugger is attached
    }
    MoveAndSlide();
}
```

### Using the Built-in Debugger Panel

When execution pauses at a breakpoint, the **Debugger** panel (bottom of the editor) provides:

- **Stack Frames** — the full call stack; click a frame to inspect its local variables.
- **Locals / Members / Globals** — inspect and modify variable values live.
- **Step Into (F11)** / **Step Over (F10)** / **Step Out (Shift+F11)** — navigate execution line by line.
- **Continue (F5)** — resume execution until the next breakpoint.

### Remote Scene Inspector

While a running game is paused or mid-session:

1. Open **Debugger > Remote** tab in the editor.
2. Click **Remote** in the Scene panel (top-left toggle next to "Scene") to switch the scene tree to the live view.
3. Click any live node to inspect its current properties in the Inspector.
4. Property changes made here are applied immediately for testing.

### Monitors Tab

**Debugger > Monitors** displays real-time engine metrics:

- **FPS / Process time / Physics time** — spot performance regressions.
- **Video RAM / Object count / Node count** — track memory growth.
- **Physics 2D/3D collision pairs** — identify expensive physics scenes.
- **Audio latency** — catch audio callback overruns.

Click any monitor name to open its graph. Use the **Add** button to build custom monitor dashboards.

---

## 3. Signal Debugging

### Inspecting Connections at Runtime

```gdscript
# List all connections on a signal
func _ready() -> void:
    var connections := health_component.get_signal_connection_list("health_changed")
    for conn in connections:
        print("Signal 'health_changed' connected to: ", conn["callable"])

# Check whether a specific callable is connected
if health_component.is_connected("health_changed", _on_health_changed):
    print("Connected")
else:
    push_warning("health_changed signal not connected — UI will not update")

# List all signals a node has emitted connections for
for sig in get_signal_list():
    var conns := get_signal_connection_list(sig["name"])
    if conns.size() > 0:
        print("Signal '%s': %d connection(s)" % [sig["name"], conns.size()])
```

### C\#

```csharp
// List all connections on a signal
var connections = healthComponent.GetSignalConnectionList("HealthChanged");
foreach (var conn in connections)
{
    GD.Print("HealthChanged connected to: ", conn["callable"]);
}

// Check whether a specific callable is connected
bool isConnected = healthComponent.IsConnected(
    HealthComponent.SignalName.HealthChanged,
    new Callable(this, MethodName.OnHealthChanged)
);
GD.Print("Connected: ", isConnected);

// List all signals a node has emitted connections for
foreach (var sig in GetSignalList())
{
    var conns = GetSignalConnectionList(sig["name"].AsStringName());
    if (conns.Count > 0)
        GD.Print($"Signal '{sig["name"]}': {conns.Count} connection(s)");
}
```

### Common Signal Issues

**Signal connected but not firing**

```gdscript
# WRONG — connecting to a signal that does not exist on the node
enemy.connect("dead", _on_enemy_dead)   # typo or wrong node type

# RIGHT — verify signal exists before connecting, or use typed references
assert("dead" in enemy.get_signal_list().map(func(s): return s["name"]),
    "Signal 'dead' not found on %s" % enemy.name)
enemy.dead.connect(_on_enemy_dead)
```

```csharp
// WRONG — connecting to a signal that does not exist (typo or wrong node type)
enemy.Connect("Dead", new Callable(this, MethodName.OnEnemyDead)); // silent failure

// RIGHT — verify signal exists before connecting
System.Diagnostics.Debug.Assert(
    enemy.HasSignal("Dead"),
    $"Signal 'Dead' not found on {enemy.Name}");
enemy.Connect(Enemy.SignalName.Dead, new Callable(this, MethodName.OnEnemyDead));
```

**Wrong argument count or types**

```gdscript
# Signal declared with one argument
signal item_picked_up(item: Item)

# WRONG receiver — missing argument causes "Expected 1 arguments" error
func _on_item_picked_up() -> void:
    print("picked up something")

# RIGHT — signature must match
func _on_item_picked_up(item: Item) -> void:
    print("picked up: ", item.display_name)
```

```csharp
// Signal declared with one argument
[Signal] public delegate void ItemPickedUpEventHandler(Item item);

// WRONG receiver — missing parameter causes argument count error
private void OnItemPickedUp() { GD.Print("picked up something"); }

// RIGHT — signature must match the delegate
private void OnItemPickedUp(Item item) { GD.Print("picked up: ", item.DisplayName); }
```

**Signal connected to a freed node**

```gdscript
# Use CONNECT_ONE_SHOT for single-fire connections to avoid stale connections
enemy.died.connect(_on_enemy_died, CONNECT_ONE_SHOT)

# Or disconnect explicitly before freeing
func _exit_tree() -> void:
    if health_component.is_connected("health_changed", _on_health_changed):
        health_component.disconnect("health_changed", _on_health_changed)

# Lambdas can capture 'self' — if self is freed the lambda may call invalid memory
# Prefer named methods or guard with is_instance_valid()
some_node.some_signal.connect(func(): 
    if is_instance_valid(self):
        _do_work()
)
```

```csharp
// Use CONNECT_ONE_SHOT for single-fire connections to avoid stale connections
enemy.Connect(Enemy.SignalName.Died,
    new Callable(this, MethodName.OnEnemyDied),
    (uint)GodotObject.ConnectFlags.OneShot);

// Or disconnect explicitly before freeing
public override void _ExitTree()
{
    if (healthComponent.IsConnected(
        HealthComponent.SignalName.HealthChanged,
        new Callable(this, MethodName.OnHealthChanged)))
    {
        healthComponent.Disconnect(
            HealthComponent.SignalName.HealthChanged,
            new Callable(this, MethodName.OnHealthChanged));
    }
}

// Guard lambda captures with IsInstanceValid
someNode.Connect(SomeNode.SignalName.SomeSignal,
    Callable.From(() =>
    {
        if (GodotObject.IsInstanceValid(this))
            DoWork();
    }));
```

**Signal emitted before receiver is ready**

```gdscript
# Autoload emits a signal during _ready before the main scene is fully loaded
# FIX — defer emission to the next frame
func _ready() -> void:
    call_deferred("_emit_ready_signal")

func _emit_ready_signal() -> void:
    game_ready.emit()
```

```csharp
// Autoload emits a signal during _Ready before the main scene is fully loaded
// FIX — defer emission to the next frame
public override void _Ready()
{
    CallDeferred(MethodName.EmitReadySignal);
}

private void EmitReadySignal()
{
    EmitSignal(SignalName.GameReady);
}
```

---

## 4. Common Error Patterns

| Error Message | Cause | Fix |
|---|---|---|
| `Node not found: "Player" (relative to "...")` | Wrong node path, node renamed, or accessed before it is added to the tree | Use `$NodeName` only in/after `_ready()`. Verify path with `print(get_node_or_null("Player"))`. Use `@onready`. |
| `Attempt to call function on a null instance` | Node was freed, export not assigned, or `get_node()` returned null | Guard with `is_instance_valid(node)`. Check exports in Inspector. Prefer `@onready var _node := $Node`. |
| `Can't change this state while flushing queries` | Modifying physics state (e.g. disabling a CollisionShape) inside a physics callback such as `body_entered` | Defer the change: `collision_shape.set_deferred("disabled", true)`. |
| `Invalid call. Nonexistent function 'X' in base 'Y'` | Calling a method that does not exist on that type, or accessing a node as the wrong type | Check `class_name`, cast with `as`, or verify the script is attached. Use `has_method("X")` to guard. |
| `Cyclic reference` (on `JSON.stringify` or resource save) | A Resource or Dictionary references itself, directly or indirectly | Break the cycle. Use node references instead of resource references where possible, or mark sub-resources as local only. |
| `Cannot access member without instance` | Calling an instance method as if it were static, or accessing `self` in a `@static` function | Move the call to an instance context or refactor to a proper static helper that takes data as arguments. |
| `Stack overflow / Maximum recursion depth reached` | Infinite recursion — often a signal that triggers itself, or a setter that sets itself | Add a guard variable (`_updating := true`) in setters. Trace the call stack in the Debugger. |
| `Already connected` | Calling `connect()` a second time on the same signal/callable pair without `CONNECT_ONE_SHOT` | Check `is_connected()` before connecting, or disconnect first, or use `CONNECT_REFERENCE_COUNTED`. |
| `Index out of bounds (index X out of size Y)` | Accessing an Array or PackedArray beyond its length | Validate index before access: `if index < array.size()`. Use `array.get(index)` where available. |
| `Condition "p_mbuf_current..." is true` / audio underrun | Audio callback missed its deadline; processing too much on the audio thread | Reduce audio bus effects, lower polyphony, or increase audio buffer size in Project Settings. |

---

## 5. Performance Debugging

### Profiler

Open **Debugger > Profiler**, press **Start** while the game is running, play through the scenario you want to measure, then press **Stop**.

- **Frame Time** column — total time per frame in milliseconds.
- **Self** column — time spent in that function excluding callees; the primary bottleneck indicator.
- **Calls** column — call frequency; a function called thousands of times per frame is a candidate for optimisation.
- Click any function name to jump to its source.

```gdscript
# Profile a specific block manually
var start := Time.get_ticks_usec()
_run_expensive_operation()
var elapsed := Time.get_ticks_usec() - start
print("_run_expensive_operation took: %d µs" % elapsed)
```

```csharp
// Profile a specific block manually
long start = Time.GetTicksUsec();
RunExpensiveOperation();
long elapsed = Time.GetTicksUsec() - start;
GD.Print($"RunExpensiveOperation took: {elapsed} µs");
```

### Monitors

**Debugger > Monitors** — key metrics to watch:

| Monitor | What to look for |
|---|---|
| `Time > FPS` | Below target (e.g. 60 fps) indicates frame budget overrun |
| `Time > Process` | High value means `_process()` callbacks are expensive |
| `Time > Physics Process` | High value means `_physics_process()` or physics sim is expensive |
| `Render > Total Draw Calls` | Above ~500 on mobile or ~2000 on desktop may need batching |
| `Render > Video RAM` | Steadily growing value indicates a memory leak (unfreed textures/meshes) |
| `Object > Object Count` | Growing count across identical scenes indicates nodes are not freed |
| `Physics 3D > Active Bodies` | Large count with simple scenes suggests objects are not sleeping |

### Identifying Draw Call Bottlenecks

```gdscript
# Reduce draw calls with VisibilityNotifier3D — pause processing when off-screen
@onready var _vis: VisibleOnScreenNotifier3D = $VisibleOnScreenNotifier3D

func _ready() -> void:
    _vis.screen_entered.connect(_on_screen_entered)
    _vis.screen_exited.connect(_on_screen_exited)

func _on_screen_entered() -> void:
    set_process(true)

func _on_screen_exited() -> void:
    set_process(false)
```

```csharp
// Reduce draw calls with VisibleOnScreenNotifier3D — pause processing when off-screen
private VisibleOnScreenNotifier3D _vis;

public override void _Ready()
{
    _vis = GetNode<VisibleOnScreenNotifier3D>("VisibleOnScreenNotifier3D");
    _vis.ScreenEntered += OnScreenEntered;
    _vis.ScreenExited += OnScreenExited;
}

private void OnScreenEntered() => SetProcess(true);
private void OnScreenExited() => SetProcess(false);
```

- Enable **Rendering > Debug > Draw Calls** in the editor Viewport menu to visualise batching.
- Use `RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME)` for runtime draw call counts.

### Physics Tick Monitoring

```gdscript
# Track physics ticks to detect spiral-of-death (physics can't keep up)
var _physics_ticks_this_second := 0
var _second_timer := 0.0

func _physics_process(delta: float) -> void:
    _physics_ticks_this_second += 1

func _process(delta: float) -> void:
    _second_timer += delta
    if _second_timer >= 1.0:
        print("Physics ticks last second: ", _physics_ticks_this_second,
              " (target: ", Engine.physics_ticks_per_second, ")")
        _physics_ticks_this_second = 0
        _second_timer -= 1.0
```

```csharp
// Track physics ticks to detect spiral-of-death
private int _physicsTicksThisSecond = 0;
private double _secondTimer = 0.0;

public override void _PhysicsProcess(double delta)
{
    _physicsTicksThisSecond++;
}

public override void _Process(double delta)
{
    _secondTimer += delta;
    if (_secondTimer >= 1.0)
    {
        GD.Print($"Physics ticks last second: {_physicsTicksThisSecond}" +
                 $" (target: {Engine.PhysicsTicksPerSecond})");
        _physicsTicksThisSecond = 0;
        _secondTimer -= 1.0;
    }
}
```

- If ticks per second fall below `Engine.physics_ticks_per_second`, reduce physics complexity or lower `physics_ticks_per_second` in Project Settings.

---

## 6. Scene Tree Debugging

### print_tree_pretty()

```gdscript
# Print the full subtree of a node in a readable format
func _ready() -> void:
    print_tree_pretty()
    # Output example:
    # ┖╴Player
    #    ┠╴CollisionShape3D
    #    ┠╴MeshInstance3D
    #    ┖╴Camera3D

# Print the entire scene tree from root
func _ready() -> void:
    get_tree().root.print_tree_pretty()
```

```csharp
// Print the full subtree of a node in a readable format
public override void _Ready()
{
    PrintTreePretty();

    // Print the entire scene tree from root
    GetTree().Root.PrintTreePretty();
}
```

### Remote Scene Tree in the Editor

1. Run the game.
2. In the **Scene** panel, click **Remote** (top-left toggle).
3. The live scene tree appears — nodes are shown with their current state.
4. Click any node to open it in the **Inspector** and edit properties in real time.
5. Use **Debugger > Breakpoints** to pause and then inspect mid-frame state.

### Node Groups for Debugging

```gdscript
# Tag nodes at runtime for batch inspection
func _ready() -> void:
    add_to_group("debug_enemies")

# Retrieve all tagged nodes from anywhere
func _input(event: InputEvent) -> void:
    if event.is_action_pressed("debug_dump_enemies"):
        for enemy in get_tree().get_nodes_in_group("debug_enemies"):
            print(enemy.name, " HP: ", enemy.health, " pos: ", enemy.global_position)
```

```csharp
// Tag nodes at runtime for batch inspection
public override void _Ready()
{
    AddToGroup("debug_enemies");
}

public override void _Input(InputEvent @event)
{
    if (@event.IsActionPressed("debug_dump_enemies"))
    {
        foreach (var node in GetTree().GetNodesInGroup("debug_enemies"))
        {
            if (node is Enemy enemy)
                GD.Print($"{enemy.Name} HP: {enemy.Health} pos: {enemy.GlobalPosition}");
        }
    }
}
```

### _get_configuration_warnings() for @tool Scripts

Use `_get_configuration_warnings()` in `@tool` scripts to surface misconfiguration warnings directly in the editor (a yellow warning icon on the node).

```gdscript
@tool
extends Node3D

@export var target_path: NodePath

func _get_configuration_warnings() -> PackedStringArray:
    var warnings := PackedStringArray()
    if target_path.is_empty():
        warnings.append("target_path must be set — this node will not function without it.")
    if not get_node_or_null(target_path) is CharacterBody3D:
        warnings.append("target_path must point to a CharacterBody3D node.")
    return warnings
```

### C\#

```csharp
#if TOOLS
[Tool]
public partial class EnemySpawner : Node3D
{
    [Export] public NodePath TargetPath { get; set; }

    public override string[] _GetConfigurationWarnings()
    {
        var warnings = new System.Collections.Generic.List<string>();
        if (TargetPath == null || TargetPath.IsEmpty)
            warnings.Add("TargetPath must be set.");
        return warnings.ToArray();
    }
}
#endif
```

---

## 7. Systematic Debugging Checklist

Follow these steps in order. Skipping ahead to "just try a fix" wastes time and often introduces new bugs.

### Step 1 — Reproduce

- Identify the exact steps that trigger the bug, every time.
- If it is intermittent, add logging around the suspected area and run until it occurs.
- Note the Godot version, build type (debug vs release), and platform.

```gdscript
# Add a counter to catch intermittent bugs
var _frame_of_crash := 0

func _process(_delta: float) -> void:
    _frame_of_crash = Engine.get_process_frames()

func _on_enemy_died() -> void:
    print("Enemy died at frame: ", _frame_of_crash)
```

```csharp
// Add a counter to catch intermittent bugs
private long _frameOfCrash = 0;

public override void _Process(double delta)
{
    _frameOfCrash = Engine.GetProcessFrames();
}

private void OnEnemyDied()
{
    GD.Print("Enemy died at frame: ", _frameOfCrash);
}
```

### Step 2 — Isolate

- Remove unrelated systems. Can you reproduce in a minimal scene with only the suspect nodes?
- Disable scripts one by one using `set_script(null)` or commenting out `_process` / `_physics_process`.
- Use binary search: disable half the code, see if the bug persists, then narrow further.

```gdscript
# Quick isolation — disable a node's script temporarily at runtime
func _ready() -> void:
    $SuspectNode.set_script(null)  # removes script, node becomes a plain Node
```

```csharp
// Quick isolation — disable a node's script temporarily at runtime
public override void _Ready()
{
    GetNode("SuspectNode").SetScript(default);
}
```

### Step 3 — Form a Hypothesis

- State the hypothesis explicitly: "I believe X causes Y because Z."
- Write it down. This prevents hypothesis drift during investigation.

### Step 4 — Trace

- Use breakpoints, `print()`, or the Profiler to confirm or refute the hypothesis.
- Print values immediately before and after the suspected line.
- Check signal connections with `get_signal_connection_list()`.
- Inspect the scene tree with `print_tree_pretty()`.

```gdscript
func take_damage(amount: int) -> void:
    print("[TRACE] take_damage called — amount: %d, health before: %d" % [amount, health])
    health -= amount
    print("[TRACE] health after: %d" % health)
    if health <= 0:
        die()
```

```csharp
public void TakeDamage(int amount)
{
    GD.Print($"[TRACE] TakeDamage called — amount: {amount}, health before: {_health}");
    _health -= amount;
    GD.Print($"[TRACE] health after: {_health}");
    if (_health <= 0)
        Die();
}
```

### Step 5 — Fix

- Make the smallest change that addresses the root cause.
- Do not fix symptoms; fix the underlying cause identified by the trace.
- If the fix requires touching multiple systems, consider whether a design change is needed.

### Step 6 — Verify

- Reproduce the original steps — confirm the bug is gone.
- Run any existing tests: `gut -gdir=res://tests` or `gdunit4_runner`.
- Check for regressions in related functionality.

```bash
# Run GUT tests headless
godot --headless --script res://addons/gut/gut_cmdln.gd -gdir=res://tests -gexit

# Run gdUnit4 tests headless
godot --headless -s res://addons/gdUnit4/bin/GdUnit4CmdTool.gd
```

### Step 7 — Add a Test

- Write a regression test that would have caught this bug.
- Name the test after the bug scenario so it serves as documentation.

```gdscript
# tests/unit/test_health_component.gd
func test_take_damage_does_not_go_below_zero_regression() -> void:
    # Regression: health could go negative when overkill damage was applied
    _health.take_damage(9999)
    assert_eq(_health.current_health, 0,
        "Health must clamp to 0, not go negative on overkill")
```

```csharp
// tests/HealthComponentTest.cs (using GdUnit4 or similar C# test framework)
[TestCase]
public void TakeDamage_DoesNotGoBelowZero_Regression()
{
    // Regression: health could go negative when overkill damage was applied
    _health.TakeDamage(9999);
    AssertThat(_health.CurrentHealth).IsEqual(0);
}
```
