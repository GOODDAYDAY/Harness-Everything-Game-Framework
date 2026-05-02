---
name: python-assets-pipeline
description: "Python游戏资源管线——精灵加载、缓存、调色板管理、程序化生成"
auto_load: false
---

# 资源管线 (Python/pygame)

## 精灵缓存

```python
_sprite_cache = {}
def get_sprite(key, generator_fn):
    if key not in _sprite_cache:
        _sprite_cache[key] = generator_fn()
    return _sprite_cache[key]
```

## 调色板

集中管理所有颜色常量，不在渲染代码中创建新颜色：
```python
COLORS = {"night_sky": (10,15,30), "day_sky": (150,200,240)}
```

## 程序化生成

像素精灵应在首次请求时生成并缓存，避免加载外部文件。
