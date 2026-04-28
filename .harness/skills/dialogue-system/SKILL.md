---
name: dialogue-system
description: Use when implementing dialogue — data structures for branching dialogue, conditions, and UI presentation
---

# Dialogue Systems in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, then C#.

> **Related skills:** **resource-pattern** for dialogue data as Resources, **godot-ui** for Control node layout, **state-machine** for dialogue flow management, **save-load** for dialogue state persistence.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                        UI Layer                         │
│   DialogueUI (Control)                                  │
│     ├─ Label (speaker_name)                             │
│     ├─ TextureRect (portrait)                           │
│     ├─ RichTextLabel (dialogue_text, typewriter effect) │
│     └─ VBoxContainer (choice_container)                 │
│           └─ Button × N (choice buttons)                │
│                                                         │
│   Connects to: line_displayed, choice_presented signals │
└───────────────────────┬─────────────────────────────────┘
                        │ drives UI via signals
┌───────────────────────▼─────────────────────────────────┐
│              DialogueManager (Autoload / Node)           │
│   start_dialogue(dialogue_data)                         │
│   advance()  → next line or end                         │
│   choose(choice_index)                                  │
│   current_line: DialogueLine (read-only)                │
│                                                         │
│   signals: dialogue_started                             │
│             line_displayed(line)                        │
│             choice_presented(choices)                   │
│             dialogue_ended                              │
└───────────────────────┬─────────────────────────────────┘
                        │ reads
┌───────────────────────▼─────────────────────────────────┐
│                   Data Layer (Resources)                 │
│   DialogueData (Resource)                               │
│     lines: Dictionary  ← id → DialogueLine              │
│     start_line_id: String                               │
│                                                         │
│   DialogueLine (Resource)                               │
│     speaker, text, choices, next_line_id, condition     │
└─────────────────────────────────────────────────────────┘
```

---

## 2. DialogueLine Resource

`DialogueLine` holds all data for a single beat of dialogue. Choices is an `Array[Dictionary]` so each entry can carry a `text`, `next_line_id`, and optional `condition` without a separate class.

### GDScript

```gdscript
# dialogue_line.gd
class_name DialogueLine
extends Resource

## Display name shown in the UI speaker box.
@export var speaker: String = ""

## The body text. Supports BBCode and variable placeholders: {player_name}.
@export_multiline var text: String = ""

## When non-empty, overrides next_line_id. Each Dictionary must have:
##   "text"        : String   — label on the choice button
##   "next_line_id": String   — line to jump to when chosen
##   "condition"   : String   — (optional) expression; omit or "" to always show
@export var choices: Array = []

## ID of the next DialogueLine. Ignored when choices is non-empty.
@export var next_line_id: String = ""

## Optional condition expression evaluated before displaying this line.
## If the expression returns false the manager skips to next_line_id.
## Example: "GameState.has_item('key')"
@export var condition: String = ""
```

### C#

```csharp
// DialogueLine.cs
using Godot;
using Godot.Collections;

[GlobalClass]
public partial class DialogueLine : Resource
{
    /// <summary>Display name shown in the speaker box.</summary>
    [Export] public string Speaker     { get; set; } = "";

    /// <summary>Body text. Supports BBCode and {variable} placeholders.</summary>
    [Export(PropertyHint.MultilineText)]
    public string Text                 { get; set; } = "";

    /// <summary>
    /// When non-empty, overrides NextLineId. Each Dictionary entry must contain:
    ///   "text"         : string  — choice button label
    ///   "next_line_id" : string  — line to jump to
    ///   "condition"    : string  — (optional) expression; omit or "" to always show
    /// </summary>
    [Export] public Array Choices      { get; set; } = new();

    /// <summary>ID of the next DialogueLine. Ignored when Choices is non-empty.</summary>
    [Export] public string NextLineId  { get; set; } = "";

    /// <summary>
    /// Optional condition expression. Evaluated before displaying this line.
    /// Example: "GameState.HasItem(\"key\")"
    /// </summary>
    [Export] public string Condition   { get; set; } = "";
}
```

---

## 3. DialogueData Resource

`DialogueData` is a container Resource that holds a dictionary of all lines, keyed by their string ID. Creating it as a `.tres` file lets you assign it to NPCs in the Inspector.

### GDScript

```gdscript
# dialogue_data.gd
class_name DialogueData
extends Resource

## Dictionary mapping line ID strings to DialogueLine resources.
## Example: { "intro": <DialogueLine>, "ask_quest": <DialogueLine> }
@export var lines: Dictionary = {}

## ID of the first line to display when dialogue starts.
@export var start_line_id: String = ""


## Convenience accessor — returns null for unknown IDs.
func get_line(id: String) -> DialogueLine:
    return lines.get(id, null)
```

### C#

```csharp
// DialogueData.cs
using Godot;
using Godot.Collections;

[GlobalClass]
public partial class DialogueData : Resource
{
    /// <summary>Maps line ID strings to DialogueLine resources.</summary>
    [Export] public Dictionary Lines        { get; set; } = new();

    /// <summary>ID of the first line to display when dialogue starts.</summary>
    [Export] public string StartLineId      { get; set; } = "";

    /// <summary>Returns the DialogueLine for id, or null if not found.</summary>
    public DialogueLine GetLine(string id)
    {
        if (Lines.ContainsKey(id))
            return Lines[id].As<DialogueLine>();
        return null;
    }
}
```

> Populate `lines` in the Inspector by adding Dictionary entries with string keys and `DialogueLine` resource values, or load them programmatically from JSON (see section 7).

---

## 4. DialogueManager

`DialogueManager` drives the state machine. Register it as an **Autoload** (`Project > Project Settings > Autoload`) so any scene can call `DialogueManager.start_dialogue(data)`.

### GDScript

```gdscript
# dialogue_manager.gd
class_name DialogueManager
extends Node

signal dialogue_started
signal line_displayed(line: DialogueLine)
signal choice_presented(choices: Array)
signal dialogue_ended

var current_line: DialogueLine:
    get: return _current_line

var _data: DialogueData = null
var _current_line: DialogueLine = null
var _active: bool = false


func start_dialogue(dialogue_data: DialogueData) -> void:
    assert(dialogue_data != null, "DialogueManager.start_dialogue: data must not be null")
    _data   = dialogue_data
    _active = true
    dialogue_started.emit()
    _go_to_line(_data.start_line_id)


func advance() -> void:
    if not _active or _current_line == null:
        return
    if not _current_line.choices.is_empty():
        push_warning("DialogueManager.advance: call choose() when choices are presented")
        return
    _go_to_line(_current_line.next_line_id)


func choose(choice_index: int) -> void:
    if not _active or _current_line == null:
        return
    if _current_line.choices.is_empty():
        push_warning("DialogueManager.choose: no choices on the current line")
        return

    var visible_choices := _visible_choices(_current_line.choices)
    if choice_index < 0 or choice_index >= visible_choices.size():
        push_error("DialogueManager.choose: index %d out of range" % choice_index)
        return

    _go_to_line(visible_choices[choice_index].get("next_line_id", ""))


func _go_to_line(id: String) -> void:
    if id.is_empty():
        _end_dialogue()
        return

    var line: DialogueLine = _data.get_line(id)
    if line == null:
        push_error("DialogueManager: unknown line id '%s'" % id)
        _end_dialogue()
        return

    # Skip line if its condition is not met
    if not line.condition.is_empty() and not _evaluate_condition(line.condition):
        _go_to_line(line.next_line_id)
        return

    _current_line = line
    line_displayed.emit(line)

    var visible := _visible_choices(line.choices)
    if not visible.is_empty():
        choice_presented.emit(visible)


func _end_dialogue() -> void:
    _active       = false
    _current_line = null
    _data         = null
    dialogue_ended.emit()


# Returns only choices whose condition passes (or have no condition).
func _visible_choices(choices: Array) -> Array:
    return choices.filter(func(c: Dictionary) -> bool:
        var cond: String = c.get("condition", "")
        return cond.is_empty() or _evaluate_condition(cond)
    )


# Evaluates a condition string against the current game state.
# See section 5 for a full condition evaluator example.
func _evaluate_condition(expression: String) -> bool:
    var expr := Expression.new()
    var err   := expr.parse(expression)
    if err != OK:
        push_error("DialogueManager: bad condition '%s' — %s" % [expression, expr.get_error_text()])
        return false
    var result = expr.execute([], self)
    if expr.has_execute_failed():
        push_error("DialogueManager: condition execute failed for '%s'" % expression)
        return false
    return bool(result)
```

### C#

```csharp
// DialogueManager.cs
using Godot;
using Godot.Collections;

public partial class DialogueManager : Node
{
    [Signal] public delegate void DialogueStartedEventHandler();
    [Signal] public delegate void LineDisplayedEventHandler(DialogueLine line);
    [Signal] public delegate void ChoicePresentedEventHandler(Array choices);
    [Signal] public delegate void DialogueEndedEventHandler();

    public DialogueLine CurrentLine => _currentLine;

    private DialogueData  _data        = null;
    private DialogueLine  _currentLine = null;
    private bool          _active      = false;

    public void StartDialogue(DialogueData dialogueData)
    {
        if (dialogueData == null)
        {
            GD.PushError("DialogueManager.StartDialogue: data must not be null");
            return;
        }

        _data   = dialogueData;
        _active = true;
        EmitSignal(SignalName.DialogueStarted);
        GoToLine(_data.StartLineId);
    }

    public void Advance()
    {
        if (!_active || _currentLine == null) return;
        if (_currentLine.Choices.Count > 0)
        {
            GD.PushWarning("DialogueManager.Advance: call Choose() when choices are presented");
            return;
        }
        GoToLine(_currentLine.NextLineId);
    }

    public void Choose(int choiceIndex)
    {
        if (!_active || _currentLine == null) return;
        if (_currentLine.Choices.Count == 0)
        {
            GD.PushWarning("DialogueManager.Choose: no choices on the current line");
            return;
        }

        var visible = VisibleChoices(_currentLine.Choices);
        if (choiceIndex < 0 || choiceIndex >= visible.Count)
        {
            GD.PushError($"DialogueManager.Choose: index {choiceIndex} out of range");
            return;
        }

        var chosen = visible[choiceIndex].AsGodotDictionary();
        GoToLine(chosen.ContainsKey("next_line_id") ? chosen["next_line_id"].As<string>() : "");
    }

    private void GoToLine(string id)
    {
        if (string.IsNullOrEmpty(id)) { EndDialogue(); return; }

        var line = _data.GetLine(id);
        if (line == null)
        {
            GD.PushError($"DialogueManager: unknown line id '{id}'");
            EndDialogue();
            return;
        }

        // Skip line if condition is not met
        if (!string.IsNullOrEmpty(line.Condition) && !EvaluateCondition(line.Condition))
        {
            GoToLine(line.NextLineId);
            return;
        }

        _currentLine = line;
        EmitSignal(SignalName.LineDisplayed, line);

        var visible = VisibleChoices(line.Choices);
        if (visible.Count > 0)
            EmitSignal(SignalName.ChoicePresented, visible);
    }

    private void EndDialogue()
    {
        _active      = false;
        _currentLine = null;
        _data        = null;
        EmitSignal(SignalName.DialogueEnded);
    }

    private Array VisibleChoices(Array choices)
    {
        var result = new Array();
        foreach (var c in choices)
        {
            var dict = c.AsGodotDictionary();
            string cond = dict.ContainsKey("condition") ? dict["condition"].As<string>() : "";
            if (string.IsNullOrEmpty(cond) || EvaluateCondition(cond))
                result.Add(c);
        }
        return result;
    }

    private bool EvaluateCondition(string expression)
    {
        var expr = new Expression();
        var err  = expr.Parse(expression);
        if (err != Error.Ok)
        {
            GD.PushError($"DialogueManager: bad condition '{expression}' — {expr.GetErrorText()}");
            return false;
        }
        var result = expr.Execute(Array.From(System.Array.Empty<Variant>()), this);
        if (expr.HasExecuteFailed())
        {
            GD.PushError($"DialogueManager: condition execute failed for '{expression}'");
            return false;
        }
        return result.As<bool>();
    }
}
```

---

## 5. Branching and Conditions

### Choice Nodes

A `DialogueLine` with a non-empty `choices` array acts as a branch point. Each choice entry is a plain Dictionary:

```gdscript
# Inside a DialogueLine resource (set in code or loaded from JSON)
var ask_line := DialogueLine.new()
ask_line.speaker = "Guard"
ask_line.text    = "What brings you here, traveller?"
ask_line.choices = [
    {"text": "I seek the king.",       "next_line_id": "seek_king"},
    {"text": "Just passing through.",  "next_line_id": "passing_through"},
    {"text": "I have a letter.",       "next_line_id": "letter_branch",
     "condition": "GameState.has_item('royal_letter')"},
]
```

The third choice only appears when `GameState.has_item('royal_letter')` is true. `DialogueManager._visible_choices()` filters the list before emitting `choice_presented`.

### Condition Evaluator

`DialogueManager._evaluate_condition()` uses Godot's built-in `Expression` class, which can call methods on any object passed as the base instance. Wire it to a `GameState` autoload for clean condition strings:

```gdscript
# game_state.gd — autoload named GameState
extends Node

var flags:     Dictionary = {}  # arbitrary boolean flags
var inventory: Inventory         # set by the player scene


func has_flag(key: String) -> bool:
    return flags.get(key, false)


func set_flag(key: String, value: bool = true) -> void:
    flags[key] = value


func has_item(item_id: String, quantity: int = 1) -> bool:
    if inventory == null:
        return false
    var item: ItemData = ItemRegistry.get_item(item_id)
    return item != null and inventory.has_item(item, quantity)


func quest_stage(quest_id: String) -> int:
    return flags.get("quest_%s_stage" % quest_id, 0)
```

Pass `GameState` as the expression base to resolve method calls:

```gdscript
# In DialogueManager._evaluate_condition():
var result = expr.execute([], GameState)   # ← pass autoload as base instance
```

Condition strings in dialogue data then read naturally:

```
"GameState.has_flag('met_queen')"
"GameState.quest_stage('main') >= 2"
"GameState.has_item('potion', 3)"
```

---

## 6. Dialogue UI

### Scene Structure

```
DialogueUI (Control)
  ├─ PanelContainer
  │    ├─ HBoxContainer
  │    │    ├─ TextureRect      (portrait)
  │    │    └─ VBoxContainer
  │    │         ├─ Label       (speaker_name)
  │    │         └─ RichTextLabel (dialogue_text)
  │    └─ VBoxContainer         (choice_container)
  │         └─ Button × N       (instantiated at runtime)
  └─ Timer                      (typewriter_timer)
```

### GDScript

```gdscript
# dialogue_ui.gd
class_name DialogueUI
extends Control

@export var manager: DialogueManager  # assign the autoload or a node ref

@onready var speaker_label:    Label          = $PanelContainer/HBoxContainer/VBoxContainer/Label
@onready var dialogue_text:    RichTextLabel  = $PanelContainer/HBoxContainer/VBoxContainer/RichTextLabel
@onready var portrait:         TextureRect    = $PanelContainer/HBoxContainer/TextureRect
@onready var choice_container: VBoxContainer  = $PanelContainer/VBoxContainer
@onready var typewriter_timer: Timer          = $Timer

const TYPEWRITER_INTERVAL := 0.04  # seconds per character


func _ready() -> void:
    if manager == null:
        manager = get_node("/root/DialogueManager")
    manager.line_displayed.connect(_on_line_displayed)
    manager.choice_presented.connect(_on_choice_presented)
    manager.dialogue_ended.connect(_on_dialogue_ended)
    hide()


# ── Input ─────────────────────────────────────────────────────────────────────

func _unhandled_input(event: InputEvent) -> void:
    if not visible:
        return
    if event.is_action_pressed("ui_accept"):
        if typewriter_timer.is_stopped():
            manager.advance()
        else:
            # Skip typewriter — reveal full text immediately
            typewriter_timer.stop()
            dialogue_text.visible_characters = -1


# ── Signal handlers ───────────────────────────────────────────────────────────

func _on_line_displayed(line: DialogueLine) -> void:
    show()
    _clear_choices()

    speaker_label.text = line.speaker
    # Variable interpolation happens before display (see section 8)
    dialogue_text.text = _interpolate(line.text)
    dialogue_text.visible_characters = 0

    # Optionally set portrait from a Dictionary keyed by speaker name
    # portrait.texture = PortraitRegistry.get_portrait(line.speaker)

    typewriter_timer.wait_time = TYPEWRITER_INTERVAL
    typewriter_timer.start()


func _on_typewriter_tick() -> void:
    if dialogue_text.visible_characters < dialogue_text.get_total_character_count():
        dialogue_text.visible_characters += 1
    else:
        typewriter_timer.stop()


func _on_choice_presented(choices: Array) -> void:
    _clear_choices()
    for i in choices.size():
        var choice: Dictionary = choices[i]
        var btn := Button.new()
        btn.text = choice.get("text", "")
        btn.pressed.connect(manager.choose.bind(i))
        choice_container.add_child(btn)


func _on_dialogue_ended() -> void:
    hide()
    _clear_choices()


# ── Helpers ───────────────────────────────────────────────────────────────────

func _clear_choices() -> void:
    for child in choice_container.get_children():
        child.queue_free()


# Variable interpolation — see section 8.
func _interpolate(text: String) -> String:
    return text.format({
        "player_name": GameState.get("player_name") if GameState.get("player_name") else "Hero",
    })
```

Connect the `Timer`'s `timeout` signal to `_on_typewriter_tick` in the editor or in `_ready()`:

```gdscript
typewriter_timer.timeout.connect(_on_typewriter_tick)
```

---

## 7. External Formats

### JSON Dialogue Files

Storing dialogue as plain JSON decouples writing from the Godot editor and lets writers use any text editor or spreadsheet tool. Load at runtime with `FileAccess`:

```gdscript
# dialogue_loader.gd
class_name DialogueLoader
extends RefCounted

static func load_from_json(path: String) -> DialogueData:
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        push_error("DialogueLoader: cannot open '%s'" % path)
        return null

    var json   := JSON.new()
    var err    := json.parse(file.get_as_text())
    if err != OK:
        push_error("DialogueLoader: JSON parse error in '%s' — %s" % [path, json.get_error_message()])
        return null

    var raw: Dictionary = json.data
    var data := DialogueData.new()
    data.start_line_id = raw.get("start_line_id", "")

    for id: String in raw.get("lines", {}).keys():
        var entry: Dictionary = raw["lines"][id]
        var line              := DialogueLine.new()
        line.speaker          = entry.get("speaker", "")
        line.text             = entry.get("text", "")
        line.choices          = entry.get("choices", [])
        line.next_line_id     = entry.get("next_line_id", "")
        line.condition        = entry.get("condition", "")
        data.lines[id]        = line

    return data
```

Example JSON layout (`res://dialogue/guard.json`):

```json
{
  "start_line_id": "greet",
  "lines": {
    "greet": {
      "speaker": "Guard",
      "text": "Halt! State your business.",
      "choices": [
        { "text": "I bring a message.",  "next_line_id": "message" },
        { "text": "Never mind.",         "next_line_id": "" }
      ]
    },
    "message": {
      "speaker": "Guard",
      "text": "Very well. You may pass.",
      "next_line_id": ""
    }
  }
}
```

### Dialogic Addon

For larger projects, **[Dialogic](https://github.com/coppolaemilio/dialogic)** is the most widely used Godot dialogue addon. It provides a visual timeline editor, character management, portrait handling, and its own condition/event system. Consider Dialogic when:

- The writing team is non-technical and needs a visual editor.
- You need built-in localization, save/load of dialogue state, or audio cue events.
- The dialogue graph is large enough that manual JSON management becomes error-prone.

For small-to-medium projects the hand-rolled system in this skill keeps dependencies minimal and stays fully under your control.

---

## 8. Variable Interpolation

Insert runtime values — player name, item names, quest counts — into dialogue text using `String.format()`. This works with both plain text and BBCode.

### GDScript

```gdscript
# Simple format call — keys match {placeholder} tokens in the text.
var template := "Welcome back, {player_name}! You have {gold} gold."
var result   := template.format({
    "player_name": GameState.player_name,
    "gold":        GameState.gold,
})
# → "Welcome back, Aria! You have 120 gold."


# BBCode-safe — format() does not escape BBCode tags, so this works directly:
var bbcode_template := "[color=yellow]{item_name}[/color] has been added to your pack."
var bbcode_result   := bbcode_template.format({"item_name": acquired_item.name})
dialogue_text.text  = bbcode_result  # RichTextLabel renders both BBCode and substituted value.
```

Define a central `_interpolate()` helper in `DialogueUI` (or `DialogueManager`) so all text passes through the same substitution table:

```gdscript
func _interpolate(raw: String) -> String:
    return raw.format({
        "player_name": GameState.player_name,
        "chapter":     str(GameState.quest_stage("main")),
        # add more keys as the game grows
    })
```

### C#

```csharp
// String.Format with named placeholders is not built into C#.
// Use a simple regex-replace helper or a dedicated method:

private string Interpolate(string raw)
{
    return raw
        .Replace("{player_name}", GameState.Instance.PlayerName)
        .Replace("{gold}",        GameState.Instance.Gold.ToString());
}

// Or use a Dictionary for extensibility:
private string Interpolate(string raw)
{
    var vars = new System.Collections.Generic.Dictionary<string, string>
    {
        ["player_name"] = GameState.Instance.PlayerName,
        ["chapter"]     = GameState.Instance.QuestStage("main").ToString(),
    };

    foreach (var (key, value) in vars)
        raw = raw.Replace($"{{{key}}}", value);

    return raw;
}
```

> For Godot's `RichTextLabel`, BBCode tags and `{placeholder}` tokens can coexist in the same string — `format()` only replaces `{key}` patterns and leaves all other characters untouched.

---

## 9. Implementation Checklist

- [ ] `DialogueLine` and `DialogueData` extend `Resource` and carry `[GlobalClass]` (C#) for Inspector integration
- [ ] `DialogueManager` is registered as an Autoload so all scenes share a single instance
- [ ] `start_dialogue()` asserts that `dialogue_data` is non-null before accessing it
- [ ] `advance()` guards against being called when choices are pending
- [ ] `choose()` operates on the filtered visible-choices list, not the raw `choices` array
- [ ] Condition strings reference only stable autoload method names — avoid referencing scene-local nodes
- [ ] `_evaluate_condition()` passes a known base instance (`GameState`) to `Expression.execute()` to resolve method calls
- [ ] Typewriter timer uses `visible_characters`, not frame-by-frame string slicing, for BBCode compatibility
- [ ] Pressing `ui_accept` mid-typewriter reveals full text; a second press advances the line
- [ ] Choice buttons are freed (`queue_free`) before creating new ones — never accumulate stale children
- [ ] JSON loader validates file open and parse steps separately, emitting clear error messages for each failure
- [ ] Variable interpolation is centralised in one `_interpolate()` helper, not scattered across signal handlers
- [ ] `next_line_id = ""` signals end-of-dialogue — no magic sentinel strings beyond the empty string
- [ ] All `push_error()` messages include class name and method for easy log tracing
