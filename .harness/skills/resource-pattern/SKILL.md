---
name: resource-pattern
description: Use when creating data containers in Godot — custom Resources for configuration, items, stats, and editor integration
---

# Resource Pattern in Godot 4.3+

Resources are Godot's built-in data containers. Use them for configuration, item definitions, character stats, and any data that lives outside the scene tree. All examples target Godot 4.3+ with no deprecated APIs.

> **Related skills:** **inventory-system** for Resource-based item definitions, **save-load** for Resource serialization, **component-system** for data-driven component configuration.

---

## 1. What Are Resources

A `Resource` is a reference-counted data object that:

- Is saved as a `.tres` (text) or `.res` (binary) file on disk
- Is editable directly in the Godot Inspector
- Is **loaded once and shared by default** — every node that loads the same path gets the same in-memory object
- Can be nested inside other Resources and PackedScenes
- Survives scene changes (unlike Node state, which is discarded on scene reload)

Because Resources are shared by default, they are ideal for read-only data (item definitions, audio settings, ability blueprints). For per-instance mutable state, call `make_unique()` or `duplicate()` — see section 8.

---

## 2. When to Use Resources

| Use Case | Example Resource | Alternative |
|---|---|---|
| Item definitions | `ItemData` with name, icon, value | Dictionary (loses type safety) |
| Enemy configuration | `EnemyStats` with health, speed, damage | Exported vars on Node (not reusable) |
| Character stats | `CharacterStats` with base values | Autoload (global state, hard to test) |
| Ability definitions | `AbilityData` with cooldown, cost, effect | Hardcoded constants |
| Level metadata | `LevelConfig` with music, time limit, goals | JSON (no editor integration) |
| Audio / visual themes | `UIThemeData` with color palette, fonts | Theme resource (same idea, built-in) |
| Dialogue trees | `DialogueLine` referencing next line | JSON (no type checking) |

Use a custom Resource any time you want **Inspector editing + typed data + sharing across scenes**.

---

## 3. Basic Custom Resource

### GDScript

```gdscript
# item_data.gd
class_name ItemData
extends Resource

enum ItemType { WEAPON, ARMOUR, CONSUMABLE, QUEST }

@export var name:        String   = ""
@export var description: String   = ""
@export var icon:        Texture2D
@export var value:       int      = 0
@export var item_type:   ItemType = ItemType.CONSUMABLE
```

Create an instance in the editor: **right-click** the FileSystem panel → **New Resource** → choose `ItemData`. Fill in the Inspector fields and save as `res://data/items/health_potion.tres`.

Load it at runtime:

```gdscript
var potion: ItemData = load("res://data/items/health_potion.tres")
print(potion.name)        # "Health Potion"
print(potion.value)       # 50
```

### C#

```csharp
// ItemData.cs
using Godot;

[GlobalClass]
public partial class ItemData : Resource
{
    public enum ItemType { Weapon, Armour, Consumable, Quest }

    [Export] public string   Name        { get; set; } = "";
    [Export] public string   Description { get; set; } = "";
    [Export] public Texture2D Icon       { get; set; }
    [Export] public int      Value       { get; set; } = 0;
    [Export] public ItemType Type        { get; set; } = ItemType.Consumable;
}
```

> `[GlobalClass]` is required in C# so the editor recognizes the class and shows it in **New Resource**.

```csharp
var potion = GD.Load<ItemData>("res://data/items/health_potion.tres");
GD.Print(potion.Name);   // "Health Potion"
GD.Print(potion.Value);  // 50
```

---

## 4. Editor Integration

Export annotations control how properties appear in the Inspector.

### GDScript

```gdscript
class_name AbilityData
extends Resource

# Groups collapse related fields under a named header
@export_group("Identity")
@export var ability_name: String = ""
@export var description:  String = ""
@export var icon:         Texture2D

# Category draws a bold separator (not collapsible)
@export_category("Tuning")

# Range clamps the value and shows a slider in the Inspector
@export_range(0.0, 60.0, 0.1, "suffix:s") var cooldown:   float = 1.0
@export_range(1,   999,   1)               var mana_cost:  int   = 10
@export_range(0.0, 1.0,  0.01)             var crit_chance: float = 0.05

# Enum shows a dropdown in the Inspector
enum DamageType { PHYSICAL, FIRE, ICE, LIGHTNING }
@export var damage_type: DamageType = DamageType.PHYSICAL

@export_group("Flags")
@export var is_passive:     bool = false
@export var requires_target: bool = true
```

| Annotation | Effect |
|---|---|
| `@export` | Exposes any typed property in the Inspector |
| `@export_range(min, max, step)` | Adds a slider, clamps input |
| `@export_enum("A","B","C")` | Dropdown for `int` when no enum type available |
| `@export_group("Label")` | Collapsible header grouping following properties |
| `@export_category("Label")` | Bold non-collapsible separator |

### C#

```csharp
[GlobalClass]
public partial class AbilityData : Resource
{
    public enum DamageType { Physical, Fire, Ice, Lightning }

    [ExportGroup("Identity")]
    [Export] public string    AbilityName { get; set; } = "";
    [Export] public string    Description { get; set; } = "";
    [Export] public Texture2D Icon        { get; set; }

    [ExportCategory("Tuning")]
    [Export(PropertyHint.Range, "0,60,0.1,suffix:s")]
    public float Cooldown    { get; set; } = 1.0f;

    [Export(PropertyHint.Range, "1,999,1")]
    public int   ManaCost    { get; set; } = 10;

    [Export(PropertyHint.Range, "0,1,0.01")]
    public float CritChance  { get; set; } = 0.05f;

    [Export] public DamageType Damage { get; set; } = DamageType.Physical;

    [ExportGroup("Flags")]
    [Export] public bool IsPassive      { get; set; } = false;
    [Export] public bool RequiresTarget { get; set; } = true;
}
```

---

## 5. Resource as Configuration

Use Resources to define enemy tuning parameters. Designers can tweak values in the Inspector without touching code. The `@export_range` annotation enforces bounds and surfaces sliders.

### GDScript

```gdscript
# enemy_stats.gd
class_name EnemyStats
extends Resource

@export_group("Combat")
@export_range(1,    5000, 1)    var health:          int   = 100
@export_range(0.0,  500.0, 0.1) var speed:           float = 80.0
@export_range(0,    999,   1)   var damage:          int   = 10
@export_range(0.0,  1.0,  0.01) var crit_chance:     float = 0.05
@export_range(0.1, 10.0,  0.1)  var attack_interval: float = 1.5

@export_group("Drops")
## Each entry must be a Resource subclass that describes a drop (e.g. DropEntry).
@export var drop_table: Array[Resource] = []
@export_range(0.0,  1.0,  0.01) var drop_chance: float = 0.3
```

```gdscript
# enemy.gd — consumes EnemyStats
class_name Enemy
extends CharacterBody2D

@export var stats: EnemyStats

var _current_health: int


func _ready() -> void:
    # make_unique() so this instance has its own mutable copy
    stats = stats.duplicate()
    _current_health = stats.health


func take_damage(amount: int) -> void:
    _current_health -= amount
    if _current_health <= 0:
        _die()


func _die() -> void:
    _roll_drops()
    queue_free()


func _roll_drops() -> void:
    if randf() > stats.drop_chance:
        return
    for drop: Resource in stats.drop_table:
        # Spawn drop — implementation depends on project drop system
        pass
```

### C#

```csharp
// EnemyStats.cs
using Godot;
using Godot.Collections;

[GlobalClass]
public partial class EnemyStats : Resource
{
    [ExportGroup("Combat")]
    [Export(PropertyHint.Range, "1,5000,1")]     public int   Health         { get; set; } = 100;
    [Export(PropertyHint.Range, "0,500,0.1")]    public float Speed          { get; set; } = 80.0f;
    [Export(PropertyHint.Range, "0,999,1")]      public int   Damage         { get; set; } = 10;
    [Export(PropertyHint.Range, "0,1,0.01")]     public float CritChance     { get; set; } = 0.05f;
    [Export(PropertyHint.Range, "0.1,10,0.1")]   public float AttackInterval { get; set; } = 1.5f;

    [ExportGroup("Drops")]
    [Export] public Array<Resource> DropTable  { get; set; } = new();
    [Export(PropertyHint.Range, "0,1,0.01")]
    public float DropChance { get; set; } = 0.3f;
}
```

```csharp
// Enemy.cs — consumes EnemyStats
using Godot;

public partial class Enemy : CharacterBody2D
{
    [Export] public EnemyStats Stats { get; set; }

    private int _currentHealth;

    public override void _Ready()
    {
        // Duplicate so this instance has its own mutable copy
        Stats = (EnemyStats)Stats.Duplicate();
        _currentHealth = Stats.Health;
    }

    public void TakeDamage(int amount)
    {
        _currentHealth -= amount;
        if (_currentHealth <= 0)
            Die();
    }

    private void Die()
    {
        RollDrops();
        QueueFree();
    }

    private void RollDrops()
    {
        if (GD.Randf() > Stats.DropChance) return;
        foreach (var drop in Stats.DropTable)
        {
            // Spawn drop — implementation depends on project drop system
        }
    }
}
```

---

## 6. Resource Collections

### Array[Resource] exports

Declare a typed array on a Resource or Node to hold multiple sub-resources editable in the Inspector.

```gdscript
# item_database.gd
class_name ItemDatabase
extends Resource

@export var items: Array[ItemData] = []


func find_by_name(item_name: String) -> ItemData:
    for item: ItemData in items:
        if item.name == item_name:
            return item
    return null
```

### ResourcePreloader

`ResourcePreloader` is a Node that loads a named set of resources at scene load, holding strong references so they are not unloaded.

```gdscript
# Attach a ResourcePreloader node named "Preloader" to your scene.
# In the Inspector, add resources with string keys.

@onready var preloader: ResourcePreloader = $Preloader


func _ready() -> void:
    var potion: ItemData = preloader.get_resource("health_potion")
    var sword:  ItemData = preloader.get_resource("iron_sword")
```

### Loading all resources from a directory

```gdscript
func load_all_items(dir_path: String) -> Array[ItemData]:
    var result: Array[ItemData] = []
    var dir := DirAccess.open(dir_path)
    if dir == null:
        push_error("ItemDatabase: cannot open directory '%s'" % dir_path)
        return result

    dir.list_dir_begin()
    var file_name := dir.get_next()
    while file_name != "":
        if not dir.current_is_dir() and (file_name.ends_with(".tres") or file_name.ends_with(".res")):
            var res := load(dir_path.path_join(file_name))
            if res is ItemData:
                result.append(res)
        file_name = dir.get_next()

    return result
```

---

## 7. Resource vs Node

| Aspect | Resource | Node |
|---|---|---|
| Purpose | Data storage and configuration | Behavior, rendering, physics, input |
| Scene tree | Not in the tree | Lives in the scene tree |
| Lifecycle hooks | None (`_init` only) | `_ready`, `_process`, `_physics_process`, etc. |
| Sharing | Shared by default (same path = same object) | Each instance is independent |
| Serialization | Saved as `.tres` / `.res`, Inspector-editable | Saved inside `.tscn` |
| Signals | Supported | Supported |
| Use for | Item data, stats, config, ability blueprints | Player, enemy, UI widgets, cameras |
| Avoid for | Anything needing per-frame updates or scene queries | Static data that never changes at runtime |

**Rule of thumb:** if it has no behavior and no need to exist in the scene tree, make it a Resource. If it needs to move, render, receive input, or run per-frame logic, make it a Node.

---

## 8. Sharing vs Unique

Resources loaded from the same path are **shared**. Every node that loads `res://data/enemies/goblin.tres` gets the exact same object in memory.

```gdscript
# Both variables point to the same object — modifying one modifies the other.
var a: EnemyStats = load("res://data/enemies/goblin.tres")
var b: EnemyStats = load("res://data/enemies/goblin.tres")
print(a == b)  # true
```

**For per-instance mutable state, call `duplicate()`:**

```gdscript
func _ready() -> void:
    # Shallow duplicate — nested Resources are still shared
    stats = stats.duplicate()

    # Deep duplicate — all nested Resources are also copied
    stats = stats.duplicate(true)
```

`duplicate()` returns a new Resource with the same property values. The original `.tres` file is untouched.

**`make_unique()` in the editor:** In the Inspector, any sub-resource slot shows a **Make Unique** button. Clicking it embeds a private copy of the sub-resource into the parent scene instead of referencing the shared file. Use this when one scene needs different values than the shared default.

**Guideline:**
- Read-only data (item definitions, level config) — share freely, no duplication needed.
- Mutable runtime state (current health, active buffs) — always `duplicate()` in `_ready()`.

---

## 9. Saving Custom Resources

Use `ResourceSaver` to write Resources to disk at runtime (procedurally generated content, unlocked items, etc.).

### GDScript

```gdscript
func save_resource(res: Resource, path: String) -> bool:
    var err := ResourceSaver.save(res, path)
    if err != OK:
        push_error("Failed to save resource to '%s' — error %d" % [path, err])
        return false
    return true


# .tres — human-readable text, good for debugging and version control
save_resource(my_item, "user://generated/custom_sword.tres")

# .res — binary, smaller and faster to load, use in production builds
save_resource(my_item, "user://generated/custom_sword.res")
```

### C#

```csharp
public bool SaveResource(Resource res, string path)
{
    var err = ResourceSaver.Save(res, path);
    if (err != Error.Ok)
    {
        GD.PushError($"Failed to save resource to '{path}' — error {err}");
        return false;
    }
    return true;
}

// .tres — human-readable, for debugging and version control
SaveResource(myItem, "user://generated/custom_sword.tres");

// .res — binary, faster to load, use in production
SaveResource(myItem, "user://generated/custom_sword.res");
```

**Format guidance:**

| Format | Pros | Cons | Use When |
|---|---|---|---|
| `.tres` | Human-readable, diffable, debuggable | Larger file, slower to parse | Development, version control, user-editable files |
| `.res` | Compact binary, faster to load | Not human-readable | Production builds, shipped game data |

> **Security:** Never load `.tres` or `.res` files from untrusted sources (user uploads, downloaded mods). They can execute embedded GDScript. Use JSON for user-controlled data.

---

## 10. Anti-patterns

### Mutable shared Resources without `duplicate()` — accidental shared state

```gdscript
# BAD — all enemies share the same EnemyStats object.
# Damaging one enemy damages all of them.
class_name Enemy
extends CharacterBody2D

@export var stats: EnemyStats  # loaded from .tres, shared

func take_damage(amount: int) -> void:
    stats.health -= amount  # mutates the shared Resource!
```

```gdscript
# GOOD — each enemy owns its own copy.
func _ready() -> void:
    stats = stats.duplicate()  # now safe to mutate
```

### Game logic inside Resources

```gdscript
# BAD — Resources have no scene tree access, no _process, no signals from nodes.
class_name EnemyStats
extends Resource

func update_health_regen(delta: float) -> void:
    # Can't call get_tree(), can't read Input, can't access nodes.
    # This logic belongs in a Node.
    health = min(health + regen_rate * delta, max_health)
```

```gdscript
# GOOD — keep logic in Nodes, data in Resources.
# enemy.gd
func _process(delta: float) -> void:
    _current_health = minf(_current_health + stats.regen_rate * delta, stats.max_health)
```

### Giant monolithic Resources

```gdscript
# BAD — one Resource holds everything; impossible to reuse parts.
class_name GameConfig
extends Resource

@export var player_health: int
@export var player_speed: float
@export var enemy_goblin_health: int
@export var enemy_goblin_speed: float
@export var enemy_troll_health: int
# ... 200 more properties
```

```gdscript
# GOOD — small focused Resources, composed together.
class_name PlayerConfig
extends Resource

@export var health: int   = 100
@export var speed:  float = 200.0
```

```gdscript
class_name EnemyConfig
extends Resource

@export var health: int   = 50
@export var speed:  float = 80.0
```

---

## 11. Checklist

- [ ] Resource subclass uses `class_name` so the editor can find it for **New Resource**
- [ ] C# classes have `[GlobalClass]` attribute
- [ ] All Inspector-editable fields use `@export` / `[Export]`
- [ ] `@export_range` used on numeric fields with designer-tunable bounds
- [ ] `@export_group` and `@export_category` used to organize Inspector layout for Resources with many fields
- [ ] Per-instance mutable Resources are `duplicate()`-d in `_ready()`
- [ ] Read-only shared Resources (definitions, blueprints) are **not** duplicated
- [ ] Game logic (per-frame updates, scene queries) lives in Nodes, not Resources
- [ ] Large data sets split into focused single-responsibility Resources
- [ ] `.tres` used during development; `.res` considered for shipped production data
- [ ] `ResourceSaver.save()` return value checked and errors reported with `push_error()`
- [ ] `.tres` / `.res` files never loaded from untrusted external sources
