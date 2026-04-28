---
name: audio-system
description: Use when implementing audio — audio buses, AudioStreamPlayer, spatial audio, music management, SFX pooling, and dynamic mixing
---

# Audio System in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, then C#.

> **Related skills:** **event-bus** for decoupled audio triggers, **save-load** for persisting audio settings, **resource-pattern** for audio data containers.

---

## 1. Core Concepts

### Audio Node Types

| Node                   | Dimensions | Use For                                       |
|------------------------|------------|-----------------------------------------------|
| `AudioStreamPlayer`    | Non-positional | Music, UI sounds, global SFX              |
| `AudioStreamPlayer2D`  | 2D positional  | Footsteps, gunfire, environmental sounds  |
| `AudioStreamPlayer3D`  | 3D positional  | Same as 2D but in 3D space                |

### Audio Bus Architecture

Godot routes all audio through **buses** (like a mixing console).

```
Master (always exists)
├── Music          → volume, effects for background music
├── SFX            → volume, effects for sound effects
│   ├── Footsteps  → sub-bus for fine-tuning
│   └── Weapons    → sub-bus for fine-tuning
└── UI             → volume for menu sounds
```

**Setup:** Bottom panel → Audio tab → Add buses, set names, route outputs.

Every AudioStreamPlayer has a `bus` property — set it to the target bus name (e.g., `"SFX"`, `"Music"`).

---

## 2. Basic Audio Playback

### GDScript

```gdscript
extends Node2D

@onready var sfx_player: AudioStreamPlayer2D = $AudioStreamPlayer2D
@onready var music_player: AudioStreamPlayer = $MusicPlayer

func _ready() -> void:
    # Play background music (looping is set on the AudioStream resource)
    music_player.play()

func play_jump_sound() -> void:
    sfx_player.stream = preload("res://audio/sfx/jump.wav")
    sfx_player.play()
```

### C#

```csharp
using Godot;

public partial class AudioExample : Node2D
{
    private AudioStreamPlayer2D _sfxPlayer;
    private AudioStreamPlayer _musicPlayer;

    public override void _Ready()
    {
        _sfxPlayer = GetNode<AudioStreamPlayer2D>("AudioStreamPlayer2D");
        _musicPlayer = GetNode<AudioStreamPlayer>("MusicPlayer");
        _musicPlayer.Play();
    }

    public void PlayJumpSound()
    {
        _sfxPlayer.Stream = GD.Load<AudioStream>("res://audio/sfx/jump.wav");
        _sfxPlayer.Play();
    }
}
```

### Looping Audio

Looping is configured on the **AudioStream resource**, not the player node:

- **WAV:** Import tab → Loop Mode → Forward (or Ping-Pong)
- **OGG:** Import tab → Loop → On, set Loop Offset
- **MP3:** Import tab → Loop → On

> Always use OGG Vorbis for music (smaller files, good quality). Use WAV for short SFX (no decoding latency). Avoid MP3 for SFX — it adds silence at the start.

---

## 3. Audio Bus Management

### Setting Volume from Code

Godot uses **decibels (dB)** for volume. Linear-to-dB conversion is required for sliders.

#### GDScript

```gdscript
# Get bus index by name
var bus_index: int = AudioServer.get_bus_index("SFX")

# Set volume in dB directly
AudioServer.set_bus_volume_db(bus_index, -6.0)  # -6 dB = ~50% perceived volume

# Convert linear (0.0–1.0) to dB — use for UI sliders
func set_bus_volume_linear(bus_name: String, linear: float) -> void:
    var index := AudioServer.get_bus_index(bus_name)
    AudioServer.set_bus_volume_db(index, linear_to_db(linear))

# Mute / unmute a bus
AudioServer.set_bus_mute(bus_index, true)

# Read current volume as linear (for displaying on a slider)
func get_bus_volume_linear(bus_name: String) -> float:
    var index := AudioServer.get_bus_index(bus_name)
    return db_to_linear(AudioServer.get_bus_volume_db(index))
```

#### C#

```csharp
int busIndex = AudioServer.GetBusIndex("SFX");

// Set volume in dB
AudioServer.SetBusVolumeDb(busIndex, -6.0f);

// Linear to dB conversion for UI sliders
public void SetBusVolumeLinear(string busName, float linear)
{
    int index = AudioServer.GetBusIndex(busName);
    AudioServer.SetBusVolumeDb(index, Mathf.LinearToDb(linear));
}

// Mute / unmute
AudioServer.SetBusMute(busIndex, true);

// Read current volume as linear
public float GetBusVolumeLinear(string busName)
{
    int index = AudioServer.GetBusIndex(busName);
    return Mathf.DbToLinear(AudioServer.GetBusVolumeDb(index));
}
```

### Audio Bus Effects

Add effects to buses in the Audio panel (bottom dock). Common effects:

| Effect          | Use For                                     |
|-----------------|---------------------------------------------|
| `Reverb`        | Cave, cathedral, bathroom ambience           |
| `Delay`         | Echo effects                                 |
| `Compressor`    | Normalize loud/quiet sounds (master bus)     |
| `Limiter`       | Prevent clipping on master bus               |
| `LowPassFilter` | Muffled sounds (underwater, behind walls)    |
| `HighPassFilter` | Thin/tinny sound (radio, phone)             |
| `Chorus`        | Thicken sounds                               |
| `Distortion`    | Gritty/overdrive effects                     |
| `EQ`            | Fine-tune frequency bands                    |

### Dynamic Effect Toggle

```gdscript
# Enable/disable an effect on a bus at runtime
var bus_index := AudioServer.get_bus_index("SFX")
var effect_index := 0  # First effect on the bus
AudioServer.set_bus_effect_enabled(bus_index, effect_index, true)

# Apply low-pass filter for "underwater" feel
func set_underwater(enabled: bool) -> void:
    var index := AudioServer.get_bus_index("SFX")
    # Assumes a LowPassFilter is the first effect on the SFX bus
    AudioServer.set_bus_effect_enabled(index, 0, enabled)
```

---

## 4. Spatial Audio (2D & 3D)

### AudioStreamPlayer2D

Automatically adjusts volume and panning based on distance to the nearest `AudioListener2D` (or the Camera2D if no listener exists).

```
Enemy (CharacterBody2D)
├── Sprite2D
└── AudioStreamPlayer2D   ← positioned at enemy's location
    bus = "SFX"
    max_distance = 1000.0
    attenuation = 1.0
```

Key properties:

| Property        | Description                                   | Default  |
|-----------------|-----------------------------------------------|----------|
| `max_distance`  | Beyond this distance, sound is silent          | 2000.0   |
| `attenuation`   | Volume falloff curve (1.0 = linear, higher = sharper) | 1.0 |
| `max_polyphony` | Max simultaneous instances of this player      | 1        |
| `panning_strength` | How much the sound pans left/right          | 1.0      |

### AudioStreamPlayer3D

Same concept but in 3D. Works with `AudioListener3D` (or the Camera3D).

Key additional properties:

| Property            | Description                                 |
|---------------------|---------------------------------------------|
| `unit_size`         | Distance at which volume is 0 dB            |
| `max_db`            | Maximum volume cap                          |
| `attenuation_model` | Inverse, InverseSquare, Logarithmic, Disabled |
| `doppler_tracking`  | Enable Doppler effect for moving sources    |

### AudioListener

```gdscript
# Make a specific camera the audio listener
# 2D: add AudioListener2D as child of Camera2D, call make_current()
# 3D: add AudioListener3D as child of Camera3D, call make_current()

# By default, the current Camera2D/3D acts as the listener.
# Only add an explicit AudioListener if you need a different listening position.
```

---

## 5. Music Manager (Autoload)

A global music manager that handles crossfading between tracks.

### GDScript

```gdscript
# music_manager.gd — add as autoload named MusicManager
extends Node

@export var crossfade_duration: float = 1.5

var _player_a: AudioStreamPlayer
var _player_b: AudioStreamPlayer
var _active_player: AudioStreamPlayer

func _ready() -> void:
    _player_a = AudioStreamPlayer.new()
    _player_a.bus = "Music"
    add_child(_player_a)

    _player_b = AudioStreamPlayer.new()
    _player_b.bus = "Music"
    add_child(_player_b)

    _active_player = _player_a


func play_music(stream: AudioStream, from_position: float = 0.0) -> void:
    # If already playing this track, do nothing
    if _active_player.stream == stream and _active_player.playing:
        return

    var next_player := _player_b if _active_player == _player_a else _player_a

    # Crossfade
    next_player.stream = stream
    next_player.volume_db = -80.0
    next_player.play(from_position)

    var tween := create_tween().set_parallel(true)
    tween.tween_property(_active_player, "volume_db", -80.0, crossfade_duration)
    tween.tween_property(next_player, "volume_db", 0.0, crossfade_duration)
    tween.chain().tween_callback(_active_player.stop)

    _active_player = next_player


func stop_music(fade_duration: float = 1.0) -> void:
    var tween := create_tween()
    tween.tween_property(_active_player, "volume_db", -80.0, fade_duration)
    tween.tween_callback(_active_player.stop)


func set_music_volume(linear: float) -> void:
    var index := AudioServer.get_bus_index("Music")
    AudioServer.set_bus_volume_db(index, linear_to_db(linear))
```

### C#

```csharp
using Godot;

public partial class MusicManager : Node
{
    [Export] public float CrossfadeDuration { get; set; } = 1.5f;

    private AudioStreamPlayer _playerA;
    private AudioStreamPlayer _playerB;
    private AudioStreamPlayer _activePlayer;

    public override void _Ready()
    {
        _playerA = new AudioStreamPlayer { Bus = "Music" };
        AddChild(_playerA);

        _playerB = new AudioStreamPlayer { Bus = "Music" };
        AddChild(_playerB);

        _activePlayer = _playerA;
    }

    public void PlayMusic(AudioStream stream, float fromPosition = 0.0f)
    {
        if (_activePlayer.Stream == stream && _activePlayer.Playing)
            return;

        var nextPlayer = _activePlayer == _playerA ? _playerB : _playerA;

        nextPlayer.Stream = stream;
        nextPlayer.VolumeDb = -80.0f;
        nextPlayer.Play(fromPosition);

        var tween = CreateTween().SetParallel(true);
        tween.TweenProperty(_activePlayer, "volume_db", -80.0f, CrossfadeDuration);
        tween.TweenProperty(nextPlayer, "volume_db", 0.0f, CrossfadeDuration);
        tween.Chain().TweenCallback(Callable.From(_activePlayer.Stop));

        _activePlayer = nextPlayer;
    }

    public void StopMusic(float fadeDuration = 1.0f)
    {
        var tween = CreateTween();
        tween.TweenProperty(_activePlayer, "volume_db", -80.0f, fadeDuration);
        tween.TweenCallback(Callable.From(_activePlayer.Stop));
    }

    public void SetMusicVolume(float linear)
    {
        int index = AudioServer.GetBusIndex("Music");
        AudioServer.SetBusVolumeDb(index, Mathf.LinearToDb(linear));
    }
}
```

**Usage:**

```gdscript
# From any script:
MusicManager.play_music(preload("res://audio/music/boss_theme.ogg"))
MusicManager.stop_music(2.0)
```

---

## 6. SFX Pool

Prevent overlapping sounds and manage polyphony with a reusable SFX pool.

### GDScript

```gdscript
# sfx_pool.gd — add as autoload named SFXPool
extends Node

@export var pool_size: int = 16

var _players: Array[AudioStreamPlayer] = []
var _index: int = 0


func _ready() -> void:
    for i in pool_size:
        var player := AudioStreamPlayer.new()
        player.bus = "SFX"
        add_child(player)
        _players.append(player)


func play(stream: AudioStream, volume_db: float = 0.0, pitch_scale: float = 1.0) -> void:
    var player := _players[_index]
    _index = (_index + 1) % pool_size

    player.stream = stream
    player.volume_db = volume_db
    player.pitch_scale = pitch_scale
    player.play()


func play_random_pitch(stream: AudioStream, min_pitch: float = 0.9, max_pitch: float = 1.1) -> void:
    play(stream, 0.0, randf_range(min_pitch, max_pitch))
```

### C#

```csharp
using Godot;

public partial class SfxPool : Node
{
    [Export] public int PoolSize { get; set; } = 16;

    private AudioStreamPlayer[] _players;
    private int _index;

    public override void _Ready()
    {
        _players = new AudioStreamPlayer[PoolSize];
        for (int i = 0; i < PoolSize; i++)
        {
            var player = new AudioStreamPlayer { Bus = "SFX" };
            AddChild(player);
            _players[i] = player;
        }
    }

    public void Play(AudioStream stream, float volumeDb = 0.0f, float pitchScale = 1.0f)
    {
        var player = _players[_index];
        _index = (_index + 1) % PoolSize;

        player.Stream = stream;
        player.VolumeDb = volumeDb;
        player.PitchScale = pitchScale;
        player.Play();
    }

    public void PlayRandomPitch(AudioStream stream, float minPitch = 0.9f, float maxPitch = 1.1f)
    {
        Play(stream, 0.0f, (float)GD.RandRange(minPitch, maxPitch));
    }
}
```

**Usage:**

```gdscript
# Slightly randomize pitch to avoid repetitive sound
SFXPool.play_random_pitch(preload("res://audio/sfx/footstep.wav"))

# Fixed pitch and volume
SFXPool.play(preload("res://audio/sfx/explosion.wav"), -3.0, 1.0)
```

> **Why pool?** Creating new AudioStreamPlayer nodes every frame is wasteful. A pool recycles a fixed number of players in round-robin order. If pool_size players are already playing, the oldest one gets interrupted — this is usually fine for SFX.

---

## 7. 2D Positional SFX Pool

For spatial sounds that need position in 2D space.

### GDScript

```gdscript
# sfx_pool_2d.gd — add as autoload named SFXPool2D
extends Node

@export var pool_size: int = 16

var _players: Array[AudioStreamPlayer2D] = []
var _index: int = 0


func _ready() -> void:
    for i in pool_size:
        var player := AudioStreamPlayer2D.new()
        player.bus = "SFX"
        add_child(player)
        _players.append(player)


func play_at(stream: AudioStream, global_pos: Vector2, volume_db: float = 0.0, pitch_scale: float = 1.0) -> void:
    var player := _players[_index]
    _index = (_index + 1) % pool_size

    player.global_position = global_pos
    player.stream = stream
    player.volume_db = volume_db
    player.pitch_scale = pitch_scale
    player.play()
```

### C#

```csharp
using Godot;

public partial class SfxPool2D : Node
{
    [Export] public int PoolSize { get; set; } = 16;

    private AudioStreamPlayer2D[] _players;
    private int _index;

    public override void _Ready()
    {
        _players = new AudioStreamPlayer2D[PoolSize];
        for (int i = 0; i < PoolSize; i++)
        {
            var player = new AudioStreamPlayer2D { Bus = "SFX" };
            AddChild(player);
            _players[i] = player;
        }
    }

    public void PlayAt(AudioStream stream, Vector2 globalPos, float volumeDb = 0.0f, float pitchScale = 1.0f)
    {
        var player = _players[_index];
        _index = (_index + 1) % PoolSize;

        player.GlobalPosition = globalPos;
        player.Stream = stream;
        player.VolumeDb = volumeDb;
        player.PitchScale = pitchScale;
        player.Play();
    }
}
```

**Usage:**

```gdscript
# Play an explosion sound at the enemy's position
SFXPool2D.play_at(
    preload("res://audio/sfx/explosion.wav"),
    enemy.global_position,
    -3.0
)
```

---

## 8. Audio Settings Integration

Tie audio buses to a settings UI. Works well with the **save-load** skill's ConfigFile approach.

### GDScript

```gdscript
# In your settings/audio menu script:
@onready var master_slider: HSlider = %MasterSlider
@onready var music_slider: HSlider = %MusicSlider
@onready var sfx_slider: HSlider = %SFXSlider

func _ready() -> void:
    # Load saved values (0.0–1.0 linear)
    master_slider.value = _get_saved_volume("master")
    music_slider.value = _get_saved_volume("music")
    sfx_slider.value = _get_saved_volume("sfx")

    # Apply to buses
    _apply_volume("Master", master_slider.value)
    _apply_volume("Music", music_slider.value)
    _apply_volume("SFX", sfx_slider.value)

func _on_master_slider_value_changed(value: float) -> void:
    _apply_volume("Master", value)
    _save_volume("master", value)

func _on_music_slider_value_changed(value: float) -> void:
    _apply_volume("Music", value)
    _save_volume("music", value)

func _on_sfx_slider_value_changed(value: float) -> void:
    _apply_volume("SFX", value)
    _save_volume("sfx", value)

func _apply_volume(bus_name: String, linear: float) -> void:
    var index := AudioServer.get_bus_index(bus_name)
    if linear <= 0.01:
        AudioServer.set_bus_mute(index, true)
    else:
        AudioServer.set_bus_mute(index, false)
        AudioServer.set_bus_volume_db(index, linear_to_db(linear))

func _get_saved_volume(key: String) -> float:
    # Integrate with your settings system (see save-load skill)
    return SettingsManager.get_setting("audio", "%s_volume" % key, 1.0)

func _save_volume(key: String, value: float) -> void:
    SettingsManager.set_setting("audio", "%s_volume" % key, value)
```

### C#

```csharp
using Godot;

public partial class AudioSettings : Control
{
    private HSlider _masterSlider;
    private HSlider _musicSlider;
    private HSlider _sfxSlider;

    public override void _Ready()
    {
        _masterSlider = GetNode<HSlider>("%MasterSlider");
        _musicSlider = GetNode<HSlider>("%MusicSlider");
        _sfxSlider = GetNode<HSlider>("%SFXSlider");

        _masterSlider.Value = GetSavedVolume("master");
        _musicSlider.Value = GetSavedVolume("music");
        _sfxSlider.Value = GetSavedVolume("sfx");

        ApplyVolume("Master", (float)_masterSlider.Value);
        ApplyVolume("Music", (float)_musicSlider.Value);
        ApplyVolume("SFX", (float)_sfxSlider.Value);

        _masterSlider.ValueChanged += v => { ApplyVolume("Master", (float)v); SaveVolume("master", (float)v); };
        _musicSlider.ValueChanged += v => { ApplyVolume("Music", (float)v); SaveVolume("music", (float)v); };
        _sfxSlider.ValueChanged += v => { ApplyVolume("SFX", (float)v); SaveVolume("sfx", (float)v); };
    }

    private void ApplyVolume(string busName, float linear)
    {
        int index = AudioServer.GetBusIndex(busName);
        if (linear <= 0.01f)
            AudioServer.SetBusMute(index, true);
        else
        {
            AudioServer.SetBusMute(index, false);
            AudioServer.SetBusVolumeDb(index, Mathf.LinearToDb(linear));
        }
    }

    private float GetSavedVolume(string key)
    {
        // Integrate with your settings system (see save-load skill)
        return 1.0f;
    }

    private void SaveVolume(string key, float value)
    {
        // Integrate with your settings system (see save-load skill)
    }
}
```

---

## 9. Audio Import Best Practices

| Format    | Use For        | File Size | Decode Latency | Loop Support  |
|-----------|----------------|-----------|----------------|---------------|
| **WAV**   | Short SFX      | Large     | None (PCM)     | Via import    |
| **OGG**   | Music, long SFX| Small     | Minimal        | Via import    |
| **MP3**   | Music (fallback)| Small    | Has padding    | Via import    |

### Import Settings

In the Import dock (select an audio file):

- **Loop:** Enable for music and ambient loops
- **BPM / Beat Count / Bar Beats:** Set for rhythm-synced games
- **Force Mono:** Enable for 3D positional audio (stereo doesn't spatialize well)

> **Tip:** Keep SFX as 16-bit WAV at 44.1kHz. Godot stores WAV uncompressed in PCK, so they play instantly with zero decode overhead. For music, OGG Vorbis at quality 6–8 is a good balance.

---

## 10. Interactive & Adaptive Music (Godot 4.3+)

Godot 4.3 introduced specialized AudioStream types for dynamic music that responds to gameplay.

### AudioStreamPlaylist

Plays a sequence of audio streams in order. Use for level music with intro → loop → outro structure, or for jukebox-style playlists.

```gdscript
# Create a playlist with intro and loop
var playlist := AudioStreamPlaylist.new()
playlist.stream_count = 2
playlist.set_list_stream(0, preload("res://audio/music/boss_intro.ogg"))
playlist.set_list_stream(1, preload("res://audio/music/boss_loop.ogg"))
# BPM sync ensures transitions land on beat boundaries
playlist.bpm = 120.0
playlist.shuffle = false
playlist.loop = true    # loop the entire playlist

$MusicPlayer.stream = playlist
$MusicPlayer.play()
```

```csharp
var playlist = new AudioStreamPlaylist();
playlist.StreamCount = 2;
playlist.SetListStream(0, GD.Load<AudioStream>("res://audio/music/boss_intro.ogg"));
playlist.SetListStream(1, GD.Load<AudioStream>("res://audio/music/boss_loop.ogg"));
playlist.Shuffle = false;
playlist.Loop = true;

GetNode<AudioStreamPlayer>("MusicPlayer").Stream = playlist;
GetNode<AudioStreamPlayer>("MusicPlayer").Play();
```

### AudioStreamSynchronized

Plays multiple streams in perfect sync, allowing you to blend layers. Use for adaptive music — e.g. a base track with combat percussion that fades in when enemies appear.

```gdscript
# Three synchronized layers: base, drums, intensity
var sync := AudioStreamSynchronized.new()
sync.stream_count = 3
sync.set_sync_stream(0, preload("res://audio/music/ambient_base.ogg"))
sync.set_sync_stream(1, preload("res://audio/music/ambient_drums.ogg"))
sync.set_sync_stream(2, preload("res://audio/music/ambient_intense.ogg"))

# Set initial volumes — layer 0 full, others silent
sync.set_sync_stream_volume(0, 0.0)   # 0 dB
sync.set_sync_stream_volume(1, -80.0)  # silent
sync.set_sync_stream_volume(2, -80.0)  # silent

$MusicPlayer.stream = sync
$MusicPlayer.play()

# When combat starts — fade in drums layer
func _on_combat_started() -> void:
    var playback := $MusicPlayer.get_stream_playback() as AudioStreamPlaybackSynchronized
    # Tween the volume of layer 1 from silent to audible
    var tween := create_tween()
    tween.tween_method(
        func(db: float) -> void: playback.set_stream_volume(1, db),
        -80.0, 0.0, 1.5
    )
```

```csharp
var sync = new AudioStreamSynchronized();
sync.StreamCount = 3;
sync.SetSyncStream(0, GD.Load<AudioStream>("res://audio/music/ambient_base.ogg"));
sync.SetSyncStream(1, GD.Load<AudioStream>("res://audio/music/ambient_drums.ogg"));
sync.SetSyncStream(2, GD.Load<AudioStream>("res://audio/music/ambient_intense.ogg"));
sync.SetSyncStreamVolume(0, 0.0f);
sync.SetSyncStreamVolume(1, -80.0f);
sync.SetSyncStreamVolume(2, -80.0f);

GetNode<AudioStreamPlayer>("MusicPlayer").Stream = sync;
GetNode<AudioStreamPlayer>("MusicPlayer").Play();

// When combat starts — fade in drums layer
public void OnCombatStarted()
{
    var playback = GetNode<AudioStreamPlayer>("MusicPlayer").GetStreamPlayback() as AudioStreamPlaybackSynchronized;
    var tween = CreateTween();
    tween.TweenMethod(Callable.From<float>(db => playback.SetStreamVolume(1, db)), -80.0f, 0.0f, 1.5);
}
```

### AudioStreamInteractive

Transitions between music clips based on triggers (e.g. exploration → combat → boss). Define transition rules: crossfade, fade-to-silence, or immediate switch. Set transitions between clips by index with configurable fade times.

> **Note:** AudioStreamInteractive is configured primarily through the Inspector — set up clips and transition rules in the AudioStreamInteractive resource editor. Code triggers the switch:

```gdscript
# Switch to clip index 2 (e.g. "combat" clip)
var playback: AudioStreamPlaybackInteractive = $MusicPlayer.get_stream_playback()
playback.switch_to_clip(2)
```

```csharp
var playback = GetNode<AudioStreamPlayer>("MusicPlayer").GetStreamPlayback() as AudioStreamPlaybackInteractive;
playback.SwitchToClip(2);
```

### When to Use Which

| Stream Type | Use For |
|---|---|
| `AudioStreamPlaylist` | Sequential tracks (intro → loop), jukeboxes |
| `AudioStreamSynchronized` | Layered music with volume blending |
| `AudioStreamInteractive` | State-based music with designed transitions |

### Runtime WAV Loading (Godot 4.4+)

Godot 4.4 allows loading WAV files at runtime from user directories (mods, user-generated content):

```gdscript
func load_wav_from_path(path: String) -> AudioStreamWAV:
    var file := FileAccess.open(path, FileAccess.READ)
    if not file:
        push_error("Cannot open audio file: %s" % path)
        return null

    var wav := AudioStreamWAV.new()
    wav.data = file.get_buffer(file.get_length())
    wav.format = AudioStreamWAV.FORMAT_16_BITS
    wav.mix_rate = 44100
    wav.stereo = false
    return wav
```

> **Warning:** Runtime-loaded audio bypasses Godot's import system. You must set `format`, `mix_rate`, and `stereo` manually to match the actual file. Incorrect values produce garbled audio.

---

## 11. Common Pitfalls

| Symptom                            | Cause                                          | Fix                                                               |
|------------------------------------|-------------------------------------------------|-------------------------------------------------------------------|
| Sound doesn't play                 | Player not in the scene tree                    | Ensure the AudioStreamPlayer is `add_child()`'d before `play()`  |
| Sound plays but no audio heard     | Wrong bus name or bus is muted                  | Check `bus` property matches a bus name exactly (case-sensitive)   |
| Music restarts on scene change     | Player is part of the scene, not an autoload    | Move music player to an autoload (MusicManager)                   |
| Positional audio has no panning    | No AudioListener or Camera in the scene         | Add an AudioListener2D/3D or ensure a Camera is current           |
| Sound clicks or pops               | Audio file has no fade-in/fade-out              | Add a tiny fade (2–5ms) at start/end of WAV in audio editor      |
| Too many sounds playing at once    | No polyphony limit                              | Set `max_polyphony` on players or use an SFX pool                 |
| Volume slider feels non-linear     | Using dB directly instead of linear conversion  | Use `linear_to_db()` / `db_to_linear()` for slider values        |
| 3D audio sounds mono/flat          | Stereo source file                              | Import as mono (Force Mono in Import tab) for 3D spatialization   |
| MP3 has silence at start           | MP3 format adds encoder padding                 | Use WAV for timing-critical SFX, OGG for music                   |

---

## 12. Implementation Checklist

- [ ] Audio buses are set up: Master, Music, SFX (minimum)
- [ ] All AudioStreamPlayer nodes have the correct `bus` property assigned
- [ ] Music uses OGG Vorbis format; short SFX uses WAV
- [ ] Music player is in an autoload (survives scene changes)
- [ ] Music crossfading is implemented for smooth transitions
- [ ] SFX pool is used instead of creating new AudioStreamPlayer nodes dynamically
- [ ] Volume sliders use `linear_to_db()` / `db_to_linear()` conversion
- [ ] Near-zero slider values mute the bus (avoid `linear_to_db(0.0)` = `-inf`)
- [ ] 3D audio sources use mono audio files for proper spatialization
- [ ] Audio settings are saved and restored on game launch (ConfigFile or similar)
- [ ] Looping is configured on the AudioStream resource, not in code
- [ ] Interactive/adaptive music uses `AudioStreamPlaylist`, `AudioStreamSynchronized`, or `AudioStreamInteractive` (Godot 4.3+) instead of manual track-switching code
