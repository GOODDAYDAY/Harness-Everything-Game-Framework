---
name: godot-packedscene
description: Godot PackedScene使用指南。当用户需要场景加载和池化相关信息时使用。
---

# godot-packedscene

## 何时使用
当用户需要了解Godot PackedScene使用、场景加载和池化技术时使用此技能。

## 执行指示
1. 提供PackedScene的详细说明和使用方法
2. 回答用户关于场景加载、实例化、池化等问题
3. 提供场景加载和池化的示例代码和最佳实践

## 输出格式
返回Godot PackedScene使用指南内容，包括场景加载和池化示例。

## 示例

**用户请求：**
我需要了解如何在Godot中加载和实例化场景。

**执行过程：**
1. 查找PackedScene相关内容
2. 提供详细说明和示例代码

**输出：**
Godot中加载和实例化场景的方法：

### 预加载场景

```gdscript
# 预加载场景（推荐用于频繁使用的场景）
var _enemy_scene = preload("res://scenes/enemy.tscn")

# 实例化场景
var enemy = _enemy_scene.instantiate()
add_child(enemy)
enemy.position = Vector2(100, 100)
```

### 异步加载场景

```gdscript
# 异步加载大型场景
func load_boss_scene() -> void:
    var thread = Thread.new()
    thread.start(func():
        var scene = ResourceLoader.load_threaded_get("res://scenes/boss.tscn")
        call_deferred("_on_boss_scene_loaded", scene)
    )

func _on_boss_scene_loaded(scene: PackedScene) -> void:
    var boss = scene.instantiate()
    add_child(boss)
```

### 场景池化

```gdscript
# 场景池化示例
class_name ScenePool

var scene: PackedScene
var pool: Array[Node] = []
var max_pool_size: int = 10

func initialize(scene_path: String, size: int) -> void:
    scene = preload(scene_path)
    max_pool_size = size
    # 预创建实例
    for i in range(size):
        var instance = scene.instantiate()
        instance.queue_free()  # 初始状态为未使用
        pool.append(instance)

func get_instance() -> Node:
    # 从池中获取实例
    for instance in pool:
        if not is_instance_valid(instance) or not instance.is_inside_tree():
            var new_instance = scene.instantiate()
            pool[pool.find(instance)] = new_instance
            return new_instance
    # 池已满，创建新实例
    if pool.size() < max_pool_size:
        var new_instance = scene.instantiate()
        pool.append(new_instance)
        return new_instance
    return null

func return_instance(instance: Node) -> void:
    # 归还实例到池
    if instance in pool:
        instance.remove_from_parent()
        instance.queue_free()
```