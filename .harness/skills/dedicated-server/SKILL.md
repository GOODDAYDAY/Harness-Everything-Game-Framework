---
name: dedicated-server
description: Use when building dedicated servers — headless export, server architecture, lobby management, and deployment
---

# Dedicated Server in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, C# follows.

**Related skills:** See **multiplayer-basics** for ENet setup, RPCs, and authority model. See **multiplayer-sync** for state synchronization and interpolation.

---

## 1. Headless Export

A dedicated server runs without a display, GPU, or audio device. Godot supports this through the `--headless` flag and a dedicated export preset.

### --headless Flag

Pass `--headless` on the command line to suppress the display and audio drivers at runtime:

```
./my_game.x86_64 --headless
```

This is distinct from the `server` platform — `--headless` is a runtime flag that works on any exported binary. The `server` export template strips rendering entirely from the binary, reducing its size.

### Server Export Preset

In the Godot editor, create a dedicated **Linux/X11** (or **Linux Server**) export preset:

1. Open **Project → Export**.
2. Add a **Linux/X11** preset and name it `Linux Server`.
3. Under **Options → Binary**, enable **Export As Dedicated Server** (Godot 4.2+). This uses the server export template that omits rendering and audio code.
4. Under **Resources**, use the **Exclude** list to strip client-only assets (shaders, high-res textures, audio files) from the server PCK.

### Feature Tags

Use `OS.has_feature()` to branch between server and client code at runtime. Define a custom `server` feature in the export preset (Project Settings → Export → Custom Features) or rely on the built-in `dedicated_server` feature that the server template sets automatically:

```gdscript
# boot.gd — autoload, runs before any scene loads
extends Node

func _ready() -> void:
    if OS.has_feature("dedicated_server") or DisplayServer.get_name() == "headless":
        # Disable rendering-dependent systems
        RenderingServer.set_render_loop_enabled(false)
        # Start server logic
        ServerBootstrap.start()
    else:
        # Start client logic
        ClientBootstrap.start()
```

**Feature tag summary:**

| Tag | Set by | Notes |
|-----|--------|-------|
| `dedicated_server` | Server export template | Most reliable way to detect a server binary |
| `headless` | `--headless` CLI flag | Set at runtime, not baked into the binary |
| Custom `server` | Your export preset's Custom Features | Useful when sharing a binary between roles |

---

## 2. Server Architecture

### Game Loop Without Rendering

On a headless server, `_process` and `_physics_process` still run normally — but nothing is rendered. Keep all server logic in `_physics_process` for deterministic, fixed-rate updates.

### GDScript

```gdscript
# server_main.gd — add as autoload named ServerMain
extends Node

## Physics frames per second — matches Project Settings → Physics → Common → Physics Ticks Per Second.
## Override via --tick-rate CLI argument (see Section 5).
var tick_rate: int = 60

## Current server tick counter.
var server_tick: int = 0


func _ready() -> void:
    # Guard: this node does nothing on the client.
    if not _is_server():
        set_process(false)
        set_physics_process(false)
        return

    Engine.physics_ticks_per_second = tick_rate
    print("[Server] Started — tick rate: %d Hz" % tick_rate)


func _physics_process(_delta: float) -> void:
    server_tick += 1
    _tick_game_logic()


func _tick_game_logic() -> void:
    # All authoritative game simulation goes here.
    # Never reference Camera, CanvasLayer, or any rendering node from this path.
    pass


## Returns true when this process is acting as the authoritative server.
func _is_server() -> bool:
    # Covers both: dedicated binary and hosted listen-server.
    return multiplayer.is_server()
```

### Server-Only Logic Separated from Client

Structure your scenes so server-only nodes are in a dedicated branch and skipped on clients:

```gdscript
# world.gd
extends Node

@onready var server_systems: Node = $ServerSystems   # physics, AI, scoring
@onready var client_systems: Node = $ClientSystems   # camera, HUD, audio


func _ready() -> void:
    # Disable server systems on clients and vice versa.
    server_systems.set_process_mode(
        PROCESS_MODE_ALWAYS if multiplayer.is_server() else PROCESS_MODE_DISABLED
    )
    client_systems.set_process_mode(
        PROCESS_MODE_DISABLED if multiplayer.is_server() else PROCESS_MODE_ALWAYS
    )
```

### Engine.is_editor_hint() + is_server Checks

Use these guards at the top of scripts that must behave differently in the editor, on the server, and on clients:

```gdscript
func _ready() -> void:
    if Engine.is_editor_hint():
        return  # Skip all runtime setup in editor preview

    if multiplayer.is_server():
        _server_init()
    else:
        _client_init()


func _server_init() -> void:
    print("[Server] Initializing authoritative state")


func _client_init() -> void:
    print("[Client] Initializing local presentation layer")
```

### C#

```csharp
// ServerMain.cs — add as autoload named ServerMain
using Godot;

public partial class ServerMain : Node
{
    /// <summary>Physics ticks per second. Override via --tick-rate CLI argument.</summary>
    public int TickRate { get; set; } = 60;

    /// <summary>Current server tick counter.</summary>
    public int ServerTick { get; private set; }

    public override void _Ready()
    {
        if (!IsServer())
        {
            SetProcess(false);
            SetPhysicsProcess(false);
            return;
        }

        Engine.PhysicsTicksPerSecond = TickRate;
        GD.Print($"[Server] Started — tick rate: {TickRate} Hz");
    }

    public override void _PhysicsProcess(double delta)
    {
        ServerTick++;
        TickGameLogic();
    }

    private void TickGameLogic()
    {
        // All authoritative game simulation goes here.
    }

    private bool IsServer() => Multiplayer.IsServer();
}
```

```csharp
// World.cs
using Godot;

public partial class World : Node
{
    [Export] private Node _serverSystems = null!;
    [Export] private Node _clientSystems = null!;

    public override void _Ready()
    {
        if (Engine.IsEditorHint()) return;

        _serverSystems.ProcessMode = Multiplayer.IsServer()
            ? ProcessModeEnum.Always
            : ProcessModeEnum.Disabled;

        _clientSystems.ProcessMode = Multiplayer.IsServer()
            ? ProcessModeEnum.Disabled
            : ProcessModeEnum.Always;
    }
}
```

---

## 3. Lobby System

### GDScript

```gdscript
# lobby_manager.gd — autoload named LobbyManager, runs on server only
extends Node

## Maximum concurrent players. Set via --max-players CLI argument.
var max_players: int = 8

## player_list[peer_id] = { "username": String, "ready": bool }
var player_list: Dictionary = {}

signal player_joined(peer_id: int)
signal player_left(peer_id: int)
signal all_players_ready()


func _ready() -> void:
    if not multiplayer.is_server():
        return
    multiplayer.peer_connected.connect(_on_peer_connected)
    multiplayer.peer_disconnected.connect(_on_peer_disconnected)


# ── Connection handling ───────────────────────────────────────────────────────

func _on_peer_connected(peer_id: int) -> void:
    if player_list.size() >= max_players:
        # Reject: lobby is full.
        _kick_peer.rpc_id(peer_id, "Lobby is full")
        return

    player_list[peer_id] = {"username": "Player%d" % peer_id, "ready": false}
    print("[Lobby] Peer %d joined (%d/%d)" % [peer_id, player_list.size(), max_players])

    # Send the new player the current lobby state.
    _sync_lobby_state.rpc_id(peer_id, player_list)
    # Notify everyone else.
    _notify_player_joined.rpc(peer_id, player_list[peer_id]["username"])
    player_joined.emit(peer_id)


func _on_peer_disconnected(peer_id: int) -> void:
    if not player_list.has(peer_id):
        return
    var username: String = player_list[peer_id]["username"]
    player_list.erase(peer_id)
    _notify_player_left.rpc(peer_id, username)
    print("[Lobby] Peer %d left (%d/%d)" % [peer_id, player_list.size(), max_players])
    player_left.emit(peer_id)


# ── Ready state ───────────────────────────────────────────────────────────────

## Clients call this RPC to toggle their ready state.
@rpc("any_peer", "reliable")
func set_ready(is_ready: bool) -> void:
    var sender_id := multiplayer.get_remote_sender_id()
    if not player_list.has(sender_id):
        return
    player_list[sender_id]["ready"] = is_ready
    _notify_ready_changed.rpc(sender_id, is_ready)
    _check_all_ready()


func _check_all_ready() -> void:
    if player_list.is_empty():
        return
    for data in player_list.values():
        if not data["ready"]:
            return
    print("[Lobby] All players ready — starting game")
    all_players_ready.emit()
    _start_game.rpc()


# ── RPCs to clients ───────────────────────────────────────────────────────────

@rpc("authority", "reliable")
func _sync_lobby_state(state: Dictionary) -> void:
    # Client receives this once on join to populate its local lobby UI.
    pass  # Override in client-side lobby UI script


@rpc("authority", "reliable", "call_local")
func _notify_player_joined(peer_id: int, username: String) -> void:
    print("[Lobby] %s joined (id %d)" % [username, peer_id])


@rpc("authority", "reliable", "call_local")
func _notify_player_left(peer_id: int, username: String) -> void:
    print("[Lobby] %s left (id %d)" % [username, peer_id])


@rpc("authority", "reliable", "call_local")
func _notify_ready_changed(peer_id: int, is_ready: bool) -> void:
    print("[Lobby] Peer %d ready: %s" % [peer_id, str(is_ready)])


@rpc("authority", "reliable")
func _kick_peer(reason: String) -> void:
    push_error("[Lobby] Kicked: %s" % reason)
    multiplayer.multiplayer_peer.close()


@rpc("authority", "reliable", "call_local")
func _start_game() -> void:
    # Transition to gameplay scene on all peers.
    get_tree().change_scene_to_file("res://scenes/game.tscn")
```

### C#

```csharp
// LobbyManager.cs — autoload named LobbyManager, runs on server only
using System.Collections.Generic;
using Godot;
using Godot.Collections;

public partial class LobbyManager : Node
{
    /// <summary>Maximum concurrent players. Set via --max-players CLI argument.</summary>
    public int MaxPlayers { get; set; } = 8;

    /// <summary>PlayerList[peerId] = { "username": string, "ready": bool }</summary>
    private readonly System.Collections.Generic.Dictionary<long, PlayerData> _playerList = new();

    [Signal] public delegate void PlayerJoinedEventHandler(long peerId);
    [Signal] public delegate void PlayerLeftEventHandler(long peerId);
    [Signal] public delegate void AllPlayersReadyEventHandler();

    public record PlayerData(string Username, bool Ready);

    public override void _Ready()
    {
        if (!Multiplayer.IsServer()) return;
        Multiplayer.PeerConnected    += OnPeerConnected;
        Multiplayer.PeerDisconnected += OnPeerDisconnected;
    }

    private void OnPeerConnected(long peerId)
    {
        if (_playerList.Count >= MaxPlayers)
        {
            RpcId(peerId, MethodName.KickPeer, "Lobby is full");
            return;
        }

        _playerList[peerId] = new PlayerData($"Player{peerId}", false);
        GD.Print($"[Lobby] Peer {peerId} joined ({_playerList.Count}/{MaxPlayers})");

        var state = BuildLobbyStateDict();
        RpcId(peerId, MethodName.SyncLobbyState, state);
        Rpc(MethodName.NotifyPlayerJoined, peerId, _playerList[peerId].Username);
        EmitSignal(SignalName.PlayerJoined, peerId);
    }

    private void OnPeerDisconnected(long peerId)
    {
        if (!_playerList.TryGetValue(peerId, out var data)) return;
        _playerList.Remove(peerId);
        Rpc(MethodName.NotifyPlayerLeft, peerId, data.Username);
        GD.Print($"[Lobby] Peer {peerId} left ({_playerList.Count}/{MaxPlayers})");
        EmitSignal(SignalName.PlayerLeft, peerId);
    }

    // ── Ready state ────────────────────────────────────────────────────────────

    [Rpc(MultiplayerApi.RpcMode.AnyPeer, TransferMode = MultiplayerPeer.TransferModeEnum.Reliable)]
    public void SetReady(bool isReady)
    {
        long senderId = Multiplayer.GetRemoteSenderId();
        if (!_playerList.ContainsKey(senderId)) return;
        _playerList[senderId] = _playerList[senderId] with { Ready = isReady };
        Rpc(MethodName.NotifyReadyChanged, senderId, isReady);
        CheckAllReady();
    }

    private void CheckAllReady()
    {
        if (_playerList.Count == 0) return;
        foreach (var data in _playerList.Values)
            if (!data.Ready) return;

        GD.Print("[Lobby] All players ready — starting game");
        EmitSignal(SignalName.AllPlayersReady);
        Rpc(MethodName.StartGame);
    }

    // ── RPCs to clients ────────────────────────────────────────────────────────

    [Rpc(MultiplayerApi.RpcMode.Authority, TransferMode = MultiplayerPeer.TransferModeEnum.Reliable)]
    private void SyncLobbyState(Godot.Collections.Dictionary state) { /* client overrides */ }

    [Rpc(MultiplayerApi.RpcMode.Authority, CallLocal = true,
         TransferMode = MultiplayerPeer.TransferModeEnum.Reliable)]
    private void NotifyPlayerJoined(long peerId, string username)
        => GD.Print($"[Lobby] {username} joined (id {peerId})");

    [Rpc(MultiplayerApi.RpcMode.Authority, CallLocal = true,
         TransferMode = MultiplayerPeer.TransferModeEnum.Reliable)]
    private void NotifyPlayerLeft(long peerId, string username)
        => GD.Print($"[Lobby] {username} left (id {peerId})");

    [Rpc(MultiplayerApi.RpcMode.Authority, CallLocal = true,
         TransferMode = MultiplayerPeer.TransferModeEnum.Reliable)]
    private void NotifyReadyChanged(long peerId, bool isReady)
        => GD.Print($"[Lobby] Peer {peerId} ready: {isReady}");

    [Rpc(MultiplayerApi.RpcMode.Authority,
         TransferMode = MultiplayerPeer.TransferModeEnum.Reliable)]
    private void KickPeer(string reason)
    {
        GD.PushError($"[Lobby] Kicked: {reason}");
        Multiplayer.MultiplayerPeer.Close();
    }

    [Rpc(MultiplayerApi.RpcMode.Authority, CallLocal = true,
         TransferMode = MultiplayerPeer.TransferModeEnum.Reliable)]
    private void StartGame()
        => GetTree().ChangeSceneToFile("res://scenes/game.tscn");

    private Godot.Collections.Dictionary BuildLobbyStateDict()
    {
        var dict = new Godot.Collections.Dictionary();
        foreach (var (id, data) in _playerList)
        {
            dict[id] = new Godot.Collections.Dictionary
            {
                ["username"] = data.Username,
                ["ready"]    = data.Ready,
            };
        }
        return dict;
    }
}
```

---

## 4. Match Flow

### State Enum and Transitions

```
Lobby → Countdown → Gameplay → Results → Lobby
```

### GDScript

```gdscript
# match_manager.gd — autoload named MatchManager, runs on server only
extends Node

enum MatchState {
    LOBBY,
    COUNTDOWN,
    GAMEPLAY,
    RESULTS,
}

var current_state: MatchState = MatchState.LOBBY

## Countdown duration in seconds.
const COUNTDOWN_DURATION := 5.0
## Results screen duration in seconds.
const RESULTS_DURATION := 10.0

var _countdown_timer: float = 0.0
var _results_timer: float = 0.0


func _ready() -> void:
    if not multiplayer.is_server():
        set_physics_process(false)
        return
    # LobbyManager emits this when all players are ready.
    LobbyManager.all_players_ready.connect(_on_all_players_ready)


func _physics_process(delta: float) -> void:
    match current_state:
        MatchState.COUNTDOWN:
            _countdown_timer -= delta
            if _countdown_timer <= 0.0:
                _transition_to(MatchState.GAMEPLAY)
        MatchState.RESULTS:
            _results_timer -= delta
            if _results_timer <= 0.0:
                _transition_to(MatchState.LOBBY)


func _on_all_players_ready() -> void:
    _transition_to(MatchState.COUNTDOWN)


func _transition_to(new_state: MatchState) -> void:
    current_state = new_state
    print("[Match] Transitioning to %s" % MatchState.keys()[new_state])

    match new_state:
        MatchState.LOBBY:
            _reset_lobby()
            _notify_state_changed.rpc(new_state)

        MatchState.COUNTDOWN:
            _countdown_timer = COUNTDOWN_DURATION
            _notify_state_changed.rpc(new_state)
            _notify_countdown.rpc(COUNTDOWN_DURATION)

        MatchState.GAMEPLAY:
            _notify_state_changed.rpc(new_state)
            get_tree().change_scene_to_file("res://scenes/game.tscn")

        MatchState.RESULTS:
            _results_timer = RESULTS_DURATION
            _notify_state_changed.rpc(new_state)


## Call this from gameplay code when win/loss conditions are met.
func end_match() -> void:
    if current_state != MatchState.GAMEPLAY:
        return
    _transition_to(MatchState.RESULTS)


func _reset_lobby() -> void:
    # Reset ready states so players must re-confirm for the next match.
    for peer_id in LobbyManager.player_list:
        LobbyManager.player_list[peer_id]["ready"] = false


# ── RPCs ──────────────────────────────────────────────────────────────────────

@rpc("authority", "reliable", "call_local")
func _notify_state_changed(new_state: MatchState) -> void:
    print("[Match] State → %s" % MatchState.keys()[new_state])
    # Clients update their UI here.


@rpc("authority", "reliable", "call_local")
func _notify_countdown(seconds: float) -> void:
    print("[Match] Countdown: %.0f seconds" % seconds)
    # Clients start their countdown overlay here.
```

### C#

```csharp
// MatchManager.cs — autoload named MatchManager, runs on server only
using Godot;

public partial class MatchManager : Node
{
    public enum MatchState { Lobby, Countdown, Gameplay, Results }

    public MatchState CurrentState { get; private set; } = MatchState.Lobby;

    private const float CountdownDuration = 5.0f;
    private const float ResultsDuration   = 10.0f;

    private float _countdownTimer;
    private float _resultsTimer;

    public override void _Ready()
    {
        if (!Multiplayer.IsServer())
        {
            SetPhysicsProcess(false);
            return;
        }
        var lobby = GetNode<LobbyManager>("/root/LobbyManager");
        lobby.AllPlayersReady += OnAllPlayersReady;
    }

    public override void _PhysicsProcess(double delta)
    {
        switch (CurrentState)
        {
            case MatchState.Countdown:
                _countdownTimer -= (float)delta;
                if (_countdownTimer <= 0f)
                    TransitionTo(MatchState.Gameplay);
                break;

            case MatchState.Results:
                _resultsTimer -= (float)delta;
                if (_resultsTimer <= 0f)
                    TransitionTo(MatchState.Lobby);
                break;
        }
    }

    private void OnAllPlayersReady() => TransitionTo(MatchState.Countdown);

    private void TransitionTo(MatchState newState)
    {
        CurrentState = newState;
        GD.Print($"[Match] Transitioning to {newState}");

        switch (newState)
        {
            case MatchState.Lobby:
                ResetLobby();
                Rpc(MethodName.NotifyStateChanged, (int)newState);
                break;

            case MatchState.Countdown:
                _countdownTimer = CountdownDuration;
                Rpc(MethodName.NotifyStateChanged, (int)newState);
                Rpc(MethodName.NotifyCountdown, CountdownDuration);
                break;

            case MatchState.Gameplay:
                Rpc(MethodName.NotifyStateChanged, (int)newState);
                GetTree().ChangeSceneToFile("res://scenes/game.tscn");
                break;

            case MatchState.Results:
                _resultsTimer = ResultsDuration;
                Rpc(MethodName.NotifyStateChanged, (int)newState);
                break;
        }
    }

    public void EndMatch()
    {
        if (CurrentState != MatchState.Gameplay) return;
        TransitionTo(MatchState.Results);
    }

    private void ResetLobby()
    {
        var lobby = GetNode<LobbyManager>("/root/LobbyManager");
        foreach (var peerId in lobby.GetPlayerIds())
            lobby.SetPlayerReady(peerId, false);
    }

    [Rpc(MultiplayerApi.RpcMode.Authority, CallLocal = true,
         TransferMode = MultiplayerPeer.TransferModeEnum.Reliable)]
    private void NotifyStateChanged(int newState)
        => GD.Print($"[Match] State → {(MatchState)newState}");

    [Rpc(MultiplayerApi.RpcMode.Authority, CallLocal = true,
         TransferMode = MultiplayerPeer.TransferModeEnum.Reliable)]
    private void NotifyCountdown(float seconds)
        => GD.Print($"[Match] Countdown: {seconds:F0} seconds");
}
```

---

## 5. Server Configuration

### Command Line Argument Parsing

### GDScript

```gdscript
# server_config.gd — autoload named ServerConfig, parsed before any other autoload logic
extends Node

var port: int        = 7777
var max_players: int = 8
var tick_rate: int   = 60
var log_level: int   = 1   # 0 = quiet, 1 = info, 2 = verbose


func _ready() -> void:
    _parse_args()
    _load_config_file("user://server.cfg")
    _apply_env_vars()

    if OS.has_feature("dedicated_server") or DisplayServer.get_name() == "headless":
        print("[Config] port=%d  max_players=%d  tick_rate=%d" % [port, max_players, tick_rate])


func _parse_args() -> void:
    var args := OS.get_cmdline_args()
    var i := 0
    while i < args.size():
        match args[i]:
            "--port":
                if i + 1 < args.size():
                    port = int(args[i + 1])
                    i += 1
            "--max-players":
                if i + 1 < args.size():
                    max_players = int(args[i + 1])
                    i += 1
            "--tick-rate":
                if i + 1 < args.size():
                    tick_rate = int(args[i + 1])
                    i += 1
            "--log-level":
                if i + 1 < args.size():
                    log_level = int(args[i + 1])
                    i += 1
        i += 1


func _load_config_file(path: String) -> void:
    var cfg := ConfigFile.new()
    var err := cfg.load(path)
    if err != OK:
        return  # No config file — defaults remain in effect

    port        = cfg.get_value("server", "port",        port)
    max_players = cfg.get_value("server", "max_players", max_players)
    tick_rate   = cfg.get_value("server", "tick_rate",   tick_rate)
    log_level   = cfg.get_value("server", "log_level",   log_level)
    print("[Config] Loaded config from: %s" % path)


func _apply_env_vars() -> void:
    # Environment variables override the config file but are overridden by CLI args.
    var env_port := OS.get_environment("SERVER_PORT")
    if env_port != "":
        port = int(env_port)

    var env_max := OS.get_environment("SERVER_MAX_PLAYERS")
    if env_max != "":
        max_players = int(env_max)

    var env_tick := OS.get_environment("SERVER_TICK_RATE")
    if env_tick != "":
        tick_rate = int(env_tick)
```

**Example config file (`server.cfg`):**

```ini
[server]
port=7777
max_players=16
tick_rate=60
log_level=1
```

**Example launch:**

```bash
./my_game_server.x86_64 --headless --port 7778 --max-players 4 --tick-rate 30
```

### C#

```csharp
// ServerConfig.cs — autoload named ServerConfig
using Godot;

public partial class ServerConfig : Node
{
    public int  Port       { get; private set; } = 7777;
    public int  MaxPlayers { get; private set; } = 8;
    public int  TickRate   { get; private set; } = 60;
    public int  LogLevel   { get; private set; } = 1;

    public override void _Ready()
    {
        ParseArgs();
        LoadConfigFile("user://server.cfg");
        ApplyEnvVars();

        if (OS.HasFeature("dedicated_server") || DisplayServer.GetName() == "headless")
            GD.Print($"[Config] port={Port}  max_players={MaxPlayers}  tick_rate={TickRate}");
    }

    private void ParseArgs()
    {
        var args = OS.GetCmdlineArgs();
        for (int i = 0; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "--port"        when i + 1 < args.Length: Port       = int.Parse(args[++i]); break;
                case "--max-players" when i + 1 < args.Length: MaxPlayers = int.Parse(args[++i]); break;
                case "--tick-rate"   when i + 1 < args.Length: TickRate   = int.Parse(args[++i]); break;
                case "--log-level"   when i + 1 < args.Length: LogLevel   = int.Parse(args[++i]); break;
            }
        }
    }

    private void LoadConfigFile(string path)
    {
        var cfg = new ConfigFile();
        if (cfg.Load(path) != Error.Ok) return;

        Port       = (int)cfg.GetValue("server", "port",        Port);
        MaxPlayers = (int)cfg.GetValue("server", "max_players", MaxPlayers);
        TickRate   = (int)cfg.GetValue("server", "tick_rate",   TickRate);
        LogLevel   = (int)cfg.GetValue("server", "log_level",   LogLevel);
        GD.Print($"[Config] Loaded config from: {path}");
    }

    private void ApplyEnvVars()
    {
        var envPort = OS.GetEnvironment("SERVER_PORT");
        if (envPort != string.Empty) Port = int.Parse(envPort);

        var envMax = OS.GetEnvironment("SERVER_MAX_PLAYERS");
        if (envMax != string.Empty) MaxPlayers = int.Parse(envMax);

        var envTick = OS.GetEnvironment("SERVER_TICK_RATE");
        if (envTick != string.Empty) TickRate = int.Parse(envTick);
    }
}
```

---

## 6. Deployment

### Dockerfile

The server binary must be the Linux server export (`dedicated_server` feature enabled). Build a minimal container from the exported binary and its PCK file.

```dockerfile
# Dockerfile
FROM ubuntu:22.04

# Install runtime dependencies for ENet and audio stub (even headless needs libc).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libfontconfig1 \
        libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the exported server binary and PCK.
# Replace "my_game_server" with your actual export name.
COPY export/my_game_server.x86_64 ./my_game_server
COPY export/my_game_server.pck    ./my_game_server.pck

RUN chmod +x ./my_game_server

EXPOSE 7777/udp

ENV SERVER_PORT=7777
ENV SERVER_MAX_PLAYERS=8
ENV SERVER_TICK_RATE=60

ENTRYPOINT ["./my_game_server", "--headless"]
```

**Build and run:**

```bash
docker build -t my-game-server:latest .
docker run -d \
    -p 7777:7777/udp \
    -e SERVER_MAX_PLAYERS=16 \
    --name game-server \
    my-game-server:latest
```

### Linux VPS Setup

After uploading the server binary to a VPS (e.g. via `scp` or a CI artifact):

```bash
# 1. Make the binary executable.
chmod +x /opt/my-game/my_game_server.x86_64

# 2. Open the UDP port in the firewall (ufw example).
sudo ufw allow 7777/udp

# 3. Test a one-shot run to check for missing libraries.
/opt/my-game/my_game_server.x86_64 --headless --port 7777
```

If you see `error while loading shared libraries`, install the missing package reported and re-run.

### systemd Service File

```ini
# /etc/systemd/system/my-game-server.service
[Unit]
Description=My Game Dedicated Server
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=gameserver
WorkingDirectory=/opt/my-game
ExecStart=/opt/my-game/my_game_server.x86_64 --headless --port 7777 --max-players 16
Restart=on-failure
RestartSec=5s

# Redirect stdout/stderr to the journal (viewable with journalctl).
StandardOutput=journal
StandardError=journal
SyslogIdentifier=my-game-server

# Optional resource limits.
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable my-game-server
sudo systemctl start  my-game-server
sudo systemctl status my-game-server
```

### Log Output

Godot prints to stdout by default. With the systemd service above, use `journalctl` to inspect logs:

```bash
# Follow live output:
sudo journalctl -u my-game-server -f

# Last 100 lines:
sudo journalctl -u my-game-server -n 100

# Since last boot:
sudo journalctl -u my-game-server -b
```

To write structured logs from GDScript, prefix lines with a tag so they are easy to `grep`:

```gdscript
func log_info(msg: String) -> void:
    print("[INFO]  %s  %s" % [Time.get_datetime_string_from_system(), msg])

func log_error(msg: String) -> void:
    push_error("[ERROR] %s  %s" % [Time.get_datetime_string_from_system(), msg])
```

---

## 7. Checklist

- [ ] Export preset uses the **server** export template (`dedicated_server` feature is set automatically)
- [ ] Client-only assets (shaders, audio, high-res textures) are excluded from the server PCK
- [ ] Boot script checks `OS.has_feature("dedicated_server")` or `DisplayServer.get_name() == "headless"` to branch server vs client startup
- [ ] `RenderingServer.set_render_loop_enabled(false)` called on the server to prevent any render work
- [ ] Server-only nodes use `PROCESS_MODE_DISABLED` on clients; client-only nodes use `PROCESS_MODE_DISABLED` on the server
- [ ] `Engine.is_editor_hint()` guard at the top of `_ready()` in every script that has side effects
- [ ] `ServerConfig` parses `--port`, `--max-players`, `--tick-rate` from CLI args before `_ready()` of other autoloads
- [ ] Config file loading falls back gracefully when `server.cfg` does not exist
- [ ] Environment variables (`SERVER_PORT`, `SERVER_MAX_PLAYERS`, `SERVER_TICK_RATE`) are applied after config file, before CLI args
- [ ] `LobbyManager.player_list` size is checked against `max_players` before accepting a new peer
- [ ] Peer is kicked via RPC before closing if the lobby is full
- [ ] Ready states are reset when `MatchState` returns to `LOBBY` so players must re-confirm each round
- [ ] `MatchManager` only runs `_physics_process` on the server (`SetPhysicsProcess(false)` on clients)
- [ ] Countdown and results timers are driven by `_physics_process` delta, not `Timer` nodes (avoids scene dependency)
- [ ] Dockerfile copies both the binary and the `.pck` file to the image
- [ ] UDP port is opened in the VPS firewall before the first test run
- [ ] systemd service has `Restart=on-failure` so the server recovers from crashes automatically
- [ ] Logs are routed to the systemd journal and inspectable with `journalctl -u <service> -f`
