---
name: responsive-ui
description: Use when handling multiple resolutions — stretch modes, aspect ratios, DPI scaling, and mobile/desktop adaptation
---

# Responsive UI in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, then C#.

> **Related skills:** **godot-ui** for Control node layout and themes, **export-pipeline** for platform-specific export settings, **godot-project-setup** for initial project resolution settings.

---

## 1. Project Settings for Resolution

Configure base resolution and stretch behaviour in `Project > Project Settings > Display > Window`.

Key settings and their `.godot/project.godot` keys:

| Setting | project.godot key | Recommended value |
|---|---|---|
| Viewport width | `window/size/viewport_width` | `1920` (or your base design width) |
| Viewport height | `window/size/viewport_height` | `1080` (or your base design height) |
| Stretch mode | `window/stretch/mode` | `canvas_items` (most games) |
| Stretch aspect | `window/stretch/aspect` | `expand` (fill screen) or `keep` (letterbox) |
| Scale factor | `window/stretch/scale` | `1` (adjust for pixel art integer scaling) |

These can also be set at runtime:

**GDScript:**

```gdscript
# Read current viewport size
var viewport_size: Vector2 = get_viewport().get_visible_rect().size

# Change stretch mode at runtime
ProjectSettings.set_setting("display/window/stretch/mode", "canvas_items")
```

**C#:**

```csharp
// Read current viewport size
Vector2I viewportSize = GetViewport().GetVisibleRect().Size;

// Change a project setting at runtime (takes effect next frame)
ProjectSettings.SetSetting("display/window/stretch/mode", "canvas_items");
```

---

## 2. Stretch Mode Comparison

| Mode | `project.godot` value | Rendering | Best For |
|---|---|---|---|
| `canvas_items` | `"canvas_items"` | Viewport rendered at design resolution, then upscaled — UI and 2D nodes scale smoothly | Most 2D and UI-heavy games |
| `viewport` | `"viewport"` | Entire viewport is rendered at design resolution and stretched; no sub-pixel blending | Pixel art games needing pixel-perfect output |
| `disabled` | `"disabled"` | No automatic scaling; every Control node must handle its own layout | Complex custom scaling, 3D games with a Control HUD |

**When to choose each:**

- **`canvas_items`** — Default recommendation. Smooth scaling at any resolution. UI built with `Control` nodes and anchors responds naturally. Text and icons stay crisp at high DPI when combined with `content_scale_factor`.
- **`viewport`** — Locks rendering to the design resolution. Combined with integer scaling and nearest-neighbour filtering it gives a classic pixel-perfect look. Avoid for high-DPI displays unless you intentionally want chunky pixels.
- **`disabled`** — Use when you need full manual control, e.g. a 3D game where the UI must adapt to safe areas or unusual aspect ratios without Godot scaling it.

---

## 3. Aspect Ratio Handling

Set via `Project > Project Settings > Display > Window > Stretch > Aspect` or the `window/stretch/aspect` key.

| Mode | Visual Result | When to Use |
|---|---|---|
| `keep` | Letterbox (black bars top/bottom) or pillarbox (bars left/right) — design rect is preserved exactly | Games with a fixed layout that must not be cropped (e.g. score-based arcade, puzzle) |
| `expand` | Screen is fully filled; the visible game area grows on wider or taller displays | Action games, platformers — more visible play area is a bonus, not a problem |
| `keep_width` | Width is fixed; height expands on taller screens (mobile portrait) | Portrait mobile games where horizontal alignment is strict |
| `keep_height` | Height is fixed; width expands on wider screens (landscape) | Landscape games where vertical alignment is strict (e.g. side-scroller HUD) |

**`expand` with adaptive UI** is the most versatile choice for games targeting both desktop and mobile. Anchor your HUD elements to screen edges so they follow the expanded visible area.

---

## 4. Pixel Art Setup

### Project Settings

In `Project > Project Settings`:

- `Display > Window > Stretch > Mode` → `viewport`
- `Display > Window > Stretch > Scale` → `2` (or `3`, `4` — any integer)
- `Rendering > Textures > Canvas Textures > Default Texture Filter` → `Nearest`

Setting the texture filter to `Nearest` globally avoids blurry pixels without per-sprite configuration.

### Integer Scaling via Script

**GDScript:**

```gdscript
# res://autoload/display_manager.gd
extends Node

const BASE_SIZE := Vector2i(320, 180)  # pixel art design resolution

func _ready() -> void:
    get_window().content_scale_size = BASE_SIZE
    get_window().content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
    get_window().content_scale_aspect = Window.CONTENT_SCALE_ASPECT_KEEP
    _apply_integer_scale()
    get_viewport().size_changed.connect(_apply_integer_scale)


func _apply_integer_scale() -> void:
    var screen_size := DisplayServer.screen_get_size()
    var scale_x := screen_size.x / BASE_SIZE.x
    var scale_y := screen_size.y / BASE_SIZE.y
    var integer_scale := maxi(1, mini(scale_x, scale_y))
    get_window().content_scale_factor = float(integer_scale)
```

**C#:**

```csharp
// autoload/DisplayManager.cs
using Godot;

public partial class DisplayManager : Node
{
    private static readonly Vector2I BaseSize = new(320, 180);

    public override void _Ready()
    {
        var window = GetWindow();
        window.ContentScaleSize   = BaseSize;
        window.ContentScaleMode   = Window.ContentScaleModeEnum.Viewport;
        window.ContentScaleAspect = Window.ContentScaleAspectEnum.Keep;
        ApplyIntegerScale();
        GetViewport().SizeChanged += ApplyIntegerScale;
    }

    private void ApplyIntegerScale()
    {
        var screenSize  = DisplayServer.ScreenGetSize();
        int scaleX      = screenSize.X / BaseSize.X;
        int scaleY      = screenSize.Y / BaseSize.Y;
        int intScale    = Mathf.Max(1, Mathf.Min(scaleX, scaleY));
        GetWindow().ContentScaleFactor = intScale;
    }
}
```

### Nearest-Neighbour Filter per Node (Override)

If the global filter is `Linear` and you only want `Nearest` on specific sprites:

**GDScript:**

```gdscript
# On a Sprite2D or TextureRect node
$Sprite2D.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
```

**C#:**

```csharp
GetNode<Sprite2D>("Sprite2D").TextureFilter = CanvasItem.TextureFilterEnum.Nearest;
```

---

## 5. DPI Scaling

### content_scale_factor

`Window.content_scale_factor` multiplies all UI element sizes uniformly. Increase it on high-DPI (Retina) displays so text and controls are not microscopic.

**GDScript:**

```gdscript
# autoload/dpi_scaler.gd
extends Node

func _ready() -> void:
    _apply_dpi_scale()


func _apply_dpi_scale() -> void:
    var dpi := DisplayServer.screen_get_dpi()
    # 96 dpi is the standard desktop reference
    var scale := clampf(dpi / 96.0, 1.0, 3.0)
    # Round to nearest 0.25 to avoid blurry half-pixel rendering
    scale = roundf(scale * 4.0) / 4.0
    get_window().content_scale_factor = scale


func get_dpi() -> int:
    return DisplayServer.screen_get_dpi()
```

**C#:**

```csharp
// autoload/DpiScaler.cs
using Godot;

public partial class DpiScaler : Node
{
    public override void _Ready() => ApplyDpiScale();

    private void ApplyDpiScale()
    {
        float dpi   = DisplayServer.ScreenGetDpi();
        float scale = Mathf.Clamp(dpi / 96f, 1f, 3f);
        // Round to nearest 0.25
        scale = Mathf.Round(scale * 4f) / 4f;
        GetWindow().ContentScaleFactor = scale;
    }

    public int GetDpi() => DisplayServer.ScreenGetDpi();
}
```

### Querying DPI at Runtime

**GDScript:**

```gdscript
var dpi: int = DisplayServer.screen_get_dpi()
print("Screen DPI: %d" % dpi)  # 96 on standard, 192+ on Retina
```

**C#:**

```csharp
int dpi = DisplayServer.ScreenGetDpi();
GD.Print($"Screen DPI: {dpi}");
```

> **Tip:** On macOS Retina displays `screen_get_dpi()` returns 220+. On Windows with 200 % scaling it returns 192. Use these thresholds to decide whether to enable a 2x UI scale.

---

## 6. Mobile Considerations

### Touch Input

**GDScript:**

```gdscript
extends Node

func _input(event: InputEvent) -> void:
    if event is InputEventScreenTouch:
        if event.pressed:
            _on_touch_begin(event.position, event.index)
        else:
            _on_touch_end(event.position, event.index)
    elif event is InputEventScreenDrag:
        _on_touch_drag(event.position, event.relative, event.index)


func _on_touch_begin(pos: Vector2, finger: int) -> void:
    pass  # handle tap / press

func _on_touch_end(pos: Vector2, finger: int) -> void:
    pass

func _on_touch_drag(pos: Vector2, delta: Vector2, finger: int) -> void:
    pass  # handle swipe / scroll
```

**C#:**

```csharp
using Godot;

public partial class TouchHandler : Node
{
    public override void _Input(InputEvent @event)
    {
        if (@event is InputEventScreenTouch touch)
        {
            if (touch.Pressed) OnTouchBegin(touch.Position, touch.Index);
            else               OnTouchEnd(touch.Position, touch.Index);
        }
        else if (@event is InputEventScreenDrag drag)
        {
            OnTouchDrag(drag.Position, drag.Relative, drag.Index);
        }
    }

    private void OnTouchBegin(Vector2 pos, int finger) { }
    private void OnTouchEnd(Vector2 pos, int finger) { }
    private void OnTouchDrag(Vector2 pos, Vector2 delta, int finger) { }
}
```

### Safe Area Insets

Phones with notches, camera cut-outs, or rounded corners report a safe area rectangle. Place interactive UI elements inside it.

**GDScript:**

```gdscript
func _ready() -> void:
    var safe_area: Rect2i = DisplayServer.get_display_safe_area()
    var screen_size: Vector2i = DisplayServer.screen_get_size()

    # Calculate insets (pixels from each edge)
    var inset_left   := safe_area.position.x
    var inset_top    := safe_area.position.y
    var inset_right  := screen_size.x - (safe_area.position.x + safe_area.size.x)
    var inset_bottom := screen_size.y - (safe_area.position.y + safe_area.size.y)

    # Apply to a MarginContainer wrapping all HUD content
    $SafeAreaMargin.add_theme_constant_override("margin_left",   inset_left)
    $SafeAreaMargin.add_theme_constant_override("margin_top",    inset_top)
    $SafeAreaMargin.add_theme_constant_override("margin_right",  inset_right)
    $SafeAreaMargin.add_theme_constant_override("margin_bottom", inset_bottom)
```

**C#:**

```csharp
public override void _Ready()
{
    Rect2I safeArea  = DisplayServer.GetDisplaySafeArea();
    Vector2I screen  = DisplayServer.ScreenGetSize();

    int insetLeft   = safeArea.Position.X;
    int insetTop    = safeArea.Position.Y;
    int insetRight  = screen.X - (safeArea.Position.X + safeArea.Size.X);
    int insetBottom = screen.Y - (safeArea.Position.Y + safeArea.Size.Y);

    var margin = GetNode<MarginContainer>("SafeAreaMargin");
    margin.AddThemeConstantOverride("margin_left",   insetLeft);
    margin.AddThemeConstantOverride("margin_top",    insetTop);
    margin.AddThemeConstantOverride("margin_right",  insetRight);
    margin.AddThemeConstantOverride("margin_bottom", insetBottom);
}
```

### Orientation Lock

In `Project > Project Settings > Display > Window`:

- `Handheld > Orientation` → `landscape`, `portrait`, `reverse_landscape`, `sensor`, etc.

Or at runtime:

**GDScript:**

```gdscript
# Lock to landscape
DisplayServer.screen_set_orientation(DisplayServer.SCREEN_LANDSCAPE)

# Lock to portrait
DisplayServer.screen_set_orientation(DisplayServer.SCREEN_PORTRAIT)

# Follow device sensor
DisplayServer.screen_set_orientation(DisplayServer.SCREEN_SENSOR)
```

**C#:**

```csharp
DisplayServer.ScreenSetOrientation(DisplayServer.ScreenOrientationEnum.Landscape);
DisplayServer.ScreenSetOrientation(DisplayServer.ScreenOrientationEnum.Portrait);
DisplayServer.ScreenSetOrientation(DisplayServer.ScreenOrientationEnum.Sensor);
```

### Virtual Keyboard

**GDScript:**

```gdscript
# Show keyboard (call after focusing a LineEdit, or manually)
DisplayServer.virtual_keyboard_show("initial text")

# Hide keyboard
DisplayServer.virtual_keyboard_hide()

# Query keyboard height to shift UI above it
var kb_height: int = DisplayServer.virtual_keyboard_get_height()
```

**C#:**

```csharp
DisplayServer.VirtualKeyboardShow("initial text");
DisplayServer.VirtualKeyboardHide();
int kbHeight = DisplayServer.VirtualKeyboardGetHeight();
```

> **Note:** `LineEdit` and `TextEdit` show/hide the virtual keyboard automatically when they gain and lose focus. Call the API manually only when building custom text input widgets.

---

## 7. Adaptive Layouts

### Anchor + Container Strategy

Design for your base resolution, anchor every HUD element to the nearest screen edge, and use `Container` nodes for anything that must reflow.

```
HUD (CanvasLayer)
└── SafeAreaMargin (MarginContainer — anchor: Full Rect)
    ├── TopBar (HBoxContainer — anchor: Top Wide)
    │   ├── HealthLabel (Label — size_flags_h: EXPAND_FILL)
    │   └── ScoreLabel  (Label)
    └── BottomBar (HBoxContainer — anchor: Bottom Wide)
        ├── InventoryButton (Button — custom_minimum_size: Vector2(64, 64))
        └── MapButton       (Button — custom_minimum_size: Vector2(64, 64))
```

**GDScript — setting size flags and minimum sizes in code:**

```gdscript
func _ready() -> void:
    # Expand to fill available horizontal space
    $TopBar/HealthLabel.size_flags_horizontal = Control.SIZE_EXPAND_FILL

    # Never collapse below 64x64
    $BottomBar/InventoryButton.custom_minimum_size = Vector2(64.0, 64.0)
```

**C#:**

```csharp
public override void _Ready()
{
    GetNode<Label>("TopBar/HealthLabel").SizeFlagsHorizontal = Control.SizeFlags.ExpandFill;
    GetNode<Button>("BottomBar/InventoryButton").CustomMinimumSize = new Vector2(64f, 64f);
}
```

### Detecting Resolution Changes

**GDScript:**

```gdscript
func _ready() -> void:
    get_viewport().size_changed.connect(_on_viewport_size_changed)


func _on_viewport_size_changed() -> void:
    var new_size: Vector2 = get_viewport().get_visible_rect().size
    _relayout(new_size)


func _relayout(size: Vector2) -> void:
    # Example: switch between side-by-side and stacked layout
    if size.x >= 1280.0:
        $SplitContainer.vertical = false   # wide layout
    else:
        $SplitContainer.vertical = true    # stacked layout
```

**C#:**

```csharp
public override void _Ready()
{
    GetViewport().SizeChanged += OnViewportSizeChanged;
}

private void OnViewportSizeChanged()
{
    Vector2 size = GetViewport().GetVisibleRect().Size;
    Relayout(size);
}

private void Relayout(Vector2 size)
{
    var split = GetNode<SplitContainer>("SplitContainer");
    split.Vertical = size.X < 1280f;
}
```

### Useful size_flags Values

| Constant | Behaviour in Container |
|---|---|
| `SIZE_SHRINK_BEGIN` | Align to start; take only minimum size |
| `SIZE_FILL` | Expand to fill available space without claiming extra |
| `SIZE_EXPAND` | Claim extra space from the container |
| `SIZE_EXPAND_FILL` | Claim extra space **and** fill it — most common for stretchy widgets |
| `SIZE_SHRINK_CENTER` | Centre within available space at minimum size |
| `SIZE_SHRINK_END` | Align to end; take only minimum size |

---

## 8. Testing Multiple Resolutions

### Editor Preview Sizes

In the editor viewport, use **Editor > Editor Settings > Run > Window Placement** to start the game at specific sizes, or use the viewport size selector in the 2D editor toolbar.

Add common test sizes under **Project > Project Settings > Display > Window > Size > Test Width/Height** to preview in the editor.

### `--resolution` CLI Flag

Launch from the command line with an override resolution:

```bash
# Windows
godot.exe --path "C:/projects/mygame" --resolution 1280x720

# Linux / macOS
godot --path /projects/mygame --resolution 1280x720

# Run an exported binary at a specific size
./mygame.x86_64 --resolution 375x812
```

### Common Test Resolutions

| Resolution | Aspect | Common Use |
|---|---|---|
| `1920×1080` | 16:9 | Standard 1080p desktop / TV |
| `2560×1440` | 16:9 | 1440p high-DPI desktop |
| `1280×720` | 16:9 | Low-end desktop / minimum target |
| `640×360` | 16:9 | Pixel art base resolution (2× of 320×180) |
| `2732×2048` | 4:3 | iPad Pro — tests non-16:9 aspect ratios |
| `390×844` | ~19.5:9 | iPhone 14 portrait |
| `844×390` | ~19.5:9 | iPhone 14 landscape |
| `1080×2400` | 20:9 | Android tall portrait |
| `360×800` | ~20:9 | Android low-end portrait |

> **Strategy:** Always test at your base design resolution, one resolution wider than 16:9 (e.g. 21:9 ultrawide), and one taller (e.g. mobile portrait). These three cases catch the most layout bugs.

---

## 9. Checklist

- [ ] Base viewport size (`viewport_width` / `viewport_height`) matches the design canvas in the editor
- [ ] Stretch mode chosen deliberately: `canvas_items` for most games, `viewport` for pixel art
- [ ] Aspect ratio mode chosen: `expand` unless fixed-layout content requires `keep`
- [ ] Pixel art games use `viewport` stretch + `Nearest` texture filter + integer `content_scale_factor`
- [ ] All HUD `Control` nodes use anchors anchored to the nearest edge, not fixed `position` values
- [ ] `custom_minimum_size` set on buttons and interactive elements to prevent collapse below tap target size (minimum 44×44 px recommended for mobile)
- [ ] `size_flags_horizontal` / `size_flags_vertical` set to `SIZE_EXPAND_FILL` on elements that should fill space
- [ ] `get_viewport().size_changed` signal connected where layout must respond to window resize
- [ ] Safe area insets read from `DisplayServer.get_display_safe_area()` and applied to a root `MarginContainer`
- [ ] `content_scale_factor` set at startup based on `DisplayServer.screen_get_dpi()` for high-DPI / Retina displays
- [ ] Touch input handled via `InputEventScreenTouch` / `InputEventScreenDrag`, not mouse events alone
- [ ] Orientation locked to the correct mode (`SCREEN_LANDSCAPE` / `SCREEN_PORTRAIT`) or `SCREEN_SENSOR` where rotation is intended
- [ ] Virtual keyboard height queried after show and used to shift UI content upward on mobile
- [ ] Tested at minimum: design resolution, one ultra-wide (21:9), and one mobile portrait resolution
- [ ] `--resolution` flag used in CI or playtest scripts to automate multi-resolution smoke tests
