---
name: inventory-system
description: Use when building inventory systems — Resource-based items, slot management, stacking, and UI binding
---

# Inventory Systems in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, then C#.

> **Related skills:** **resource-pattern** for custom Resource data containers, **save-load** for inventory serialization, **event-bus** for inventory change notifications, **hud-system** for inventory UI display.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                        UI Layer                         │
│   InventoryUI (Control)                                 │
│     └─ GridContainer                                    │
│           └─ SlotUI × N (Button)                        │
│                 └─ TextureRect (icon) + Label (qty)     │
│                                                         │
│   Connects to: inventory_changed signal                 │
│   Drag-and-drop via _get_drag_data / _drop_data         │
└───────────────────────┬─────────────────────────────────┘
                        │ reads / mutates
┌───────────────────────▼─────────────────────────────────┐
│                    Inventory (Node)                      │
│   slots: Array[InventorySlot]                           │
│   add_item(item, qty) → leftover: int                   │
│   remove_item(item, qty)                                │
│   has_item(item, qty) → bool                            │
│   get_item_count(item) → int                            │
│                                                         │
│   signals: inventory_changed                            │
│             item_added(item, quantity)                  │
│             item_removed(item, quantity)                │
└───────────────────────┬─────────────────────────────────┘
                        │ references
┌───────────────────────▼─────────────────────────────────┐
│                   Data Layer (Resources)                 │
│   ItemData (Resource)                                   │
│     id, name, description, icon, max_stack_size,        │
│     item_type enum                                      │
│                                                         │
│   InventorySlot (inner class / Resource)                │
│     item: ItemData, quantity: int                       │
└─────────────────────────────────────────────────────────┘
```

---

## 2. ItemData Resource

Define items as Resources so they live in `.tres` files, are shareable across scenes, and benefit from full editor integration.

### GDScript

```gdscript
# item_data.gd
class_name ItemData
extends Resource

enum ItemType {
    CONSUMABLE,
    EQUIPMENT,
    MATERIAL,
    KEY_ITEM,
}

@export var id: String = ""
@export var name: String = ""
@export var description: String = ""
@export var icon: Texture2D
@export var max_stack_size: int = 99
@export var item_type: ItemType = ItemType.MATERIAL
```

Create item assets: **res://items/potion_health.tres**, set `id = "potion_health"`, etc.

### C#

```csharp
// ItemData.cs
using Godot;

[GlobalClass]
public partial class ItemData : Resource
{
    public enum ItemType
    {
        Consumable,
        Equipment,
        Material,
        KeyItem,
    }

    [Export] public string Id          { get; set; } = "";
    [Export] public string Name        { get; set; } = "";
    [Export] public string Description { get; set; } = "";
    [Export] public Texture2D Icon     { get; set; }
    [Export] public int MaxStackSize   { get; set; } = 99;
    [Export] public ItemType Type      { get; set; } = ItemType.Material;
}
```

> Use `[GlobalClass]` so the Inspector dropdown shows `ItemData` as a resource type when creating `.tres` files.

---

## 3. Inventory Class

### GDScript

```gdscript
# inventory.gd
class_name Inventory
extends Node

signal inventory_changed
signal item_added(item: ItemData, quantity: int)
signal item_removed(item: ItemData, quantity: int)

@export var capacity: int = 20

var slots: Array[InventorySlot] = []


func _ready() -> void:
    slots.resize(capacity)
    for i in capacity:
        slots[i] = InventorySlot.new()


# Returns the number of items that could NOT be added (leftover).
func add_item(item: ItemData, quantity: int = 1) -> int:
    var remaining := quantity

    # Fill existing stacks first
    for slot in slots:
        if remaining <= 0:
            break
        if not slot.is_empty() and slot.item == item:
            remaining = slot.add_to_stack(remaining)

    # Open empty slots next
    for slot in slots:
        if remaining <= 0:
            break
        if slot.is_empty():
            slot.item = item
            remaining = slot.add_to_stack(remaining)

    var added := quantity - remaining
    if added > 0:
        item_added.emit(item, added)
        inventory_changed.emit()

    return remaining


func remove_item(item: ItemData, quantity: int = 1) -> void:
    var remaining := quantity

    for slot in slots:
        if remaining <= 0:
            break
        if not slot.is_empty() and slot.item == item:
            var removed := mini(slot.quantity, remaining)
            slot.remove_from_stack(removed)
            remaining -= removed

    var actually_removed := quantity - remaining
    if actually_removed > 0:
        item_removed.emit(item, actually_removed)
        inventory_changed.emit()


func has_item(item: ItemData, quantity: int = 1) -> bool:
    return get_item_count(item) >= quantity


func get_item_count(item: ItemData) -> int:
    var total := 0
    for slot in slots:
        if not slot.is_empty() and slot.item == item:
            total += slot.quantity
    return total
```

### C#

```csharp
// Inventory.cs
using Godot;
using Godot.Collections;

public partial class Inventory : Node
{
    [Signal] public delegate void InventoryChangedEventHandler();
    [Signal] public delegate void ItemAddedEventHandler(ItemData item, int quantity);
    [Signal] public delegate void ItemRemovedEventHandler(ItemData item, int quantity);

    [Export] public int Capacity { get; set; } = 20;

    public Array<InventorySlot> Slots { get; private set; } = new();

    public override void _Ready()
    {
        for (int i = 0; i < Capacity; i++)
            Slots.Add(new InventorySlot());
    }

    /// <summary>Returns the number of items that could NOT be added (leftover).</summary>
    public int AddItem(ItemData item, int quantity = 1)
    {
        int remaining = quantity;

        // Fill existing stacks first
        foreach (var slot in Slots)
        {
            if (remaining <= 0) break;
            if (!slot.IsEmpty() && slot.Item == item)
                remaining = slot.AddToStack(remaining);
        }

        // Open empty slots next
        foreach (var slot in Slots)
        {
            if (remaining <= 0) break;
            if (slot.IsEmpty())
            {
                slot.Item = item;
                remaining = slot.AddToStack(remaining);
            }
        }

        int added = quantity - remaining;
        if (added > 0)
        {
            EmitSignal(SignalName.ItemAdded, item, added);
            EmitSignal(SignalName.InventoryChanged);
        }

        return remaining;
    }

    public void RemoveItem(ItemData item, int quantity = 1)
    {
        int remaining = quantity;

        foreach (var slot in Slots)
        {
            if (remaining <= 0) break;
            if (!slot.IsEmpty() && slot.Item == item)
            {
                int removed = Mathf.Min(slot.Quantity, remaining);
                slot.RemoveFromStack(removed);
                remaining -= removed;
            }
        }

        int actuallyRemoved = quantity - remaining;
        if (actuallyRemoved > 0)
        {
            EmitSignal(SignalName.ItemRemoved, item, actuallyRemoved);
            EmitSignal(SignalName.InventoryChanged);
        }
    }

    public bool HasItem(ItemData item, int quantity = 1)
        => GetItemCount(item) >= quantity;

    public int GetItemCount(ItemData item)
    {
        int total = 0;
        foreach (var slot in Slots)
            if (!slot.IsEmpty() && slot.Item == item)
                total += slot.Quantity;
        return total;
    }
}
```

---

## 4. InventorySlot

`InventorySlot` is a lightweight object tracking an item reference and its quantity. Define it as an inner class on `Inventory` (GDScript) or as a standalone `RefCounted` subclass (C#).

### GDScript

```gdscript
# inventory_slot.gd  — or nest as inner class inside inventory.gd
class_name InventorySlot
extends RefCounted

var item: ItemData = null
var quantity: int   = 0


func is_empty() -> bool:
    return item == null or quantity <= 0


func can_stack(new_item: ItemData) -> bool:
    return not is_empty() and item == new_item and quantity < item.max_stack_size


# Adds amount to this slot, capped at max_stack_size.
# Returns the leftover that did not fit.
func add_to_stack(amount: int) -> int:
    if item == null:
        push_error("InventorySlot.add_to_stack: slot has no item assigned")
        return amount
    var space    := item.max_stack_size - quantity
    var to_add   := mini(amount, space)
    quantity     += to_add
    return amount - to_add


# Removes amount from this slot. Clears the slot when quantity reaches zero.
func remove_from_stack(amount: int) -> void:
    quantity -= amount
    if quantity <= 0:
        quantity = 0
        item     = null
```

### C#

```csharp
// InventorySlot.cs
using Godot;

public partial class InventorySlot : RefCounted
{
    public ItemData Item     { get; set; }
    public int      Quantity { get; set; }

    public bool IsEmpty() => Item == null || Quantity <= 0;

    public bool CanStack(ItemData newItem)
        => !IsEmpty() && Item == newItem && Quantity < Item.MaxStackSize;

    /// <summary>Adds amount to this slot. Returns leftover that did not fit.</summary>
    public int AddToStack(int amount)
    {
        if (Item == null)
        {
            GD.PushError("InventorySlot.AddToStack: slot has no item assigned");
            return amount;
        }
        int space  = Item.MaxStackSize - Quantity;
        int toAdd  = Mathf.Min(amount, space);
        Quantity  += toAdd;
        return amount - toAdd;
    }

    /// <summary>Removes amount from this slot. Clears when quantity reaches zero.</summary>
    public void RemoveFromStack(int amount)
    {
        Quantity -= amount;
        if (Quantity <= 0)
        {
            Quantity = 0;
            Item     = null;
        }
    }
}
```

---

## 5. Equipment Extension

Extend `Inventory` with a dedicated equipment layer. Equipment slots are keyed by a `SlotType` enum, and stat bonuses are aggregated on demand.

### GDScript

```gdscript
# equipment.gd
class_name Equipment
extends Node

signal equipment_changed(slot: SlotType, item: ItemData)

enum SlotType {
    HEAD,
    CHEST,
    LEGS,
    HANDS,
    FEET,
    WEAPON,
    OFF_HAND,
    ACCESSORY,
}

# Maps SlotType → the ItemData currently equipped in that slot (null = empty)
var equipment_slots: Dictionary = {}


func _ready() -> void:
    for slot_type in SlotType.values():
        equipment_slots[slot_type] = null


func equip(item: ItemData, slot: SlotType) -> ItemData:
    assert(item.item_type == ItemData.ItemType.EQUIPMENT,
        "equip: '%s' is not an EQUIPMENT item" % item.name)
    var previous: ItemData = equipment_slots[slot]
    equipment_slots[slot] = item
    equipment_changed.emit(slot, item)
    return previous  # caller can return this to the inventory


func unequip(slot: SlotType) -> ItemData:
    var item: ItemData = equipment_slots[slot]
    equipment_slots[slot] = null
    if item != null:
        equipment_changed.emit(slot, null)
    return item


func get_equipped(slot: SlotType) -> ItemData:
    return equipment_slots.get(slot, null)


# Aggregate a named numeric stat from all equipped items.
# Each ItemData can expose stat bonuses via a Dictionary property named "stats".
# e.g. item.stats = { "attack": 10, "defense": 5 }
func get_total_stat(stat_name: String) -> float:
    var total := 0.0
    for item: ItemData in equipment_slots.values():
        if item == null:
            continue
        if item.get("stats") is Dictionary:
            total += float(item.stats.get(stat_name, 0))
    return total
```

### C#

```csharp
// Equipment.cs
using Godot;
using Godot.Collections;

public partial class Equipment : Node
{
    [Signal] public delegate void EquipmentChangedEventHandler(int slot, ItemData item);

    public enum SlotType
    {
        Head,
        Chest,
        Legs,
        Hands,
        Feet,
        Weapon,
        OffHand,
        Accessory,
    }

    // Maps SlotType → ItemData (null = empty)
    private readonly Dictionary<SlotType, ItemData> _equipmentSlots = new();

    public override void _Ready()
    {
        foreach (SlotType slot in System.Enum.GetValues<SlotType>())
            _equipmentSlots[slot] = null;
    }

    /// <summary>Equips item into slot. Returns the previously equipped item (may be null).</summary>
    public ItemData Equip(ItemData item, SlotType slot)
    {
        if (item.Type != ItemData.ItemType.Equipment)
        {
            GD.PushWarning($"Equip: '{item.Name}' is not an Equipment item");
            return null;
        }

        var previous          = _equipmentSlots[slot];
        _equipmentSlots[slot] = item;
        EmitSignal(SignalName.EquipmentChanged, (int)slot, item);
        return previous;
    }

    /// <summary>Unequips the item in slot. Returns the removed item (may be null).</summary>
    public ItemData Unequip(SlotType slot)
    {
        var item              = _equipmentSlots[slot];
        _equipmentSlots[slot] = null;
        if (item != null)
            EmitSignal(SignalName.EquipmentChanged, (int)slot, default(Variant));
        return item;
    }

    public ItemData GetEquipped(SlotType slot) => _equipmentSlots[slot];

    /// <summary>Aggregate a numeric stat from all currently equipped items.</summary>
    public float GetTotalStat(string statName)
    {
        float total = 0f;
        foreach (var item in _equipmentSlots.Values)
        {
            if (item == null) continue;
            // Expects ItemData to expose a Stats Dictionary property
            if (item.Get("stats").Obj is Godot.Collections.Dictionary stats
                && stats.ContainsKey(statName))
                total += stats[statName].As<float>();
        }
        return total;
    }
}
```

---

## 6. UI Binding

### Scene Structure

```
InventoryUI (Control)
  └─ GridContainer          ← auto-fills slots
       └─ SlotUI × N (Button)
            ├─ TextureRect  ← item icon
            └─ Label        ← quantity ("x3")
```

### GDScript

```gdscript
# inventory_ui.gd
class_name InventoryUI
extends Control

@export var slot_scene: PackedScene  # scene for SlotUI
@export var inventory: Inventory

@onready var grid: GridContainer = $GridContainer

var _slot_nodes: Array[SlotUI] = []


func _ready() -> void:
    assert(inventory != null, "InventoryUI: inventory must be assigned")
    inventory.inventory_changed.connect(_refresh)
    _build_grid()
    _refresh()


func _build_grid() -> void:
    for child in grid.get_children():
        child.queue_free()
    _slot_nodes.clear()

    for i in inventory.slots.size():
        var slot_ui: SlotUI = slot_scene.instantiate()
        grid.add_child(slot_ui)
        slot_ui.slot_index = i
        slot_ui.inventory  = inventory
        _slot_nodes.append(slot_ui)


func _refresh() -> void:
    for i in _slot_nodes.size():
        _slot_nodes[i].update_display(inventory.slots[i])
```

```gdscript
# slot_ui.gd
class_name SlotUI
extends Button

var slot_index: int   = -1
var inventory: Inventory

@onready var icon_rect: TextureRect = $TextureRect
@onready var qty_label: Label       = $Label


func update_display(slot: InventorySlot) -> void:
    if slot.is_empty():
        icon_rect.texture = null
        qty_label.text    = ""
    else:
        icon_rect.texture = slot.item.icon
        qty_label.text    = "x%d" % slot.quantity if slot.quantity > 1 else ""


# ── Drag-and-drop ────────────────────────────────────────────────────────────

func _get_drag_data(_at_position: Vector2) -> Variant:
    var slot := inventory.slots[slot_index]
    if slot.is_empty():
        return null

    # Preview
    var preview := TextureRect.new()
    preview.texture         = slot.item.icon
    preview.expand_mode     = TextureRect.EXPAND_FIT_WIDTH
    preview.custom_minimum_size = Vector2(48, 48)
    set_drag_preview(preview)

    return {"from_index": slot_index, "item": slot.item, "quantity": slot.quantity}


func _can_drop_data(_at_position: Vector2, data: Variant) -> bool:
    return data is Dictionary and data.has("from_index")


func _drop_data(_at_position: Vector2, data: Dictionary) -> void:
    var from: int = data["from_index"]
    var to:   int = slot_index
    if from == to:
        return

    # Swap slot contents directly (bypass add/remove to avoid signals noise)
    var from_slot := inventory.slots[from]
    var to_slot   := inventory.slots[to]

    var tmp_item := to_slot.item
    var tmp_qty  := to_slot.quantity
    to_slot.item     = from_slot.item
    to_slot.quantity = from_slot.quantity
    from_slot.item     = tmp_item
    from_slot.quantity = tmp_qty

    inventory.inventory_changed.emit()
```

### C#

```csharp
// InventoryUI.cs
using Godot;
using Godot.Collections;

public partial class InventoryUI : Control
{
    [Export] public PackedScene SlotScene { get; set; }
    [Export] public Inventory   Inventory { get; set; }

    private GridContainer        _grid;
    private System.Collections.Generic.List<SlotUI> _slotNodes = new();

    public override void _Ready()
    {
        _grid = GetNode<GridContainer>("GridContainer");
        if (Inventory == null)
        {
            GD.PushError("InventoryUI: inventory must be assigned");
            return;
        }

        Inventory.InventoryChanged += Refresh;
        BuildGrid();
        Refresh();
    }

    private void BuildGrid()
    {
        foreach (var child in _grid.GetChildren())
            child.QueueFree();
        _slotNodes.Clear();

        for (int i = 0; i < Inventory.Slots.Count; i++)
        {
            var slotUi         = SlotScene.Instantiate<SlotUI>();
            slotUi.SlotIndex   = i;
            slotUi.Inventory   = Inventory;
            _grid.AddChild(slotUi);
            _slotNodes.Add(slotUi);
        }
    }

    private void Refresh()
    {
        for (int i = 0; i < _slotNodes.Count; i++)
            _slotNodes[i].UpdateDisplay(Inventory.Slots[i]);
    }
}
```

```csharp
// SlotUI.cs
using Godot;

public partial class SlotUI : Button
{
    public int       SlotIndex { get; set; } = -1;
    public Inventory Inventory { get; set; }

    private TextureRect _iconRect;
    private Label       _qtyLabel;

    public override void _Ready()
    {
        _iconRect = GetNode<TextureRect>("TextureRect");
        _qtyLabel = GetNode<Label>("Label");
    }

    public void UpdateDisplay(InventorySlot slot)
    {
        if (slot.IsEmpty())
        {
            _iconRect.Texture = null;
            _qtyLabel.Text    = "";
        }
        else
        {
            _iconRect.Texture = slot.Item.Icon;
            _qtyLabel.Text    = slot.Quantity > 1 ? $"x{slot.Quantity}" : "";
        }
    }

    // ── Drag-and-drop ────────────────────────────────────────────────────────

    public override Variant _GetDragData(Vector2 atPosition)
    {
        var slot = Inventory.Slots[SlotIndex];
        if (slot.IsEmpty()) return default;

        var preview             = new TextureRect();
        preview.Texture         = slot.Item.Icon;
        preview.ExpandMode      = TextureRect.ExpandModeEnum.FitWidth;
        preview.CustomMinimumSize = new Vector2(48, 48);
        SetDragPreview(preview);

        return new Godot.Collections.Dictionary
        {
            ["from_index"] = SlotIndex,
            ["item"]       = slot.Item,
            ["quantity"]   = slot.Quantity,
        };
    }

    public override bool _CanDropData(Vector2 atPosition, Variant data)
    {
        var dict = data.AsGodotDictionary();
        return dict != null && dict.ContainsKey("from_index");
    }

    public override void _DropData(Vector2 atPosition, Variant data)
    {
        var dict = data.AsGodotDictionary();
        int from = dict["from_index"].As<int>();
        int to   = SlotIndex;
        if (from == to) return;

        var fromSlot = Inventory.Slots[from];
        var toSlot   = Inventory.Slots[to];

        (toSlot.Item, fromSlot.Item)         = (fromSlot.Item, toSlot.Item);
        (toSlot.Quantity, fromSlot.Quantity) = (fromSlot.Quantity, toSlot.Quantity);

        Inventory.EmitSignal(Inventory.SignalName.InventoryChanged);
    }
}
```

---

## 7. Serialization

Save inventories as `item_id + quantity` pairs. Never serialize the full `ItemData` Resource — instead, look up items at load time from a preloaded registry. This keeps save files small and decoupled from resource paths.

### GDScript

```gdscript
# item_registry.gd — add as autoload named ItemRegistry
extends Node

# Populate by scanning a folder, or assign manually in _ready().
var _items: Dictionary = {}  # id → ItemData


func _ready() -> void:
    _load_all("res://items/")


func _load_all(folder: String) -> void:
    var dir := DirAccess.open(folder)
    if dir == null:
        return
    dir.list_dir_begin()
    var file_name := dir.get_next()
    while file_name != "":
        if file_name.ends_with(".tres"):
            var item: ItemData = load(folder + file_name)
            if item and item.id != "":
                _items[item.id] = item
        file_name = dir.get_next()


func get_item(id: String) -> ItemData:
    return _items.get(id, null)


# ── Serialize ────────────────────────────────────────────────────────────────

func serialize_inventory(inventory: Inventory) -> Array:
    var data: Array = []
    for slot in inventory.slots:
        if slot.is_empty():
            data.append(null)
        else:
            data.append({"id": slot.item.id, "qty": slot.quantity})
    return data


# ── Deserialize ──────────────────────────────────────────────────────────────

func deserialize_inventory(inventory: Inventory, data: Array) -> void:
    for i in mini(data.size(), inventory.slots.size()):
        var entry = data[i]
        if entry == null:
            inventory.slots[i] = InventorySlot.new()
        else:
            var item: ItemData = get_item(entry["id"])
            if item == null:
                push_error("ItemRegistry: unknown item id '%s'" % entry["id"])
                inventory.slots[i] = InventorySlot.new()
                continue
            var slot          := InventorySlot.new()
            slot.item         = item
            slot.quantity     = entry["qty"]
            inventory.slots[i] = slot
    inventory.inventory_changed.emit()
```

**Usage inside a save system:**

```gdscript
# In SaveManager.save_game():
data["inventory"] = ItemRegistry.serialize_inventory(player.inventory)

# In SaveManager.load_game():
ItemRegistry.deserialize_inventory(player.inventory, data["inventory"])
```

### C#

```csharp
// ItemRegistry.cs — add as autoload named ItemRegistry
using System.Collections.Generic;
using Godot;
using Godot.Collections;

public partial class ItemRegistry : Node
{
    private readonly Dictionary<string, ItemData> _items = new();

    public override void _Ready() => LoadAll("res://items/");

    private void LoadAll(string folder)
    {
        using var dir = DirAccess.Open(folder);
        if (dir == null) return;

        dir.ListDirBegin();
        string fileName = dir.GetNext();
        while (fileName != "")
        {
            if (fileName.EndsWith(".tres"))
            {
                var item = GD.Load<ItemData>(folder + fileName);
                if (item != null && item.Id != "")
                    _items[item.Id] = item;
            }
            fileName = dir.GetNext();
        }
    }

    public ItemData GetItem(string id)
        => _items.TryGetValue(id, out var item) ? item : null;

    // ── Serialize ─────────────────────────────────────────────────────────────

    public Godot.Collections.Array SerializeInventory(Inventory inventory)
    {
        var data = new Godot.Collections.Array();
        foreach (var slot in inventory.Slots)
        {
            if (slot.IsEmpty())
                data.Add(default(Variant));
            else
                data.Add(new Godot.Collections.Dictionary
                {
                    ["id"]  = slot.Item.Id,
                    ["qty"] = slot.Quantity,
                });
        }
        return data;
    }

    // ── Deserialize ───────────────────────────────────────────────────────────

    public void DeserializeInventory(Inventory inventory, Godot.Collections.Array data)
    {
        int count = Mathf.Min(data.Count, inventory.Slots.Count);
        for (int i = 0; i < count; i++)
        {
            if (data[i].VariantType == Variant.Type.Nil)
            {
                inventory.Slots[i] = new InventorySlot();
                continue;
            }

            var entry = data[i].AsGodotDictionary();
            var item  = GetItem(entry["id"].As<string>());
            if (item == null)
            {
                GD.PushError($"ItemRegistry: unknown item id '{entry["id"]}'");
                inventory.Slots[i] = new InventorySlot();
                continue;
            }

            inventory.Slots[i] = new InventorySlot
            {
                Item     = item,
                Quantity = entry["qty"].As<int>(),
            };
        }
        inventory.EmitSignal(Inventory.SignalName.InventoryChanged);
    }
}
```

---

## 8. Implementation Checklist

- [ ] `ItemData` extends `Resource` with a stable `id` string set in the Inspector
- [ ] `ItemData` files live under `res://items/` and are committed to version control
- [ ] `Inventory.add_item()` returns leftover count; callers handle a full inventory
- [ ] `inventory_changed` signal drives all UI updates — UI never polls per-frame
- [ ] `InventorySlot.remove_from_stack()` clears `item` to `null` when quantity reaches 0
- [ ] Equipment slots keyed by `SlotType` enum, not by string, to catch typos at compile time
- [ ] `Equipment.get_total_stat()` is called when stats are needed, not cached unless profiling demands it
- [ ] Serialization stores `id + quantity` only — never full `ItemData` objects or resource paths
- [ ] `ItemRegistry` loads items at startup; all deserialization goes through it
- [ ] Drag-and-drop swaps slot contents directly then emits `inventory_changed` once
- [ ] `max_stack_size = 1` on `EQUIPMENT` and `KEY_ITEM` types to prevent stacking
- [ ] All `push_error()` messages include the class name and method for easy tracing
