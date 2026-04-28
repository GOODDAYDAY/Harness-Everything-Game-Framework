---
name: dependency-injection
description: Use when managing dependencies between systems — autoloads, service locators, @export injection, and scene injection patterns
---

# Dependency Injection in Godot 4.3+

Patterns for wiring dependencies between systems so nodes stay loosely coupled, swappable, and testable. All examples target Godot 4.3+ with no deprecated APIs.

> **Related skills:** **godot-testing** for test-friendly architecture, **event-bus** for signal-based decoupling, **godot-project-setup** for autoload registration.

---

## 1. The Problem

Tight coupling makes code hard to test, extend, and swap. The most common form in Godot is reaching directly into a global autoload from everywhere in the codebase.

```gdscript
# BAD — tight coupling via direct autoload access scattered everywhere

# player.gd
func take_damage(amount: int) -> void:
    health -= amount
    AudioManager.play_sfx("hurt")          # hard dependency on AudioManager
    UIManager.update_health_bar(health)    # hard dependency on UIManager
    if health <= 0:
        GameState.record_death()           # hard dependency on GameState

# enemy.gd
func attack() -> void:
    AudioManager.play_sfx("attack")        # same AudioManager dependency again
```

**Problems with this approach:**

- Every node that calls `AudioManager` directly is coupled to its concrete implementation.
- Swapping `AudioManager` for a different implementation requires changing every caller.
- Unit-testing `Player` in isolation is impossible — `AudioManager`, `UIManager`, and `GameState` must all exist and be valid.
- Autoload initialization order bugs silently break behaviour when scenes load.
- Hidden dependencies make it hard to see what a class actually needs to function.

---

## 2. Approach Comparison

| Pattern | Complexity | Testability | Best For |
|---|---|---|---|
| **Autoloads** | Low | Low | Truly global singletons: audio, settings, platform services |
| **@export Injection** | Low | High | Most nodes — wire deps in the editor, no runtime lookup needed |
| **Service Locator** | Medium | Medium | Plugins, optional systems, swappable implementations at runtime |
| **Scene Injection** | Low | High | Parent-to-child wiring: Level sets up Enemy, HUD sets up sub-panels |

---

## 3. Autoloads as Singletons

Autoloads are appropriate for services that are **genuinely global** and have **no meaningful test double** (e.g., audio playback, OS settings, platform APIs). Avoid using them as a dumping ground for any shared state.

**When appropriate:**
- Audio mixer / SFX player
- User settings / ConfigFile wrapper
- Platform-specific services (achievements, IAP)
- Scene transition manager

**Dangers:**
- Hidden dependencies — callers do not declare what they need
- Autoload ordering bugs — A depends on B, but B isn't ready yet
- Test difficulty — autoloads must be fully operational during unit tests

### GDScript (`autoloads/audio_manager.gd`)

```gdscript
extends Node

## Plays a one-shot sound effect by key.
func play_sfx(key: String) -> void:
    var stream: AudioStream = _sfx_library.get(key)
    if stream == null:
        push_warning("AudioManager: unknown sfx key '%s'" % key)
        return
    var player := AudioStreamPlayer.new()
    player.stream = stream
    player.finished.connect(player.queue_free)
    add_child(player)
    player.play()


## Plays background music, crossfading from the current track.
func play_music(key: String, crossfade_time: float = 0.5) -> void:
    pass  # implementation omitted for brevity


var _sfx_library: Dictionary = {}


func _ready() -> void:
    _load_sfx_library()


func _load_sfx_library() -> void:
    # Populate _sfx_library from a Resource or folder scan
    pass
```

### C# (`Autoloads/AudioManager.cs`)

```csharp
using Godot;
using System.Collections.Generic;

/// <summary>
/// Global audio service. Register as autoload named "AudioManager".
/// </summary>
public partial class AudioManager : Node
{
    private readonly Dictionary<string, AudioStream> _sfxLibrary = new();

    public override void _Ready()
    {
        LoadSfxLibrary();
    }

    /// <summary>Plays a one-shot sound effect by key.</summary>
    public void PlaySfx(string key)
    {
        if (!_sfxLibrary.TryGetValue(key, out AudioStream stream))
        {
            GD.PushWarning($"AudioManager: unknown sfx key '{key}'");
            return;
        }

        var player = new AudioStreamPlayer { Stream = stream };
        player.Finished += player.QueueFree;
        AddChild(player);
        player.Play();
    }

    private void LoadSfxLibrary()
    {
        // Populate _sfxLibrary from a Resource or folder scan
    }
}
```

---

## 4. @export Node Injection

The most Godot-idiomatic DI pattern. Declare a dependency as `@export` and wire it in the editor Inspector — or assign it from a parent in code. The node never needs to know *where* its dependency lives in the tree.

This is preferred over `get_node("../../SomeNode")` hard-coded paths, which break silently when the scene tree is reorganised.

### GDScript

```gdscript
# health_component.gd — receives its audio dependency via @export
class_name HealthComponent
extends Node

@export var audio: AudioManager          ## Set in the Inspector or by parent
@export var max_health: int = 100

var current_health: int


func _ready() -> void:
    current_health = max_health


func take_damage(amount: int) -> void:
    current_health = clampi(current_health - amount, 0, max_health)
    # Uses the injected reference — no direct autoload access
    if audio != null:
        audio.play_sfx("hurt")
    health_changed.emit(current_health, max_health)
    if current_health == 0:
        died.emit()


signal health_changed(current: int, maximum: int)
signal died
```

```gdscript
# player.gd — wires the component in the editor or in _ready()
extends CharacterBody2D

@export var health: HealthComponent      ## Drag HealthComponent node here in Inspector
```

### C#

```csharp
using Godot;

/// <summary>
/// Reusable health component. Wire dependencies via the Inspector.
/// </summary>
public partial class HealthComponent : Node
{
    [Export] public AudioManager Audio { get; set; }   // Set in Inspector or by parent
    [Export] public int MaxHealth { get; set; } = 100;

    [Signal] public delegate void HealthChangedEventHandler(int current, int maximum);
    [Signal] public delegate void DiedEventHandler();

    private int _currentHealth;

    public override void _Ready()
    {
        _currentHealth = MaxHealth;
    }

    public void TakeDamage(int amount)
    {
        _currentHealth = Mathf.Clamp(_currentHealth - amount, 0, MaxHealth);
        Audio?.PlaySfx("hurt");
        EmitSignal(SignalName.HealthChanged, _currentHealth, MaxHealth);
        if (_currentHealth == 0)
            EmitSignal(SignalName.Died);
    }
}
```

```csharp
using Godot;

public partial class Player : CharacterBody2D
{
    // Drag HealthComponent node here in the Inspector
    [Export] public HealthComponent Health { get; set; }
}
```

---

## 5. Service Locator Pattern

A Service Locator is an autoload that acts as a runtime registry. Systems register themselves by name; consumers retrieve them by name. Unlike direct autoload access, the locator is the *only* hard dependency — everything else is swappable.

Useful for:
- Plugin architectures where systems opt in at runtime
- Swapping real implementations for stubs in tests
- Optional systems (e.g., analytics) that may or may not be present

### GDScript (`autoloads/service_locator.gd`)

```gdscript
extends Node

var _services: Dictionary = {}


## Registers a service under [param service_name].
## Call from the service's own _ready().
func register(service_name: String, instance: Object) -> void:
    if _services.has(service_name):
        push_warning("ServiceLocator: overwriting existing service '%s'" % service_name)
    _services[service_name] = instance


## Removes a service registration. Call from _exit_tree() of the service.
func unregister(service_name: String) -> void:
    _services.erase(service_name)


## Returns the service registered under [param service_name], or null.
## Cast the result to the expected type at the call site.
func get_service(service_name: String) -> Object:
    if not _services.has(service_name):
        push_warning("ServiceLocator: no service registered for '%s'" % service_name)
        return null
    return _services[service_name]


## Typed convenience helper — returns null and warns if the cast fails.
func get_typed(service_name: String, expected_type: Variant) -> Variant:
    var svc: Object = get_service(service_name)
    if svc == null:
        return null
    if not is_instance_of(svc, expected_type):
        push_warning(
            "ServiceLocator: '%s' is not an instance of %s" % [service_name, expected_type]
        )
        return null
    return svc
```

```gdscript
# audio_service.gd — self-registers on ready
extends Node
class_name AudioService

func _ready() -> void:
    ServiceLocator.register("audio", self)

func _exit_tree() -> void:
    ServiceLocator.unregister("audio")

func play_sfx(key: String) -> void:
    pass  # implementation


# consumer.gd — retrieves the service at runtime
func _ready() -> void:
    var audio := ServiceLocator.get_typed("audio", AudioService) as AudioService
    if audio != null:
        audio.play_sfx("pickup")
```

### C# (`Autoloads/ServiceLocator.cs`)

```csharp
using Godot;
using System.Collections.Generic;

/// <summary>
/// Runtime service registry. Register as autoload named "ServiceLocator".
/// </summary>
public partial class ServiceLocator : Node
{
    private readonly Dictionary<string, GodotObject> _services = new();

    /// <summary>Registers a service under <paramref name="serviceName"/>.</summary>
    public void Register(string serviceName, GodotObject instance)
    {
        if (_services.ContainsKey(serviceName))
            GD.PushWarning($"ServiceLocator: overwriting existing service '{serviceName}'");
        _services[serviceName] = instance;
    }

    /// <summary>Removes a service registration.</summary>
    public void Unregister(string serviceName) => _services.Remove(serviceName);

    /// <summary>Returns the service or null, with a warning if missing.</summary>
    public GodotObject GetService(string serviceName)
    {
        if (!_services.TryGetValue(serviceName, out var service))
        {
            GD.PushWarning($"ServiceLocator: no service registered for '{serviceName}'");
            return null;
        }
        return service;
    }

    /// <summary>Typed retrieval — returns null and warns on type mismatch.</summary>
    public T GetService<T>(string serviceName) where T : GodotObject
    {
        var service = GetService(serviceName);
        if (service is T typed)
            return typed;
        if (service != null)
            GD.PushWarning($"ServiceLocator: '{serviceName}' is not of type {typeof(T).Name}");
        return null;
    }
}
```

```csharp
using Godot;

// AudioService.cs — self-registers
public partial class AudioService : Node
{
    public override void _Ready()
    {
        GetNode<ServiceLocator>("/root/ServiceLocator").Register("audio", this);
    }

    public override void _ExitTree()
    {
        GetNode<ServiceLocator>("/root/ServiceLocator").Unregister("audio");
    }

    public void PlaySfx(string key) { /* implementation */ }
}

// Consumer.cs — typed retrieval
public partial class Pickup : Area2D
{
    public override void _Ready()
    {
        var audio = GetNode<ServiceLocator>("/root/ServiceLocator")
            .GetService<AudioService>("audio");
        audio?.PlaySfx("pickup");
    }
}
```

---

## 6. Scene Injection

A parent scene constructs or loads its children and sets their dependencies in `_ready()`. Children declare what they need via `@export` properties or setter methods; the parent fills them in. Children stay free of hard-coded paths.

**Example: Level injects the player reference into all Enemy children.**

### GDScript

```gdscript
# enemy.gd — declares its dependency; does not go looking for the player
class_name Enemy
extends CharacterBody2D

## Set by the Level scene in _ready(). Enemy will not search for the player itself.
var player: CharacterBody2D = null


func _physics_process(delta: float) -> void:
    if player == null:
        return
    # Move toward the injected player reference
    var direction := (player.global_position - global_position).normalized()
    velocity = direction * 120.0
    move_and_slide()
```

```gdscript
# level.gd — owns both Player and Enemies; injects the reference
extends Node2D

@onready var player: CharacterBody2D = $Player


func _ready() -> void:
    # Inject the player reference into every enemy in the Enemies group
    for enemy in get_tree().get_nodes_in_group("enemies"):
        if enemy is Enemy:
            enemy.player = player
```

### C#

```csharp
using Godot;

// Enemy.cs — receives its dependency; does not search the tree
public partial class Enemy : CharacterBody2D
{
    /// <summary>Set by the Level scene in _Ready(). Do not call GetNode here.</summary>
    public CharacterBody2D Player { get; set; }

    public override void _PhysicsProcess(double delta)
    {
        if (Player == null) return;

        Vector2 direction = (Player.GlobalPosition - GlobalPosition).Normalized();
        Velocity = direction * 120f;
        MoveAndSlide();
    }
}
```

```csharp
using Godot;

// Level.cs — owns Player and Enemies; wires the dependency
public partial class Level : Node2D
{
    private CharacterBody2D _player;

    public override void _Ready()
    {
        _player = GetNode<CharacterBody2D>("Player");

        foreach (Node node in GetTree().GetNodesInGroup("enemies"))
        {
            if (node is Enemy enemy)
                enemy.Player = _player;
        }
    }
}
```

---

## 7. Testing with Dependency Injection

Injectable dependencies make tests trivial: swap the real service for a stub or mock. Because the node declares what it needs (via `@export` or a property), tests can provide a controlled stand-in without touching autoloads.

### GDScript (using GUT)

```gdscript
# stub_audio.gd — a lightweight stand-in for AudioManager
class_name StubAudio
extends Node

var last_sfx: String = ""
var play_count: int = 0

func play_sfx(key: String) -> void:
    last_sfx = key
    play_count += 1
```

```gdscript
# test_health_component.gd
extends GutTest

var health: HealthComponent
var audio_stub: StubAudio


func before_each() -> void:
    audio_stub = StubAudio.new()
    add_child_autofree(audio_stub)

    health = preload("res://components/health_component.tscn").instantiate()
    health.audio = audio_stub   # inject the stub — no real AudioManager needed
    health.max_health = 100
    add_child_autofree(health)


func test_take_damage_plays_hurt_sfx() -> void:
    health.take_damage(10)

    assert_eq(audio_stub.last_sfx, "hurt")
    assert_eq(audio_stub.play_count, 1)


func test_no_sfx_when_audio_is_null() -> void:
    health.audio = null   # also valid — null is handled gracefully
    health.take_damage(10)
    pass  # should not crash


func test_died_signal_emitted_at_zero_health() -> void:
    watch_signals(health)
    health.take_damage(100)
    assert_signal_emitted(health, "died")
```

---

## 8. When to Use What

| Situation | Recommended Pattern |
|---|---|
| Service used by nearly every node in every scene | Autoload singleton |
| Node needs 1–3 deps, scene is editor-authored | `@export` injection |
| System is optional or swappable at runtime | Service Locator |
| Parent scene constructs children and knows their needs | Scene injection |
| Writing tests for a node with external dependencies | `@export` or property injection + stubs |
| Plugin that must work in any project | Service Locator (self-registers, no assumptions) |
| Two sibling nodes need the same dep | Let their parent hold it and inject downward |

**Quick decision guide:**

```
Does every scene in the project need it?
  YES → Autoload singleton
  NO  ↓

Is the dependency known at edit-time and wired in the Inspector?
  YES → @export injection
  NO  ↓

Does the dependency need to be swapped at runtime (plugins, A/B testing)?
  YES → Service Locator
  NO  ↓

Does a parent scene own both the consumer and the dependency?
  YES → Scene injection
  NO  → Reconsider — either promote to autoload or restructure ownership
```

---

## 9. Anti-patterns

### Autoload for everything

```gdscript
# BAD — GameManager, EnemySpawner, InventorySystem, DialogueSystem all as autoloads.
# Every node in the game is coupled to every other system at module level.
# Test one component → must initialise all autoloads.

# GOOD — Only AudioManager, Settings, and SceneTransition are autoloads.
# EnemySpawner is a node in the Level scene, injected into enemies that need it.
```

### Deep dependency chains

```gdscript
# BAD — Player needs HealthComponent, which needs AudioManager,
# which needs SoundBank, which needs FileSystem...
# A change deep in the chain breaks everything above it.

# GOOD — flatten: HealthComponent takes only AudioManager (or a narrow interface).
# Each node declares only immediate dependencies.
```

### Circular dependencies

```gdscript
# BAD
# PlayerController._ready() calls ServiceLocator.get_service("inventory")
# InventorySystem._ready() calls ServiceLocator.get_service("player")
# Neither can fully initialise because the other isn't ready yet.

# GOOD — break the cycle with a signal.
# InventorySystem emits item_used; PlayerController connects to it.
# PlayerController never holds a reference to InventorySystem at all.
```

### Service Locator as a god object

```gdscript
# BAD — everything is registered: enemies, UI panels, individual nodes.
# ServiceLocator becomes a second, untyped scene tree.

# GOOD — only register stable, long-lived services (audio, analytics, save system).
# Short-lived nodes are wired by their parent via scene injection.
```

### Forgetting null checks after injection

```gdscript
# BAD — crashes if the @export was never set in the editor
func take_damage(amount: int) -> void:
    audio.play_sfx("hurt")   # NullReferenceError if audio was not wired

# GOOD — guard or assert clearly
func take_damage(amount: int) -> void:
    assert(audio != null, "HealthComponent: audio dependency was not injected")
    audio.play_sfx("hurt")

# OR — treat it as optional
func take_damage(amount: int) -> void:
    if audio != null:
        audio.play_sfx("hurt")
```

---

## 10. Checklist

- [ ] Autoloads are used only for genuinely global services (audio, settings, platform)
- [ ] Nodes declare their dependencies explicitly (`@export` or a public property) rather than calling `get_node` on distant relatives
- [ ] `@export` fields are validated (`assert` or null check) before use
- [ ] Service Locator services call `unregister` in `_exit_tree()` / `_ExitTree()`
- [ ] Scene injection is done in the parent's `_ready()`, after children are fully initialised
- [ ] No circular dependencies between services or autoloads
- [ ] Each node depends only on its immediate collaborators — no deep chains
- [ ] Test stubs/mocks are plain nodes that implement the same interface as the real service
- [ ] C# `@export` (`[Export]`) dependencies are disconnected / cleared in `_ExitTree()` if they hold event subscriptions
- [ ] Service Locator is not used to store scene-specific or short-lived nodes
