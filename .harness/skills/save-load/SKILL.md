---
name: save-load
description: Use when implementing save/load systems — ConfigFile, JSON, Resource serialization, save game architecture
---

# Save / Load Systems in Godot 4.3+

Choose the right serialization strategy for your data type. All examples target Godot 4.3+ with no deprecated APIs.

> **Related skills:** **resource-pattern** for custom Resource data containers, **inventory-system** for inventory serialization patterns, **godot-project-setup** for SaveManager autoload setup.

---

## 1. Strategy Comparison

| Strategy          | Best For                        | Readable | Editor Support | Notes                              |
|-------------------|---------------------------------|----------|----------------|------------------------------------|
| ConfigFile        | Settings, simple key-value data | Yes      | No             | Built-in INI-style, no extra deps  |
| JSON              | Game saves, flexible structures | Yes      | No             | Cross-platform, version-migratable |
| Resource .tres    | Editor-integrated data          | Yes      | Yes            | **NOT secure — never load untrusted files** |
| Resource .res     | Fast binary data                | No       | Yes            | **NOT secure — never load untrusted files** |

> **Security warning:** Loading `.tres` or `.res` files executes arbitrary GDScript embedded in the resource. Never load Resource files from untrusted sources (user-uploaded files, downloaded mods). Use ConfigFile or JSON for user-generated save data.

---

## 2. ConfigFile — Settings

Use ConfigFile for application settings: audio volumes, display options, key bindings. It produces a human-readable INI-style file.

### GDScript

```gdscript
# settings_manager.gd — add as autoload named SettingsManager
extends Node

const SETTINGS_PATH := "user://settings.cfg"

var _config := ConfigFile.new()


func _ready() -> void:
	load_settings()


func load_settings() -> void:
	var err := _config.load(SETTINGS_PATH)
	if err != OK:
		_set_defaults()
		save_settings()


func save_settings() -> void:
	var err := _config.save(SETTINGS_PATH)
	if err != OK:
		push_error("SettingsManager: failed to save settings — error %d" % err)


func get_setting(section: String, key: String, default: Variant = null) -> Variant:
	return _config.get_value(section, key, default)


func set_setting(section: String, key: String, value: Variant) -> void:
	_config.set_value(section, key, value)
	save_settings()


func _set_defaults() -> void:
	# Audio
	_config.set_value("audio", "master_volume", 1.0)
	_config.set_value("audio", "music_volume", 0.8)
	_config.set_value("audio", "sfx_volume", 1.0)
	# Display
	_config.set_value("display", "fullscreen", false)
	_config.set_value("display", "vsync", true)
	_config.set_value("display", "resolution_scale", 1.0)
```

**Usage:**

```gdscript
# Read
var vol: float = SettingsManager.get_setting("audio", "master_volume", 1.0)

# Write
SettingsManager.set_setting("audio", "master_volume", 0.5)
```

### C#

```csharp
// SettingsManager.cs — add as autoload named SettingsManager
using Godot;

public partial class SettingsManager : Node
{
    private const string SettingsPath = "user://settings.cfg";

    private readonly ConfigFile _config = new();

    public override void _Ready()
    {
        LoadSettings();
    }

    public void LoadSettings()
    {
        var err = _config.Load(SettingsPath);
        if (err != Error.Ok)
        {
            SetDefaults();
            SaveSettings();
        }
    }

    public void SaveSettings()
    {
        var err = _config.Save(SettingsPath);
        if (err != Error.Ok)
            GD.PushError($"SettingsManager: failed to save settings — error {err}");
    }

    public Variant GetSetting(string section, string key, Variant @default = default)
        => _config.GetValue(section, key, @default);

    public void SetSetting(string section, string key, Variant value)
    {
        _config.SetValue(section, key, value);
        SaveSettings();
    }

    private void SetDefaults()
    {
        // Audio
        _config.SetValue("audio", "master_volume", Variant.From(1.0f));
        _config.SetValue("audio", "music_volume",  Variant.From(0.8f));
        _config.SetValue("audio", "sfx_volume",    Variant.From(1.0f));
        // Display
        _config.SetValue("display", "fullscreen",       Variant.From(false));
        _config.SetValue("display", "vsync",            Variant.From(true));
        _config.SetValue("display", "resolution_scale", Variant.From(1.0f));
    }
}
```

**Usage:**

```csharp
// Read
float vol = SettingsManager.GetSetting("audio", "master_volume", Variant.From(1.0f)).As<float>();

// Write
SettingsManager.SetSetting("audio", "master_volume", Variant.From(0.5f));
```

---

## 3. JSON — Game Saves

Use JSON for game saves. It is portable, debuggable, and easy to version-migrate.

### GDScript

```gdscript
# save_manager.gd — add as autoload named SaveManager
extends Node

const SAVE_DIR       := "user://saves/"
const SAVE_EXTENSION := ".json"
const CURRENT_VERSION := 2


func _ready() -> void:
	DirAccess.make_dir_recursive_absolute(SAVE_DIR)


# ── Save ──────────────────────────────────────────────────────────────────────

func save_game(slot_name: String) -> bool:
	var player := get_tree().get_first_node_in_group("player")
	var world  := get_tree().get_first_node_in_group("world")

	var data: Dictionary = {
		"version":   CURRENT_VERSION,
		"timestamp": Time.get_unix_time_from_system(),
		"player":    _serialize_player(player),
		"world":     _serialize_world(world),
	}

	var json_string := JSON.stringify(data, "\t")
	var path        := SAVE_DIR + slot_name + SAVE_EXTENSION
	var file        := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		push_error("SaveManager: cannot open '%s' for writing — error %d" % [path, FileAccess.get_open_error()])
		return false

	file.store_string(json_string)
	return true


func _serialize_player(player: Node) -> Dictionary:
	return {
		"position":  {"x": player.global_position.x, "y": player.global_position.y},
		"health":    player.health,
		"inventory": player.inventory.duplicate(),
	}


func _serialize_world(world: Node) -> Dictionary:
	var enemies: Array = []
	for enemy in get_tree().get_nodes_in_group("enemies"):
		enemies.append({
			"scene_path": enemy.scene_file_path,
			"position":   {"x": enemy.global_position.x, "y": enemy.global_position.y},
			"health":     enemy.health,
		})
	return {"enemies": enemies}


# ── Load ──────────────────────────────────────────────────────────────────────

func load_game(slot_name: String) -> bool:
	var path := SAVE_DIR + slot_name + SAVE_EXTENSION
	if not FileAccess.file_exists(path):
		push_error("SaveManager: save file not found at '%s'" % path)
		return false

	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("SaveManager: cannot open '%s' for reading — error %d" % [path, FileAccess.get_open_error()])
		return false

	var json   := JSON.new()
	var err    := json.parse(file.get_as_text())
	if err != OK:
		push_error("SaveManager: JSON parse error in '%s': %s" % [path, json.get_error_message()])
		return false

	var data: Dictionary = json.data
	data = _migrate(data)

	var player := get_tree().get_first_node_in_group("player")
	var world  := get_tree().get_first_node_in_group("world")
	_deserialize_player(player, data["player"])
	_deserialize_world(world, data["world"])
	return true


func _deserialize_player(player: Node, data: Dictionary) -> void:
	player.global_position = Vector2(data["position"]["x"], data["position"]["y"])
	player.health          = data["health"]
	player.inventory       = data["inventory"].duplicate()


func _deserialize_world(world: Node, data: Dictionary) -> void:
	# Remove existing enemies spawned at runtime
	for enemy in get_tree().get_nodes_in_group("enemies"):
		enemy.queue_free()

	for entry: Dictionary in data["enemies"]:
		var scene: PackedScene = load(entry["scene_path"])
		if scene == null:
			push_error("SaveManager: missing scene '%s'" % entry["scene_path"])
			continue
		var enemy: Node = scene.instantiate()
		world.add_child(enemy)
		enemy.global_position = Vector2(entry["position"]["x"], entry["position"]["y"])
		enemy.health          = entry["health"]


# ── Helpers ───────────────────────────────────────────────────────────────────

func get_save_slots() -> Array[String]:
	var slots: Array[String] = []
	var dir := DirAccess.open(SAVE_DIR)
	if dir == null:
		return slots
	dir.list_dir_begin()
	var file_name := dir.get_next()
	while file_name != "":
		if not dir.current_is_dir() and file_name.ends_with(SAVE_EXTENSION):
			slots.append(file_name.trim_suffix(SAVE_EXTENSION))
		file_name = dir.get_next()
	return slots


func delete_save(slot_name: String) -> bool:
	var path := SAVE_DIR + slot_name + SAVE_EXTENSION
	var err  := DirAccess.remove_absolute(path)
	if err != OK:
		push_error("SaveManager: failed to delete '%s' — error %d" % [path, err])
		return false
	return true


# ── Migration ─────────────────────────────────────────────────────────────────

func _migrate(data: Dictionary) -> Dictionary:
	var version: int = data.get("version", 0)

	if version < 1:
		# v0 → v1: add inventory array
		data["player"]["inventory"] = []
		version = 1

	if version < 2:
		# v1 → v2: add skills array to player
		data["player"]["skills"] = []
		version = 2

	data["version"] = CURRENT_VERSION
	return data
```

### C#

```csharp
// SaveManager.cs — add as autoload named SaveManager
using System.Collections.Generic;
using Godot;

public partial class SaveManager : Node
{
    private const string SaveDir        = "user://saves/";
    private const string SaveExtension  = ".json";
    private const int    CurrentVersion = 2;

    public override void _Ready()
    {
        DirAccess.MakeDirRecursiveAbsolute(SaveDir);
    }

    // ── Save ─────────────────────────────────────────────────────────────────

    public bool SaveGame(string slotName)
    {
        var player = GetTree().GetFirstNodeInGroup("player");
        var world  = GetTree().GetFirstNodeInGroup("world");

        var data = new Godot.Collections.Dictionary
        {
            ["version"]   = CurrentVersion,
            ["timestamp"] = Time.GetUnixTimeFromSystem(),
            ["player"]    = SerializePlayer(player),
            ["world"]     = SerializeWorld(world),
        };

        string json = Json.Stringify(data, "\t");
        string path = SaveDir + slotName + SaveExtension;

        using var file = FileAccess.Open(path, FileAccess.ModeFlags.Write);
        if (file == null)
        {
            GD.PushError($"SaveManager: cannot open '{path}' for writing — error {FileAccess.GetOpenError()}");
            return false;
        }

        file.StoreString(json);
        return true;
    }

    private Godot.Collections.Dictionary SerializePlayer(Node player)
    {
        var p = (CharacterBody2D)player;
        var health = p.GetNode<Node>("HealthComponent");
        return new Godot.Collections.Dictionary
        {
            ["position"]  = new Godot.Collections.Dictionary { ["x"] = p.GlobalPosition.X, ["y"] = p.GlobalPosition.Y },
            ["health"]    = health.Get("current_health"),
        };
    }

    private Godot.Collections.Dictionary SerializeWorld(Node world)
    {
        var enemies = new Godot.Collections.Array();
        foreach (Node enemy in GetTree().GetNodesInGroup("enemies"))
        {
            var e = (Node2D)enemy;
            var health = e.GetNode<Node>("HealthComponent");
            enemies.Add(new Godot.Collections.Dictionary
            {
                ["scene_path"] = enemy.SceneFilePath,
                ["position"]   = new Godot.Collections.Dictionary { ["x"] = e.GlobalPosition.X, ["y"] = e.GlobalPosition.Y },
                ["health"]     = health.Get("current_health"),
            });
        }
        return new Godot.Collections.Dictionary { ["enemies"] = enemies };
    }

    // ── Load ─────────────────────────────────────────────────────────────────

    public bool LoadGame(string slotName)
    {
        string path = SaveDir + slotName + SaveExtension;
        if (!FileAccess.FileExists(path))
        {
            GD.PushError($"SaveManager: save file not found at '{path}'");
            return false;
        }

        using var file = FileAccess.Open(path, FileAccess.ModeFlags.Read);
        if (file == null)
        {
            GD.PushError($"SaveManager: cannot open '{path}' for reading — error {FileAccess.GetOpenError()}");
            return false;
        }

        var json    = new Json();
        var err     = json.Parse(file.GetAsText());
        if (err != Error.Ok)
        {
            GD.PushError($"SaveManager: JSON parse error in '{path}': {json.GetErrorMessage()}");
            return false;
        }

        var data = json.Data.AsGodotDictionary();
        data = Migrate(data);

        var player = GetTree().GetFirstNodeInGroup("player");
        var world  = GetTree().GetFirstNodeInGroup("world");
        DeserializePlayer(player, data["player"].AsGodotDictionary());
        DeserializeWorld(world,   data["world"].AsGodotDictionary());
        return true;
    }

    private void DeserializePlayer(Node player, Godot.Collections.Dictionary data)
    {
        var p = (CharacterBody2D)player;
        var pos = data["position"].AsGodotDictionary();
        p.GlobalPosition = new Vector2(pos["x"].As<float>(), pos["y"].As<float>());
        var health = p.GetNode<Node>("HealthComponent");
        health.Set("current_health", data["health"].As<int>());
    }

    private void DeserializeWorld(Node world, Godot.Collections.Dictionary data)
    {
        foreach (Node enemy in GetTree().GetNodesInGroup("enemies"))
            enemy.QueueFree();

        foreach (Variant entry in data["enemies"].AsGodotArray())
        {
            var e     = entry.AsGodotDictionary();
            var scene = GD.Load<PackedScene>(e["scene_path"].As<string>());
            if (scene == null)
            {
                GD.PushError($"SaveManager: missing scene '{e["scene_path"]}'");
                continue;
            }
            var enemy  = scene.Instantiate();
            world.AddChild(enemy);
            var pos    = e["position"].AsGodotDictionary();
            var node   = (Node2D)enemy;
            node.GlobalPosition = new Vector2(pos["x"].As<float>(), pos["y"].As<float>());
            var health = enemy.GetNode<Node>("HealthComponent");
            health.Set("current_health", e["health"].As<int>());
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    public List<string> GetSaveSlots()
    {
        var slots = new List<string>();
        using var dir = DirAccess.Open(SaveDir);
        if (dir == null) return slots;

        dir.ListDirBegin();
        string fileName = dir.GetNext();
        while (fileName != "")
        {
            if (!dir.CurrentIsDir() && fileName.EndsWith(SaveExtension))
                slots.Add(fileName[..^SaveExtension.Length]);
            fileName = dir.GetNext();
        }
        return slots;
    }

    public bool DeleteSave(string slotName)
    {
        string path = SaveDir + slotName + SaveExtension;
        var err     = DirAccess.RemoveAbsolute(path);
        if (err != Error.Ok)
        {
            GD.PushError($"SaveManager: failed to delete '{path}' — error {err}");
            return false;
        }
        return true;
    }

    // ── Migration ─────────────────────────────────────────────────────────────

    private Godot.Collections.Dictionary Migrate(Godot.Collections.Dictionary data)
    {
        int version = data.ContainsKey("version") ? data["version"].As<int>() : 0;

        if (version < 1)
        {
            // v0 → v1: add inventory array
            data["player"].AsGodotDictionary()["inventory"] = new Godot.Collections.Array();
            version = 1;
        }

        if (version < 2)
        {
            // v1 → v2: add skills array to player
            data["player"].AsGodotDictionary()["skills"] = new Godot.Collections.Array();
            version = 2;
        }

        data["version"] = CurrentVersion;
        return data;
    }
}
```

---

## 4. Save Architecture Pattern

For complex games, use the "saveable" group pattern. SaveManager collects serialized data from all registered nodes on save, then distributes data back to them on load.

```
SaveManager.save_game()
    │
    ├─► get_nodes_in_group("saveable")
    │       └─► node.serialize.call()  →  { id, data }
    │
    └─► write combined dict to disk

SaveManager.load_game()
    │
    ├─► read dict from disk
    │
    └─► get_nodes_in_group("saveable")
            └─► node.deserialize.call(data[node.id])
```

### SaveableComponent Pattern

Add this component to any node that needs to participate in saving.

**GDScript (`saveable_component.gd`)**

```gdscript
# Attach to any node that should save/load its own state.
class_name SaveableComponent
extends Node

## Unique stable ID for this saveable object (set in the Inspector).
@export var save_id: String = ""

## Assign a Callable that returns a Dictionary of state to save.
var serialize: Callable = func() -> Dictionary:
	push_error("SaveableComponent: serialize not set on '%s'" % get_parent().name)
	return {}

## Assign a Callable that accepts a Dictionary to restore state from.
var deserialize: Callable = func(_data: Dictionary) -> void:
	push_error("SaveableComponent: deserialize not set on '%s'" % get_parent().name)


func _ready() -> void:
	add_to_group("saveable")
```

**Example — Chest node using SaveableComponent:**

```gdscript
# chest.gd
extends Node3D

@onready var saveable: SaveableComponent = $SaveableComponent

var is_open: bool = false
var contents: Array = ["sword", "potion"]


func _ready() -> void:
	saveable.serialize   = _serialize
	saveable.deserialize = _deserialize


func _serialize() -> Dictionary:
	return {"is_open": is_open, "contents": contents.duplicate()}


func _deserialize(data: Dictionary) -> void:
	is_open  = data["is_open"]
	contents = data["contents"].duplicate()
	if is_open:
		_play_open_animation()
```

---

## 5. Save File Locations

`user://` resolves to a platform-specific writable directory outside the project folder.

| Platform | Path                                                                          |
|----------|-------------------------------------------------------------------------------|
| Windows  | `%APPDATA%\Godot\app_userdata\<project-name>\`                                |
| macOS    | `~/Library/Application Support/Godot/app_userdata/<project-name>/`           |
| Linux    | `~/.local/share/godot/app_userdata/<project-name>/`                          |

> Always use `user://` for save data, never `res://`. The `res://` path is read-only in exported builds.

---

## 6. Version Migration

Always store a `version` integer in every save file. Apply migrations incrementally so any old save can be brought forward to the current format regardless of how many versions it has missed.

```gdscript
func _migrate(data: Dictionary) -> Dictionary:
	var version: int = data.get("version", 0)

	if version < 1:
		# v0 → v1: inventory did not exist, add empty array
		data["player"]["inventory"] = []
		version = 1

	if version < 2:
		# v1 → v2: skills system added, seed from empty array
		data["player"]["skills"] = []
		version = 2

	# v2 → v3: add stamina stat with default value
	if version < 3:
		data["player"]["stamina"] = 100
		version = 3

	data["version"] = CURRENT_VERSION
	return data
```

Key rules:
- Each migration block is additive — it only adds or transforms, never removes data
- Use `data.get("key", default)` defensively within migration blocks
- The version field must be written back before returning

---

## 7. Implementation Checklist

- [ ] Use ConfigFile for settings, JSON for game saves (not Resources)
- [ ] Every save file includes a `version` integer field
- [ ] Save path uses `user://`, never `res://`
- [ ] Call `DirAccess.make_dir_recursive_absolute()` before writing saves
- [ ] Vector2/Vector3 serialized as separate `x`/`y`/`z` floats (JSON has no Vector type)
- [ ] All file operations check return codes and call `push_error()` on failure
- [ ] `_migrate()` handles every version from 0 to current, applied incrementally
- [ ] Resource files (.tres/.res) are never used for player-controlled save data
- [ ] `get_save_slots()` and `delete_save()` helpers exist for UI slot management
- [ ] Saveable nodes use stable IDs that do not change between sessions
