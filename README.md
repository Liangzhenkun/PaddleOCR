# PaddleOCR Desktop Tool

Desktop GUI wrapper for local PaddleOCR-based document parsing on Windows.

This project packages a simple Tkinter application around official PaddleOCR
pipelines so you can:

- run plain OCR with `PP-OCRv5`
- run structured parsing with `PP-StructureV3`
- try official `PaddleOCR-VL` variants
- export results to Markdown and JSON
- check for upstream PaddleOCR updates from the official repository

## Included files

- `ocr_gui.py`: main desktop application
- `launch_gui.bat`: double-click launcher for Windows
- `requirements.txt`: Python package requirements for the app layer

## What is intentionally excluded from Git

The repository ignores local-only content such as:

- virtual environments
- generated OCR outputs
- local logs
- benchmark files
- test PDFs and sample images

This keeps the repository clean for public sharing while preserving all local
working data on your machine.

## Setup

1. Create and activate a Python 3.12 environment.
2. Install a PaddlePaddle build that matches your device and CUDA runtime.
3. Install the app requirements:

```powershell
pip install -r requirements.txt
```

## Run

Double-click:

```text
launch_gui.bat
```

Or run manually:

```powershell
.\.venv\Scripts\pythonw.exe .\ocr_gui.py
```

## Output

Generated results are written to:

```text
outputs\
```

Each run creates a timestamped subfolder.

## Notes

- The first run of a model may take longer because official model weights may
  need to be downloaded.
- For GPU usage, install the correct PaddlePaddle package separately according
  to the official PaddleOCR / PaddlePaddle documentation.
