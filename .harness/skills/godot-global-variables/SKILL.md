---
name: godot-global-variables
description: Godot全局变量使用指南。当用户需要全局变量和Autoload相关信息时使用。
---

# godot-global-variables

## 何时使用
当用户需要了解Godot全局变量使用和Autoload模式时使用此技能。

## 执行指示
1. 提供Godot全局变量和Autoload的详细说明
2. 回答用户关于Autoload注册、访问方式、最佳实践等问题
3. 提供Autoload使用示例代码

## 输出格式
返回Godot全局变量使用指南内容，包括Autoload配置和使用示例。

## 示例

**用户请求：**
我需要了解如何在Godot中使用Autoload。

**执行过程：**
1. 查找Autoload相关内容
2. 提供详细说明和示例代码

**输出：**
Godot中使用Autoload的步骤：

1. **注册Autoload**：在Godot编辑器中，进入Project → Autoload，添加需要全局访问的脚本
2. **访问方式**：直接使用注册的名称访问，如`$Game`或`Game`
3. **最佳实践**：将全局状态、游戏管理等功能放在Autoload中

示例Autoload脚本：

```gdscript
# Game.gd
class_name Game

var score: int = 0
var player_health: int = 100

func add_score(points: int) -> void:
    score += points
    print("Score: %d" % score)

func damage_player(amount: int) -> void:
    player_health -= amount
    if player_health <= 0:
        player_health = 0
        game_over()

func game_over() -> void:
    print("Game Over!")
```

访问Autoload：

```gdscript
# 在其他脚本中访问
Game.add_score(100)
Game.damage_player(20)
```