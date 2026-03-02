# 生成 2D 口型帧数据的脚本

[English](README.md) | [中文](README_CN.md)

## 使用说明

本脚本支持两种输入模式：

1. Whisper JSON 模式
2. 音频模式（Rhubarb）

Whisper JSON 模式下，可以用例如以下命令生成输入：

```bash
$ whisper audio.flac --model large-v3 --language Chinese --word_timestamps True --output_format json --initial_prompt "以下是普通话的句子。"
```

### 安装依赖

理论上所有系统都通用。

- Whisper JSON 模式需要安装 **eSpeak NG**
- 音频模式需要安装 **Rhubarb Lip Sync**，并保证 `rhubarb` 命令在 `PATH` 中可用

根据自己的系统解决 eSpeak NG 的安装问题，Linux 一般只需一行命令，Windows 请参考官方文档。

```bash
$ # If use uv
$ uv sync
$ # If use pip
$ pip install -r requirements.txt
```

### 脚本使用

Whisper JSON 模式（输入文件为 `audio.json`）：

```bash
$ python main.py audio.json -l zh
```

音频模式（Rhubarb）：

```bash
$ python main.py audio.wav
```

### 脚本参数

* `--frame` `-f` Blender 中对应的帧率，默认 `30`
* `--min-gap-seconds` `-g` 关键帧之间的最小间隔（秒），默认 `0.18`
* `--silence-seconds` `-s` 不说话的关键帧的持续时间（秒），默认 `0.22`
* `--max-duration-seconds` 非静音口型的最大持续时间（秒），默认 `0`（不启用）
* `--viseme_map` `-m` 唇形与数值的映射文件路径，默认 `viseme_map.json`
* `--language` `-l` 语言，`zh` 为中文，`en` 为英文，默认 `en`
* `--output` `-o` 输出关键帧数据文件路径，默认 `output.txt`

Rhubarb 相关行为：

* 输入文件后缀为 `.wav` 或 `.ogg` 时，会自动进入 Rhubarb 模式
* 如果 `--viseme_map` 保持默认值 `viseme_map.json`，且目录下存在 `rhubarb_map.json`，则会自动改用 `rhubarb_map.json`

## 示例.blend 使用

需要切换到 Scripting 运行一次脚本，才会有侧边面板

3 个部分的参数：

1. 在需要打关键帧的属性上右键点 `复制完整数据路径`，然后粘贴到这里
2. 可调整关键帧的偏移
3. 指定输出的关键帧数据文件

## 备注

Whisper JSON 模式：

`viseme_map.json` 对应 poimiku 的嘴巴贴图，`viseme_map2.json` 对应马娘默认的嘴巴贴图

Rhubarb 模式：

`rhubarb_map.json` 对应 poimiku 的嘴巴贴图，`rhubarb_map2.json` 对应马娘默认的嘴巴贴图

## Credits

* [poimiku](https://space.bilibili.com/16381701) 提供嘴巴贴图和肯定
* [Blender Lip Sync Addon by Charley 3D](https://github.com/Charley3d/lip-sync)

## 更新日志

### v0.2.0

* 改进口型生成算法，为中文添加了拼音到音素的转换
* 添加 `--language` 参数，用于指定语言，`zh` 为中文，`en` 为英文

### v0.1.2

* 修复 `--output` 和输入数据无作用
* 完善说明文档

### v0.1.1

* 修复不说话的关键帧不全
* 无法打出全部关键帧的语段，将采取跳帧来处理，而不是只取前 N 个
* 改 `.python-version` 中的版本号为 3.10
* 更新 `示例.blend`

### v0.1

初始版本，已实现基本功能
