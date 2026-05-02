---
name: python-ui-system
description: "Python/pygame UI系统——按钮、面板、HUD布局、文字渲染、交互反馈"
auto_load: false
---

# UI 系统 (Python/pygame)

## 响应式布局

所有 UI 元素位置基于屏幕比例，不硬编码像素：
```python
sidebar_x = int(screen_width * 0.85)
button_w = int(screen_width * 0.12)
```

## 按钮

必须包含：hover高亮、点击反馈、禁用状态。
使用 `pygame.Rect` 做碰撞检测。

## 面板

半透明背景 + 边框。使用 `Surface.set_alpha()` 做透明度。

## HUD

固定层（不随地图滚动），包含：阶段标签、玩家列表、日志、按钮。
