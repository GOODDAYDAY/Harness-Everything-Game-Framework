---
name: python-state-machine
description: "Python状态机模式——Enum状态定义、transition规则、进入/退出回调、状态历史"
auto_load: false
---

# 状态机模式 (Python)

## 定义

```python
from enum import Enum
class Phase(Enum):
    SETUP = auto()
    NIGHT = auto()
    DAY_DISCUSSION = auto()
    DAY_VOTE = auto()
    GAME_OVER = auto()
```

## 转换规则

定义合法转换：`SETUP → NIGHT → DAY_DISCUSSION → DAY_VOTE → NIGHT → ... → GAME_OVER`

非法转换应抛出异常或记录警告。

## 进入/退出回调

每个状态可定义 `on_enter()` 和 `on_exit()` 执行初始化和清理。
