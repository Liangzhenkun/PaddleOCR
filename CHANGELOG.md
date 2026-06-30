# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog, with lightweight version notes for this repository.

## [Unreleased]

- Sanitized the public README visuals and removed screenshots that exposed local desktop context.

## [0.3.1] - 2026-06-30

### Fixed

- Corrected upstream version parsing so update checks no longer misreport reachable repositories as connection failures
- Hid the progress indicator when the app is idle instead of showing a stray green block at startup
- Added safer uninstall cleanup rules for the packaged Windows installer to better remove `PaddleOCRDesktopTool.exe` and `_internal`

### Added

- New Settings window with General / Help / About tabs
- In-app About information with author, version, release date, and project URL
- Quick usage help inside the desktop app

### Changed

- Slightly reduced the default main-window height so the preview area feels less oversized
- Simplified installer language setup to a single choice by reusing the installer language as the app's initial language

## [0.3.0] - 2026-06-30

### Added

- Chinese / English desktop UI switching
- Persistent application language settings
- PyInstaller build spec for standalone EXE output
- Inno Setup installer script for Windows packaging
- Bundled Simplified Chinese installer language file

### Changed

- Installed builds now store logs, settings, and outputs under the user-local app data directory

## [0.2.0] - 2026-06-30

### Added

- Public-facing `LICENSE` file using Apache-2.0
- Improved bilingual README for GitHub visitors
- Safe public preview assets under `docs/`
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
