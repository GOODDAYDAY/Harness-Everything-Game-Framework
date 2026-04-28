---
name: godot-tscn-format
description: Godot TSCN文件格式详解。当用户需要TSCN文件格式相关信息时使用。
---

# godot-tscn-format

## 何时使用
当用户需要Godot TSCN文件格式详解时使用此技能。

## 执行指示
1. 提供TSCN文件格式的详细说明
2. 回答用户关于TSCN文件结构、节点定义、资源引用等问题
3. 提供TSCN文件示例和最佳实践

## 输出格式
返回Godot TSCN文件格式详解内容，包括文件结构说明和示例代码。

## 示例

**用户请求：**
我需要了解TSCN文件的基本结构。

**执行过程：**
1. 查找TSCN文件结构相关内容
2. 提供详细说明和示例代码

**输出：**
TSCN文件分为五个主要部分，按以下顺序排列：

1. **文件描述符**
2. **外部资源**
3. **内部资源**
4. **节点**
5. **连接**

### 文件描述符

```
[gd_scene load_steps=4 format=3 uid="uid://cecaux1sm7mo0"]
```

### 外部资源

```
[ext_resource type="Script" path="res://script.gd" id=1]
```

### 内部资源

```
[sub_resource type="SphereMesh" id="SphereMesh_6x2n3"]
```

### 节点

```
[node name="Player" type="Node3D"]                    ; 场景根
[node name="Arm" type="Node3D" parent="."]            ; 直接子节点
[node name="Hand" type="Node3D" parent="Arm"]         ; Arm的子节点
```

### 连接

```
[connection signal="pressed" from="Button" to="Script" method="on_button_pressed"]
```