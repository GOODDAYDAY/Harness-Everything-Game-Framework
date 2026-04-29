---
name: godot-class-name-checker
description: "Godot 4.x 内置类名冲突检查器 — 创建新类前检查是否与Godot内置类名冲突"
auto_load: false
---
# Godot 类名冲突检查器

## 概述

这个技能帮助AI在Godot项目中创建自定义类时，避免与Godot内置类名发生命名冲突。

## 触发条件

当AI需要：
- 创建新的GDScript类（`class_name XXX`）
- 命名新的脚本文件
- 定义新的类/类型名称
- 创建Autoload单例

## Godot 4.x 内置类名列表

以下是Godot 4.x所有内置类名，创建自定义类时**必须避免**使用这些名称：

### 核心/基础类
```
Object, Node, Resource, RefCounted
```

### 2D节点
```
Node2D, CanvasItem, Control, CanvasLayer
Sprite2D, Sprite3D, SpriteBase3D
AnimatedSprite2D, AnimatedSprite3D
Area2D, Area3D
PhysicsBody2D, PhysicsBody3D
CharacterBody2D, CharacterBody3D
StaticBody2D, StaticBody3D
RigidBody2D, RigidBody3D
KinematicBody2D, KinematicBody3D
CollisionShape2D, CollisionShape3D
CollisionPolygon2D, CollisionPolygon3D
CollisionObject2D, CollisionObject3D
Joint2D, Joint3D
PinJoint2D, PinJoint3D
HingeJoint2D, HingeJoint3D
SliderJoint2D, SliderJoint3D
Generic6DOFJoint2D, Generic6DOFJoint3D
RayCast2D, RayCast3D
RayCast2D, RayCast3D
Light2D, Light3D, Light2D, Light3D
OccluderPolygon2D
TileMap, TileMapLayer, TileSet
```

### 3D节点
```
Node3D, VisualInstance3D
MeshInstance3D, MeshInstance2D
MultiMeshInstance3D
CSGPrimitive3D, CSGBox3D, CSGSphere3D, CSGCylinder3D, CSGTorus3D, CSGPolygon3D, CSGCombiner3D
Camera3D, Camera3D
AudioListener3D, AudioListener3D
DirectionalLight3D, OmniLight3D, SpotLight3D
WorldEnvironment
FogVolume
ReflectionProbe
GPUParticles3D, GPUParticles2D
GPUParticlesAttractor3D, GPUParticlesAttractorVectorField3D
VehicleBody3D, VehicleWheel3D
NavigationRegion3D, NavigationAgent3D, NavigationLink3D, NavigationObstacle3D
VoxelGI, SDFGI
VisibleOnScreenNotifier3D, VisibleOnScreenNotifier2D
NavigationMeshInstance3D
Skeleton3D, Skeleton2D
BoneAttachment3D
PhysicalBone3D
SoftBody3D
```

### UI/Control节点
```
Control, LayoutContainer, BaseButton
Button, CheckBox, CheckButton, RadioButton
Label, RichTextLabel
LineEdit, TextEdit, CodeEdit
HSlider, VSlider
ScrollContainer, HScrollBar, VScrollBar
Panel, PanelContainer
ColorRect
TextureRect, TextureButton, TextureProgressBar
ProgressBar, ProgressBar
ItemList, Tree, Table
TabContainer, TabBar
MenuBar, PopupMenu, MenuButton
Window, AcceptDialog, ConfirmationDialog, FileDialog
ColorPicker, ColorPickerButton
HSeparator, VSeparator
BoxContainer, HBoxContainer, VBoxContainer
GridContainer, FlowContainer, HFlowContainer, VFlowContainer
CenterContainer, AspectRatioContainer
SubViewport, SubViewportContainer
GraphNode, GraphEdit
TreeItem
```

### 容器/其他节点
```
Container, Viewport
SplitContainer, HSplitContainer, VSplitContainer
MenuButton, OptionButton
Timer, Tween, ProcessTween
AnimationPlayer, AnimationTree, AnimationMixer
AudioStreamPlayer, AudioStreamPlayer2D, AudioStreamPlayer3D
VideoStreamPlayer
CanvasModulate
HTTPRequest
WebSocketPeer, WebSocketMultiplayerPeer
TCPServer, TCPStreamPeer, PacketPeer
UDPServer
FileAccess, Directory, ConfigFile
Marshalls
ResourcePreloader
AnimationNode, AnimationNodeStateMachine, AnimationNodeBlendTree
```

### 资源类
```
Resource, Script, TextFile
Mesh, ArrayMesh, ImmediateMesh, SurfaceTool, MeshDataTool
ArrayMesh, PrismMesh, BoxMesh, SphereMesh, CapsuleMesh, CylinderMesh, TorusMesh, TubeTrailMesh, RibbonTrailMesh, ParticleProcessMaterial
Texture2D, Texture3D, TextureLayered, Texture2DArray
CompressedTexture2D,CompressedTexture3D,CompressedTexture2DArray
Gradient, GradientTexture1D, GradientTexture2D
Image, ImageTexture
Font, BitmapFont, DynamicFont
FontFile, FontVariation
Theme
StyleBox, StyleBoxFlat, StyleBoxTexture, StyleBoxLine
Shader, ShaderMaterial
PhysicsMaterial
BoxShape3D, SphereShape3D, CapsuleShape3D, CylinderShape3D, ConvexPolygonShape3D, ConcavePolygonShape3D
World3D, World2D
Environment, Sky, ProceduralSkyMaterial, PanoramaSkyMaterial
Curve, Curve2D, Curve3D
Path3D, PathFollow3D
NavigationMesh
Polygon2D
Line2D
Path2D
```

### 数学类型
```
Vector2, Vector3, Vector4
Vector2i, Vector3i, Vector4i
Transform2D, Transform3D
Basis, Quaternion
Color, Color8
AABB, Rect2, Rect2i
Plane
Projection
```

### 内置类型关键字
```
int, float, bool, String
Array, Dictionary
PackedByteArray, PackedInt32Array, PackedInt64Array, PackedFloat32Array, PackedFloat64Array
PackedStringArray, PackedVector2Array, PackedVector3Array, PackedColorArray
Callable, Signal
Variant, Null
```

### 全局/单例
```
Engine, ClassDB, JSON
ProjectSettings, Input, InputMap
ResourceLoader, ResourceSaver
OS, FileSystem
Time, TLSOptions
```

### @GlobalScope 常量/方法
```
print, print_rich, push_error, push_warning
load, preload
instantiate, new
assert, breakpoint
```

## 检查流程

### 当AI准备创建新类时，必须执行以下检查：

1. **读取用户请求**: 确定要创建的类名
2. **转换为小写比较**: Godot类名不区分大小写
3. **检查冲突列表**: 对比上述列表

### 推荐做法：

1. **检查脚本命名**:
   - 读取 `project.godot` 查看已有的 `class_name` 注册
   - 读取已有脚本文件检查class_name

2. **命名建议格式**:
   - 使用项目特定前缀：`MyGamePlayer` 而非 `Player`
   - 使用功能性描述：`BattleCharacter` 而非 `Character`
   - 避免使用：`Node`, `Sprite`, `Button`, `Area`, `Body`, `Light`, `Camera` 等

3. **验证步骤**:
   ```gdscript
   # 在创建类前验证
   var proposed_name = "Player"
   if ClassDB.class_exists(proposed_name):
       print("警告: " + proposed_name + " 是Godot内置类名!")
   ```

## 推荐的命名模式

### ✅ 推荐
```
# 游戏相关
FF14Character, FF14BattleSystem, FF14Inventory
RPGPlayer, RPGBattleManager, RPGQuestSystem
MyGamePlayerController, MyGameEnemyBase

# 功能性描述
DamageCalculator, StateMachine, InventoryGrid
BattleEffectResolver, DialogueSystem, SaveManager
```

### ❌ 避免
```
Player (与Godot内置无关但容易冲突)
Enemy (通用名称)
Node, Sprite, Area, Body (直接冲突)
Button, Label, Window (UI组件名)
```

## 输出格式

当AI准备创建新类时，应该输出类似：

```
## 类名冲突检查
- 提议名称: [XXX]
- 冲突检查: [是/否]
- 建议名称: [如果冲突，提供替代名称]
- 项目已有类名: [列出project.godot中已有的class_name]
```

## 相关文档

- Godot类参考: https://docs.godotengine.org/en/stable/classes/index.html
- ClassDB API: https://docs.godotengine.org/en/stable/classes/class_classdb.html
