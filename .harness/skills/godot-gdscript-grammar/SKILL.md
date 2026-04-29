---
name: godot-gdscript-grammar
description: Godot GDScript语法详解。当用户需要GDScript语法相关信息时使用。
auto_load: true
---

# godot-gdscript-grammar

## 何时使用
当用户需要GDScript语法详解和示例代码时使用此技能。

## 执行指示
1. 提供GDScript语法的详细说明
2. 回答用户关于GDScript语法规则、数据类型、控制流等问题
3. 提供GDScript示例代码和最佳实践

## 输出格式
返回GDScript语法详解内容，包括代码示例和使用说明。

## 示例

**用户请求：**
我需要了解GDScript的函数定义语法。

**执行过程：**
1. 查找GDScript函数定义相关内容
2. 提供详细说明和示例代码

**输出：**
GDScript函数定义语法：

```gdscript
# 基本函数定义
func my_function():
    print("Hello from function")

# 带参数的函数
func add(a, b):
    return a + b

# 带类型注解的函数
func multiply(a: int, b: int) -> int:
    return a * b

# 带默认参数的函数
func greet(name: String = "World"):
    print("Hello, %s!" % name)

# 可变参数函数
func sum_all(args...):
    var total = 0
    for arg in args:
        total += arg
    return total
```