---
name: pygame-basics
description: "pygame 基础开发：窗口创建、Surface操作、draw绘图、事件处理、图像加载、字体渲染"
auto_load: true
---

# Pygame 基础

## 窗口与初始化

```python
import pygame
pygame.init()
screen = pygame.display.set_mode((2560, 1440), pygame.RESIZABLE)
pygame.display.set_caption("Game Title")
clock = pygame.time.Clock()
```

## 主循环

```python
running = True
while running:
    dt = clock.tick(60) / 1000.0  # delta time in seconds
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    # update(dt)
    # render(screen)
    pygame.display.flip()
pygame.quit()
```

## 绘图

- `screen.fill((r, g, b))` — 填充背景色
- `pygame.draw.rect(screen, color, (x, y, w, h))` — 矩形
- `pygame.draw.circle(screen, color, (x, y), radius)` — 圆形
- `pygame.draw.line(screen, color, start, end, width)` — 线段
- `screen.blit(surface, (x, y))` — 贴图

## 图像

```python
img = pygame.image.load("path.png")
# 像素风格：禁用平滑缩放
img = pygame.transform.scale(img, (w, h))
# 或使用 .convert() 和 .convert_alpha()
```

## 字体

```python
font = pygame.font.Font(None, 36)  # 默认字体
text_surf = font.render("Hello", True, (255, 255, 255))
screen.blit(text_surf, (10, 10))
```

## 事件

常用事件类型：`QUIT`, `KEYDOWN`, `KEYUP`, `MOUSEBUTTONDOWN`, `MOUSEMOTION`
