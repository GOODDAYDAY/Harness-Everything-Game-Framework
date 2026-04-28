---
name: ai-navigation
description: Use when implementing AI movement — NavigationAgent2D/3D, steering behaviors, behavior trees, and patrol patterns
---

# AI Navigation in Godot 4.3+

Cover NavigationAgent2D/3D, steering behaviors, behavior trees, and patrol patterns. All examples target Godot 4.3+ with no deprecated APIs.

> **Related skills:** **state-machine** for AI state management, **component-system** for modular AI behaviors, **player-controller** for movement physics patterns.

---

## 1. Navigation Setup

### Scene Structure

```
World (Node2D or Node3D)
└── NavigationRegion2D (or NavigationRegion3D)
    ├── TileMapLayer / StaticBody2D (geometry)
    └── Enemy (CharacterBody2D with NavigationAgent2D child)
```

### NavigationRegion2D / NavigationRegion3D

1. Add a **NavigationRegion2D** (or **NavigationRegion3D**) node to your scene.
2. Assign a **NavigationPolygon** (2D) or **NavigationMesh** (3D) resource to it.
3. Draw the walkable area in the NavigationPolygon editor, or configure the NavigationMesh bounds in 3D.
4. **Bake the mesh at edit time:** select the NavigationRegion node → click **Bake NavigationPolygon** (2D) or **Bake NavigationMesh** (3D) in the toolbar.
5. **Bake at runtime** when the world changes dynamically:

```gdscript
# 2D
$NavigationRegion2D.bake_navigation_polygon()

# 3D
$NavigationRegion3D.bake_navigation_mesh()
```

```csharp
// 2D
GetNode<NavigationRegion2D>("NavigationRegion2D").BakeNavigationPolygon();

// 3D
GetNode<NavigationRegion3D>("NavigationRegion3D").BakeNavigationMesh();
```

### Async Navigation Baking (Godot 4.4+)

Navigation baking can cause frame drops on large maps. Godot 4.4 supports baking on a background thread:

```gdscript
# 2D — bake on a background thread
func rebake_async() -> void:
	var nav_region: NavigationRegion2D = $NavigationRegion2D
	# Connect to know when baking finishes
	NavigationServer2D.bake_from_source_geometry_data_async(
		nav_region.navigation_polygon,
		NavigationMeshSourceGeometryData2D.new()
	)
	# Or use the region's built-in signal:
	nav_region.bake_finished.connect(_on_bake_finished, CONNECT_ONE_SHOT)
	nav_region.bake_navigation_polygon(true)  # true = use thread

func _on_bake_finished() -> void:
	print("Navigation mesh ready")
```

```gdscript
# 3D — bake on a background thread
func rebake_async_3d() -> void:
	var nav_region: NavigationRegion3D = $NavigationRegion3D
	nav_region.bake_finished.connect(_on_bake_finished_3d, CONNECT_ONE_SHOT)
	nav_region.bake_navigation_mesh(true)  # true = use thread

func _on_bake_finished_3d() -> void:
	print("3D navigation mesh ready")
```

```csharp
// 3D — bake on a background thread
public void RebakeAsync3D()
{
    var navRegion = GetNode<NavigationRegion3D>("NavigationRegion3D");
    navRegion.BakeFinished += OnBakeFinished;
    navRegion.BakeNavigationMesh(true); // true = use thread
}

private void OnBakeFinished()
{
    GD.Print("3D navigation mesh ready");
}
```

> **When to use async baking:** Procedurally generated levels, destructible terrain, or any scene where the navigation mesh must be rebuilt at runtime. The game continues running while the mesh bakes.

### Navigation Layers

Navigation layers let you separate walkable areas for different agent types (ground troops, flying units, large enemies).

```gdscript
# Assign layer bits on the NavigationRegion (Inspector or code)
# Layer 1 = ground, Layer 2 = air, Layer 3 = large

# On the NavigationAgent, set matching layers:
$NavigationAgent2D.navigation_layers = 1   # ground only
$NavigationAgent2D.navigation_layers = 2   # air only
$NavigationAgent2D.navigation_layers = 1 | 2  # both (bitwise OR)
```

```csharp
// Assign layer bits on the NavigationRegion (Inspector or code)
// Layer 1 = ground, Layer 2 = air, Layer 3 = large

var navAgent = GetNode<NavigationAgent2D>("NavigationAgent2D");
navAgent.NavigationLayers = 1;       // ground only
navAgent.NavigationLayers = 2;       // air only
navAgent.NavigationLayers = 1 | 2;   // both (bitwise OR)
```

> Set `navigation_layers` on both the **NavigationRegion** and the **NavigationAgent** so they match. Mismatched layers are one of the most common reasons an agent finds no path.

---

## 2. NavigationAgent2D Basic Usage

### GDScript

```gdscript
extends CharacterBody2D

@export var speed: float = 120.0

@onready var nav_agent: NavigationAgent2D = $NavigationAgent2D


func _ready() -> void:
	# velocity_computed fires when avoidance calculates a safe velocity
	nav_agent.velocity_computed.connect(_on_velocity_computed)


func _physics_process(delta: float) -> void:
	if nav_agent.is_navigation_finished():
		return

	var next_pos: Vector2 = nav_agent.get_next_path_position()
	var direction: Vector2 = (next_pos - global_position).normalized()
	var desired_velocity: Vector2 = direction * speed

	if nav_agent.avoidance_enabled:
		# Hand desired velocity to the avoidance system; wait for the signal
		nav_agent.velocity = desired_velocity
	else:
		velocity = desired_velocity
		move_and_slide()


func _on_velocity_computed(safe_velocity: Vector2) -> void:
	velocity = safe_velocity
	move_and_slide()


func set_target(target_pos: Vector2) -> void:
	nav_agent.target_position = target_pos
```

**Key NavigationAgent2D properties:**

| Property | Purpose |
|---|---|
| `target_position` | World-space destination |
| `path_desired_distance` | How close to each waypoint counts as reached (default 1) |
| `target_desired_distance` | How close to the final target counts as finished (default 10) |
| `avoidance_enabled` | Enable RVO obstacle avoidance |
| `radius` | Agent collision radius for avoidance |
| `time_horizon_agents` | Seconds of avoidance look-ahead (tune to reduce jitter) |

### C#

```csharp
using Godot;

public partial class Enemy2D : CharacterBody2D
{
    [Export] public float Speed { get; set; } = 120f;

    private NavigationAgent2D _navAgent;

    public override void _Ready()
    {
        _navAgent = GetNode<NavigationAgent2D>("NavigationAgent2D");
        _navAgent.VelocityComputed += OnVelocityComputed;
    }

    public override void _PhysicsProcess(double delta)
    {
        if (_navAgent.IsNavigationFinished()) return;

        Vector2 nextPos = _navAgent.GetNextPathPosition();
        Vector2 direction = (nextPos - GlobalPosition).Normalized();
        Vector2 desiredVelocity = direction * Speed;

        if (_navAgent.AvoidanceEnabled)
            _navAgent.Velocity = desiredVelocity;
        else
        {
            Velocity = desiredVelocity;
            MoveAndSlide();
        }
    }

    private void OnVelocityComputed(Vector2 safeVelocity)
    {
        Velocity = safeVelocity;
        MoveAndSlide();
    }

    public void SetTarget(Vector2 targetPos) => _navAgent.TargetPosition = targetPos;
}
```

---

## 3. NavigationAgent3D Basic Usage

### GDScript

```gdscript
extends CharacterBody3D

@export var speed: float = 4.0
@export var gravity: float = 9.8

@onready var nav_agent: NavigationAgent3D = $NavigationAgent3D


func _ready() -> void:
	nav_agent.velocity_computed.connect(_on_velocity_computed)


func _physics_process(delta: float) -> void:
	# Apply gravity
	if not is_on_floor():
		velocity.y -= gravity * delta

	if nav_agent.is_navigation_finished():
		move_and_slide()
		return

	var next_pos: Vector3 = nav_agent.get_next_path_position()
	var direction: Vector3 = (next_pos - global_position)
	direction.y = 0.0
	direction = direction.normalized()
	var desired_velocity: Vector3 = direction * speed
	desired_velocity.y = velocity.y  # preserve gravity

	if nav_agent.avoidance_enabled:
		nav_agent.velocity = desired_velocity
	else:
		velocity = desired_velocity
		move_and_slide()


func _on_velocity_computed(safe_velocity: Vector3) -> void:
	velocity = safe_velocity
	move_and_slide()


func set_target(target_pos: Vector3) -> void:
	nav_agent.target_position = target_pos
```

### C#

```csharp
using Godot;

public partial class Enemy3D : CharacterBody3D
{
    [Export] public float Speed   { get; set; } = 4f;
    [Export] public float Gravity { get; set; } = 9.8f;

    private NavigationAgent3D _navAgent;

    public override void _Ready()
    {
        _navAgent = GetNode<NavigationAgent3D>("NavigationAgent3D");
        _navAgent.VelocityComputed += OnVelocityComputed;
    }

    public override void _PhysicsProcess(double delta)
    {
        var vel = Velocity;
        if (!IsOnFloor()) vel.Y -= Gravity * (float)delta;

        if (_navAgent.IsNavigationFinished())
        {
            Velocity = vel;
            MoveAndSlide();
            return;
        }

        Vector3 nextPos = _navAgent.GetNextPathPosition();
        var direction = (nextPos - GlobalPosition) with { Y = 0f };
        direction = direction.Normalized();
        vel.X = direction.X * Speed;
        vel.Z = direction.Z * Speed;

        if (_navAgent.AvoidanceEnabled)
            _navAgent.Velocity = vel;
        else
        {
            Velocity = vel;
            MoveAndSlide();
        }
    }

    private void OnVelocityComputed(Vector3 safeVelocity)
    {
        Velocity = safeVelocity;
        MoveAndSlide();
    }

    public void SetTarget(Vector3 targetPos) => _navAgent.TargetPosition = targetPos;
}
```

---

## 4. Steering Behaviors

Steering behaviors are lightweight calculations that run every physics frame. Combine them to produce natural-looking movement without a full navigation mesh.

### GDScript

```gdscript
extends CharacterBody2D

@export var speed: float = 120.0
@export var arrive_radius: float = 80.0    # start slowing down at this distance
@export var arrive_stop: float = 8.0       # stop at this distance
@export var wander_angle_change: float = 0.4  # radians per frame max

var _wander_angle: float = 0.0


# ── Seek ────────────────────────────────────────────────────────────────────
# Accelerate toward target at full speed.
func seek(target_pos: Vector2) -> Vector2:
	return (target_pos - global_position).normalized() * speed


# ── Flee ────────────────────────────────────────────────────────────────────
# Accelerate directly away from target at full speed.
func flee(target_pos: Vector2) -> Vector2:
	return (global_position - target_pos).normalized() * speed


# ── Arrive ──────────────────────────────────────────────────────────────────
# Like seek, but smoothly decelerates inside arrive_radius.
func arrive(target_pos: Vector2) -> Vector2:
	var to_target: Vector2 = target_pos - global_position
	var dist: float = to_target.length()
	if dist < arrive_stop:
		return Vector2.ZERO
	var ramped_speed: float = speed * (dist / arrive_radius)
	var clamped_speed: float = minf(ramped_speed, speed)
	return to_target.normalized() * clamped_speed


# ── Wander ──────────────────────────────────────────────────────────────────
# Project a circle ahead of the agent, then jitter a point on its edge.
func wander() -> Vector2:
	var circle_distance: float = 60.0
	var circle_radius: float = 30.0
	_wander_angle += randf_range(-wander_angle_change, wander_angle_change)
	var circle_center: Vector2 = velocity.normalized() * circle_distance
	if circle_center == Vector2.ZERO:
		circle_center = Vector2.RIGHT * circle_distance
	var displacement: Vector2 = Vector2(
		cos(_wander_angle) * circle_radius,
		sin(_wander_angle) * circle_radius
	)
	return (circle_center + displacement).normalized() * speed


# ── Usage example ────────────────────────────────────────────────────────────
func _physics_process(_delta: float) -> void:
	# Swap the desired behavior:
	velocity = arrive(get_tree().get_first_node_in_group("player").global_position)
	# velocity = flee(...)
	# velocity = wander()
	move_and_slide()
```

### C#

```csharp
using Godot;

public partial class SteeringEnemy : CharacterBody2D
{
    [Export] public float Speed { get; set; } = 120f;
    [Export] public float ArriveRadius { get; set; } = 80f;
    [Export] public float ArriveStop { get; set; } = 8f;
    [Export] public float WanderAngleChange { get; set; } = 0.4f;

    private float _wanderAngle;

    // ── Seek ──────────────────────────────────────────────────────────────
    public Vector2 Seek(Vector2 targetPos)
        => (targetPos - GlobalPosition).Normalized() * Speed;

    // ── Flee ──────────────────────────────────────────────────────────────
    public Vector2 Flee(Vector2 targetPos)
        => (GlobalPosition - targetPos).Normalized() * Speed;

    // ── Arrive ────────────────────────────────────────────────────────────
    public Vector2 Arrive(Vector2 targetPos)
    {
        Vector2 toTarget = targetPos - GlobalPosition;
        float dist = toTarget.Length();
        if (dist < ArriveStop) return Vector2.Zero;
        float rampedSpeed = Speed * (dist / ArriveRadius);
        float clampedSpeed = Mathf.Min(rampedSpeed, Speed);
        return toTarget.Normalized() * clampedSpeed;
    }

    // ── Wander ────────────────────────────────────────────────────────────
    public Vector2 Wander()
    {
        float circleDistance = 60f;
        float circleRadius = 30f;
        _wanderAngle += GD.RandRange(-WanderAngleChange, WanderAngleChange);
        Vector2 circleCenter = Velocity.Normalized() * circleDistance;
        if (circleCenter == Vector2.Zero)
            circleCenter = Vector2.Right * circleDistance;
        var displacement = new Vector2(
            Mathf.Cos(_wanderAngle) * circleRadius,
            Mathf.Sin(_wanderAngle) * circleRadius
        );
        return (circleCenter + displacement).Normalized() * Speed;
    }

    // ── Usage example ─────────────────────────────────────────────────────
    public override void _PhysicsProcess(double delta)
    {
        var player = GetTree().GetFirstNodeInGroup("player") as Node2D;
        Velocity = Arrive(player.GlobalPosition);
        // Velocity = Flee(...);
        // Velocity = Wander();
        MoveAndSlide();
    }
}
```

---

## 5. Patrol Patterns

### GDScript

```gdscript
extends CharacterBody2D

@export var waypoints: Array[Marker2D] = []
@export var speed: float = 80.0
@export var wait_time: float = 1.0  # seconds to pause at each waypoint

@onready var nav_agent: NavigationAgent2D = $NavigationAgent2D
@onready var wait_timer: Timer = $WaitTimer

var _current_index: int = 0
var _waiting: bool = false


func _ready() -> void:
	wait_timer.wait_time = wait_time
	wait_timer.one_shot = true
	wait_timer.timeout.connect(_on_wait_timer_timeout)
	_go_to_current_waypoint()


func _physics_process(_delta: float) -> void:
	if _waiting or waypoints.is_empty():
		return

	if nav_agent.is_navigation_finished():
		_waiting = true
		wait_timer.start()
		return

	var next_pos: Vector2 = nav_agent.get_next_path_position()
	velocity = (next_pos - global_position).normalized() * speed
	move_and_slide()


func _on_wait_timer_timeout() -> void:
	_waiting = false
	_current_index = (_current_index + 1) % waypoints.size()
	_go_to_current_waypoint()


func _go_to_current_waypoint() -> void:
	if waypoints.is_empty():
		return
	nav_agent.target_position = waypoints[_current_index].global_position
```

**Scene setup:** add a `Timer` node named `WaitTimer` as a child. Assign `Marker2D` nodes to the `waypoints` export array in the Inspector.

### C#

```csharp
using Godot;
using Godot.Collections;

public partial class PatrolEnemy : CharacterBody2D
{
    [Export] public Array<Marker2D> Waypoints { get; set; } = new();
    [Export] public float Speed     { get; set; } = 80f;
    [Export] public float WaitTime  { get; set; } = 1f;

    private NavigationAgent2D _navAgent;
    private Timer _waitTimer;
    private int _currentIndex;
    private bool _waiting;

    public override void _Ready()
    {
        _navAgent   = GetNode<NavigationAgent2D>("NavigationAgent2D");
        _waitTimer  = GetNode<Timer>("WaitTimer");

        _waitTimer.WaitTime = WaitTime;
        _waitTimer.OneShot  = true;
        _waitTimer.Timeout += OnWaitTimerTimeout;

        GoToCurrentWaypoint();
    }

    public override void _PhysicsProcess(double delta)
    {
        if (_waiting || Waypoints.Count == 0) return;

        if (_navAgent.IsNavigationFinished())
        {
            _waiting = true;
            _waitTimer.Start();
            return;
        }

        Vector2 nextPos  = _navAgent.GetNextPathPosition();
        Velocity = (nextPos - GlobalPosition).Normalized() * Speed;
        MoveAndSlide();
    }

    private void OnWaitTimerTimeout()
    {
        _waiting = false;
        _currentIndex = (_currentIndex + 1) % Waypoints.Count;
        GoToCurrentWaypoint();
    }

    private void GoToCurrentWaypoint()
    {
        if (Waypoints.Count == 0) return;
        _navAgent.TargetPosition = Waypoints[_currentIndex].GlobalPosition;
    }
}
```

---

## 6. Behavior Tree Concept

A behavior tree (BT) is a tree of nodes evaluated every tick. Three core node types:

| Type | Succeeds when | Fails when |
|---|---|---|
| **Sequence** | all children succeed (AND) | any child fails |
| **Selector** | any child succeeds (OR) | all children fail |
| **Action** | the leaf action completes | the leaf reports failure |

Sequences model "do A then B then C". Selectors model "try A, else try B, else try C".

### Lightweight GDScript Implementation

```gdscript
# bt_node.gd — base class
class_name BTNode
extends RefCounted

enum Status { SUCCESS, FAILURE, RUNNING }

func tick(actor: Node, _delta: float) -> Status:
	return Status.FAILURE
```

```gdscript
# bt_sequence.gd — run children in order; fail fast
class_name BTSequence
extends BTNode

var children: Array[BTNode] = []


func tick(actor: Node, delta: float) -> Status:
	for child in children:
		var result: BTNode.Status = child.tick(actor, delta)
		if result != Status.SUCCESS:
			return result  # FAILURE or RUNNING stops the sequence
	return Status.SUCCESS
```

```gdscript
# bt_selector.gd — try children in order; succeed on first success
class_name BTSelector
extends BTNode

var children: Array[BTNode] = []


func tick(actor: Node, delta: float) -> Status:
	for child in children:
		var result: BTNode.Status = child.tick(actor, delta)
		if result != Status.FAILURE:
			return result  # SUCCESS or RUNNING stops the selector
	return Status.FAILURE
```

```gdscript
# bt_action.gd — leaf node backed by a callable
class_name BTAction
extends BTNode

var _action: Callable


func _init(action: Callable) -> void:
	_action = action


func tick(actor: Node, delta: float) -> Status:
	return _action.call(actor, delta) as Status
```

### Lightweight C# Implementation

```csharp
// BTNode.cs — base class
public abstract class BTNode
{
    public enum Status { Success, Failure, Running }

    public virtual Status Tick(Node actor, float delta) => Status.Failure;
}
```

```csharp
// BTSequence.cs — run children in order; fail fast
using Godot;
using System.Collections.Generic;

public class BTSequence : BTNode
{
    public List<BTNode> Children { get; set; } = new();

    public override Status Tick(Node actor, float delta)
    {
        foreach (var child in Children)
        {
            var result = child.Tick(actor, delta);
            if (result != Status.Success)
                return result; // Failure or Running stops the sequence
        }
        return Status.Success;
    }
}
```

```csharp
// BTSelector.cs — try children in order; succeed on first success
using Godot;
using System.Collections.Generic;

public class BTSelector : BTNode
{
    public List<BTNode> Children { get; set; } = new();

    public override Status Tick(Node actor, float delta)
    {
        foreach (var child in Children)
        {
            var result = child.Tick(actor, delta);
            if (result != Status.Failure)
                return result; // Success or Running stops the selector
        }
        return Status.Failure;
    }
}
```

```csharp
// BTAction.cs — leaf node backed by a delegate
using Godot;
using System;

public class BTAction : BTNode
{
    private readonly Func<Node, float, Status> _action;

    public BTAction(Func<Node, float, Status> action) => _action = action;

    public override Status Tick(Node actor, float delta) => _action(actor, delta);
}
```

### Wiring a BT in an Enemy

```gdscript
extends CharacterBody2D

var _bt_root: BTNode


func _ready() -> void:
	# "Chase player OR patrol" selector
	var chase_seq := BTSequence.new()
	chase_seq.children = [
		BTAction.new(_can_see_player),
		BTAction.new(_chase_player),
	]

	var patrol_act := BTAction.new(_patrol)

	var root := BTSelector.new()
	root.children = [chase_seq, patrol_act]
	_bt_root = root


func _physics_process(delta: float) -> void:
	_bt_root.tick(self, delta)
	move_and_slide()


func _can_see_player(_actor: Node, _delta: float) -> BTNode.Status:
	var player := get_tree().get_first_node_in_group("player")
	if not is_instance_valid(player):
		return BTNode.Status.FAILURE
	return BTNode.Status.SUCCESS if global_position.distance_to(player.global_position) < 300.0 \
		else BTNode.Status.FAILURE


func _chase_player(actor: Node, _delta: float) -> BTNode.Status:
	var player := get_tree().get_first_node_in_group("player")
	velocity = (player.global_position - global_position).normalized() * 120.0
	return BTNode.Status.RUNNING


func _patrol(_actor: Node, _delta: float) -> BTNode.Status:
	# minimal inline patrol; replace with full patrol logic
	velocity = Vector2.RIGHT * 60.0
	return BTNode.Status.RUNNING
```

### C#

```csharp
using Godot;

public partial class BTEnemy : CharacterBody2D
{
    private BTNode _btRoot;

    public override void _Ready()
    {
        var chaseSeq = new BTSequence
        {
            Children = { new BTAction(CanSeePlayer), new BTAction(ChasePlayer) }
        };
        var patrolAct = new BTAction(Patrol);
        _btRoot = new BTSelector { Children = { chaseSeq, patrolAct } };
    }

    public override void _PhysicsProcess(double delta)
    {
        _btRoot.Tick(this, (float)delta);
        MoveAndSlide();
    }

    private BTNode.Status CanSeePlayer(Node actor, float delta)
    {
        var player = GetTree().GetFirstNodeInGroup("player") as Node2D;
        if (!IsInstanceValid(player)) return BTNode.Status.Failure;
        return GlobalPosition.DistanceTo(player.GlobalPosition) < 300f
            ? BTNode.Status.Success
            : BTNode.Status.Failure;
    }

    private BTNode.Status ChasePlayer(Node actor, float delta)
    {
        var player = GetTree().GetFirstNodeInGroup("player") as Node2D;
        Velocity = (player.GlobalPosition - GlobalPosition).Normalized() * 120f;
        return BTNode.Status.Running;
    }

    private BTNode.Status Patrol(Node actor, float delta)
    {
        // Minimal inline patrol; replace with full patrol logic
        Velocity = Vector2.Right * 60f;
        return BTNode.Status.Running;
    }
}
```

---

## 7. Chase + Attack Pattern

Combines NavigationAgent2D with a state machine. See the **state-machine** skill for the full FSM infrastructure.

### States

| State | Entry condition | Exit condition |
|---|---|---|
| PATROL | default / player escaped | player enters detect_range |
| CHASE | player in detect_range | player in attack_range OR player escaped |
| ATTACK | player in attack_range | player left attack_range |

### GDScript

```gdscript
extends CharacterBody2D

enum State { PATROL, CHASE, ATTACK }

@export var detect_range: float  = 250.0
@export var attack_range: float  = 40.0
@export var escape_range: float  = 320.0
@export var speed: float         = 110.0
@export var attack_cooldown: float = 0.8

@export var patrol_waypoints: Array[Marker2D] = []

@onready var nav_agent: NavigationAgent2D     = $NavigationAgent2D
@onready var attack_timer: Timer              = $AttackTimer
@onready var patrol_wait_timer: Timer         = $PatrolWaitTimer

var _state: State = State.PATROL
var _patrol_index: int = 0
var _patrol_waiting: bool = false

@onready var _player: Node2D = get_tree().get_first_node_in_group("player")


func _ready() -> void:
	attack_timer.wait_time = attack_cooldown
	attack_timer.one_shot = true
	patrol_wait_timer.wait_time = 1.0
	patrol_wait_timer.one_shot = true
	patrol_wait_timer.timeout.connect(_advance_patrol)
	nav_agent.velocity_computed.connect(_on_velocity_computed)
	_go_to_patrol_point()


func _physics_process(_delta: float) -> void:
	if not is_instance_valid(_player):
		return

	var dist: float = global_position.distance_to(_player.global_position)

	match _state:
		State.PATROL:
			_do_patrol()
			if dist <= detect_range:
				_enter_chase()

		State.CHASE:
			nav_agent.target_position = _player.global_position
			if dist <= attack_range:
				_enter_attack()
			elif dist >= escape_range:
				_enter_patrol()
			else:
				var next := nav_agent.get_next_path_position()
				nav_agent.velocity = (next - global_position).normalized() * speed

		State.ATTACK:
			velocity = Vector2.ZERO
			if dist > attack_range:
				_enter_chase()

	move_and_slide()


func _on_velocity_computed(safe_vel: Vector2) -> void:
	velocity = safe_vel


# ── State transitions ────────────────────────────────────────────────────────

func _enter_chase() -> void:
	_state = State.CHASE


func _enter_attack() -> void:
	_state = State.ATTACK
	if attack_timer.is_stopped():
		_perform_attack()
		attack_timer.start()


func _enter_patrol() -> void:
	_state = State.PATROL
	_go_to_patrol_point()


# ── Patrol helpers ────────────────────────────────────────────────────────────

func _do_patrol() -> void:
	if patrol_waypoints.is_empty() or _patrol_waiting:
		velocity = Vector2.ZERO
		return
	if nav_agent.is_navigation_finished():
		_patrol_waiting = true
		patrol_wait_timer.start()
		return
	var next := nav_agent.get_next_path_position()
	nav_agent.velocity = (next - global_position).normalized() * (speed * 0.5)


func _advance_patrol() -> void:
	_patrol_waiting = false
	_patrol_index = (_patrol_index + 1) % patrol_waypoints.size()
	_go_to_patrol_point()


func _go_to_patrol_point() -> void:
	if patrol_waypoints.is_empty():
		return
	nav_agent.target_position = patrol_waypoints[_patrol_index].global_position


# ── Attack ────────────────────────────────────────────────────────────────────

func _perform_attack() -> void:
	# Replace with your attack logic (animation, hitbox, etc.)
	pass
```

### C#

```csharp
using Godot;
using Godot.Collections;

public partial class ChaseAttackEnemy : CharacterBody2D
{
    private enum State { Patrol, Chase, Attack }

    [Export] public float DetectRange { get; set; } = 250f;
    [Export] public float AttackRange { get; set; } = 40f;
    [Export] public float EscapeRange { get; set; } = 320f;
    [Export] public float Speed { get; set; } = 110f;
    [Export] public float AttackCooldown { get; set; } = 0.8f;
    [Export] public Array<Marker2D> PatrolWaypoints { get; set; } = new();

    private NavigationAgent2D _navAgent;
    private Timer _attackTimer;
    private Timer _patrolWaitTimer;
    private State _state = State.Patrol;
    private int _patrolIndex;
    private bool _patrolWaiting;
    private Node2D _player;

    public override void _Ready()
    {
        _navAgent = GetNode<NavigationAgent2D>("NavigationAgent2D");
        _attackTimer = GetNode<Timer>("AttackTimer");
        _patrolWaitTimer = GetNode<Timer>("PatrolWaitTimer");

        _attackTimer.WaitTime = AttackCooldown;
        _attackTimer.OneShot = true;
        _patrolWaitTimer.WaitTime = 1.0;
        _patrolWaitTimer.OneShot = true;
        _patrolWaitTimer.Timeout += AdvancePatrol;
        _navAgent.VelocityComputed += OnVelocityComputed;

        _player = GetTree().GetFirstNodeInGroup("player") as Node2D;
        GoToPatrolPoint();
    }

    public override void _PhysicsProcess(double delta)
    {
        if (!IsInstanceValid(_player)) return;

        float dist = GlobalPosition.DistanceTo(_player.GlobalPosition);

        switch (_state)
        {
            case State.Patrol:
                DoPatrol();
                if (dist <= DetectRange) EnterChase();
                break;

            case State.Chase:
                _navAgent.TargetPosition = _player.GlobalPosition;
                if (dist <= AttackRange)
                    EnterAttack();
                else if (dist >= EscapeRange)
                    EnterPatrol();
                else
                {
                    Vector2 next = _navAgent.GetNextPathPosition();
                    _navAgent.Velocity = (next - GlobalPosition).Normalized() * Speed;
                }
                break;

            case State.Attack:
                Velocity = Vector2.Zero;
                if (dist > AttackRange) EnterChase();
                break;
        }

        MoveAndSlide();
    }

    private void OnVelocityComputed(Vector2 safeVel) => Velocity = safeVel;

    // ── State transitions ─────────────────────────────────────────────────
    private void EnterChase() => _state = State.Chase;

    private void EnterAttack()
    {
        _state = State.Attack;
        if (_attackTimer.IsStopped())
        {
            PerformAttack();
            _attackTimer.Start();
        }
    }

    private void EnterPatrol()
    {
        _state = State.Patrol;
        GoToPatrolPoint();
    }

    // ── Patrol helpers ────────────────────────────────────────────────────
    private void DoPatrol()
    {
        if (PatrolWaypoints.Count == 0 || _patrolWaiting)
        {
            Velocity = Vector2.Zero;
            return;
        }
        if (_navAgent.IsNavigationFinished())
        {
            _patrolWaiting = true;
            _patrolWaitTimer.Start();
            return;
        }
        Vector2 next = _navAgent.GetNextPathPosition();
        _navAgent.Velocity = (next - GlobalPosition).Normalized() * (Speed * 0.5f);
    }

    private void AdvancePatrol()
    {
        _patrolWaiting = false;
        _patrolIndex = (_patrolIndex + 1) % PatrolWaypoints.Count;
        GoToPatrolPoint();
    }

    private void GoToPatrolPoint()
    {
        if (PatrolWaypoints.Count == 0) return;
        _navAgent.TargetPosition = PatrolWaypoints[_patrolIndex].GlobalPosition;
    }

    // ── Attack ────────────────────────────────────────────────────────────
    private void PerformAttack()
    {
        // Replace with your attack logic (animation, hitbox, etc.)
    }
}
```

> For larger projects, extract each state into its own node class using the **state-machine** skill and inject the `NavigationAgent2D` reference from the parent.

---

## 8. Common Pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| **Navigation mesh not baked** | Agent stands still; no path found | Bake the NavigationPolygon/NavigationMesh before running, or call `bake_navigation_polygon()` at runtime after scene loads |
| **`agent_radius` too large** | Agent can't fit through doorways or narrow corridors | Lower `radius` on NavigationAgent to be slightly less than half the passage width |
| **Avoidance jitter** | Agent stutters or oscillates when near other agents | Increase `time_horizon_agents` (try 2–4 s) or slightly lower `max_speed` on the agent |
| **Path recalculation too frequent** | CPU spike each frame; agents lag | Add a `Timer` (0.2–0.5 s) and only set `target_position` when the timer fires, not every physics frame |
| **Wrong navigation layer** | Agent ignores some regions or finds no path | Confirm `navigation_layers` bitmask matches between the NavigationRegion and the NavigationAgent |
| **Target set before NavigationServer is ready** | Path is empty on the first frame | Defer `target_position` assignment to `_ready()` or await `NavigationServer2D.map_changed` |
| **Gravity ignored in 3D** | Agent floats or sinks into the floor | Always accumulate `velocity.y` from gravity separately; only zero out X/Z from the nav direction |
| **Baking causes frame drop** | Synchronous bake on large maps blocks the main thread | Use async baking: `bake_navigation_mesh(true)` (Godot 4.4+); connect `bake_finished` signal |

---

## 9. Checklist

- [ ] NavigationRegion2D/3D added to the scene with a NavigationPolygon/NavigationMesh resource
- [ ] Navigation mesh baked (edit-time or at runtime before the agent needs a path)
- [ ] `navigation_layers` bitmask matches between NavigationRegion and NavigationAgent
- [ ] `NavigationAgent2D`/`NavigationAgent3D` is a **child** of the enemy node
- [ ] `get_next_path_position()` called each physics frame, not `get_target_position()`
- [ ] `velocity_computed` signal connected when `avoidance_enabled` is `true`
- [ ] `is_navigation_finished()` checked before moving to avoid jitter at the destination
- [ ] Path target updated via a throttle timer rather than every frame when following a moving player
- [ ] `agent_radius` small enough to fit through the narrowest passage in the level
- [ ] Gravity applied independently of horizontal nav velocity (3D only)
- [ ] Large or dynamic maps use async baking (`bake_navigation_mesh(true)`) to avoid frame drops (Godot 4.4+)
