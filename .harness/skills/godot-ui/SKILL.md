---
name: godot-ui
description: Use when building user interfaces — Control nodes, themes, anchors, containers, and layout patterns
---

# Godot UI — Control Nodes, Themes & Layout

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, then C#.

> **Related skills:** **responsive-ui** for multi-resolution scaling, **hud-system** for in-game HUD patterns, **dialogue-system** for dialogue UI presentation.

---

## 1. Control Node Hierarchy

### How Control Differs from Node2D

`Control` is the base class for all UI nodes. It lives in a separate branch of the scene tree from `Node2D`/`Node3D` and has a fundamentally different layout model.

| Feature | `Node2D` | `Control` |
|---|---|---|
| Position model | World-space `position` (pixels from parent) | Anchor + offset relative to parent rect |
| Size | No intrinsic size | Has `size`, `minimum_size`, `custom_minimum_size` |
| Theme | None | Inherits and overrides `Theme` resources |
| Focus | Not applicable | Built-in focus system (`focus_mode`, `grab_focus()`) |
| Mouse events | Manual via `_input` | `gui_input`, `mouse_entered`, `mouse_exited` |
| Layout helpers | None | `Container` subclasses auto-arrange children |

### Control as Base Class

Every UI widget (`Button`, `Label`, `LineEdit`, etc.) extends `Control`. The key properties defined on `Control` itself are:

- `anchor_left`, `anchor_top`, `anchor_right`, `anchor_bottom` — fractional values (0.0–1.0) relative to the parent's rect
- `offset_left`, `offset_top`, `offset_right`, `offset_bottom` — pixel offsets applied after the anchor is resolved
- `size_flags_horizontal`, `size_flags_vertical` — how the node participates in `Container` layout
- `theme` — a `Theme` resource; if `null` the node walks up the tree to find the nearest ancestor with one
- `focus_mode` — controls whether the node can receive keyboard/gamepad focus

Place UI nodes inside a `CanvasLayer` (or directly under the scene root's built-in canvas) so they always render on top of the 3D/2D world and are not affected by `Camera` transforms.

---

## 2. Common Container Nodes

| Container | Purpose | When to Use |
|---|---|---|
| `VBoxContainer` | Stacks children vertically, top to bottom | Lists, option rows, vertical menus |
| `HBoxContainer` | Stacks children horizontally, left to right | Toolbars, stat rows, horizontal nav |
| `GridContainer` | Arranges children in a fixed-column grid | Inventory grids, key-binding tables |
| `MarginContainer` | Adds padding around a single child | Wrapping any node to give it breathing room |
| `PanelContainer` | Draws a `StyleBox` background, then lays out children | Card UI, dialog boxes, HUD panels |
| `ScrollContainer` | Makes its single child scrollable; clips overflow | Long lists, logs, scrollable settings |
| `TabContainer` | Stacks children as named tabs; shows one at a time | Settings screens, multi-section panels |

**Sizing tips:**
- Set `size_flags_horizontal = SIZE_EXPAND_FILL` on children that should fill available space.
- Use `custom_minimum_size` to prevent a child from collapsing to zero.
- `MarginContainer` reads margin from the theme property `margin_*`; override at runtime with `add_theme_constant_override("margin_left", 16)`.

---

## 3. Anchors & Margins

### How Anchor Presets Work

An anchor is a point on the **parent** rect expressed as a fraction (0 = top/left edge, 1 = bottom/right edge). Godot resolves the final pixel position of each edge as:

```
final_left   = parent_width  * anchor_left   + offset_left
final_top    = parent_height * anchor_top    + offset_top
final_right  = parent_width  * anchor_right  + offset_right
final_bottom = parent_height * anchor_bottom + offset_bottom
```

The editor exposes built-in presets:

| Preset | Anchor values | Use case |
|---|---|---|
| Full Rect | L=0, T=0, R=1, B=1 | Overlay / fill parent — most common for root UI |
| Center | L=0.5, T=0.5, R=0.5, B=0.5 | Fixed-size widget centred in parent |
| Top Left | L=0, T=0, R=0, B=0 | Fixed-size widget pinned to top-left corner |
| Top Right | L=1, T=0, R=1, B=0 | Fixed-size widget pinned to top-right corner |
| Bottom Center | L=0.5, T=1, R=0.5, B=1 | HUD element anchored to bottom centre |

### Setting Anchors in Code

**GDScript:**

```gdscript
# Fill parent completely (equivalent to "Full Rect" preset)
$Panel.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

# Anchor to top-right corner, fixed 200x60 size
$HUDLabel.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
$HUDLabel.size = Vector2(200.0, 60.0)
# Fine-tune with a 16 px margin from the right and top edges
$HUDLabel.offset_right  = -16.0
$HUDLabel.offset_top    =  16.0

# Custom responsive anchor: right half of screen, full height
$SidePanel.anchor_left   = 0.5
$SidePanel.anchor_top    = 0.0
$SidePanel.anchor_right  = 1.0
$SidePanel.anchor_bottom = 1.0
$SidePanel.offset_left   = 0.0
$SidePanel.offset_top    = 0.0
$SidePanel.offset_right  = 0.0
$SidePanel.offset_bottom = 0.0
```

**C#:**

```csharp
// Fill parent completely
GetNode<Control>("Panel").SetAnchorsAndOffsetsPreset(Control.LayoutPreset.FullRect);

// Anchor to top-right corner
var label = GetNode<Control>("HUDLabel");
label.SetAnchorsAndOffsetsPreset(Control.LayoutPreset.TopRight);
label.Size = new Vector2(200f, 60f);
label.OffsetRight = -16f;
label.OffsetTop   =  16f;

// Custom anchor: right half of screen
var panel = GetNode<Control>("SidePanel");
panel.AnchorLeft   = 0.5f;
panel.AnchorTop    = 0.0f;
panel.AnchorRight  = 1.0f;
panel.AnchorBottom = 1.0f;
panel.OffsetLeft   = 0f;
panel.OffsetTop    = 0f;
panel.OffsetRight  = 0f;
panel.OffsetBottom = 0f;
```

### Anchor vs Offset

- **Anchor** determines *where on the parent* the node's edges track. It is resolution-independent.
- **Offset** is a *fixed pixel value* added after the anchor. It does not scale with the parent.

For fully responsive layout, keep offsets at 0 and let anchors do the work. Add small fixed offsets only for cosmetic margins (e.g., a 16 px gutter from an edge).

---

## 4. Theme System

### Creating a Theme Resource

Create a `Theme` resource once (`resources/themes/main_theme.tres`) and assign it to the root `Control` of each screen. All descendant nodes inherit it automatically.

### StyleBoxFlat

`StyleBoxFlat` draws a solid-colour, rounded rectangle with optional borders and shadows — no textures needed.

**GDScript:**

```gdscript
# Create and configure a StyleBoxFlat in code
var stylebox := StyleBoxFlat.new()
stylebox.bg_color = Color(0.1, 0.1, 0.15, 0.95)
stylebox.corner_radius_top_left     = 8
stylebox.corner_radius_top_right    = 8
stylebox.corner_radius_bottom_left  = 8
stylebox.corner_radius_bottom_right = 8
stylebox.border_width_left   = 2
stylebox.border_width_top    = 2
stylebox.border_width_right  = 2
stylebox.border_width_bottom = 2
stylebox.border_color = Color(0.4, 0.6, 1.0, 1.0)

# Apply to a PanelContainer's "panel" draw type
$DialogPanel.add_theme_stylebox_override("panel", stylebox)
```

**C#:**

```csharp
var stylebox = new StyleBoxFlat
{
    BgColor = new Color(0.1f, 0.1f, 0.15f, 0.95f),
    CornerRadiusTopLeft     = 8,
    CornerRadiusTopRight    = 8,
    CornerRadiusBottomLeft  = 8,
    CornerRadiusBottomRight = 8,
    BorderWidthLeft   = 2,
    BorderWidthTop    = 2,
    BorderWidthRight  = 2,
    BorderWidthBottom = 2,
    BorderColor = new Color(0.4f, 0.6f, 1.0f, 1.0f),
};

GetNode<PanelContainer>("DialogPanel").AddThemeStyleboxOverride("panel", stylebox);
```

### Font Overrides

**GDScript:**

```gdscript
# Load a font and apply it to a single Label
var font := preload("res://assets/fonts/Roboto-Regular.ttf") as FontFile
$TitleLabel.add_theme_font_override("font", font)
$TitleLabel.add_theme_font_size_override("font_size", 32)
```

**C#:**

```csharp
var font = GD.Load<FontFile>("res://assets/fonts/Roboto-Regular.ttf");
var label = GetNode<Label>("TitleLabel");
label.AddThemeFontOverride("font", font);
label.AddThemeFontSizeOverride("font_size", 32);
```

### Theme Inheritance

Godot resolves theme properties by walking up the scene tree:

1. Node's own `theme_override_*` properties (highest priority).
2. The nearest ancestor `Control` that has a `theme` resource assigned.
3. The project default theme (`Project > Project Settings > GUI > Theme > Custom`).
4. Godot's built-in fallback theme (lowest priority).

Assign one `Theme` resource at the root `CanvasLayer` or root `Control` of each screen. Avoid assigning themes deep in the tree unless you intentionally want to override a sub-section.

### theme_override_ Methods for Per-Node Styling

| Method | What it overrides | Example key |
|---|---|---|
| `add_theme_stylebox_override(name, stylebox)` | Background / border style | `"panel"`, `"normal"`, `"hover"`, `"pressed"` |
| `add_theme_font_override(name, font)` | Font resource | `"font"` |
| `add_theme_font_size_override(name, size)` | Font size (px) | `"font_size"` |
| `add_theme_color_override(name, color)` | Text / icon colour | `"font_color"`, `"icon_normal_color"` |
| `add_theme_constant_override(name, value)` | Integer constant | `"separation"`, `"margin_left"` |
| `add_theme_icon_override(name, texture)` | Icon texture | `"checked"`, `"unchecked"` |

Remove an override to fall back to the inherited theme:

```gdscript
$Button.remove_theme_stylebox_override("normal")
```

```csharp
GetNode<Button>("Button").RemoveThemeStyleboxOverride("normal");
```

---

## 5. Focus & Navigation

### Focus Modes

Set `focus_mode` on any `Control` node:

| Value | Constant | Behaviour |
|---|---|---|
| `0` | `Control.FOCUS_NONE` | Node cannot receive focus (e.g., decorative labels) |
| `1` | `Control.FOCUS_CLICK` | Receives focus only when clicked with the mouse |
| `2` | `Control.FOCUS_ALL` | Receives focus from mouse click, Tab, and gamepad/keyboard |

Interactive widgets (`Button`, `LineEdit`, `Slider`) default to `FOCUS_ALL`. Set `FOCUS_NONE` on `Label` and `TextureRect` nodes so they are skipped during keyboard navigation.

### focus_neighbor Properties

By default Godot infers neighbours geometrically. Override manually for non-linear layouts (e.g., a circular menu or a layout where nodes are not physically adjacent):

**GDScript:**

```gdscript
# Wire focus neighbours explicitly using NodePaths
$StartButton.focus_neighbor_bottom = $OptionsButton.get_path()
$OptionsButton.focus_neighbor_top  = $StartButton.get_path()
$OptionsButton.focus_neighbor_bottom = $QuitButton.get_path()
$QuitButton.focus_neighbor_top     = $OptionsButton.get_path()
# Wrap around: bottom of last → top of first
$QuitButton.focus_neighbor_bottom  = $StartButton.get_path()
$StartButton.focus_neighbor_top    = $QuitButton.get_path()
```

**C#:**

```csharp
var start   = GetNode<Button>("StartButton");
var options = GetNode<Button>("OptionsButton");
var quit    = GetNode<Button>("QuitButton");

start.FocusNeighborBottom   = options.GetPath();
options.FocusNeighborTop    = start.GetPath();
options.FocusNeighborBottom = quit.GetPath();
quit.FocusNeighborTop       = options.GetPath();
quit.FocusNeighborBottom    = start.GetPath();
start.FocusNeighborTop      = quit.GetPath();
```

### UI Navigation with Gamepad/Keyboard

Godot maps controller D-pad and left stick to the built-in `ui_left`, `ui_right`, `ui_up`, `ui_down` actions automatically. Ensure your interactive nodes have `FOCUS_ALL` and neighbours wired so gamepad navigation feels intentional.

- `ui_accept` (Enter / A button) — activates the focused widget.
- `ui_cancel` (Escape / B button) — typically used to go back; handle in `_unhandled_input`.
- Tab / Shift-Tab cycles through `FOCUS_ALL` nodes in tree order.

### grab_focus()

Call `grab_focus()` on the first interactive widget when a screen becomes visible so keyboard/gamepad users do not need to click before navigating.

**GDScript:**

```gdscript
func _ready() -> void:
    # Give focus to the first button when the menu appears
    $StartButton.grab_focus()
```

**C#:**

```csharp
public override void _Ready()
{
    GetNode<Button>("StartButton").GrabFocus();
}
```

---

## 6. Common UI Patterns

### Main Menu Scene Tree

```
MainMenu (Control — LayoutPreset: Full Rect)
└── Background (TextureRect — stretch: EXPAND_FIT, anchor: Full Rect)
└── CenterContainer (anchor: Full Rect)
    └── VBoxContainer
        ├── TitleLabel (Label)
        ├── StartButton (Button)
        ├── OptionsButton (Button)
        └── QuitButton (Button)
```

**GDScript:**

```gdscript
# scenes/screens/main_menu.gd
extends Control

func _ready() -> void:
    $CenterContainer/VBoxContainer/StartButton.grab_focus()

func _on_start_button_pressed() -> void:
    GameManager.change_scene("res://scenes/levels/level_01.tscn")

func _on_options_button_pressed() -> void:
    # Replace with your options screen path or overlay
    GameManager.change_scene("res://scenes/screens/options.tscn")

func _on_quit_button_pressed() -> void:
    get_tree().quit()
```

**C#:**

```csharp
// scenes/screens/MainMenu.cs
using Godot;

public partial class MainMenu : Control
{
    public override void _Ready()
    {
        GetNode<Button>("CenterContainer/VBoxContainer/StartButton").GrabFocus();
    }

    private void OnStartButtonPressed() =>
        GameManager.Instance.ChangeScene("res://scenes/levels/level_01.tscn");

    private void OnOptionsButtonPressed() =>
        GameManager.Instance.ChangeScene("res://scenes/screens/options.tscn");

    private void OnQuitButtonPressed() =>
        GetTree().Quit();
}
```

---

### Settings Screen with Tabs

```
OptionsScreen (Control — anchor: Full Rect)
└── PanelContainer (anchor: Full Rect)
    └── VBoxContainer
        ├── TitleLabel (Label — text: "Settings")
        ├── TabContainer
        │   ├── AudioTab (VBoxContainer — name: "Audio")
        │   │   ├── HBoxContainer
        │   │   │   ├── Label (text: "Master Volume")
        │   │   │   └── MasterSlider (HSlider)
        │   │   ├── HBoxContainer
        │   │   │   ├── Label (text: "Music Volume")
        │   │   │   └── MusicSlider (HSlider)
        │   │   └── HBoxContainer
        │   │       ├── Label (text: "SFX Volume")
        │   │       └── SFXSlider (HSlider)
        │   └── VideoTab (VBoxContainer — name: "Video")
        │       ├── HBoxContainer
        │       │   ├── Label (text: "Fullscreen")
        │       │   └── FullscreenCheck (CheckButton)
        │       └── HBoxContainer
        │           ├── Label (text: "Resolution")
        │           └── ResolutionOptions (OptionButton)
        └── CloseButton (Button — text: "Close")
```

**GDScript:**

```gdscript
# scenes/screens/options_screen.gd
extends Control

func _ready() -> void:
    var master_bus := AudioServer.get_bus_index("Master")
    $PanelContainer/VBoxContainer/TabContainer/AudioTab/HBoxContainer/MasterSlider.value = \
        db_to_linear(AudioServer.get_bus_volume_db(master_bus))

func _on_master_slider_value_changed(value: float) -> void:
    AudioServer.set_bus_volume_db(
        AudioServer.get_bus_index("Master"),
        linear_to_db(value)
    )

func _on_fullscreen_check_toggled(button_pressed: bool) -> void:
    DisplayServer.window_set_mode(
        DisplayServer.WINDOW_MODE_FULLSCREEN if button_pressed
        else DisplayServer.WINDOW_MODE_WINDOWED
    )

func _on_close_button_pressed() -> void:
    queue_free()   # or hide() if you want to keep state
```

**C#:**

```csharp
// scenes/screens/OptionsScreen.cs
using Godot;

public partial class OptionsScreen : Control
{
    public override void _Ready()
    {
        int masterBus = AudioServer.GetBusIndex("Master");
        var slider = GetNode<HSlider>(
            "PanelContainer/VBoxContainer/TabContainer/AudioTab/HBoxContainer/MasterSlider");
        slider.Value = Mathf.DbToLinear(AudioServer.GetBusVolumeDb(masterBus));
    }

    private void OnMasterSliderValueChanged(float value)
    {
        AudioServer.SetBusVolumeDb(
            AudioServer.GetBusIndex("Master"),
            Mathf.LinearToDb(value));
    }

    private void OnFullscreenCheckToggled(bool buttonPressed)
    {
        DisplayServer.WindowSetMode(buttonPressed
            ? DisplayServer.WindowMode.Fullscreen
            : DisplayServer.WindowMode.Windowed);
    }

    private void OnCloseButtonPressed() => QueueFree();
}
```

---

### Pause Menu Overlay

The pause menu lives in its own scene that is added to the tree at runtime. Set the root `Control`'s `process_mode` to `PROCESS_MODE_ALWAYS` so it continues running while the tree is paused.

```
PauseMenu (Control — anchor: Full Rect, process_mode: Always)
└── ColorRect (anchor: Full Rect, color: Color(0,0,0,0.6))
└── CenterContainer (anchor: Full Rect)
    └── PanelContainer
        └── VBoxContainer
            ├── Label (text: "Paused")
            ├── ResumeButton (Button)
            ├── OptionsButton (Button)
            └── QuitToMenuButton (Button)
```

**GDScript:**

```gdscript
# scenes/ui/pause_menu.gd
extends Control

func _ready() -> void:
    # Ensure this node and all children keep processing while paused
    process_mode = Node.PROCESS_MODE_ALWAYS
    $CenterContainer/PanelContainer/VBoxContainer/ResumeButton.grab_focus()

func _unhandled_input(event: InputEvent) -> void:
    if event.is_action_pressed("ui_cancel"):
        _on_resume_button_pressed()

func _on_resume_button_pressed() -> void:
    get_tree().paused = false
    queue_free()

func _on_options_button_pressed() -> void:
    var options := preload("res://scenes/screens/options_screen.tscn").instantiate()
    add_child(options)

func _on_quit_to_menu_button_pressed() -> void:
    get_tree().paused = false
    GameManager.change_scene("res://scenes/screens/main_menu.tscn")
```

**C#:**

```csharp
// scenes/ui/PauseMenu.cs
using Godot;

public partial class PauseMenu : Control
{
    public override void _Ready()
    {
        ProcessMode = ProcessModeEnum.Always;
        GetNode<Button>(
            "CenterContainer/PanelContainer/VBoxContainer/ResumeButton").GrabFocus();
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        if (@event.IsActionPressed("ui_cancel"))
            OnResumeButtonPressed();
    }

    private void OnResumeButtonPressed()
    {
        GetTree().Paused = false;
        QueueFree();
    }

    private void OnOptionsButtonPressed()
    {
        var options = GD.Load<PackedScene>("res://scenes/screens/options_screen.tscn").Instantiate();
        AddChild(options);
    }

    private void OnQuitToMenuButtonPressed()
    {
        GetTree().Paused = false;
        GameManager.Instance.ChangeScene("res://scenes/screens/main_menu.tscn");
    }
}
```

**Toggling the pause menu from game code (GDScript):**

```gdscript
# In your GameManager or a player HUD script
var _pause_menu_scene := preload("res://scenes/ui/pause_menu.tscn")
var _pause_menu: Control = null

func _unhandled_input(event: InputEvent) -> void:
    if event.is_action_just_pressed("ui_cancel"):
        if get_tree().paused:
            return  # PauseMenu handles its own resume
        _pause_menu = _pause_menu_scene.instantiate()
        get_tree().root.add_child(_pause_menu)
        get_tree().paused = true
```

---

## 7. Signals

Common UI signals and the nodes that emit them:

| Signal | Node(s) | When emitted | Signature |
|---|---|---|---|
| `pressed` | `Button`, `LinkButton` | Mouse click or keyboard/gamepad confirm | `()` |
| `toggled` | `Button` (toggle mode), `CheckButton`, `CheckBox` | Toggle state changes | `(button_pressed: bool)` |
| `text_changed` | `LineEdit`, `TextEdit` | User edits text | `(new_text: String)` |
| `text_submitted` | `LineEdit` | User presses Enter | `(new_text: String)` |
| `value_changed` | `HSlider`, `VSlider`, `SpinBox`, `ScrollBar` | Value changes | `(value: float)` |
| `item_selected` | `OptionButton`, `ItemList` | User selects an item | `(index: int)` |
| `tab_changed` | `TabContainer`, `TabBar` | Active tab changes | `(tab: int)` |
| `visibility_changed` | `Control` (all) | `show()`/`hide()`/`visible` toggled | `()` |
| `mouse_entered` | `Control` (all) | Mouse cursor enters the node's rect | `()` |
| `mouse_exited` | `Control` (all) | Mouse cursor leaves the node's rect | `()` |
| `focus_entered` | `Control` (all) | Node receives focus | `()` |
| `focus_exited` | `Control` (all) | Node loses focus | `()` |
| `resized` | `Control` (all) | Node's `size` property changes | `()` |
| `gui_input` | `Control` (all) | Any `InputEvent` within the node's rect | `(event: InputEvent)` |

**Connecting signals in GDScript:**

```gdscript
func _ready() -> void:
    $StartButton.pressed.connect(_on_start_button_pressed)
    $VolumeSlider.value_changed.connect(_on_volume_slider_value_changed)
    $SearchField.text_changed.connect(_on_search_field_text_changed)

func _on_start_button_pressed() -> void:
    pass

func _on_volume_slider_value_changed(value: float) -> void:
    pass

func _on_search_field_text_changed(new_text: String) -> void:
    pass
```

**Connecting signals in C#:**

```csharp
public override void _Ready()
{
    GetNode<Button>("StartButton").Pressed += OnStartButtonPressed;
    GetNode<HSlider>("VolumeSlider").ValueChanged += OnVolumeSliderValueChanged;
    GetNode<LineEdit>("SearchField").TextChanged += OnSearchFieldTextChanged;
}

private void OnStartButtonPressed() { }
private void OnVolumeSliderValueChanged(double value) { }
private void OnSearchFieldTextChanged(string newText) { }
```

---

## 8. Checklist

- [ ] Root UI `Control` has anchor preset **Full Rect** (or appropriate preset for the layout)
- [ ] All interactive widgets (`Button`, `LineEdit`, `Slider`) have `focus_mode = FOCUS_ALL`
- [ ] Decorative nodes (`Label`, `TextureRect`) have `focus_mode = FOCUS_NONE`
- [ ] Focus neighbours are wired for non-linear layouts so gamepad navigation wraps correctly
- [ ] `grab_focus()` called on the first interactive widget in `_ready()` for each screen
- [ ] Pause menu root `Control` has `process_mode = PROCESS_MODE_ALWAYS`
- [ ] One `Theme` resource assigned at the screen root — not duplicated on every child
- [ ] `StyleBoxFlat` used instead of image assets for simple solid-colour panels
- [ ] `add_theme_*_override()` used for per-node overrides rather than assigning a whole new `Theme`
- [ ] Containers (`VBoxContainer`, `HBoxContainer`, etc.) used for layout instead of manual `position` values
- [ ] `custom_minimum_size` set on widgets that must not collapse to zero
- [ ] Slider and volume code uses `linear_to_db` / `db_to_linear` — not raw linear values mapped to audio bus
- [ ] Signals connected in `_ready()` (or via the editor); no polling of UI state in `_process`
- [ ] Tab order in `TabContainer` matches logical reading / navigation order
