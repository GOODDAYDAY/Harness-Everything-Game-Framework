---
name: godot-scene-skill
description: Godot UI与场景开发指南。当用户需要UI和场景开发相关信息时使用。
auto_load: false
---

# godot-scene-skill

## 何时使用
当用户需要Godot UI与场景开发指南时使用此技能。

## 执行指示
1. 提供Godot UI节点系统和场景开发的详细说明
2. 回答用户关于TSCN文件格式、UI布局、场景组织等问题
3. 提供UI和场景开发的最佳实践和示例代码

## 输出格式
返回Godot UI与场景开发指南内容，包括TSCN文件示例和使用说明。

## 示例

**用户请求：**
我需要了解Godot的UI布局系统。

**执行过程：**
1. 查找Godot UI布局系统相关内容
2. 提供详细说明和示例代码

**输出：**
Godot的UI布局系统基于锚点和偏移量，支持多种布局模式：

### 锚点预设

```tscn
[node name="Button" type="Button"]
# 全屏覆盖
anchors_preset = 15  # Full Rect
# 居中对齐
anchors_preset = 12  # Center
# 顶部左侧
anchors_preset = 0   # Top Left
```

### 容器布局

```tscn
[node name="VBoxContainer" type="VBoxContainer"]
layout_mode = 3
anchors_preset = 15
offset_right = 400.0
offset_bottom = 300.0
vertical_alignment = 1  # Center
spacing = 20

[node name="Button1" type="Button" parent="VBoxContainer"]
text = "按钮1"
size_flags_horizontal = 3  # Fill

[node name="Button2" type="Button" parent="VBoxContainer"]
text = "按钮2"
size_flags_horizontal = 3  # Fill
```