---
name: godot-singleton-pattern
description: Godot单例模式指南。当用户需要单例模式实现相关信息时使用。
---

# godot-singleton-pattern

## 何时使用
当用户需要了解Godot单例模式实现和使用方法时使用此技能。

## 执行指示
1. 提供Godot单例模式的详细说明
2. 回答用户关于单例模式实现、Autoload配置、最佳实践等问题
3. 提供单例模式的示例代码

## 输出格式
返回Godot单例模式指南内容，包括单例实现和使用示例。

## 示例

**用户请求：**
我需要了解如何在Godot中实现单例模式。

**执行过程：**
1. 查找单例模式相关内容
2. 提供详细说明和示例代码

**输出：**
Godot中实现单例模式的方法：

### 使用Autoload实现单例

1. **注册Autoload**：在Godot编辑器中，进入Project → Autoload，添加需要全局访问的脚本
2. **访问方式**：直接使用注册的名称访问，如`Game`或`UIManager`

### 示例单例脚本

```gdscript
# GameManager.gd
class_name GameManager

# 单例实例
var instance: GameManager

# 游戏状态
var game_state: String = "menu"
var score: int = 0
var lives: int = 3

# 初始化
func _ready() -> void:
    # 确保只存在一个实例
    if instance:
        queue_free()
        return
    instance = self
    set_process(false)

# 游戏状态管理
func set_game_state(new_state: String) -> void:
    game_state = new_state
    print("Game state changed to: %s" % new_state)

func add_score(points: int) -> void:
    score += points
    print("Score: %d" % score)

func lose_life() -> void:
    lives -= 1
    if lives <= 0:
        lives = 0
        game_over()
    print("Lives: %d" % lives)

func game_over() -> void:
    set_game_state("game_over")
    print("Game Over!")

# 静态访问方法
static func get_instance() -> GameManager:
    return instance
```

### 使用单例

```gdscript
# 在其他脚本中访问
GameManager.set_game_state("playing")
GameManager.add_score(100)
GameManager.lose_life()

# 检查游戏状态
if GameManager.game_state == "game_over":
    print("Game over detected!")
```

### 最佳实践

- **职责单一**：每个单例负责一个特定功能
- **最小化使用**：只在必要时使用单例，避免过度依赖
- **状态管理**：使用单例管理全局游戏状态
- **服务提供**：使用单例提供全局服务（如音频管理、网络请求等）