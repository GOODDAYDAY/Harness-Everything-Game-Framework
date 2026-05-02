---
name: python-game-tools
description: "Python游戏工具：截图、录屏、输入模拟、状态查询——与harness TCP bridge配合"
auto_load: false
---

# Python 游戏工具

## 截图

```python
def take_screenshot(screen, path):
    """保存当前画面为 PNG"""
    import os
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    pygame.image.save(screen, path)
```

## 录屏

```python
# 每 N 帧保存一张 PNG，后期合成为 MP4（ffmpeg）
frame_count = 0
record_interval = 6  # 每 6 帧存一张

# 在主循环中：
if recording and frame_count % record_interval == 0:
    pygame.image.save(screen, f"frames/frame_{frame_count:04d}.png")
```

后期合成：`ffmpeg -framerate 30 -i frames/frame_%04d.png output.mp4`

## 输入注入

```python
# 模拟鼠标点击
ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=1)
pygame.event.post(ev)

# 模拟按键
ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
pygame.event.post(ev)
```

## 状态查询

游戏应维护一个 `get_state()` 方法，返回 dict：
```python
def get_state(self):
    return {
        "phase": self.phase,
        "round": self.round,
        "players": [p.to_dict() for p in self.players],
        "alive_count": sum(1 for p in self.players if p.alive),
    }
```

## TCP Bridge

框架自带 `tcp_server.py`，监听 19840，提供：
- `ping` — 存活检测
- `screenshot` — 截图到文件
- `input_click/key` — 远程输入
- `state` — 查询游戏状态
- `record_start/stop/frame` — 帧录制
- `quit` — 优雅退出
