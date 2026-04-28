---
name: godot-serialization-pattern
description: Godot序列化模式指南。当用户需要数据序列化和反序列化相关信息时使用。
---

# godot-serialization-pattern

## 何时使用
当用户需要了解Godot数据序列化和反序列化模式时使用此技能。

## 执行指示
1. 提供Godot序列化模式的详细说明
2. 回答用户关于数据序列化、保存/加载游戏状态等问题
3. 提供序列化和反序列化的示例代码和最佳实践

## 输出格式
返回Godot序列化模式指南内容，包括序列化示例和使用说明。

## 示例

**用户请求：**
我需要了解如何在Godot中实现数据序列化。

**执行过程：**
1. 查找序列化模式相关内容
2. 提供详细说明和示例代码

**输出：**
Godot中实现数据序列化的推荐模式：

### 基本序列化模式

```gdscript
class_name Item extends RefCounted

var id: String = ""
var name: String = ""
var quantity: int = 1

func to_dict() -> Dictionary:
    return {
        "id": id,
        "name": name,
        "quantity": quantity
    }

func from_dict(data: Dictionary) -> Item:
    id = data.get("id", id)
    name = data.get("name", name)
    quantity = data.get("quantity", quantity)
    return self

static func create_from_dict(data: Dictionary) -> Item:
    return Item.new().from_dict(data)
```

### 复杂对象序列化

```gdscript
class_name Player extends RefCounted

var name: String = ""
var level: int = 1
var health: int = 100
var inventory: Array[Item] = []

func to_dict() -> Dictionary:
    var inventory_data = []
    for item in inventory:
        inventory_data.append(item.to_dict())
    
    return {
        "name": name,
        "level": level,
        "health": health,
        "inventory": inventory_data
    }

func from_dict(data: Dictionary) -> Player:
    name = data.get("name", name)
    level = data.get("level", level)
    health = data.get("health", health)
    
    # 解析物品数据
    inventory.clear()
    var inventory_data = data.get("inventory", [])
    for item_data in inventory_data:
        inventory.append(Item.create_from_dict(item_data))
    
    return self

static func create_from_dict(data: Dictionary) -> Player:
    return Player.new().from_dict(data)
```

### 保存和加载游戏状态

```gdscript
func save_game(slot: int) -> void:
    var save_data = {
        "player": player.to_dict(),
        "current_level": current_level,
        "timestamp": OS.get_unix_time()
    }
    
    var file = FileAccess.open("user://save_%d.json" % slot, FileAccess.WRITE)
    if file:
        file.store_line(JSON.stringify(save_data))
        file.close()

func load_game(slot: int) -> bool:
    var file_path = "user://save_%d.json" % slot
    if not FileAccess.file_exists(file_path):
        return false
    
    var file = FileAccess.open(file_path, FileAccess.READ)
    if file:
        var content = file.get_as_text()
        var save_data = JSON.parse_string(content)
        file.close()
        
        # 加载数据
        player = Player.create_from_dict(save_data.get("player", {}))
        current_level = save_data.get("current_level", 1)
        return true
    
    return false
```