---
name: multiplayer-sync
description: Use when synchronizing multiplayer state — MultiplayerSynchronizer, interpolation, prediction, and lag compensation
---

# Multiplayer Synchronization in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, then C#.

**Related skills:** See **multiplayer-basics** for ENet setup, RPCs, and authority model. See **dedicated-server** for headless export and deployment. See **physics-system** for physics interpolation and RigidBody synchronization.

---

## 1. MultiplayerSynchronizer

`MultiplayerSynchronizer` is Godot's built-in node for replicating properties across the network. Add it as a child of the node whose state you want to share.

### What It Does

- Sends property values from the **authority** peer to all others at a configured interval
- Supports both **delta sync** (only changed values) and **full sync** (all values every tick)
- Allows **visibility filters** to control which peers receive updates

### Replication Config in the Editor

1. Select the `MultiplayerSynchronizer` node in the scene tree.
2. In the Inspector, open **Replication** and click **Add Property**.
3. Pick the parent node path and property name (e.g. `position`, `velocity`).
4. Set **Sync** (send every interval) or **Spawn** (send only on spawn) per property.
5. Set the **Replication Interval** (seconds). `0` means every physics frame.

### Key Properties

| Property | Description |
|---|---|
| `replication_interval` | Seconds between full sync updates. `0` = every physics frame |
| `delta_interval` | Seconds between delta sync updates. `0` = disabled |
| `public_visibility` | When `true`, updates go to all peers (default) |
| `visibility_filters` | Array of `Callable`s; each returns `true` if a peer should receive updates |

### Delta vs Full Sync

| Mode | How It Works | Best For |
|---|---|---|
| **Full sync** | Sends all configured properties every `replication_interval` | Simple objects, low property count |
| **Delta sync** | Sends only properties that changed since last sync, every `delta_interval` | Objects with many properties that change infrequently |

Use both together: set `replication_interval` for periodic full state and `delta_interval` for frequent change-only bursts.

### Visibility Filters (GDScript)

```gdscript
# Only send updates to peers within 500 units of this object.
func _ready() -> void:
    $MultiplayerSynchronizer.add_visibility_filter(_is_peer_in_range)

func _is_peer_in_range(peer_id: int) -> bool:
    var peer_player := _get_player_node(peer_id)
    if peer_player == null:
        return false
    return global_position.distance_to(peer_player.global_position) <= 500.0
```

### Visibility Filters (C#)

```csharp
// Only send updates to peers within 500 units of this object.
public override void _Ready()
{
    var sync = GetNode<MultiplayerSynchronizer>("MultiplayerSynchronizer");
    sync.AddVisibilityFilter(Callable.From<int>(IsPeerInRange));
}

private bool IsPeerInRange(int peerId)
{
    var peerPlayer = GetPlayerNode(peerId);
    if (peerPlayer is null)
        return false;
    return GlobalPosition.DistanceTo(peerPlayer.GlobalPosition) <= 500.0f;
}
```

---

## 2. Property Synchronization

### What to Sync

Sync the minimal state needed to reconstruct the visual on remote peers. Typical properties:

| Property | Type | Notes |
|---|---|---|
| `position` | `Vector2` / `Vector3` | Core transform — sync every frame or use interpolation |
| `velocity` | `Vector2` / `Vector3` | Helps remote prediction stay ahead of position snaps |
| `health` | `int` / `float` | Sync reliably on change; delta sync is ideal |
| `animation_state` | `String` / `int` | Sync on change; use an enum int to save bandwidth |
| `is_crouching` | `bool` | Low-change boolean; delta sync or RPC on change |

### Synced Player (GDScript)

```gdscript
# synced_player.gd
extends CharacterBody2D

## Sync interval in seconds — exposed so designers can tune per object type.
@export var sync_interval: float = 0.05  # 20 Hz

@export var speed: float = 200.0

# These properties are listed in the MultiplayerSynchronizer replication config.
var synced_position: Vector2 = Vector2.ZERO
var synced_velocity: Vector2 = Vector2.ZERO
var synced_health: int = 100
var synced_anim: int = 0  # 0 = idle, 1 = run, 2 = jump

@onready var _sync: MultiplayerSynchronizer = $MultiplayerSynchronizer


func _ready() -> void:
    _sync.replication_interval = sync_interval
    # Only the authority (owner) drives movement.
    set_physics_process(is_multiplayer_authority())


func _physics_process(_delta: float) -> void:
    # Authority: write canonical state so MultiplayerSynchronizer can replicate it.
    synced_position = global_position
    synced_velocity = velocity
    synced_anim     = _compute_anim_state()
```

### Synced Player (C#)

```csharp
// SyncedPlayer.cs
using Godot;

public partial class SyncedPlayer : CharacterBody2D
{
    /// <summary>Sync interval in seconds. Exposed so designers can tune per object type.</summary>
    [Export] public float SyncInterval { get; set; } = 0.05f; // 20 Hz

    [Export] public float Speed { get; set; } = 200.0f;

    // These properties are listed in the MultiplayerSynchronizer replication config.
    public Vector2 SyncedPosition { get; set; } = Vector2.Zero;
    public Vector2 SyncedVelocity { get; set; } = Vector2.Zero;
    public int SyncedHealth { get; set; } = 100;
    public int SyncedAnim   { get; set; } = 0; // 0=idle, 1=run, 2=jump

    private MultiplayerSynchronizer _sync = null!;

    public override void _Ready()
    {
        _sync = GetNode<MultiplayerSynchronizer>("MultiplayerSynchronizer");
        _sync.ReplicationInterval = SyncInterval;
        SetPhysicsProcess(IsMultiplayerAuthority());
    }

    public override void _PhysicsProcess(double delta)
    {
        // Authority: write canonical state for replication.
        SyncedPosition = GlobalPosition;
        SyncedVelocity = Velocity;
        SyncedAnim     = ComputeAnimState();
    }

    private int ComputeAnimState()
    {
        if (!IsOnFloor()) return 2;
        return Velocity.Length() > 1f ? 1 : 0;
    }
}
```

---

## 3. Interpolation

Network updates arrive in discrete ticks (e.g. every 50 ms at 20 Hz). Without interpolation, remote players visibly stutter from position to position. Interpolation smooths this by blending between the previous received state and the current received state over time.

### Why `_process`, Not `_physics_process`

- `_physics_process` runs at a fixed physics rate (default 60 Hz) and is coupled to simulation.
- `_process` runs every rendered frame and has access to the render sub-tick fraction via `Engine.get_physics_interpolation_fraction()`.
- Visual smoothing belongs in `_process` because it does not affect gameplay state — it only affects what the player sees.

### Interpolation (GDScript)

```gdscript
# remote_player_display.gd — attached to a non-authority instance
extends Node2D

var _prev_pos: Vector2 = Vector2.ZERO
var _curr_pos: Vector2 = Vector2.ZERO
var _prev_health: int = 100
var _curr_health: int = 100

@onready var _sync_source: Node = $"../SyncedPlayer"  # the node with MultiplayerSynchronizer


func _ready() -> void:
    # Disable physics on remote display nodes — authority drives state.
    set_physics_process(false)
    # Listen for each sync tick to capture before/after state.
    _sync_source.connect("synchronized", _on_synchronized)


func _on_synchronized() -> void:
    # Called by MultiplayerSynchronizer after each replication tick.
    _prev_pos    = _curr_pos
    _curr_pos    = _sync_source.synced_position
    _prev_health = _curr_health
    _curr_health = _sync_source.synced_health


func _process(_delta: float) -> void:
    # interpolation_fraction is 0.0..1.0 between the last and next physics tick.
    var f: float = Engine.get_physics_interpolation_fraction()
    global_position = _prev_pos.lerp(_curr_pos, f)
    # Health and other discrete values are not lerped — snap on change.
```

### Interpolation (C#)

```csharp
// RemotePlayerDisplay.cs — attached to a non-authority instance
using Godot;

public partial class RemotePlayerDisplay : Node2D
{
    private Vector2 _prevPos = Vector2.Zero;
    private Vector2 _currPos = Vector2.Zero;
    private int _prevHealth;
    private int _currHealth;

    private SyncedPlayer _syncSource = null!;

    public override void _Ready()
    {
        SetPhysicsProcess(false);
        _syncSource = GetNode<SyncedPlayer>("../SyncedPlayer");
        _syncSource.Connect(
            MultiplayerSynchronizer.SignalName.Synchronized,
            Callable.From(OnSynchronized));
    }

    private void OnSynchronized()
    {
        _prevPos    = _currPos;
        _currPos    = _syncSource.SyncedPosition;
        _prevHealth = _currHealth;
        _currHealth = _syncSource.SyncedHealth;
    }

    public override void _Process(double delta)
    {
        float f = (float)Engine.GetPhysicsInterpolationFraction();
        GlobalPosition = _prevPos.Lerp(_currPos, f);
        // Discrete values like health snap immediately — no lerp.
    }
}
```

---

## 4. Client-Side Prediction

Client-side prediction lets the local player's input feel instant by applying it locally before the server confirms it. When the server sends a correction, the client reconciles by replaying any unconfirmed inputs on top of the corrected state.

### Pattern (GDScript)

```gdscript
# predicted_player.gd — authority is the server; this runs on the local client
extends CharacterBody2D

@export var speed: float = 200.0

# Ring buffer of unacknowledged inputs indexed by tick number.
var _pending_inputs: Dictionary = {}
var _current_tick: int = 0

# Last server-confirmed state.
var _server_position: Vector2 = Vector2.ZERO
var _server_tick: int = -1


func _physics_process(delta: float) -> void:
    var input_dir: Vector2 = Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")

    # 1. Predict: apply input locally right now.
    _apply_input(input_dir, delta)

    # 2. Store input so we can replay it if the server corrects us.
    _pending_inputs[_current_tick] = {"dir": input_dir, "delta": delta}
    _current_tick += 1

    # 3. Send input to server every frame (or batch at a lower rate).
    if multiplayer.is_server():
        return
    _send_input_to_server.rpc_id(1, input_dir, _current_tick - 1)


func _apply_input(dir: Vector2, delta: float) -> void:
    velocity = dir * speed
    move_and_slide()


@rpc("authority", "call_remote", "unreliable")
func _receive_server_correction(corrected_pos: Vector2, ack_tick: int) -> void:
    # Server has confirmed state up to ack_tick. Snap and replay.
    _server_position = corrected_pos
    _server_tick     = ack_tick

    # Drop all inputs the server has already processed.
    for tick in _pending_inputs.keys():
        if tick <= ack_tick:
            _pending_inputs.erase(tick)

    # Reconcile: rewind to server position then replay pending inputs.
    global_position = _server_position
    for tick in _pending_inputs.keys():
        var inp: Dictionary = _pending_inputs[tick]
        _apply_input(inp["dir"], inp["delta"])


@rpc("any_peer", "call_remote", "unreliable")
func _send_input_to_server(dir: Vector2, tick: int) -> void:
    # Server receives client input, simulates, then confirms.
    _apply_input(dir, get_physics_process_delta_time())
    _receive_server_correction.rpc_id(
        multiplayer.get_remote_sender_id(),
        global_position,
        tick
    )
```

### Pattern (C#)

```csharp
// PredictedPlayer.cs — authority is the server; this runs on the local client
using Godot;
using System.Collections.Generic;
using System.Linq;

public partial class PredictedPlayer : CharacterBody2D
{
    [Export] public float Speed { get; set; } = 200.0f;

    // Ring buffer of unacknowledged inputs indexed by tick number.
    private readonly Dictionary<int, (Vector2 Dir, double Delta)> _pendingInputs = new();
    private int _currentTick;

    // Last server-confirmed state.
    private Vector2 _serverPosition = Vector2.Zero;
    private int _serverTick = -1;

    public override void _PhysicsProcess(double delta)
    {
        var inputDir = Input.GetVector("ui_left", "ui_right", "ui_up", "ui_down");

        // 1. Predict: apply input locally right now.
        ApplyInput(inputDir, delta);

        // 2. Store input so we can replay it if the server corrects us.
        _pendingInputs[_currentTick] = (inputDir, delta);
        _currentTick++;

        // 3. Send input to server every frame (or batch at a lower rate).
        if (Multiplayer.IsServer())
            return;
        RpcId(1, MethodName.SendInputToServer, inputDir, _currentTick - 1);
    }

    private void ApplyInput(Vector2 dir, double delta)
    {
        Velocity = dir * Speed;
        MoveAndSlide();
    }

    [Rpc(MultiplayerApi.RpcMode.Authority, CallLocal = false, TransferMode = MultiplayerPeer.TransferModeEnum.Unreliable)]
    private void ReceiveServerCorrection(Vector2 correctedPos, int ackTick)
    {
        _serverPosition = correctedPos;
        _serverTick = ackTick;

        // Drop all inputs the server has already processed.
        foreach (var tick in _pendingInputs.Keys.Where(t => t <= ackTick).ToList())
            _pendingInputs.Remove(tick);

        // Reconcile: rewind to server position then replay pending inputs.
        GlobalPosition = _serverPosition;
        foreach (var tick in _pendingInputs.Keys.OrderBy(t => t))
        {
            var inp = _pendingInputs[tick];
            ApplyInput(inp.Dir, inp.Delta);
        }
    }

    [Rpc(MultiplayerApi.RpcMode.AnyPeer, CallLocal = false, TransferMode = MultiplayerPeer.TransferModeEnum.Unreliable)]
    private void SendInputToServer(Vector2 dir, int tick)
    {
        // Server receives client input, simulates, then confirms.
        ApplyInput(dir, GetPhysicsProcessDeltaTime());
        RpcId(
            Multiplayer.GetRemoteSenderId(),
            MethodName.ReceiveServerCorrection,
            GlobalPosition,
            tick);
    }
}
```

**Key points:**
- Keep `_pending_inputs` bounded — evict entries older than a reasonable window (e.g. 128 ticks).
- Only reconcile if the corrected position differs from the predicted position by more than a threshold (e.g. 2 px / 0.05 m) to avoid jitter on micro-corrections.
- Use `unreliable` channel for position corrections — timeliness matters more than ordering.

---

## 5. Lag Compensation

Lag compensation lets the server validate a hit by rewinding the game state to the tick when the shooting client fired. Without it, a client would have to lead targets to account for latency — which is unfair and error-prone.

### Concept

```
Client fires at T=100ms latency ago.
Server receives the shot at T=now.
Server rewinds all character positions to T=100ms ago.
Server checks whether the bullet hit any character at that rewound state.
Server applies damage if hit, then discards the rewound snapshot.
```

### Code Sketch (GDScript)

```gdscript
# lag_compensation_manager.gd — runs on the server only
extends Node

const HISTORY_DURATION_SEC := 0.5  # how many seconds of history to keep
const PHYSICS_TICK_RATE    := 60.0

# history[tick] = { peer_id: position, ... }
var _position_history: Dictionary = {}
var _current_tick: int = 0


func _physics_process(_delta: float) -> void:
    if not multiplayer.is_server():
        return

    # Snapshot every peer's position this tick.
    var snapshot: Dictionary = {}
    for peer_id in multiplayer.get_peers():
        var player := _get_player(peer_id)
        if player:
            snapshot[peer_id] = player.global_position

    _position_history[_current_tick] = snapshot
    _current_tick += 1

    # Prune old history beyond the keep window.
    var oldest_kept: int = _current_tick - int(HISTORY_DURATION_SEC * PHYSICS_TICK_RATE)
    for old_tick in _position_history.keys():
        if old_tick < oldest_kept:
            _position_history.erase(old_tick)


func validate_shot(
    shooter_id: int,
    target_id: int,
    shot_origin: Vector3,
    shot_direction: Vector3,
    client_tick: int
) -> bool:
    if not _position_history.has(client_tick):
        return false  # too old or invalid tick

    var snapshot: Dictionary = _position_history[client_tick]
    if not snapshot.has(target_id):
        return false

    var rewound_pos: Vector2 = snapshot[target_id]

    # Simple AABB or circle hit check against the rewound position.
    var hit_radius := 32.0
    var closest_point := _closest_point_on_ray(shot_origin, shot_direction, rewound_pos)
    return closest_point.distance_to(rewound_pos) <= hit_radius


func _closest_point_on_ray(
    origin: Vector3, direction: Vector3, point: Vector2
) -> Vector2:
    # Project 2D point onto 2D ray (top-down example).
    var o := Vector2(origin.x, origin.z)
    var d := Vector2(direction.x, direction.z).normalized()
    var t := (Vector2(point) - o).dot(d)
    return o + d * max(t, 0.0)


func _get_player(peer_id: int) -> Node2D:
    return get_tree().get_first_node_in_group("player_%d" % peer_id) as Node2D
```

### Code Sketch (C#)

```csharp
// LagCompensationManager.cs — runs on the server only
using Godot;
using System.Collections.Generic;
using System.Linq;

public partial class LagCompensationManager : Node
{
    private const float HistoryDurationSec = 0.5f;
    private const float PhysicsTickRate = 60.0f;

    // history[tick] = { peerId -> position }
    private readonly Dictionary<int, Dictionary<int, Vector2>> _positionHistory = new();
    private int _currentTick;

    public override void _PhysicsProcess(double delta)
    {
        if (!Multiplayer.IsServer())
            return;

        // Snapshot every peer's position this tick.
        var snapshot = new Dictionary<int, Vector2>();
        foreach (int peerId in Multiplayer.GetPeers())
        {
            var player = GetPlayer(peerId);
            if (player is not null)
                snapshot[peerId] = player.GlobalPosition;
        }

        _positionHistory[_currentTick] = snapshot;
        _currentTick++;

        // Prune old history beyond the keep window.
        int oldestKept = _currentTick - (int)(HistoryDurationSec * PhysicsTickRate);
        foreach (int oldTick in _positionHistory.Keys.Where(t => t < oldestKept).ToList())
            _positionHistory.Remove(oldTick);
    }

    public bool ValidateShot(
        int shooterId,
        int targetId,
        Vector3 shotOrigin,
        Vector3 shotDirection,
        int clientTick)
    {
        if (!_positionHistory.TryGetValue(clientTick, out var snapshot))
            return false;

        if (!snapshot.TryGetValue(targetId, out Vector2 rewoundPos))
            return false;

        float hitRadius = 32.0f;
        Vector2 closestPoint = ClosestPointOnRay(shotOrigin, shotDirection, rewoundPos);
        return closestPoint.DistanceTo(rewoundPos) <= hitRadius;
    }

    private static Vector2 ClosestPointOnRay(Vector3 origin, Vector3 direction, Vector2 point)
    {
        // Project 2D point onto 2D ray (top-down example).
        var o = new Vector2(origin.X, origin.Z);
        Vector2 d = new Vector2(direction.X, direction.Z).Normalized();
        float t = (point - o).Dot(d);
        return o + d * Mathf.Max(t, 0.0f);
    }

    private Node2D GetPlayer(int peerId)
    {
        return GetTree().GetFirstNodeInGroup($"player_{peerId}") as Node2D;
    }
}
```

**Production considerations:**
- Store full `Transform` (not just position) for 3D games so rotation is also rewound.
- Apply hit validation on the server only; never trust hit reports from clients.
- Cap the rewind window to a max latency tolerance (e.g. 300 ms) to prevent abuse.

---

## 6. State vs Input Synchronization

Choose the synchronization model that fits your game's needs:

| Factor | Sync State | Sync Inputs |
|---|---|---|
| **What is sent** | Current property values (position, health, etc.) | Player input actions each frame |
| **Who simulates** | Authority only; others receive results | All peers run the same simulation |
| **Determinism required** | No | Yes — every peer must produce identical output from the same inputs |
| **Bandwidth** | Higher — full state sent each interval | Lower — small input structs per frame |
| **Responsiveness** | Lower — non-authority peers wait for next sync tick | Higher — local prediction is trivial when deterministic |
| **Complexity** | Lower — no reconciliation loop | Higher — requires deterministic physics, fixed-point math, or lockstep |
| **Best for** | Action games, shooters, most real-time games | Fighting games, RTS, turn-based, simulation games |
| **Lag compensation needed** | Yes, for hit detection | Usually not — all peers are in sync |

**Hybrid approach** (most real-time games): sync inputs for the local player's character (enabling prediction), sync state for all other objects and game events.

---

## 7. Bandwidth Optimization

### Sync Only Changed Properties

Use `delta_interval` on `MultiplayerSynchronizer` so only dirty properties are sent each tick. Combine with a short `replication_interval` for a full-state heartbeat.

```gdscript
func _ready() -> void:
    var sync := $MultiplayerSynchronizer
    sync.replication_interval = 1.0   # Full state every 1 s as fallback
    sync.delta_interval        = 0.05  # Changed properties every 50 ms
```

```csharp
public override void _Ready()
{
    var sync = GetNode<MultiplayerSynchronizer>("MultiplayerSynchronizer");
    sync.ReplicationInterval = 1.0;  // Full state every 1 s as fallback
    sync.DeltaInterval       = 0.05; // Changed properties every 50 ms
}
```

### Quantize Floats

Reduce float precision before sending. A 16-bit integer covers ±32767 cm — more than enough for most game worlds.

```gdscript
# Encode a position component to a 16-bit integer (1 cm precision, ±327 m range).
func quantize(value: float) -> int:
    return clampi(int(value * 100.0), -32768, 32767)

func dequantize(value: int) -> float:
    return float(value) / 100.0
```

```csharp
// Encode a position component to a 16-bit integer (1 cm precision, +/-327 m range).
public static int Quantize(float value)
{
    return Mathf.Clamp((int)(value * 100.0f), -32768, 32767);
}

public static float Dequantize(int value)
{
    return value / 100.0f;
}
```

### Distance-Based Sync Rate

Reduce the sync rate for objects far from the local player to save bandwidth.

```gdscript
# distance_sync_manager.gd — call from a timer or _physics_process
func update_sync_intervals(local_player: Node2D) -> void:
    for sync_node in get_tree().get_nodes_in_group("synced_objects"):
        var obj := sync_node.get_parent() as Node2D
        if obj == null:
            continue
        var dist: float = local_player.global_position.distance_to(obj.global_position)
        var multiplayer_sync := sync_node as MultiplayerSynchronizer
        if dist < 200.0:
            multiplayer_sync.replication_interval = 0.05   # 20 Hz — nearby
        elif dist < 600.0:
            multiplayer_sync.replication_interval = 0.1    # 10 Hz — medium
        else:
            multiplayer_sync.replication_interval = 0.5    # 2 Hz  — distant
```

```csharp
// DistanceSyncManager.cs — call from a timer or _PhysicsProcess
public void UpdateSyncIntervals(Node2D localPlayer)
{
    foreach (Node syncNode in GetTree().GetNodesInGroup("synced_objects"))
    {
        if (syncNode.GetParent() is not Node2D obj)
            continue;
        float dist = localPlayer.GlobalPosition.DistanceTo(obj.GlobalPosition);
        var multiplayerSync = (MultiplayerSynchronizer)syncNode;
        if (dist < 200.0f)
            multiplayerSync.ReplicationInterval = 0.05;  // 20 Hz — nearby
        else if (dist < 600.0f)
            multiplayerSync.ReplicationInterval = 0.1;   // 10 Hz — medium
        else
            multiplayerSync.ReplicationInterval = 0.5;   // 2 Hz  — distant
    }
}
```

### Reliable vs Unreliable Channels

| Data Type | Channel | Why |
|---|---|---|
| Position, velocity | `unreliable` | Timeliness matters; a dropped packet will be superseded by the next one |
| Health, score, kills | `reliable` | Must arrive and in order; gaps cause incorrect state |
| Spawn / despawn events | `reliable` | One-time events that must not be missed |
| Chat messages | `reliable` | Ordering and delivery matter to the user |

In Godot, set the channel per `@rpc` annotation:

```gdscript
@rpc("any_peer", "call_remote", "unreliable")
func update_position(pos: Vector2) -> void:
    synced_position = pos

@rpc("any_peer", "call_remote", "reliable")
func take_damage(amount: int) -> void:
    synced_health -= amount
```

```csharp
[Rpc(MultiplayerApi.RpcMode.AnyPeer, CallLocal = false, TransferMode = MultiplayerPeer.TransferModeEnum.Unreliable)]
private void UpdatePosition(Vector2 pos)
{
    SyncedPosition = pos;
}

[Rpc(MultiplayerApi.RpcMode.AnyPeer, CallLocal = false, TransferMode = MultiplayerPeer.TransferModeEnum.Reliable)]
private void TakeDamage(int amount)
{
    SyncedHealth -= amount;
}
```

---

## 8. Implementation Checklist

- [ ] `MultiplayerSynchronizer` is a direct child of the node it replicates
- [ ] Only the **authority** peer writes to synced properties; others are read-only
- [ ] `set_multiplayer_authority()` is called at spawn time with the correct peer ID
- [ ] `replication_interval` and `delta_interval` are tuned for the object's update rate
- [ ] Remote player visuals use interpolation in `_process`, not `_physics_process`
- [ ] Interpolation stores previous and current state and blends using `Engine.get_physics_interpolation_fraction()`
- [ ] Client-side prediction is applied only to the local player's own character
- [ ] Pending input buffer is bounded (max ~128 ticks) to prevent memory growth
- [ ] Reconciliation threshold prevents jitter from micro-corrections
- [ ] Position and velocity use `unreliable` RPC; state changes use `reliable`
- [ ] Float quantization is applied before sending position data over the network
- [ ] Lag compensation snapshot history is pruned each tick to a bounded window
- [ ] Server validates all hit detection; clients never self-report kills
- [ ] Distance-based sync rate reduces bandwidth for far-away objects
