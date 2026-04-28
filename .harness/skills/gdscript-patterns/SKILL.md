---
name: gdscript-patterns
description: Use when writing GDScript — static typing, await/coroutines, lambdas, match patterns, export annotations, inner classes, and common idioms
---

# GDScript Patterns in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs.

> **Related skills:** **godot-code-review** for style rules and anti-patterns, **csharp-godot** for GDScript-to-C# translation, **state-machine** for state patterns, **event-bus** for signal architecture.

---

## 1. Static Typing

### Type Hints

Always add type hints — they catch bugs at parse time, improve autocomplete, and boost performance.

```gdscript
# Variables
var health: int = 100
var speed: float = 200.0
var player_name: String = "Hero"
var direction: Vector2 = Vector2.ZERO

# Constants
const MAX_HEALTH: int = 100
const GRAVITY: float = 980.0

# Functions — parameters and return type
func take_damage(amount: int) -> void:
    health -= amount

func get_direction() -> Vector2:
    return Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")

# Inferred typing with :=
var pos := Vector2(100, 200)     # inferred as Vector2
var items := []                  # inferred as Array (untyped)
var count := 0                   # inferred as int
```

### Typed Collections

```gdscript
# Typed arrays — only accepts the specified type
var enemies: Array[Enemy] = []
var scores: Array[int] = [10, 20, 30]
var names: Array[String] = ["Alice", "Bob"]

# Typed dictionaries (Godot 4.4+)
var inventory: Dictionary[String, int] = {"sword": 1, "potion": 5}

# Typed loop variable
for enemy: Enemy in enemies:
    enemy.take_damage(10)

# Typed array methods work with type safety
var filtered: Array[Enemy] = enemies.filter(func(e: Enemy) -> bool: return e.health > 0)
```

### Casting with `as` and `is`

```gdscript
# 'is' — type check (returns bool)
func _on_body_entered(body: Node2D) -> void:
    if body is Player:
        var player: Player = body as Player
        player.take_damage(10)

# 'as' — cast (returns null on failure, no error)
var sprite := get_node("Sprite") as Sprite2D
if sprite:
    sprite.modulate = Color.RED

# Prefer 'is' check + cast over bare 'as' to avoid null surprises
```

### Enabling Strict Typing Warnings

In **Project > Project Settings > Debug > GDScript**:

| Warning                 | Effect                                      |
|-------------------------|---------------------------------------------|
| `UNTYPED_DECLARATION`   | Warns on any untyped variable/parameter     |
| `INFERRED_DECLARATION`  | Warns on `:=` (prefers explicit types)      |
| `UNSAFE_CAST`           | Warns on unsafe `as` casts                  |
| `UNSAFE_CALL_ARGUMENT`  | Warns when passing wrong type to a function |

> Set warnings to **Error** for strict enforcement in team projects.

---

## 2. Await & Coroutines

### Awaiting Signals

`await` pauses the function until a signal fires, then resumes. The function becomes a coroutine.

```gdscript
func death_sequence() -> void:
    $AnimationPlayer.play("death")
    await $AnimationPlayer.animation_finished  # pauses here

    $Sprite2D.visible = false
    await get_tree().create_timer(1.0).timeout  # wait 1 second

    queue_free()
```

### Awaiting with Return Values

```gdscript
# Signal that passes data
signal dialogue_choice_made(choice: int)

func show_dialogue(options: Array[String]) -> int:
    # ... display UI ...
    var choice: int = await dialogue_choice_made
    return choice

# Caller:
func _on_npc_interact() -> void:
    var result := await show_dialogue(["Yes", "No"])
    if result == 0:
        print("Player said yes")
```

### Timer Patterns

```gdscript
# One-shot delay
await get_tree().create_timer(0.5).timeout

# Repeating with await (simple but blocks the function)
for i in 5:
    do_something()
    await get_tree().create_timer(0.2).timeout

# Non-blocking timer — use SceneTreeTimer or Tween instead
get_tree().create_timer(2.0).timeout.connect(_on_delayed_action)
```

### Coroutine Safety

```gdscript
# DANGER: node may be freed while awaiting
func unsafe_coroutine() -> void:
    await get_tree().create_timer(5.0).timeout
    position = Vector2.ZERO  # crash if node was freed during wait!

# SAFE: check validity after await
func safe_coroutine() -> void:
    await get_tree().create_timer(5.0).timeout
    if not is_instance_valid(self):
        return
    position = Vector2.ZERO
```

---

## 3. Lambda Functions

Lambdas are inline anonymous functions, useful for callbacks, sorting, filtering.

### Basic Syntax

```gdscript
# Single-expression lambda
var double := func(x: int) -> int: return x * 2

# Multi-line lambda
var greet := func(name: String) -> void:
    print("Hello, %s!" % name)
    print("Welcome!")

# Calling a lambda
double.call(5)  # returns 10
greet.call("Player")
```

### With Signals

```gdscript
# Inline signal connection (one-off use)
$Button.pressed.connect(func(): print("Button pressed!"))

# With arguments
$Timer.timeout.connect(func():
    health -= 1
    if health <= 0:
        die()
)

# One-shot connection (auto-disconnects after first call)
$Timer.timeout.connect(func(): print("Once!"), CONNECT_ONE_SHOT)
```

### With Array Methods

```gdscript
var numbers: Array[int] = [1, 2, 3, 4, 5, 6, 7, 8]

# Filter — keep elements where lambda returns true
var evens: Array[int] = numbers.filter(func(n: int) -> bool: return n % 2 == 0)
# [2, 4, 6, 8]

# Map — transform each element
var doubled: Array[int] = numbers.map(func(n: int) -> int: return n * 2)
# [2, 4, 6, 8, 10, 12, 14, 16]

# Reduce — accumulate into single value
var total: int = numbers.reduce(func(acc: int, n: int) -> int: return acc + n, 0)
# 36

# Any / All
var has_negative: bool = numbers.any(func(n: int) -> bool: return n < 0)
var all_positive: bool = numbers.all(func(n: int) -> bool: return n > 0)

# Sort with custom comparison
var items: Array[Dictionary] = [{"name": "B", "value": 2}, {"name": "A", "value": 1}]
items.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return a["value"] < b["value"])
```

### Closures (Capturing Variables)

```gdscript
func create_counter(start: int) -> Callable:
    var count := start
    return func() -> int:
        count += 1
        return count

var counter := create_counter(0)
print(counter.call())  # 1
print(counter.call())  # 2
```

---

## 4. Match / Pattern Matching

GDScript's `match` is like `switch` but with pattern support.

### Basic Match

```gdscript
match state:
    State.IDLE:
        play_idle()
    State.RUNNING:
        play_run()
    State.JUMPING, State.FALLING:  # multiple patterns
        play_air()
    _:  # default (wildcard)
        push_warning("Unknown state: %s" % state)
```

### Pattern Types

```gdscript
# Literal patterns
match value:
    42:
        print("The answer")
    "hello":
        print("Greeting")
    true:
        print("Boolean true")

# Binding pattern — captures value into a variable
match command:
    ["move", var direction]:
        move(direction)
    ["attack", var target, var damage]:
        attack(target, damage)

# Array pattern
match input:
    [1, 2, 3]:
        print("Exact match")
    [1, ..]:
        print("Starts with 1")
    [var first, _, var last]:
        print("First: %s, Last: %s" % [first, last])

# Dictionary pattern
match event:
    {"type": "damage", "amount": var amt}:
        take_damage(amt)
    {"type": "heal", "amount": var amt}:
        heal(amt)

# Nested condition inside a branch
match enemy_type:
    "boss":
        if health < 50:
            enter_rage_mode()
        else:
            normal_attack()
```

---

## 5. Export Annotations

### Basic Exports

```gdscript
@export var speed: float = 200.0
@export var health: int = 100
@export var player_name: String = "Hero"
@export var color: Color = Color.WHITE
@export var texture: Texture2D
@export var scene: PackedScene
```

### Range and Hints

```gdscript
@export_range(0.0, 100.0, 0.5) var volume: float = 50.0
@export_range(1, 10) var level: int = 1
@export_range(0.0, 1.0, 0.01, "or_greater") var scale: float = 1.0

@export_multiline var description: String = ""
@export_file("*.tscn") var level_path: String
@export_dir var save_directory: String
@export_color_no_alpha var outline_color: Color

# Enum export — creates dropdown in Inspector
@export_enum("Sword", "Bow", "Staff") var weapon: int = 0
# Or use a real enum:
enum Weapon { SWORD, BOW, STAFF }
@export var weapon_type: Weapon = Weapon.SWORD
```

### Export Groups

```gdscript
@export_group("Movement")
@export var speed: float = 200.0
@export var acceleration: float = 1500.0
@export var friction: float = 1200.0

@export_group("Combat")
@export var attack_damage: int = 10
@export var attack_speed: float = 1.0

@export_subgroup("Defense")
@export var armor: int = 5
@export var dodge_chance: float = 0.1

@export_category("Advanced Settings")
@export var debug_mode: bool = false
```

### Node and Resource Exports

```gdscript
# Node references (assigned in editor by dragging)
@export var target: Node2D
@export var spawn_point: Marker2D
@export var health_bar: ProgressBar

# Array of nodes/resources
@export var patrol_points: Array[Marker2D] = []
@export var loot_table: Array[ItemResource] = []
```

---

## 6. Inner Classes & class_name

### class_name

Register a script as a global class name — available everywhere without `preload`.

```gdscript
# item_data.gd
class_name ItemData
extends Resource

@export var name: String
@export var icon: Texture2D
@export var value: int

# Now usable anywhere:
# var item: ItemData = ItemData.new()
# var items: Array[ItemData] = []
```

### Inner Classes

```gdscript
# Define a class inside another script
class HitResult:
    var damage: int
    var critical: bool
    var knockback: Vector2

    func _init(dmg: int, crit: bool, kb: Vector2 = Vector2.ZERO) -> void:
        damage = dmg
        critical = crit
        knockback = kb

# Usage
func calculate_hit() -> HitResult:
    var crit := randf() < 0.2
    var dmg := 10 * (2 if crit else 1)
    return HitResult.new(dmg, crit, Vector2.RIGHT * 50)
```

---

## 7. super() in Virtual Methods

In Godot 4, overridden virtual methods (`_ready()`, `_process()`, `_physics_process()`, `_enter_tree()`, `_exit_tree()`, etc.) do **not** automatically call the parent implementation. You must call `super()` explicitly if the parent class has logic in that method.

### The Problem

```gdscript
# parent.gd
class_name EnemyBase
extends CharacterBody2D

func _ready() -> void:
    add_to_group("enemies")
    $HealthComponent.health_depleted.connect(_on_health_depleted)

# child.gd — BUG: parent _ready() never runs!
extends EnemyBase

func _ready() -> void:
    $NavigationAgent2D.velocity_computed.connect(_on_velocity_computed)
    # Parent's group registration and signal connection are LOST
```

### The Fix

```gdscript
# child.gd — CORRECT: call super() to run parent _ready()
extends EnemyBase

func _ready() -> void:
    super()  # runs EnemyBase._ready() — group add + signal connect
    $NavigationAgent2D.velocity_computed.connect(_on_velocity_computed)
```

### C#

C# uses `base.MethodName()` — same concept:

```csharp
public partial class SpecialEnemy : EnemyBase
{
    public override void _Ready()
    {
        base._Ready(); // runs EnemyBase._Ready()
        GetNode<NavigationAgent2D>("NavigationAgent2D").VelocityComputed += OnVelocityComputed;
    }
}
```

### When super() Is Required

| Scenario | Call super()? |
|----------|---------------|
| Extending a **built-in** Godot class (Node, CharacterBody2D) | Not needed — engine handles internal callbacks |
| Extending **your own** base class with logic in the virtual | **Yes — always** |
| Extending a **third-party** class (addon, plugin) | **Yes — assume it has logic** |
| Multiple inheritance levels (A → B → C) | Each level calls `super()` to chain up |

### Common Bugs from Missing super()

| Symptom | Likely Cause |
|---------|-------------|
| Child node doesn't join a group set in parent `_ready()` | Missing `super()` in child `_ready()` |
| Signals connected in parent `_ready()` never fire | Missing `super()` — connections never made |
| Parent animation logic stops working in child | Missing `super()` in child `_process()` or `_physics_process()` |
| `@onready` vars in parent are null when child accesses them | Parent `_ready()` body never ran — those vars never initialized |

> **Rule of thumb:** If you extend a script that you or someone else wrote (not a bare Godot class), always call `super()` as the first line of any overridden virtual method.

---

## 8. Common Idioms

### Ternary Expression

```gdscript
var label := "alive" if health > 0 else "dead"
var direction := -1 if facing_left else 1
velocity.x = speed * (1.5 if sprinting else 1.0)
```

### String Formatting

```gdscript
# % operator (printf-style)
var msg := "Player %s has %d HP" % [player_name, health]
var formatted := "%.2f seconds" % elapsed_time

# String interpolation — no built-in f-strings, use % or format()
var text := "Score: %d / %d" % [current_score, max_score]
```

### Null / Empty Checks

```gdscript
# Check if a node reference is valid
if is_instance_valid(target):
    target.take_damage(10)

# Check if a variable is null
if weapon != null:
    weapon.attack()

# Shorthand for non-null (works because null is falsy)
if weapon:
    weapon.attack()

# Check array/dictionary/string emptiness
if inventory.is_empty():
    show_empty_message()
if not player_name.is_empty():
    display_name(player_name)
```

### Dictionary Access Patterns

```gdscript
var stats: Dictionary = {"health": 100, "attack": 15, "defense": 8}

# Safe access with default
var hp: int = stats.get("health", 0)
var missing: int = stats.get("magic", 0)  # returns 0, no error

# Check existence
if stats.has("attack"):
    apply_damage(stats["attack"])

# Merge dictionaries
var defaults := {"health": 100, "attack": 10}
var overrides := {"attack": 20, "speed": 5}
defaults.merge(overrides, true)  # true = overwrite existing keys
```

### Useful Array Operations

```gdscript
var items: Array[String] = ["sword", "shield", "potion", "sword"]

items.append("bow")              # add to end
items.erase("sword")             # remove first occurrence
items.has("shield")              # true
items.find("potion")             # index or -1
items.pick_random()              # random element
items.shuffle()                  # randomize order
items.reverse()                  # reverse in place
items.slice(1, 3)                # sub-array [index 1 to 3)

# Remove duplicates
var unique: Array[String] = []
for item in items:
    if item not in unique:
        unique.append(item)
```

### Setget / Properties

```gdscript
var health: int = 100:
    set(value):
        health = clampi(value, 0, max_health)
        health_changed.emit(health)
        if health == 0:
            died.emit()
    get:
        return health
```

---

## 9. Annotations Reference

| Annotation            | Purpose                                    |
|-----------------------|--------------------------------------------|
| `@export`             | Expose variable in Inspector               |
| `@export_range`       | Numeric with slider                        |
| `@export_enum`        | Dropdown from string list                  |
| `@export_file`        | File path picker                           |
| `@export_dir`         | Directory picker                           |
| `@export_multiline`   | Multi-line text box                        |
| `@export_group`       | Group heading in Inspector                 |
| `@export_subgroup`    | Subgroup heading                           |
| `@export_category`    | Category divider                           |
| `@onready`            | Initialize when node enters tree, just before `_ready()` body runs |
| `@tool`               | Run script in editor                       |
| `@icon`               | Custom icon for the script                 |
| `@warning_ignore`     | Suppress specific warning on next line     |
| `@static_unload`      | Allow static variables to be freed         |

---

## 10. Common Pitfalls

| Symptom                               | Cause                                       | Fix                                                              |
|---------------------------------------|----------------------------------------------|------------------------------------------------------------------|
| `as` cast silently returns `null`     | Type mismatch — `as` doesn't error          | Use `is` check first, then cast                                  |
| Await never resumes                   | Signal never emitted, or node freed          | Check `is_instance_valid(self)` after await; ensure signal fires |
| Lambda captures stale variable        | Loop variable captured by reference          | Copy to local var before lambda: `var local := i`                |
| `UNTYPED_DECLARATION` warnings flood  | Warning enabled but codebase isn't typed     | Type incrementally; use `@warning_ignore` for legacy code        |
| Typed array rejects valid items       | Item type doesn't match exactly              | Ensure items match the declared type (no implicit upcasting)     |
| `@onready` is `null`                  | Accessed before `_ready()` runs              | Never access `@onready` vars in `_init()` or variable declarations |
| Match doesn't enter any branch        | No matching pattern and no `_:` wildcard     | Always add `_:` default branch                                   |
| `class_name` conflict                 | Two scripts with same `class_name`           | Use unique names; check for duplicates in Project                |
| Export group applies to wrong vars     | Group scope continues until next group       | Add a new `@export_group("")` to end the group scope             |
| Parent `_ready()` logic doesn't run in child | Missing `super()` call in child's `_ready()` | Add `super()` as first line; see Section 7 |

---

## 11. Implementation Checklist

- [ ] All variables, parameters, and return types have explicit type hints
- [ ] Typed arrays (`Array[Type]`) are used instead of untyped `Array` where possible
- [ ] `await` calls are followed by `is_instance_valid(self)` checks when the node could be freed
- [ ] Lambdas connected to signals are simple — complex logic goes in named methods
- [ ] `match` statements include a `_:` default branch
- [ ] `@export` variables use appropriate hints (`@export_range`, `@export_enum`, etc.)
- [ ] `@export_group` organizes Inspector properties into logical sections
- [ ] `class_name` is only used for scripts that need global visibility
- [ ] `is` type check precedes `as` cast when the type isn't guaranteed
- [ ] Properties with setters validate and clamp values
- [ ] Overridden virtual methods call `super()` when extending non-built-in base classes
