---
name: addon-development
description: Use when creating Godot editor plugins — EditorPlugin, @tool scripts, custom inspectors, and dock panels
---

# Addon Development in Godot 4.3+

Editor plugins extend the Godot editor itself: custom node types, inspector panels, dock widgets, 3D gizmos, and toolbar buttons. All examples target Godot 4.3+ with no deprecated APIs.

> **Related skills:** **resource-pattern** for custom Resource editors, **godot-ui** for editor panel UI, **csharp-godot** for C# plugin development.

---

## 1. Plugin Structure

Every plugin lives inside `addons/` at the project root. Godot discovers plugins by scanning for `plugin.cfg` files.

```
res://
└── addons/
    └── my_plugin/
        ├── plugin.cfg          # required — plugin metadata
        ├── plugin.gd           # main EditorPlugin script (named in plugin.cfg)
        ├── my_inspector.gd     # optional — EditorInspectorPlugin
        ├── my_dock.tscn        # optional — dock panel scene
        └── icons/
            └── my_node.svg     # optional — custom node icons
```

`plugin.cfg` is a plain INI file. Godot reads it when scanning `addons/`. The `script` key must point to the main plugin script relative to the plugin folder.

Enable the plugin: **Project → Project Settings → Plugins** → tick the checkbox next to your plugin name.

---

## 2. @tool Annotation

`@tool` makes a GDScript (or its C# equivalent) run inside the editor process as well as at runtime. Without it, the script only runs when the game is playing.

### GDScript

```gdscript
@tool
extends Sprite2D

# Engine.is_editor_hint() is true when running inside the editor,
# false during a running game. Use it to guard editor-only logic.
func _process(delta: float) -> void:
    if Engine.is_editor_hint():
        # This block runs in the editor viewport — safe to call editor APIs.
        update_configuration_warnings()
    else:
        # Normal game logic here.
        pass


# _get_configuration_warnings() returns an array of strings shown as
# yellow warning icons on the node in the Scene panel.
func _get_configuration_warnings() -> PackedStringArray:
    var warnings := PackedStringArray()
    if texture == null:
        warnings.append("Texture is not set. Assign a Texture2D in the Inspector.")
    return warnings
```

### C#

```csharp
#if TOOLS
using Godot;

[Tool]
public partial class MyToolSprite : Sprite2D
{
    public override void _Process(double delta)
    {
        if (Engine.IsEditorHint())
        {
            // Editor-only logic — safe to call editor APIs here.
            UpdateConfigurationWarnings();
        }
        else
        {
            // Normal game logic.
        }
    }

    public override string[] _GetConfigurationWarnings()
    {
        if (Texture == null)
            return new[] { "Texture is not set. Assign a Texture2D in the Inspector." };
        return System.Array.Empty<string>();
    }
}
#endif
```

> Wrap C# tool scripts in `#if TOOLS` / `#endif` to prevent the class from being included in exported builds. GDScript `@tool` scripts are excluded from exports automatically.

**Key rules:**
- Add `@tool` / `[Tool]` at the top of every script that needs editor access.
- Always guard runtime-only code with `Engine.is_editor_hint()` to avoid crashing the editor when processing begins before the scene is fully loaded.
- Call `update_configuration_warnings()` whenever a property changes that might affect the warning state.

---

## 3. EditorPlugin Base

The main plugin script extends `EditorPlugin`. Godot calls `_enter_tree()` when the plugin is enabled and `_exit_tree()` when it is disabled or the project is closed. **Everything added in `_enter_tree()` must be removed in `_exit_tree()`.**

### GDScript

```gdscript
# plugin.gd
@tool
extends EditorPlugin


func _enter_tree() -> void:
    # Register a custom node type. The editor shows MyNode in the
    # "Add Node" dialog under the chosen base class, with a custom icon.
    add_custom_type(
        "MyNode",                              # name shown in editor
        "Node2D",                              # base class to extend
        preload("res://addons/my_plugin/my_node.gd"),
        preload("res://addons/my_plugin/icons/my_node.svg")
    )

    # Add a menu item to the Project menu (top toolbar).
    add_tool_menu_item("My Plugin Action", _on_tool_menu_item)


func _exit_tree() -> void:
    remove_custom_type("MyNode")
    remove_tool_menu_item("My Plugin Action")


func _on_tool_menu_item() -> void:
    print("My Plugin Action triggered")
```

### C#

```csharp
// Plugin.cs
#if TOOLS
using Godot;

[Tool]
public partial class MyPlugin : EditorPlugin
{
    public override void _EnterTree()
    {
        AddCustomType(
            "MyNode",
            "Node2D",
            GD.Load<Script>("res://addons/my_plugin/MyNode.cs"),
            GD.Load<Texture2D>("res://addons/my_plugin/icons/my_node.svg")
        );

        AddToolMenuItem("My Plugin Action", new Callable(this, MethodName.OnToolMenuAction));
    }

    public override void _ExitTree()
    {
        RemoveCustomType("MyNode");
        RemoveToolMenuItem("My Plugin Action");
    }

    private void OnToolMenuAction()
    {
        GD.Print("My Plugin Action triggered");
    }
}
#endif
```

**add_custom_type parameters:**

| Parameter | Description |
|---|---|
| `name` | The name shown in the Add Node dialog |
| `base` | String name of the Godot base class |
| `script` | The GDScript / C# script resource |
| `icon` | A `Texture2D`, typically a 16×16 SVG |

**add_tool_menu_item** adds an entry under **Project** in the top menu bar. Pass a `Callable` that takes no arguments.

---

## 4. Custom Inspector Plugin

`EditorInspectorPlugin` lets you replace or augment how specific node or resource types appear in the Inspector. Register it from your `EditorPlugin` and unregister on exit.

### GDScript

```gdscript
# my_inspector_plugin.gd
@tool
extends EditorInspectorPlugin

# Return true if this plugin should handle the given object.
# Called once when the Inspector selects a new object.
func _can_handle(object: Object) -> bool:
    return object is MyNode  # only handle MyNode instances


# Called before any properties are drawn. Insert controls at the top
# of the Inspector section for this object.
func _parse_begin(object: Object) -> void:
    var label := Label.new()
    label.text = "MyNode Inspector"
    label.add_theme_color_override("font_color", Color.CYAN)
    add_custom_control(label)


# Called for every exported property. Return true to suppress the
# default property editor and replace it with your own controls.
func _parse_property(
    object: Object,
    type: Variant.Type,
    name: String,
    hint_type: PropertyHint,
    hint_string: String,
    usage_flags: int,
    wide: bool
) -> bool:
    if name == "my_special_value":
        # Add a custom button instead of the default numeric field.
        var btn := Button.new()
        btn.text = "Reset to Default"
        btn.pressed.connect(func() -> void:
            object.my_special_value = 0
            # Notify the editor that a property changed so undo/redo works.
            EmitSignal("property_changed", name, 0)
        )
        add_custom_control(btn)
        return true  # suppress default editor for this property

    return false  # use default editor for all other properties
```

Register and unregister the plugin in your main `EditorPlugin`:

```gdscript
# plugin.gd
@tool
extends EditorPlugin

var _inspector_plugin: EditorInspectorPlugin


func _enter_tree() -> void:
    _inspector_plugin = preload("res://addons/my_plugin/my_inspector_plugin.gd").new()
    add_inspector_plugin(_inspector_plugin)


func _exit_tree() -> void:
    remove_inspector_plugin(_inspector_plugin)
```

**EditorInspectorPlugin method summary:**

| Method | When called | Return value |
|---|---|---|
| `_can_handle(object)` | On Inspector selection | `true` to claim the object |
| `_parse_begin(object)` | Before first property | — |
| `_parse_end(object)` | After last property | — |
| `_parse_category(object, category)` | At each category header | — |
| `_parse_group(object, group)` | At each group header | — |
| `_parse_property(...)` | Per property | `true` to hide default editor |

---

## 5. Custom Dock Panel

Docks are `Control`-based scenes added to one of the editor's dock slots. Add the control in `_enter_tree()` and remove it in `_exit_tree()`.

### GDScript

```gdscript
# plugin.gd
@tool
extends EditorPlugin

var _dock: Control


func _enter_tree() -> void:
    # Load a scene or instantiate a Control directly.
    _dock = preload("res://addons/my_plugin/my_dock.tscn").instantiate()

    # DOCK_SLOT_LEFT_UL = upper-left dock area (same as Scene/Import panel).
    # Other slots: DOCK_SLOT_LEFT_BL, DOCK_SLOT_RIGHT_UL, DOCK_SLOT_RIGHT_BL
    add_control_to_dock(DOCK_SLOT_LEFT_UL, _dock)


func _exit_tree() -> void:
    if _dock:
        remove_control_from_docks(_dock)
        _dock.queue_free()
        _dock = null
```

### C#

```csharp
#if TOOLS
using Godot;

[Tool]
public partial class MyPlugin : EditorPlugin
{
    private Control _dock;

    public override void _EnterTree()
    {
        _dock = GD.Load<PackedScene>("res://addons/my_plugin/MyDock.tscn").Instantiate<Control>();
        AddControlToDock(DockSlot.LeftUl, _dock);
    }

    public override void _ExitTree()
    {
        if (_dock != null)
        {
            RemoveControlFromDocks(_dock);
            _dock.QueueFree();
            _dock = null;
        }
    }
}
#endif
```

**Creating the dock scene:**

1. Create a new scene with a `Control` (or `VBoxContainer`, `PanelContainer`, etc.) as root.
2. Set the scene root's `Custom Minimum Size` so the dock has a sensible default size.
3. Add any UI controls (buttons, labels, trees) as children.
4. Save as `my_dock.tscn` inside your plugin folder.

**Available dock slots:**

| Constant | Location |
|---|---|
| `DOCK_SLOT_LEFT_UL` | Left column, upper (Scene / Import) |
| `DOCK_SLOT_LEFT_BL` | Left column, lower (FileSystem) |
| `DOCK_SLOT_RIGHT_UL` | Right column, upper (Inspector / Node) |
| `DOCK_SLOT_RIGHT_BL` | Right column, lower |

---

## 6. Custom Resource Editors

### EditorResourcePicker

`EditorResourcePicker` is the drop-down widget used in the Inspector for `Resource`-typed properties. This is an **editor-only** widget for building custom tooling — it cannot be used in runtime UI. You can embed it in your dock or inspector plugin to let users assign resources interactively.

```gdscript
# Inside a dock or editor tool scene
@tool
extends VBoxContainer

var _picker: EditorResourcePicker


func _ready() -> void:
    _picker = EditorResourcePicker.new()
    _picker.base_type = "Texture2D"      # restrict to Texture2D and subclasses
    _picker.resource_changed.connect(_on_resource_changed)
    add_child(_picker)


func _on_resource_changed(resource: Resource) -> void:
    if resource:
        print("Selected texture: ", resource.resource_path)
```

### Custom Resource Previews

Implement `EditorResourcePreviewGenerator` to show thumbnails for your custom resource types in the FileSystem panel and Inspector.

```gdscript
# my_preview_generator.gd
@tool
extends EditorResourcePreviewGenerator


# Return true if this generator handles the given type.
func _handles(type: String) -> bool:
    return type == "MyItemData"


# Generate a Texture2D thumbnail for the resource.
# size is the requested pixel size (typically 64 or 128).
func _generate(resource: Resource, size: Vector2i, metadata: Dictionary) -> Texture2D:
    var item := resource as MyItemData
    if item == null or item.icon == null:
        return null

    # Return the item's icon scaled to the requested size.
    var img: Image = item.icon.get_image().duplicate()
    img.resize(size.x, size.y, Image.INTERPOLATE_LANCZOS)
    return ImageTexture.create_from_image(img)


# Optional — generate from a path instead of a loaded resource.
# Return null to fall back to _generate.
func _generate_from_path(path: String, size: Vector2i, metadata: Dictionary) -> Texture2D:
    return null
```

Register the generator from your `EditorPlugin`:

```gdscript
var _preview_gen: EditorResourcePreviewGenerator

func _enter_tree() -> void:
    _preview_gen = preload("res://addons/my_plugin/my_preview_generator.gd").new()
    EditorInterface.get_resource_previewer().add_preview_generator(_preview_gen)

func _exit_tree() -> void:
    EditorInterface.get_resource_previewer().remove_preview_generator(_preview_gen)
```

---

## 7. Gizmos

`EditorNode3DGizmoPlugin` adds interactive handles and visual overlays to 3D nodes in the viewport. Register the plugin from your `EditorPlugin`.

### GDScript

```gdscript
# my_gizmo_plugin.gd
@tool
extends EditorNode3DGizmoPlugin

const HANDLE_RADIUS := 0.15


func _init() -> void:
    # Create a named material for the gizmo lines/handles.
    create_material("main", Color(0.5, 1.0, 0.0))
    create_handle_material("handles")


# Displayed in the View menu under "Show Gizmos".
func _get_gizmo_name() -> String:
    return "MyNode3DGizmo"


# Return true if this plugin should draw a gizmo for the given node.
func _has_gizmo(node: Node3D) -> bool:
    return node is MyNode3D


# Called whenever the node changes or the viewport is redrawn.
# Re-add all lines and handles here — do not cache between calls.
func _redraw(gizmo: EditorNode3DGizmo) -> void:
    gizmo.clear()

    var node := gizmo.get_node_3d() as MyNode3D
    if node == null:
        return

    # Draw a line from the node origin to a target point.
    var lines := PackedVector3Array([Vector3.ZERO, node.target_offset])
    gizmo.add_lines(lines, get_material("main", gizmo), false)

    # Add a draggable handle at the target offset position.
    var handles := PackedVector3Array([node.target_offset])
    gizmo.add_handles(handles, get_material("handles", gizmo), [])


# Return the current value of a handle as a Transform3D or Vector3
# so the editor can restore it on undo.
func _get_handle_value(gizmo: EditorNode3DGizmo, handle_id: int, secondary: bool) -> Variant:
    return (gizmo.get_node_3d() as MyNode3D).target_offset


# Called while dragging a handle. camera is the current viewport camera.
# point is the screen-space cursor position.
func _set_handle(
    gizmo: EditorNode3DGizmo,
    handle_id: int,
    secondary: bool,
    camera: Camera3D,
    point: Vector2
) -> void:
    var node := gizmo.get_node_3d() as MyNode3D
    # Project the screen point onto the XZ plane at the node's Y position.
    var from := camera.project_ray_origin(point)
    var dir  := camera.project_ray_normal(point)
    var dist := (node.global_position.y - from.y) / dir.y
    node.target_offset = from + dir * dist - node.global_position
    # Redraw after every drag update.
    _redraw(gizmo)


# Restore the handle to the value saved by _get_handle_value (for undo/redo).
func _commit_handle(
    gizmo: EditorNode3DGizmo,
    handle_id: int,
    secondary: bool,
    restore: Variant,
    cancel: bool
) -> void:
    var node := gizmo.get_node_3d() as MyNode3D
    if cancel:
        node.target_offset = restore
    else:
        # Register with undo/redo so Ctrl+Z works.
        get_undo_redo().create_action("Move MyNode3D Handle")
        get_undo_redo().add_do_property(node, "target_offset", node.target_offset)
        get_undo_redo().add_undo_property(node, "target_offset", restore)
        get_undo_redo().commit_action()
```

Register from `EditorPlugin`:

```gdscript
# plugin.gd
var _gizmo_plugin: EditorNode3DGizmoPlugin

func _enter_tree() -> void:
    _gizmo_plugin = preload("res://addons/my_plugin/my_gizmo_plugin.gd").new()
    add_node_3d_gizmo_plugin(_gizmo_plugin)

func _exit_tree() -> void:
    remove_node_3d_gizmo_plugin(_gizmo_plugin)
```

---

## 8. Testing Plugins

### Reloading a plugin in the editor

The fastest way to reload plugin code without restarting Godot:

1. **Project → Project Settings → Plugins** → untick the plugin → tick it again.
2. Alternatively, run this from **Editor → Execute Script** or the editor console:

```gdscript
var plugin_name := "my_plugin"
ProjectSettings.set_setting("editor_plugins/enabled", [])
ProjectSettings.save()
# Re-enable via the Plugins dialog.
```

For quicker iteration, save the plugin script — Godot hot-reloads `@tool` scripts automatically. Complex changes (new class registrations, dock changes) require a full disable/enable cycle.

### Debugging with print

`print()` and `push_error()` / `push_warning()` output to the Godot **Output** panel and the OS console when Godot is launched from a terminal.

```gdscript
func _enter_tree() -> void:
    print("[my_plugin] _enter_tree called")   # Output panel
    push_warning("[my_plugin] something unexpected")
    push_error("[my_plugin] something failed")  # also shown as red in Output
```

To launch with the OS console visible on Windows:

```
godot.exe --editor --path /path/to/project
```

### Plugin lifecycle gotchas

| Situation | What happens | Fix |
|---|---|---|
| Plugin enabled but `_enter_tree` crashes | Plugin remains enabled but broken; editor may be unstable | Disable, fix, re-enable |
| Forgot to remove a dock in `_exit_tree` | Dock orphan survives disable; duplicate docks appear on next enable | Always null-check and `queue_free()` in `_exit_tree` |
| Custom type still listed after removal | Stale entry in the project's `plugin_types` cache | Restart the editor once after `remove_custom_type` |
| `@tool` script crashes on property set | Editor shows the error but the script stops updating | Guard with `if Engine.is_editor_hint()` and validate inputs |
| C# plugin not compiling | Entire plugin silently fails to load | Check the **Mono → Build Project** output and fix C# errors first |
| `add_inspector_plugin` called twice | Inspector plugin fires twice per property | Track and guard with a null-check before `add_inspector_plugin` |

---

## 9. plugin.cfg Format

`plugin.cfg` is a plain INI file placed at the root of the plugin folder. All fields in the `[plugin]` section are required except `dependencies` and `installs`.

```ini
[plugin]

name="My Plugin"
description="Adds MyNode, a custom inspector, and a dock panel to the editor."
author="Your Name"
version="1.0.0"
script="plugin.gd"
```

**Field reference:**

| Key | Type | Description |
|---|---|---|
| `name` | String | Display name shown in Project Settings → Plugins |
| `description` | String | Short summary shown in the Plugins panel |
| `author` | String | Author name or organisation |
| `version` | String | Semantic version string (e.g. `"1.2.0"`) |
| `script` | String | Path to the main `EditorPlugin` script, **relative to the plugin folder** |

**Complete example with all optional fields:**

```ini
[plugin]

name="My Plugin"
description="Adds MyNode, a custom inspector, and a dock panel to the editor."
author="Your Name"
version="1.0.0"
script="plugin.gd"
```

> There are no other standard keys in Godot 4.x `plugin.cfg`. Dependency management is handled externally (e.g., by the Asset Library or manual installation instructions).

---

## 10. Checklist

- [ ] `addons/<plugin_name>/plugin.cfg` exists with `name`, `description`, `author`, `version`, `script`
- [ ] Main script extends `EditorPlugin` and is decorated with `@tool` (GDScript) or `[Tool]` inside `#if TOOLS` (C#)
- [ ] Everything registered in `_enter_tree()` is unregistered in `_exit_tree()`
- [ ] Custom node types use `add_custom_type` / `remove_custom_type` with a matching icon SVG
- [ ] `@tool` scripts guard editor-only code with `Engine.is_editor_hint()`
- [ ] `_get_configuration_warnings()` returns non-empty array when node is misconfigured
- [ ] Inspector plugins implement `_can_handle` to avoid handling unintended types
- [ ] `_parse_property` returns `true` only for properties that need a custom editor
- [ ] Dock scenes have a `Custom Minimum Size` set so the panel is usable at default dock widths
- [ ] Dock `Control` is freed with `queue_free()` in `_exit_tree()`
- [ ] `EditorResourcePreviewGenerator` is both added and removed via `EditorInterface.get_resource_previewer()`
- [ ] Gizmo plugin implements `_commit_handle` with `get_undo_redo()` so handle drags are undoable
- [ ] Plugin tested by full disable/enable cycle after each structural change
- [ ] `push_error()` used instead of silent failures in all `_enter_tree` setup paths
- [ ] C# plugin scripts wrapped in `#if TOOLS` / `#endif`
