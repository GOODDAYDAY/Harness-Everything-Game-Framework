---
name: game-loop-pattern
description: "游戏循环模式：update/render分离、delta time、状态机、帧率控制"
auto_load: true
---

# 游戏循环模式

## 标准循环

```python
while running:
    dt = clock.tick(60) / 1000.0  # seconds since last frame
    process_input()
    update(dt)
    render(screen)
    pygame.display.flip()
```

## 固定时间步长（物理）

```python
accumulator = 0.0
FIXED_DT = 1.0 / 60.0
while running:
    dt = clock.tick() / 1000.0
    accumulator += dt
    while accumulator >= FIXED_DT:
        fixed_update(FIXED_DT)
        accumulator -= FIXED_DT
    render(screen)
```

## 状态机

```python
class GameState(Enum):
    STARTUP = "startup"
    NIGHT = "night"
    DAY_INVESTIGATION = "day_investigation"
    DAY_VOTE = "day_vote"
    GAME_OVER = "game_over"

state = GameState.STARTUP

def update(dt):
    if state == GameState.NIGHT:
        update_night(dt)
    elif state == GameState.DAY_INVESTIGATION:
        update_day_investigation(dt)
```

## Delta Time 使用

- 所有和时间相关的计算必须乘以 `dt`：`position += velocity * dt`
- 计时器累加：`timer += dt; if timer >= duration: fire()`
- 动画帧进度：`frame = int(elapsed / frame_duration) % total_frames`

## 性能

- 不要每帧创建新 Surface——复用
- `screen.fill()` 在 render 开头
- 只在需要时调用 `pygame.display.flip()` 或 `update(rect)`
