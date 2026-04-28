---
name: godot-clear-children
description: Godot正确清除子节点的方法。当用户需要了解如何正确清除子节点时使用。
---

# godot-clear-children

## 何时使用
当用户需要了解如何在Godot中正确清除子节点时使用此技能。

## 执行指示
1. 提供Godot中清除子节点的正确方法
2. 回答用户关于节点清理、内存管理等问题
3. 提供清除子节点的示例代码和最佳实践

## 输出格式
返回Godot正确清除子节点的方法，包括代码示例和使用说明。

## 示例

**用户请求：**
我需要了解如何在Godot中正确清除子节点。

**执行过程：**
1. 查找清除子节点相关内容
2. 提供详细说明和示例代码

**输出：**
Godot中正确清除子节点的方法：

### 错误的方法

```gdscript
# 错误：直接遍历子节点数组删除会导致索引问题
for child in get_children():
    child.free()  # 或 child.queue_free()
```

### 正确的方法

#### 方法1：使用while循环

```gdscript
# 正确：使用while循环直到没有子节点
while get_child_count() > 0:
    var child = get_child(0)
    child.queue_free()  # 使用queue_free()进行延迟清理
```

#### 方法2：使用副本数组

```gdscript
# 正确：遍历子节点数组的副本
for child in get_children().duplicate():
    child.queue_free()
```

#### 方法3：使用clear_children方法（Godot 4.1+）

```gdscript
# 正确：使用内置方法（Godot 4.1+）
clear_children()  # 会自动调用queue_free()清除所有子节点
```

### 最佳实践

1. **使用queue_free()**：始终使用`queue_free()`而不是`free()`，以确保节点在合适的时机被清理
2. **避免在_process中清理**：尽量不在`_process`或`_physics_process`中频繁清理节点
3. **使用信号通知**：在节点被清理前发送信号通知其他节点
4. **检查实例有效性**：在访问可能被清理的节点前，使用`is_instance_valid()`检查

### 示例：清理敌人节点

```gdscript
func clear_enemies() -> void:
    # 清理所有敌人节点
    for child in get_children().duplicate():
        if child is Enemy:
            child.queue_free()

func _on_game_over() -> void:
    # 游戏结束时清理所有子节点
    clear_children()  # Godot 4.1+
    # 或使用while循环
    # while get_child_count() > 0:
    #     get_child(0).queue_free()
```