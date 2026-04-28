---
name: godot-console
version: 1.0
description: 提供Godot引擎控制台命令行工具的调用能力，支持运行Godot命令、执行脚本、导出项目等操作，适用于游戏开发和自动化任务。
---

# Godot控制台调用工具

## 概述

本Skill提供了与Godot引擎控制台命令行工具的交互能力，允许用户执行各种Godot相关的操作，如运行游戏、启动编辑器、导出项目、执行脚本等。

## 功能特性

- ✅ 执行Godot命令行操作
- ✅ 运行Godot脚本
- ✅ 导出Godot项目
- ✅ 调试Godot应用
- ✅ 支持各种平台（Windows、Linux、macOS）

## 环境要求

- Godot引擎已安装（建议3.5+版本）
- Godot二进制文件已添加到系统PATH环境变量（可选，但推荐）
- Windows、Linux或macOS操作系统

## 使用指南

### 基本语法

在Windows和Linux上：
```bash
godot [命令] [参数]
```

在macOS上：
```bash
/Applications/Godot.app/Contents/MacOS/Godot [命令] [参数]
```

### 常用命令

#### 运行游戏
```bash
godot # 在当前目录运行项目
godot scene.tscn # 运行特定场景
```

#### 启动编辑器
```bash
godot -e # 启动编辑器
godot -e scene.tscn # 启动编辑器并打开特定场景
```

#### 导出项目
```bash
godot --export "Windows Desktop" game.exe
godot --export Android game.apk
godot --export-pack "Linux/X11" game.pck
```

#### 运行脚本
```bash
godot -s script.gd # 运行GDScript脚本
godot -s script.gd --check-only # 仅检查脚本错误
```

#### 调试模式
```bash
godot -d # 以调试模式运行
godot -d scene.tscn # 以调试模式运行特定场景
```

## 命令参考

### 一般选项

| 命令 | 描述 |
|------|------|
| -h, --help, /? | 显示命令行选项列表 |
| --version | 显示版本字符串 |
| -v, --verbose | 使用详细的标准输出模式 |
| --quiet | 安静模式，silences stdout消息 |

### 运行选项

| 命令 | 描述 |
|------|------|
| -e, --editor | 启动编辑器而不是运行场景 |
| -p, --project-manager | 启动项目管理器 |
| -q, --quit | 在第一次迭代后退出 |
| -l <locale>, --language <locale> | 使用特定的区域设置 |
| --path <directory> | 项目路径 |
| -u, --upwards | 向上扫描文件夹查找project.godot文件 |

### 调试选项

| 命令 | 描述 |
|------|------|
| -d, --debug | 调试（本地标准输出调试器） |
| -b, --breakpoints | 断点列表 |
| --profiling | 在脚本调试器中启用分析 |
| --remote-debug <address> | 远程调试 |
| --debug-collisions | 运行场景时显示碰撞形状 |
| --debug-navigation | 运行场景时显示导航多边形 |

### 导出选项

| 命令 | 描述 |
|------|------|
| --export <target> | 使用给定的导出目标导出项目 |
| --export-debug <target> | 类似于--export，但使用调试模板 |
| --export-pack <preset> <path> | 仅导出给定预设的游戏包 |

## 平台特定说明

### Windows
- Godot二进制文件通常位于`C:\Program Files\Godot\Godot.exe`
- 建议将Godot安装目录添加到系统PATH环境变量

### Linux
- Godot二进制文件通常位于`/usr/local/bin/godot`或用户主目录
- 确保二进制文件有执行权限：`chmod +x godot`

### macOS
- Godot应用程序位于`/Applications/Godot.app`
- 命令行执行路径：`/Applications/Godot.app/Contents/MacOS/Godot`

## 示例用法

### 示例1：运行Godot项目

**输入**
```
运行当前目录的Godot项目
```

**输出**
```bash
# 执行命令
godot

# 执行结果
# Godot引擎启动并运行当前目录的项目
```

### 示例2：导出Godot项目

**输入**
```
导出Godot项目为Windows平台，预设名为"Windows Desktop"，输出文件为game.exe
```

**输出**
```bash
# 执行命令
godot --export "Windows Desktop" game.exe

# 执行结果
# 项目导出到game.exe文件
```

### 示例3：运行Godot脚本

**输入**
```
运行当前目录的test.gd脚本
```

**输出**
```bash
# 执行命令
godot -s test.gd

# 执行结果
# 脚本执行结果输出
```

### 示例4：启动Godot编辑器

**输入**
```
启动Godot编辑器并打开main.tscn场景
```

**输出**
```bash
# 执行命令
godot -e main.tscn

# 执行结果
# Godot编辑器启动并打开main.tscn场景
```

## 注意事项

1. **路径设置**：如果Godot二进制文件不在PATH中，需要指定完整路径
2. **项目路径**：对于不在当前目录的项目，需要使用`--path`参数指定项目路径
3. **导出预设**：导出项目时，预设名称必须与项目中定义的导出预设匹配
4. **macOS差异**：macOS上需要使用应用程序包内的二进制文件路径
5. **权限问题**：Linux上需要确保Godot二进制文件有执行权限

## 故障排除

### 常见问题

1. **Godot命令未找到**：确保Godot已安装并添加到PATH环境变量
2. **项目未找到**：确保当前目录包含project.godot文件，或使用--path参数指定
3. **导出失败**：检查导出预设名称是否正确，以及是否安装了相应的导出模板
4. **脚本执行失败**：确保脚本继承自SceneTree或MainLoop

### 解决方案

- **添加Godot到PATH**：
  - Windows：系统属性 → 高级 → 环境变量 → 编辑PATH
  - Linux：编辑~/.bashrc或~/.zshrc，添加`export PATH=$PATH:/path/to/godot`
  - macOS：编辑~/.bash_profile或~/.zshrc，添加`export PATH=$PATH:/Applications/Godot.app/Contents/MacOS`

- **指定项目路径**：
  ```bash
  godot --path /path/to/project [命令]
  ```

- **检查导出预设**：在Godot编辑器中查看项目 → 导出，确认预设名称

## 高级用法

### 自动化脚本

可以创建批处理脚本或shell脚本来自动化常见的Godot任务：

#### Windows批处理示例（build.bat）
```batch
@echo off
godot --export "Windows Desktop" build/windows/game.exe
godot --export "Linux/X11" build/linux/game.x86_64
godot --export Android build/android/game.apk
echo 构建完成！
pause
```

#### Linux/macOS shell脚本示例（build.sh）
```bash
#!/bin/bash
godot --export "Windows Desktop" build/windows/game.exe
godot --export "Linux/X11" build/linux/game.x86_64
godot --export Android build/android/game.apk
echo "构建完成！"
```

### CI/CD集成

可以在CI/CD流水线中使用Godot命令行工具进行自动化测试和构建：

#### GitHub Actions示例
```yaml
name: Godot Build

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Godot
        uses: croconut/godot-ci@v1.2.0
        with:
          godot-version: 3.5
      - name: Build Linux
        run: godot --export "Linux/X11" game.x86_64
      - name: Build Windows
        run: godot --export "Windows Desktop" game.exe
      - name: Upload Artifacts
        uses: actions/upload-artifact@v2
        with:
          name: builds
          path: |
            game.x86_64
            game.exe
```

## 总结

本Skill提供了完整的Godot控制台命令行工具调用能力，支持各种Godot相关的操作，适用于游戏开发、自动化任务和CI/CD集成。通过本Skill，用户可以方便地执行Godot命令、运行脚本、导出项目等操作，提高开发效率和自动化水平。

## 参考资料

- Godot官方文档：https://docs.godotengine.org/
- Godot命令行教程（原文档）：https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html#doc-command-line-tutorial
- Godot控制台手册知识库：../../../knowledge_base/documents/Godot控制台手册知识库条目.md
