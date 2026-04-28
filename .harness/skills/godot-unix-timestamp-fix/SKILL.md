---
name: godot-unix-timestamp-fix
description: Godot Unix时间戳错误修复。当用户遇到Unix时间戳相关问题时使用。
---

# godot-unix-timestamp-fix

## 何时使用
当用户在Godot中遇到Unix时间戳相关错误时使用此技能。

## 执行指示
1. 提供Godot中Unix时间戳的正确使用方法
2. 回答用户关于时间戳转换、时区处理等问题
3. 提供时间戳错误修复的示例代码和最佳实践

## 输出格式
返回Godot Unix时间戳错误修复的方法，包括代码示例和使用说明。

## 示例

**用户请求：**
我在Godot中使用Unix时间戳时遇到了问题，需要帮助。

**执行过程：**
1. 查找Unix时间戳相关内容
2. 提供详细说明和示例代码

**输出：**
Godot中Unix时间戳的正确使用方法：

### 获取当前Unix时间戳

```gdscript
# 正确：使用OS.get_unix_time()获取当前Unix时间戳（秒）
var current_timestamp = OS.get_unix_time()
print("Current Unix timestamp: %d" % current_timestamp)

# 获取当前时间戳（毫秒）
var current_timestamp_ms = OS.get_unix_time_from_system() * 1000
print("Current Unix timestamp (ms): %d" % current_timestamp_ms)
```

### 时间戳转换为日期时间

```gdscript
# 将Unix时间戳转换为DateTime对象
func timestamp_to_datetime(timestamp: int) -> DateTime:
    var datetime = DateTime.new()
    datetime.set_unix_time(timestamp)
    return datetime

# 格式化日期时间
func format_datetime(datetime: DateTime) -> String:
    return datetime.format("%Y-%m-%d %H:%M:%S")

# 示例使用
var timestamp = OS.get_unix_time()
var datetime = timestamp_to_datetime(timestamp)
var formatted = format_datetime(datetime)
print("Formatted date: %s" % formatted)
```

### 常见错误及修复

#### 错误1：时间戳精度问题

```gdscript
# 错误：混用秒和毫秒
var timestamp_ms = OS.get_unix_time()  # 错误：返回的是秒

# 正确：明确处理精度
var timestamp_sec = OS.get_unix_time()  # 秒
var timestamp_ms = timestamp_sec * 1000  # 毫秒
```

#### 错误2：时区处理

```gdscript
# 正确：考虑时区
var datetime = DateTime.new()
datetime.set_unix_time(OS.get_unix_time())
datetime = datetime.to_local_time()  # 转换为本地时区
print("Local time: %s" % datetime.format("%Y-%m-%d %H:%M:%S"))
```

#### 错误3：时间戳比较

```gdscript
# 正确：使用相同精度的时间戳进行比较
var start_time = OS.get_unix_time()
# 执行一些操作
var end_time = OS.get_unix_time()
var elapsed = end_time - start_time
print("Elapsed time: %d seconds" % elapsed)
```

### 最佳实践

1. **明确精度**：始终明确时间戳的精度（秒或毫秒）
2. **使用DateTime**：对于日期时间操作，使用DateTime对象而不是原始时间戳
3. **考虑时区**：在处理用户可见的时间时，考虑时区转换
4. **错误处理**：在解析外部时间戳时，添加错误处理

### 完整示例：保存游戏时间戳

```gdscript
func save_game_with_timestamp(slot: int) -> void:
    var save_data = {
        "player": player.to_dict(),
        "timestamp": OS.get_unix_time(),
        "save_time": format_datetime(DateTime.new().set_unix_time(OS.get_unix_time()))
    }
    
    var file = FileAccess.open("user://save_%d.json" % slot, FileAccess.WRITE)
    if file:
        file.store_line(JSON.stringify(save_data))
        file.close()
        print("Game saved at: %s" % save_data["save_time"])
```