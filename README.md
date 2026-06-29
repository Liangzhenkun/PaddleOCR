# PaddleOCR Desktop Tool

Local Windows desktop GUI for document OCR and structured parsing built on top of the official PaddleOCR pipelines.

[中文说明](#中文说明) | [English](#english)

## English

### Overview

This project wraps official PaddleOCR pipelines in a lightweight Tkinter desktop app so you can run OCR locally with a GPU and export clean Markdown/JSON results.

Supported official model options:

- `PP-OCRv5`: plain OCR, fastest
- `PP-StructureV3`: structured parsing, recommended default
- `PaddleOCR-VL`
- `PaddleOCR-VL-1.5`
- `PaddleOCR-VL-1.6`

### Features

- Local desktop GUI for image and PDF OCR
- Markdown and JSON export
- Official model selector
- Upstream PaddleOCR version check on startup
- Pure window launch mode on Windows
- Keeps generated outputs local and out of Git

### Project Structure

- `ocr_gui.py`: main application
- `launch_gui.bat`: Windows launcher
- `requirements.txt`: app-layer Python dependencies
- `.gitignore`: excludes local outputs, virtual envs, benchmarks, logs, and test assets

### Requirements

- Windows
- Python 3.12 recommended
- GPU strongly recommended for large PDFs
- PaddlePaddle installed separately for your CUDA/runtime environment

### Installation

1. Create and activate a Python environment.
2. Install a matching PaddlePaddle package for your machine.
3. Install app dependencies:

```powershell
pip install -r requirements.txt
```

### Run

Double-click:

```text
launch_gui.bat
```

Or run manually:

```powershell
.\.venv\Scripts\pythonw.exe .\ocr_gui.py
```

### Outputs

All generated files are written to:

```text
outputs\
```

Each run creates a timestamped subfolder.

Typical outputs:

- `ocr_result.txt`
- `ocr_result.md`
- `ocr_result.json`
- `document.md`
- `document_summary.json`

### Screenshots

Recommended screenshots for the GitHub homepage:

- `docs/screenshots/main-window.png`: main app window
- `docs/screenshots/model-selector.png`: model dropdown and options
- `docs/screenshots/result-preview.png`: Markdown preview after parsing
- `docs/screenshots/output-folder.png`: generated result files

If you add screenshots later, you can embed them here with:

```md
![Main Window](docs/screenshots/main-window.png)
```

### Notes

- The first run of a model may take longer because official weights may need to be downloaded.
- `PaddleOCR-VL-1.6` is stronger but significantly heavier than `PP-StructureV3`.
- Local logs are written to `logs/app.log` when available.

---

## 中文说明

### 项目简介

这是一个基于官方 PaddleOCR 管线封装的 Windows 本地桌面工具，用 Tkinter 做了一个轻量 GUI，方便直接处理图片和 PDF，并导出 Markdown / JSON 结果。

目前支持的官方模型：

- `PP-OCRv5`：纯文本 OCR，速度最快
- `PP-StructureV3`：结构化解析，推荐默认使用
- `PaddleOCR-VL`
- `PaddleOCR-VL-1.5`
- `PaddleOCR-VL-1.6`

### 功能特性

- 本地桌面 GUI，支持图片和 PDF
- 导出 Markdown 和 JSON
- 支持官方模型切换
- 启动时检查官方 PaddleOCR 版本更新
- Windows 纯窗口启动，不弹黑色控制台
- 自动把本地产物排除在 Git 之外

### 项目文件

- `ocr_gui.py`：主程序
- `launch_gui.bat`：Windows 启动器
- `requirements.txt`：应用层依赖
- `.gitignore`：忽略本地输出、虚拟环境、日志、测试文件等

### 环境要求

- Windows
- 建议 Python 3.12
- 处理大 PDF 时建议使用 GPU
- 需要你自己按本机 CUDA / 驱动环境单独安装 PaddlePaddle

### 安装步骤

1. 创建并激活 Python 虚拟环境。
2. 安装与你机器匹配的 PaddlePaddle。
3. 安装本项目依赖：

```powershell
pip install -r requirements.txt
```

### 运行方式

双击：

```text
launch_gui.bat
```

或者手动运行：

```powershell
.\.venv\Scripts\pythonw.exe .\ocr_gui.py
```

### 输出目录

所有生成结果都会写到：

```text
outputs\
```

每次运行都会自动生成一个带时间戳的子目录。

常见输出文件包括：

- `ocr_result.txt`
- `ocr_result.md`
- `ocr_result.json`
- `document.md`
- `document_summary.json`

### 截图建议

如果你后面想把仓库首页做得更完整，建议补这几张图：

- `docs/screenshots/main-window.png`：主界面
- `docs/screenshots/model-selector.png`：模型选择下拉框
- `docs/screenshots/result-preview.png`：结果预览区
- `docs/screenshots/output-folder.png`：输出目录内容

以后可以直接在 README 里这样插图：

```md
![主界面](docs/screenshots/main-window.png)
```

### 说明

- 某个模型第一次运行时，官方权重可能需要先下载，所以首跑会更慢。
- `PaddleOCR-VL-1.6` 效果更强，但资源占用和耗时也明显更高。
- 本地日志默认写入 `logs/app.log`。
