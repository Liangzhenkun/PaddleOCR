# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog, with lightweight version notes for this repository.

## [Unreleased]

- Reserve this section for future public changes before the next tagged release.

## [0.2.0] - 2026-06-30

### Added

- Public-facing `LICENSE` file using Apache-2.0
- Improved bilingual README for GitHub visitors
- Real project screenshots under `docs/screenshots/`
- Release / changelog guidance in the README
- Local log entry point in the GUI (`Open Log`)

### Changed

- Cleaned repository structure for public sharing
- Excluded local outputs, virtual environment, logs, benchmarks, and personal working files from Git

## [0.1.0] - 2026-06-30

### Added

- Initial public desktop OCR tool
- Windows GUI based on Tkinter
- Support for `PP-OCRv5`
- Support for `PP-StructureV3`
- Support for `PaddleOCR-VL`, `PaddleOCR-VL-1.5`, and `PaddleOCR-VL-1.6`
- Markdown / JSON export
- Startup update check against the official PaddleOCR repository
- Pure window launcher via `launch_gui.bat`
