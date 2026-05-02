---
name: pixel-rendering
description: "纯像素渲染：无抗锯齿、point filtering、色板管理、像素字体、瓦片绘制"
auto_load: true
---

# 像素渲染

## 核心理念

纯像素风格——无模糊、无抗锯齿、清晰锐利的像素边缘。

## 缩放

```python
# 小图放大到目标尺寸——用 NEAREST 保持像素锐利
scaled = pygame.transform.scale(small_sprite, (w * scale, h * scale))
# 不要用 smoothscale ——会模糊
```

## 色板

每个场景限制 4-6 个主色调，通过明度变化做层次而非色相变化：

```python
# 推荐：定义常量色板
PALETTE = {
    "sky_day": (200, 220, 240),
    "ground": (100, 180, 80),
    "wood": (120, 80, 40),
    "warm_light": (240, 200, 120),
    "night_bg": (10, 20, 40),
}
```

## 瓦片绘制

```python
TILE_SIZE = 80  # 80px tiles for 2560x1440
for row in range(18):  # 1440/80
    for col in range(32):  # 2560/80
        x = col * TILE_SIZE
        y = row * TILE_SIZE
        # draw tile at (x, y)
```

## 逐像素精灵生成

```python
surf = pygame.Surface((w, h))
for x in range(w):
    for y in range(h):
        surf.set_at((x, y), color_at(x, y))
```

## 字体

使用小号 bitmap/pixel 字体，通过 NEAREST 放大到可读尺寸。不要用 TrueType 平滑字体做主要 UI。
