---
name: godot-testing
description: Use when writing tests for Godot projects — TDD workflow with GUT and gdUnit4, covers both GDScript and C#
---

# Godot Testing

This skill covers test-driven development (TDD) for Godot 4.3+ projects using GUT (Godot Unit Testing) and gdUnit4. It includes framework selection, full RED-GREEN-REFACTOR examples, test structure, running tests in CI, and common testing patterns.

> **Related skills:** **godot-code-review** for review checklists, **dependency-injection** for test-friendly architecture, **export-pipeline** for CI/CD test automation.

## Framework Selection

| Feature               | GUT                              | gdUnit4                           |
|-----------------------|----------------------------------|-----------------------------------|
| Language              | GDScript-first, limited C#       | GDScript + C# (first-class)       |
| Install               | AssetLib or git submodule        | AssetLib or git submodule         |
| Editor integration    | Built-in GUT panel               | Built-in inspector + panel        |
| Mocking               | `double()` / `stub()` API        | `mock()` / `spy()` API            |
| Scene testing         | `add_child_autofree()`           | `auto_free()` + scene runner      |
| CI support            | `gut_cmdln.gd` CLI script        | `gdunit4_runner` CLI script       |
| C# support            | Minimal (GDScript wrappers only) | Native C# assertions + lifecycle  |
| Maturity              | Established (Godot 3 + 4)        | Godot 4 focused, actively updated |
| Best for              | Pure GDScript projects           | Mixed GDScript/C# or C#-only      |

**Rule of thumb:** Use GUT for GDScript-only projects. Use gdUnit4 for C# projects or when you need first-class C# support and scene runner utilities.

---

## TDD Workflow: RED-GREEN-REFACTOR

### Step 1 — RED: Write a failing test

Write the test before the implementation exists. The test must fail for the right reason (missing class or wrong behavior — not a syntax error).

#### GDScript — GUT

```gdscript
# tests/unit/test_health_component.gd
extends GutTest

var _health: HealthComponent

func before_each() -> void:
    _health = HealthComponent.new()
    _health.max_health = 100
    add_child_autofree(_health)

func test_starts_at_max_health() -> void:
    assert_eq(_health.current_health, 100)

func test_take_damage_reduces_health() -> void:
    _health.take_damage(30)
    assert_eq(_health.current_health, 70)

func test_cannot_go_below_zero() -> void:
    _health.take_damage(200)
    assert_eq(_health.current_health, 0)

func test_heal_restores_health() -> void:
    _health.take_damage(50)
    _health.heal(20)
    assert_eq(_health.current_health, 70)

func test_heal_cannot_exceed_max() -> void:
    _health.heal(50)
    assert_eq(_health.current_health, 100)

func test_death_signal_emitted_at_zero() -> void:
    watch_signals(_health)
    _health.take_damage(100)
    assert_signal_emitted(_health, "died")
```

#### C# — gdUnit4

```csharp
// tests/unit/HealthComponentTest.cs
using Godot;
using GdUnit4;
using static GdUnit4.Assertions;

[TestSuite]
public partial class HealthComponentTest : GdUnit4.GdUnitTestSuite
{
    private HealthComponent _health = default!;

    [Before]
    public void Setup() { }

    [BeforeTest]
    public void BeforeTest()
    {
        _health = AutoFree(new HealthComponent());
        _health.MaxHealth = 100;
        AddChild(_health);
    }

    [TestCase]
    public void StartsAtMaxHealth()
        => AssertThat(_health.CurrentHealth).IsEqual(100);

    [TestCase]
    public void TakeDamageReducesHealth()
    {
        _health.TakeDamage(30);
        AssertThat(_health.CurrentHealth).IsEqual(70);
    }

    [TestCase]
    public void CannotGoBelowZero()
    {
        _health.TakeDamage(200);
        AssertThat(_health.CurrentHealth).IsEqual(0);
    }

    [TestCase]
    public void HealRestoresHealth()
    {
        _health.TakeDamage(50);
        _health.Heal(20);
        AssertThat(_health.CurrentHealth).IsEqual(70);
    }

    [TestCase]
    public void HealCannotExceedMax()
    {
        _health.Heal(50);
        AssertThat(_health.CurrentHealth).IsEqual(100);
    }

    [TestCase]
    public async GdUnitAwaiter DeathSignalEmittedAtZero()
    {
        var monitor = MonitorSignals(_health);
        _health.TakeDamage(100);
        await monitor.AwaitSignal("died").WithTimeout(500);
        AssertSignal(monitor).IsEmitted("died");
    }
}
```

---

### Step 2 — GREEN: Minimal implementation

Write only enough code to make the tests pass. Do not add features that have no test yet.

#### GDScript

```gdscript
# src/components/health_component.gd
class_name HealthComponent
extends Node

signal died
signal health_changed(old_value: int, new_value: int)

@export var max_health: int = 100
var current_health: int

func _ready() -> void:
    current_health = max_health

func take_damage(amount: int) -> void:
    var old := current_health
    current_health = maxi(0, current_health - amount)
    health_changed.emit(old, current_health)
    if current_health == 0:
        died.emit()

func heal(amount: int) -> void:
    var old := current_health
    current_health = mini(max_health, current_health + amount)
    health_changed.emit(old, current_health)
```

#### C#

```csharp
// src/components/HealthComponent.cs
using Godot;

public partial class HealthComponent : Node
{
    [Signal] public delegate void DiedEventHandler();
    [Signal] public delegate void HealthChangedEventHandler(int oldValue, int newValue);

    [Export] public int MaxHealth { get; set; } = 100;
    public int CurrentHealth { get; private set; }

    public override void _Ready()
    {
        CurrentHealth = MaxHealth;
    }

    public void TakeDamage(int amount)
    {
        int old = CurrentHealth;
        CurrentHealth = Mathf.Max(0, CurrentHealth - amount);
        EmitSignal(SignalName.HealthChanged, old, CurrentHealth);
        if (CurrentHealth == 0)
            EmitSignal(SignalName.Died);
    }

    public void Heal(int amount)
    {
        int old = CurrentHealth;
        CurrentHealth = Mathf.Min(MaxHealth, CurrentHealth + amount);
        EmitSignal(SignalName.HealthChanged, old, CurrentHealth);
    }
}
```

---

### Step 3 — REFACTOR: Improve without changing behavior

All tests must still pass after refactoring. Common refactors:

- Extract a `_set_health()` helper to remove duplication between `take_damage` and `heal`
- Add `@export_range(0, 9999)` to `max_health` for editor clamping
- Add `is_dead` computed property
- Validate negative inputs with `assert(amount >= 0)`

```gdscript
# Refactored GDScript — tests still pass unchanged
class_name HealthComponent
extends Node

signal died
signal health_changed(old_value: int, new_value: int)

@export_range(0, 9999) var max_health: int = 100
var current_health: int

var is_dead: bool:
    get: return current_health == 0

func _ready() -> void:
    current_health = max_health

func take_damage(amount: int) -> void:
    assert(amount >= 0, "Damage amount must be non-negative")
    _set_health(current_health - amount)

func heal(amount: int) -> void:
    assert(amount >= 0, "Heal amount must be non-negative")
    _set_health(current_health + amount)

func _set_health(new_value: int) -> void:
    var old := current_health
    current_health = clamp(new_value, 0, max_health)
    if current_health != old:
        health_changed.emit(old, current_health)
    if current_health == 0:
        died.emit()
```

---

## Test Directory Structure

```
res://
├── src/
│   └── components/
│       ├── health_component.gd
│       └── HealthComponent.cs
└── tests/
    ├── unit/
    │   ├── test_health_component.gd      # GUT: test_ prefix required
    │   └── HealthComponentTest.cs        # gdUnit4 C#: [TestSuite] attribute
    ├── integration/
    │   ├── test_player_scene.gd
    │   └── PlayerSceneTest.cs
    └── gut_config.json                   # GUT configuration (optional)
```

### Naming conventions

| Framework | GDScript file       | C# file              | Test method prefix/attribute |
|-----------|---------------------|----------------------|------------------------------|
| GUT       | `test_*.gd`         | N/A                  | `func test_*()`              |
| gdUnit4   | `test_*.gd`         | `*Test.cs`           | `func test_*()` / `[TestCase]` |

---

## Running Tests

### GUT CLI

```bash
# Run all tests
godot --headless -s addons/gut/gut_cmdln.gd

# Run a specific directory
godot --headless -s addons/gut/gut_cmdln.gd -gdir=res://tests/unit

# Run a specific file
godot --headless -s addons/gut/gut_cmdln.gd -gtest=res://tests/unit/test_health_component.gd

# Verbose output with log file
godot --headless -s addons/gut/gut_cmdln.gd -gdir=res://tests -glog=3 -goutput_dir=res://test_results
```

### gdUnit4 CLI

```bash
# Run all tests
godot --headless -s addons/gdUnit4/bin/GdUnit4CSharpApiLoader.cs -- --testsuites res://tests

# GDScript only
godot --headless -s addons/gdUnit4/GdUnitRunner.gd -- --testsuites res://tests/unit

# Run a specific test file
godot --headless -s addons/gdUnit4/GdUnitRunner.gd -- --testsuites res://tests/unit/test_health_component.gd

# With report output
godot --headless -s addons/gdUnit4/GdUnitRunner.gd -- --testsuites res://tests --report-dir ./reports
```

### GitHub Actions CI

```yaml
# .github/workflows/tests.yml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test-gut:
    name: GUT Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Godot
        uses: chickensoft-games/setup-godot@v2
        with:
          version: 4.3.0
          use-dotnet: false

      - name: Import project
        run: godot --headless --import 2>&1 | tail -5

      - name: Run GUT tests
        run: >
          godot --headless
          -s addons/gut/gut_cmdln.gd
          -gdir=res://tests
          -gexit
          -glog=2

  test-gdunit4:
    name: gdUnit4 Tests (GDScript + C#)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Godot with .NET
        uses: chickensoft-games/setup-godot@v2
        with:
          version: 4.3.0
          use-dotnet: true

      - name: Restore NuGet packages
        run: dotnet restore

      - name: Import project
        run: godot --headless --import 2>&1 | tail -5

      - name: Run gdUnit4 tests
        run: >
          godot --headless
          -s addons/gdUnit4/GdUnitRunner.gd
          --
          --testsuites res://tests
          --report-dir ./reports

      - name: Upload test report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-report
          path: reports/
```

---

## Testing Patterns

### Scenes with Nodes

Always use `add_child_autofree` (GUT) or `auto_free` (gdUnit4) so nodes are freed after each test. Never call `queue_free()` manually inside tests — it causes race conditions.

#### GUT

```gdscript
func before_each() -> void:
    # add_child_autofree: adds to scene tree AND frees after test
    var scene := preload("res://scenes/player.tscn")
    _player = add_child_autofree(scene.instantiate())

    # autofree: frees after test but does NOT add to scene tree
    _resource = autofree(MyResource.new())
```

#### gdUnit4 (GDScript)

```gdscript
func before_test() -> void:
    var scene := preload("res://scenes/player.tscn")
    _player = auto_free(scene.instantiate())
    add_child(_player)
```

#### gdUnit4 (C#)

```csharp
[BeforeTest]
public void BeforeTest()
{
    var scene = GD.Load<PackedScene>("res://scenes/player.tscn");
    _player = AutoFree(scene.Instantiate<Player>());
    AddChild(_player);
}
```

### Signal Testing

#### GUT

```gdscript
func test_health_emits_signal() -> void:
    watch_signals(_health)
    _health.take_damage(10)

    # Assert signal was emitted
    assert_signal_emitted(_health, "health_changed")

    # Assert signal was emitted with specific arguments
    assert_signal_emitted_with_parameters(_health, "health_changed", [100, 90])

    # Assert signal was NOT emitted
    assert_signal_not_emitted(_health, "died")
```

#### gdUnit4 (GDScript)

```gdscript
func test_health_emits_signal() -> void:
    var monitor := monitor_signals(_health)
    _health.take_damage(10)

    assert_signal(monitor).is_emitted("health_changed")
    assert_signal(monitor).is_emitted("health_changed").with_parameters([100, 90])
    assert_signal(monitor).is_not_emitted("died")
```

#### gdUnit4 (C#)

```csharp
[TestCase]
public async GdUnitAwaiter HealthEmitsSignal()
{
    var monitor = MonitorSignals(_health);
    _health.TakeDamage(10);

    AssertSignal(monitor).IsEmitted("health_changed");
    AssertSignal(monitor).IsEmitted("health_changed").WithArgs(100, 90);
    AssertSignal(monitor).IsNotEmitted("died");
    await Task.CompletedTask;
}
```

### Mocking / Doubling

Use doubles/mocks to isolate the unit under test from dependencies.

#### GUT — `double()` and `stub()`

```gdscript
func test_player_uses_health_component() -> void:
    # Create a test double (all methods stubbed to return null/0)
    var mock_health := double(HealthComponent)
    stub(mock_health, "take_damage")  # no-op stub
    stub(mock_health, "current_health").to_return(75)

    _player.health_component = mock_health
    _player.take_hit(25)

    # Verify the method was called
    assert_called(mock_health, "take_damage")
    assert_called_with_parameters(mock_health, "take_damage", [25])
```

#### gdUnit4 (GDScript) — `mock()`

```gdscript
func test_player_uses_health_component() -> void:
    var mock_health := mock(HealthComponent)
    do_return(75).on(mock_health).current_health

    _player.health_component = mock_health
    _player.take_hit(25)

    verify(mock_health).take_damage(25)
```

#### gdUnit4 (C#) — `Mock<T>()`

```csharp
[TestCase]
public void PlayerUsesHealthComponent()
{
    var mockHealth = Mock<HealthComponent>();
    mockHealth.MockProperty(h => h.CurrentHealth, 75);

    _player.HealthComponent = mockHealth;
    _player.TakeHit(25);

    Verify(mockHealth).TakeDamage(25);
}
```

### Waiting for Async Operations

#### GUT

```gdscript
func test_tween_completes() -> void:
    _player.start_move_tween()

    # Wait a fixed duration
    await wait_seconds(0.5)
    assert_eq(_player.position, Vector2(100, 0))

    # Wait a number of frames
    await wait_frames(10)
    assert_true(_player.tween_finished)
```

#### gdUnit4 (GDScript)

```gdscript
func test_tween_completes() -> void:
    _player.start_move_tween()
    await await_millis(500)
    assert_that(_player.position).is_equal(Vector2(100, 0))
```

#### gdUnit4 (C#)

```csharp
[TestCase(Timeout = 1000)]
public async GdUnitAwaiter TweenCompletes()
{
    _player.StartMoveTween();
    await ISceneRunner.SimulateFrames(30);
    AssertThat(_player.Position).IsEqual(new Vector2(100, 0));
}
```

---

## Common Assertions

### GUT assertions

| Assertion                                    | Description                        |
|----------------------------------------------|------------------------------------|
| `assert_eq(actual, expected)`                | Equality                           |
| `assert_ne(actual, expected)`                | Not equal                          |
| `assert_true(value)`                         | Is truthy                          |
| `assert_false(value)`                        | Is falsy                           |
| `assert_null(value)`                         | Is null                            |
| `assert_not_null(value)`                     | Is not null                        |
| `assert_gt(actual, expected)`                | Greater than                       |
| `assert_lt(actual, expected)`                | Less than                          |
| `assert_gte(actual, expected)`               | Greater than or equal              |
| `assert_lte(actual, expected)`               | Less than or equal                 |
| `assert_has(collection, item)`               | Collection contains item           |
| `assert_does_not_have(collection, item)`     | Collection does not contain item   |
| `assert_string_contains(str, sub)`           | String contains substring          |
| `assert_almost_eq(actual, expected, margin)` | Float equality within margin       |
| `assert_signal_emitted(obj, signal_name)`    | Signal was emitted                 |
| `assert_signal_not_emitted(obj, signal_name)`| Signal was not emitted             |

### gdUnit4 assertions (GDScript + C#)

| GDScript                                           | C#                                              | Description                     |
|----------------------------------------------------|-------------------------------------------------|---------------------------------|
| `assert_that(val).is_equal(exp)`                   | `AssertThat(val).IsEqual(exp)`                  | Equality                        |
| `assert_that(val).is_not_equal(exp)`               | `AssertThat(val).IsNotEqual(exp)`               | Not equal                       |
| `assert_that(val).is_true()`                       | `AssertThat(val).IsTrue()`                      | Is true                         |
| `assert_that(val).is_false()`                      | `AssertThat(val).IsFalse()`                     | Is false                        |
| `assert_that(val).is_null()`                       | `AssertThat(val).IsNull()`                      | Is null                         |
| `assert_that(val).is_not_null()`                   | `AssertThat(val).IsNotNull()`                   | Is not null                     |
| `assert_that(val).is_greater(exp)`                 | `AssertThat(val).IsGreater(exp)`                | Greater than                    |
| `assert_that(val).is_less(exp)`                    | `AssertThat(val).IsLess(exp)`                   | Less than                       |
| `assert_that(val).is_between(min, max)`            | `AssertThat(val).IsBetween(min, max)`           | In range (inclusive)            |
| `assert_that(arr).contains([a, b])`                | `AssertThat(arr).Contains(a, b)`                | Array contains elements         |
| `assert_that(str).contains("sub")`                 | `AssertThat(str).Contains("sub")`               | String contains substring       |
| `assert_that(val).is_approximately(exp, margin)`   | `AssertThat(val).IsApproximately(exp, margin)`  | Float within margin             |
| `assert_signal(mon).is_emitted("name")`            | `AssertSignal(mon).IsEmitted("name")`           | Signal emitted                  |

---

## What NOT to Test

Avoid testing things that add noise without catching real bugs:

- **Godot engine internals** — do not assert that `Node.add_child()` works or that `@export` variables show up in the editor
- **Private implementation details** — test behavior through the public API; if a refactor breaks a test that covers only private state, the test is wrong
- **Visual/rendering output** — pixel-level rendering results are brittle; test the data driving the visuals instead
- **Timing-sensitive floats without margins** — use `assert_almost_eq` / `IsApproximately` for physics values
- **One-liners that wrap a built-in** — a property getter that just returns a field needs no test
- **Every possible invalid input** — test the documented contract, not every imaginable misuse

---

## Checklist

- [ ] Each test file matches the naming convention for the chosen framework (`test_*.gd` / `*Test.cs`)
- [ ] Tests extend the correct base class (`GutTest` / `GdUnit4.GdUnitTestSuite`)
- [ ] Nodes added to the scene tree use `add_child_autofree` or `auto_free` — never manual `queue_free()`
- [ ] Signals are watched before the action that triggers them
- [ ] Mocks/doubles are used for external dependencies, not for the unit under test
- [ ] Each test covers exactly one behavior (one logical assertion per test)
- [ ] CI workflow runs tests headlessly on every push and PR
- [ ] Flaky async tests use explicit timeouts, not arbitrary sleep durations
- [ ] Tests pass before merging (RED is only acceptable while actively implementing)
