---
name: state-machine
description: Use when implementing state machines in Godot — enum-based, node-based, and resource-based FSM patterns with trade-offs
---

# State Machines in Godot 4.3+

Choose the right FSM pattern for your complexity level. All examples target Godot 4.3+ with no deprecated APIs.

> **Related skills:** **player-controller** for movement state integration, **ai-navigation** for AI state patterns, **resource-pattern** for resource-based state configuration.

---

## 1. Approach Comparison

| Approach       | Complexity | Best For                              |
|----------------|------------|---------------------------------------|
| Enum-Based     | Low        | Simple objects, fewer than 5 states   |
| Node-Based     | Medium     | Characters with complex behavior      |
| Resource-Based | High       | Data-driven or editor-configurable AI |

---

## 2. Approach 1: Enum-Based (Simplest)

Use when you have a small number of states and no significant enter/exit logic.

### GDScript

```gdscript
extends CharacterBody2D

enum State { IDLE, PATROL, CHASE, ATTACK }

@export var patrol_range: float = 200.0
@export var chase_range: float = 300.0
@export var attack_range: float = 50.0
@export var speed: float = 80.0

var current_state: State = State.IDLE
var patrol_target: Vector2 = Vector2.ZERO

@onready var player: Node2D = get_tree().get_first_node_in_group("player")


func _physics_process(delta: float) -> void:
	match current_state:
		State.IDLE:
			_state_idle()
		State.PATROL:
			_state_patrol()
		State.CHASE:
			_state_chase()
		State.ATTACK:
			_state_attack()

	move_and_slide()


func _state_idle() -> void:
	velocity = Vector2.ZERO
	if _player_in_range(chase_range):
		current_state = State.CHASE
	elif randf() < 0.005:
		patrol_target = global_position + Vector2(randf_range(-patrol_range, patrol_range), 0.0)
		current_state = State.PATROL


func _state_patrol() -> void:
	var direction := (patrol_target - global_position)
	if direction.length() < 4.0:
		current_state = State.IDLE
		return
	velocity = direction.normalized() * speed
	if _player_in_range(chase_range):
		current_state = State.CHASE


func _state_chase() -> void:
	if not is_instance_valid(player):
		current_state = State.IDLE
		return
	if _player_in_range(attack_range):
		current_state = State.ATTACK
		return
	if not _player_in_range(chase_range):
		current_state = State.PATROL
		return
	velocity = (player.global_position - global_position).normalized() * speed


func _state_attack() -> void:
	velocity = Vector2.ZERO
	if not _player_in_range(attack_range):
		current_state = State.CHASE


func _player_in_range(range: float) -> bool:
	if not is_instance_valid(player):
		return false
	return global_position.distance_to(player.global_position) <= range
```

### C# Equivalent

```csharp
using Godot;

public partial class SimpleEnemy : CharacterBody2D
{
    private enum State { Idle, Patrol, Chase, Attack }

    [Export] public float PatrolRange { get; set; } = 200f;
    [Export] public float ChaseRange  { get; set; } = 300f;
    [Export] public float AttackRange { get; set; } = 50f;
    [Export] public float Speed       { get; set; } = 80f;

    private State _currentState = State.Idle;
    private Vector2 _patrolTarget = Vector2.Zero;
    private Node2D _player;

    public override void _Ready()
    {
        _player = GetTree().GetFirstNodeInGroup("player") as Node2D;
    }

    public override void _PhysicsProcess(double delta)
    {
        switch (_currentState)
        {
            case State.Idle:   StateIdle();   break;
            case State.Patrol: StatePatrol(); break;
            case State.Chase:  StateChase();  break;
            case State.Attack: StateAttack(); break;
        }
        MoveAndSlide();
    }

    private void StateIdle()
    {
        Velocity = Vector2.Zero;
        if (PlayerInRange(ChaseRange))
        {
            _currentState = State.Chase;
        }
        else if (GD.Randf() < 0.005f)
        {
            _patrolTarget = GlobalPosition + new Vector2(GD.RandRange(-PatrolRange, PatrolRange), 0f);
            _currentState = State.Patrol;
        }
    }

    private void StatePatrol()
    {
        var direction = _patrolTarget - GlobalPosition;
        if (direction.Length() < 4f) { _currentState = State.Idle; return; }
        Velocity = direction.Normalized() * Speed;
        if (PlayerInRange(ChaseRange)) _currentState = State.Chase;
    }

    private void StateChase()
    {
        if (!IsInstanceValid(_player)) { _currentState = State.Idle; return; }
        if (PlayerInRange(AttackRange)) { _currentState = State.Attack; return; }
        if (!PlayerInRange(ChaseRange)) { _currentState = State.Patrol; return; }
        Velocity = (_player.GlobalPosition - GlobalPosition).Normalized() * Speed;
    }

    private void StateAttack()
    {
        Velocity = Vector2.Zero;
        if (!PlayerInRange(AttackRange)) _currentState = State.Chase;
    }

    private bool PlayerInRange(float range) =>
        IsInstanceValid(_player) && GlobalPosition.DistanceTo(_player.GlobalPosition) <= range;
}
```

> **When to upgrade away from enum-based:**
> - Enter/exit logic starts duplicating across state methods
> - Animation sync requires explicit enter/exit hooks
> - The `match`/`switch` block grows beyond ~100 lines

---

## 3. Approach 2: Node-Based (Recommended for Characters)

Each state is its own node. The `StateMachine` node delegates input and process calls to whichever state is active, and states trigger transitions by name.

### Scene Tree

```
Player (CharacterBody2D)
└── StateMachine (Node)
    ├── Idle  (State)
    ├── Run   (State)
    ├── Jump  (State)
    └── Attack (State)
```

### State Base Class

**GDScript (`state.gd`)**

```gdscript
class_name State
extends Node

## Populated by StateMachine._ready()
var entity: CharacterBody2D
var state_machine: StateMachine


## Called when this state becomes active.
func enter() -> void:
	pass


## Called when this state is deactivated.
func exit() -> void:
	pass


## Mirrors _process. Return a state name string to transition, or "" to stay.
func update(delta: float) -> String:
	return ""


## Mirrors _physics_process. Return a state name string to transition, or "".
func physics_update(delta: float) -> String:
	return ""


## Mirrors _unhandled_input.
func handle_input(event: InputEvent) -> String:
	return ""
```

**C# (`State.cs`)**

```csharp
using Godot;

public partial class State : Node
{
    /// Populated by StateMachine._Ready()
    public CharacterBody2D Entity { get; set; }
    public StateMachine StateMachine { get; set; }

    public virtual void Enter() { }
    public virtual void Exit() { }
    public virtual string Update(double delta) => string.Empty;
    public virtual string PhysicsUpdate(double delta) => string.Empty;
    public virtual string HandleInput(InputEvent @event) => string.Empty;
}
```

### StateMachine Class

**GDScript (`state_machine.gd`)**

```gdscript
class_name StateMachine
extends Node

@export var initial_state: State

var current_state: State
var states: Dictionary = {}


func _ready() -> void:
	for child in get_children():
		if child is State:
			states[child.name] = child
			child.entity = owner as CharacterBody2D
			child.state_machine = self

	if initial_state:
		current_state = initial_state
		current_state.enter()


func _unhandled_input(event: InputEvent) -> void:
	var next := current_state.handle_input(event)
	if next:
		transition_to(next)


func _process(delta: float) -> void:
	var next := current_state.update(delta)
	if next:
		transition_to(next)


func _physics_process(delta: float) -> void:
	var next := current_state.physics_update(delta)
	if next:
		transition_to(next)


func transition_to(state_name: String) -> void:
	if not states.has(state_name):
		push_error("StateMachine: unknown state '%s'" % state_name)
		return
	current_state.exit()
	current_state = states[state_name]
	current_state.enter()
```

**C# (`StateMachine.cs`)**

```csharp
using System.Collections.Generic;
using Godot;

public partial class StateMachine : Node
{
    [Export] public State InitialState { get; set; }

    public State CurrentState { get; private set; }
    private readonly Dictionary<string, State> _states = new();

    public override void _Ready()
    {
        foreach (var child in GetChildren())
        {
            if (child is State state)
            {
                _states[state.Name] = state;
                state.Entity = Owner as CharacterBody2D;
                state.StateMachine = this;
            }
        }

        if (InitialState != null)
        {
            CurrentState = InitialState;
            CurrentState.Enter();
        }
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        var next = CurrentState.HandleInput(@event);
        if (!string.IsNullOrEmpty(next)) TransitionTo(next);
    }

    public override void _Process(double delta)
    {
        var next = CurrentState.Update(delta);
        if (!string.IsNullOrEmpty(next)) TransitionTo(next);
    }

    public override void _PhysicsProcess(double delta)
    {
        var next = CurrentState.PhysicsUpdate(delta);
        if (!string.IsNullOrEmpty(next)) TransitionTo(next);
    }

    public void TransitionTo(string stateName)
    {
        if (!_states.TryGetValue(stateName, out var next))
        {
            GD.PushError($"StateMachine: unknown state '{stateName}'");
            return;
        }
        CurrentState.Exit();
        CurrentState = next;
        CurrentState.Enter();
    }
}
```

### Concrete Example: IdleState

**GDScript (`idle_state.gd`)**

```gdscript
class_name IdleState
extends State


func enter() -> void:
	entity.get_node("AnimationPlayer").play("idle")


func physics_update(delta: float) -> String:
	if not entity.is_on_floor():
		return "Jump"
	if Input.get_axis("move_left", "move_right") != 0.0:
		return "Run"
	return ""


func handle_input(event: InputEvent) -> String:
	if event.is_action_pressed("jump") and entity.is_on_floor():
		return "Jump"
	if event.is_action_pressed("attack"):
		return "Attack"
	return ""
```

---

## 4. Approach 3: Resource-Based (Data-Driven)

Use when designers need to configure states in the Godot Inspector without modifying code.

### StateData Resource

```gdscript
class_name StateData
extends Resource

@export var state_name: String = ""
@export var animation_name: String = ""
@export var move_speed: float = 0.0
@export var can_transition_to: Array[String] = []
```

Export an `Array[StateData]` on your AI controller. Designers populate each entry in the Inspector — no code changes needed to tune behavior or add states. The runtime reads `can_transition_to` to validate transitions and picks `animation_name` / `move_speed` for each active state.

---

## 5. Hierarchical and Parallel State Machines

When a single flat FSM grows beyond 8–10 states, or when separate concerns (movement, combat, animation) create a combinatorial explosion, split into hierarchical or parallel machines.

### The Problem: State Explosion

A character with 3 movement states (idle, walk, run) and 3 combat states (none, attack, block) creates 9 combined states in a flat FSM. Add crouching and that's 18. Hierarchical/parallel machines keep it at 3 + 3 = 6.

### Approach A: Hierarchical (Nested State Machines)

States can contain sub-state machines. The outer machine handles high-level states; inner machines handle details.

**Scene Tree:**

```
Player (CharacterBody2D)
└── StateMachine (handles: OnGround, InAir, Climbing)
    ├── OnGround (contains sub-states: Idle, Walk, Run, Crouch)
    │   └── SubStateMachine
    │       ├── Idle
    │       ├── Walk
    │       ├── Run
    │       └── Crouch
    ├── InAir (contains sub-states: Jump, Fall, DoubleJump)
    │   └── SubStateMachine
    │       ├── Jump
    │       ├── Fall
    │       └── DoubleJump
    └── Climbing
```

**GDScript — Hierarchical State (extends the Node-based State from Section 3):**

```gdscript
# hierarchical_state.gd — a state that owns a sub-state machine
class_name HierarchicalState
extends State

@export var sub_state_machine: StateMachine

func enter() -> void:
	if sub_state_machine:
		sub_state_machine.set_physics_process(true)
		sub_state_machine.set_process(true)
		# Sub-machine starts from its initial state
		sub_state_machine.current_state.enter()

func exit() -> void:
	if sub_state_machine:
		sub_state_machine.current_state.exit()
		sub_state_machine.set_physics_process(false)
		sub_state_machine.set_process(false)

func physics_update(delta: float) -> String:
	# Check for transitions OUT of this hierarchical state first
	if not entity.is_on_floor():
		return "InAir"
	# Otherwise, let the sub-machine handle it internally
	return ""
```

**C# — Hierarchical State:**

```csharp
public partial class HierarchicalState : State
{
    [Export] public StateMachine SubStateMachine { get; set; }

    public override void Enter()
    {
        if (SubStateMachine != null)
        {
            SubStateMachine.SetPhysicsProcess(true);
            SubStateMachine.SetProcess(true);
            SubStateMachine.CurrentState.Enter();
        }
    }

    public override void Exit()
    {
        if (SubStateMachine != null)
        {
            SubStateMachine.CurrentState.Exit();
            SubStateMachine.SetPhysicsProcess(false);
            SubStateMachine.SetProcess(false);
        }
    }

    public override string PhysicsUpdate(double delta)
    {
        if (!Entity.IsOnFloor()) return "InAir";
        return string.Empty;
    }
}
```

### Approach B: Parallel State Machines

Run multiple independent state machines simultaneously. Each handles a different concern.

**Scene Tree:**

```
Player (CharacterBody2D)
├── MovementSM (StateMachine: Idle, Walk, Run, Jump, Fall)
├── CombatSM   (StateMachine: None, Attack, Block, Dodge)
└── AnimationSM (StateMachine: reads from Movement + Combat to pick animation)
```

**GDScript — Parallel machines on a character:**

```gdscript
extends CharacterBody2D

@onready var movement_sm: StateMachine = $MovementSM
@onready var combat_sm: StateMachine = $CombatSM

func _physics_process(delta: float) -> void:
	# Both machines update independently each frame.
	# The StateMachine class (Section 3) handles its own _physics_process.
	# Movement and combat don't interfere with each other.
	move_and_slide()

func get_animation_name() -> String:
	# Combine states to pick the right animation
	var move_state: String = movement_sm.current_state.name
	var combat_state: String = combat_sm.current_state.name

	if combat_state == "Attack":
		return "attack"  # combat overrides movement animation
	match move_state:
		"Run":
			return "run"
		"Jump", "Fall":
			return "air"
		_:
			return "idle"
```

**C#:**

```csharp
public partial class ParallelPlayer : CharacterBody2D
{
    private StateMachine _movementSM;
    private StateMachine _combatSM;

    public override void _Ready()
    {
        _movementSM = GetNode<StateMachine>("MovementSM");
        _combatSM = GetNode<StateMachine>("CombatSM");
    }

    public override void _PhysicsProcess(double delta)
    {
        MoveAndSlide();
    }

    public string GetAnimationName()
    {
        string moveState = _movementSM.CurrentState.Name;
        string combatState = _combatSM.CurrentState.Name;

        if (combatState == "Attack") return "attack";
        return moveState switch
        {
            "Run" => "run",
            "Jump" or "Fall" => "air",
            _ => "idle"
        };
    }
}
```

### Which to Choose

| Pattern | Use When |
|---------|----------|
| **Flat FSM** | ≤ 8 states, single concern |
| **Hierarchical** | States naturally nest (OnGround has sub-states), transitions exist between top-level groups |
| **Parallel** | Independent concerns (movement + combat + animation), no nesting relationship |

---

## 6. Decision Flowchart

```
Start
  │
  ▼
Fewer than 5 states?
  ├─ Yes ──────────────────────────────────► Enum-Based
  └─ No
       │
       ▼
     Multiple independent concerns
     (movement + combat + animation)?
       ├─ Yes ──────────────────────────────► Parallel State Machines
       └─ No
            │
            ▼
          States naturally nest
          (sub-states within states)?
            ├─ Yes ────────────────────────► Hierarchical State Machine
            └─ No
                 │
                 ▼
               Designers need to configure
               states in the Inspector?
                 ├─ Yes ──────────────────► Resource-Based
                 └─ No ──────────────────► Node-Based
```

---

## 7. Implementation Checklist

- [ ] Chose the approach that matches actual complexity (enum / node / resource)
- [ ] Every state has explicit `enter()` and `exit()` methods (or equivalent)
- [ ] All transitions are named explicitly — no implicit fallthrough between states
- [ ] Animations are started in `enter()` and cleaned up in `exit()` where needed
- [ ] No circular transition loops that could cause infinite recursion in a single frame
- [ ] Flat FSM is replaced with hierarchical or parallel when states exceed ~8 or span multiple concerns
- [ ] Parallel state machines don't modify the same state (e.g., both setting velocity) — one concern per machine
