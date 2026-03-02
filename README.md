# A simple script to generate 2D lip-sync frame data.

[English](README.md) | [中文](README_CN.md)

A simple script to generate 2D lip-sync frame data from:
- OpenAI Whisper JSON output
- Audio files (`.wav`, `.ogg`) via Rhubarb Lip Sync

## Usage Instructions

This script supports two input modes:

1. Whisper JSON mode
2. Audio mode (Rhubarb)

For Whisper JSON mode, you can generate input with a command like this:

```bash
$ whisper audio.flac --model large-v3 --language English --word_timestamps True --output_format json
```

### Installation

The script should work on all systems.

- Whisper JSON mode requires **eSpeak NG**.
- Audio mode requires **Rhubarb Lip Sync** executable in `PATH` (`rhubarb` command available).

Install eSpeak NG according to your operating system. For Linux, it's usually a single command; for Windows, please refer to the eSpeak NG documentation.

```bash
$ # If using uv
$ uv sync
$ # If using pip
$ pip install -r requirements.txt
```

### Script Usage

Whisper JSON mode:

```bash
$ python main.py audio.json -l en
```

Audio mode (Rhubarb):

```bash
$ python main.py audio.wav
```

### Script Arguments

* `--frame` `-f`: Target frame rate in Blender (default: `30`)
* `--min-gap-seconds` `-g`: Minimum interval between keyframes in seconds (default: `0.18`)
* `--silence-seconds` `-s`: Duration of silence keyframes in seconds (default: `0.22`)
* `--max-duration-seconds`: Maximum duration of a non-silence keyframe in seconds (default: `0`, disabled)
* `--viseme_map` `-m`: Path to the viseme mapping file (default: `viseme_map.json`)
* `--language` `-l`: Language code, `zh` for Chinese, `en` for English (default: `en`)
* `--output` `-o`: Path to the output keyframe data file (default: `output.txt`)

Rhubarb-specific behavior:

* If input file extension is `.wav` or `.ogg`, the script runs Rhubarb mode automatically.
* If `--viseme_map` is left as default (`viseme_map.json`) and `rhubarb_map.json` exists, the script automatically uses `rhubarb_map.json`.

## Working with Example .blend

You need to switch to the **Scripting** tab in Blender and run the script once to enable the side panel.

The panel has 3 parts:

1. Right-click on the property you want to keyframe (e.g., mouth shape index), select **Copy Full Data Path**, and paste it here.
2. Adjust the keyframe offset if needed.
3. Specify the generated keyframe data file.

## Notes

* Whisper JSON mode:
  * `viseme_map.json` is designed for **poimiku** mouth textures.
  * `viseme_map2.json` is designed for default **Uma Musume** mouth textures.
* Rhubarb mode:
  * `rhubarb_map.json` is designed for **poimiku** mouth textures.
  * `rhubarb_map2.json` is designed for default **Uma Musume** mouth textures.

## Credits

* [poimiku](https://space.bilibili.com/16381701) for providing mouth textures and support.
* [Blender Lip Sync Addon by Charley 3D](https://github.com/Charley3d/lip-sync)

## Changelog

### v0.2.0

* Improved viseme generation algorithm, added Pinyin-to-phoneme conversion for Chinese.
* Added `--language` parameter to specify language (`zh` for Chinese, `en` for English).

### v0.1.2

* Fixed issues where `--output` and input data were not working correctly.
* Improved documentation.

### v0.1.1

* Fixed missing silence keyframes.
* Handled segments where not all keyframes could be placed by implementing frame-skipping instead of truncation.
* Updated Python version in `.python-version` to 3.10.
* Updated `示例.blend`.

### v0.1

* Initial release with basic functionality.
