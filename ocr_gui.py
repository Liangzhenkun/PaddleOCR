from __future__ import annotations

import json
import locale
import logging
import os
import queue
import re
import sys
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

import fitz
import requests
import tkinter as tk
from packaging.version import Version
from tkinter import filedialog, messagebox, scrolledtext, ttk

import paddle
import paddleocr
from paddleocr import PPStructureV3, PaddleOCR, PaddleOCRVL

from app_meta import (
    APP_NAME,
    APP_PUBLISHER,
    APP_RELEASE_DATE,
    APP_RELEASE_VERSION,
    APP_REPOSITORY_URL,
    APP_SLUG,
)


SOURCE_DIR = Path(__file__).resolve().parent
UPDATE_SOURCE_URL = (
    "https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/readme/README_cn.md"
)
SUPPORTED_UI_LANGUAGES = ("zh_CN", "en_US")


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def install_dir() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return SOURCE_DIR


def default_data_root() -> Path:
    env_value = os.getenv("PADDLEOCR_DESKTOP_DATA_DIR")
    if env_value:
        return Path(env_value).expanduser()
    if is_frozen():
        local_appdata = os.getenv("LOCALAPPDATA")
        if local_appdata:
            return Path(local_appdata) / APP_SLUG
    return SOURCE_DIR


APP_DIR = install_dir()
DATA_ROOT = default_data_root()
OUTPUT_ROOT = DATA_ROOT / "outputs"
LOG_ROOT = DATA_ROOT / "logs"
SETTINGS_PATH = DATA_ROOT / "settings.json"


TEXTS: dict[str, dict[str, str]] = {
    "en_US": {
        "window_title": f"{APP_NAME} {APP_RELEASE_VERSION}",
        "app_title": APP_NAME,
        "app_subtitle": (
            "Local GPU document OCR and parsing tool with Markdown export, "
            "official model selection, and update checks."
        ),
        "ui_language": "Interface",
        "runtime": "Local runtime: app {app_version} | paddleocr {paddleocr_version} | paddle {paddle_version} | GPU: {device_name}",
        "runtime_unknown_gpu": "CPU or unavailable",
        "update_starting": "Update check: starting",
        "update_contacting": "Update check: contacting upstream PaddleOCR repo",
        "update_unreachable": "Update check: could not reach the official PaddleOCR repo",
        "update_unparsed": "Update check: connected, but could not parse the latest upstream version",
        "update_newer": "Update check: newer release available ({latest_version}), local is {local_version}",
        "update_current": "Update check: local version is current ({local_version})",
        "section_input": "1. Choose Input File",
        "button_browse": "Browse",
        "section_options": "2. Parsing Options",
        "label_model": "Model",
        "label_doc_language": "OCR Language",
        "note_veo": "Note: Veo 3 is not an official PaddleOCR model, so it is not included. Official PaddleOCR-VL variants are included.",
        "button_run": "Run",
        "button_check_updates": "Check Updates",
        "button_open_output": "Open Output Folder",
        "button_open_markdown": "Open Markdown",
        "button_open_log": "Open Log",
        "button_settings": "Settings",
        "button_close": "Close",
        "status_ready": "Ready",
        "status_completed": "Completed",
        "status_failed": "Failed",
        "status_running": "Running... Current model: {model_label}",
        "output_not_generated": "Output folder: not generated",
        "output_running": "Output folder: running",
        "output_generated": "Output folder: {path}",
        "files_not_generated": "Result files: not generated",
        "files_generating": "Result files: generating",
        "files_generated": "Result files: {files}",
        "files_open_output": "Result files: open the output folder",
        "section_preview": "3. Preview",
        "dialog_choose_input": "Choose image or PDF",
        "dialog_filetypes_primary": "Images or PDF",
        "dialog_filetypes_all": "All files",
        "warn_missing_file_title": "Missing file",
        "warn_missing_file_body": "Please choose an image or PDF first.",
        "error_missing_file_title": "File not found",
        "error_missing_file_body": "Could not find:\n{path}",
        "run_started": (
            "Job started: {model_label}\n"
            "The first run of a model may take longer because official weights may need to be downloaded.\n"
        ),
        "run_failed_title": "Run failed",
        "run_failed_body": "{error}\n\nSee logs/app.log for more details.",
        "no_preview": "[No preview text]",
        "structured_done": "[Structured parsing completed. Results were exported to Markdown/JSON.]",
        "ocr_lang_en": "English",
        "ocr_lang_ch": "Chinese",
        "ui_lang_en_US": "English",
        "ui_lang_zh_CN": "简体中文",
        "settings_title": "Settings",
        "settings_tab_general": "General",
        "settings_tab_help": "Help",
        "settings_tab_about": "About",
        "settings_language": "Interface Language",
        "help_text": (
            "Quick Start\n\n"
            "1. Choose an image or PDF.\n"
            "2. Pick a model.\n"
            "   PP-OCRv5: fastest plain text OCR.\n"
            "   PP-StructureV3: recommended for PDFs and Markdown export.\n"
            "   PaddleOCR-VL: stronger document understanding, but heavier.\n"
            "3. Pick the document language.\n"
            "4. Click Run and wait for the output folder.\n"
            "5. Use Open Output Folder or Open Markdown to inspect the results.\n\n"
            "Notes\n\n"
            "- The first run of a model may take longer because official weights may need to be downloaded.\n"
            "- After the model weights are downloaded, local OCR, Structure, and VL runs can continue offline.\n"
            "- The desktop app stores logs, settings, and outputs in your local app data folder, not inside the installer package."
        ),
        "about_text": (
            "{app_name}\n\n"
            "Version: {app_version}\n"
            "Release date: {release_date}\n"
            "Author: {publisher}\n"
            "Built on PaddleOCR {paddleocr_version} and Paddle {paddle_version}\n"
            "GPU: {device_name}\n\n"
            "Local data folder:\n{data_root}\n\n"
            "Project page:\n{repo_url}\n\n"
            "This desktop tool wraps official local PaddleOCR models for Windows use."
        ),
    },
    "zh_CN": {
        "window_title": f"PaddleOCR 本地工具 {APP_RELEASE_VERSION}",
        "app_title": "PaddleOCR 本地工具",
        "app_subtitle": "本地 GPU 文档 OCR 与结构化解析工具，支持 Markdown 导出、官方模型切换和更新检查。",
        "ui_language": "界面语言",
        "runtime": "本地运行环境：app {app_version} | paddleocr {paddleocr_version} | paddle {paddle_version} | GPU：{device_name}",
        "runtime_unknown_gpu": "CPU 或不可用",
        "update_starting": "更新检查：准备开始",
        "update_contacting": "更新检查：正在连接官方 PaddleOCR 仓库",
        "update_unreachable": "更新检查：无法连接官方 PaddleOCR 仓库",
        "update_unparsed": "更新检查：已连上官方仓库，但暂时无法解析最新版本号",
        "update_newer": "更新检查：发现新版本（{latest_version}），当前本地版本为 {local_version}",
        "update_current": "更新检查：当前本地版本已是最新（{local_version}）",
        "section_input": "1. 选择输入文件",
        "button_browse": "浏览",
        "section_options": "2. 识别选项",
        "label_model": "模型",
        "label_doc_language": "识别语言",
        "note_veo": "说明：Veo 3 不是官方 PaddleOCR 模型，因此这里不提供。程序内置的是官方 PaddleOCR-VL 系列。",
        "button_run": "开始识别",
        "button_check_updates": "检查更新",
        "button_open_output": "打开输出目录",
        "button_open_markdown": "打开 Markdown",
        "button_open_log": "打开日志",
        "button_settings": "设置",
        "button_close": "关闭",
        "status_ready": "就绪",
        "status_completed": "识别完成",
        "status_failed": "识别失败",
        "status_running": "正在运行，当前模型：{model_label}",
        "output_not_generated": "输出目录：尚未生成",
        "output_running": "输出目录：正在生成",
        "output_generated": "输出目录：{path}",
        "files_not_generated": "结果文件：尚未生成",
        "files_generating": "结果文件：生成中",
        "files_generated": "结果文件：{files}",
        "files_open_output": "结果文件：请直接打开输出目录查看",
        "section_preview": "3. 结果预览",
        "dialog_choose_input": "选择图片或 PDF",
        "dialog_filetypes_primary": "图片或 PDF",
        "dialog_filetypes_all": "所有文件",
        "warn_missing_file_title": "缺少文件",
        "warn_missing_file_body": "请先选择图片或 PDF 文件。",
        "error_missing_file_title": "文件不存在",
        "error_missing_file_body": "找不到以下文件：\n{path}",
        "run_started": "任务已开始：{model_label}\n首次运行某个模型时，官方权重可能需要先下载，因此第一次会更慢。\n",
        "run_failed_title": "运行失败",
        "run_failed_body": "{error}\n\n更多细节请查看 logs/app.log。",
        "no_preview": "[没有可显示的预览文本]",
        "structured_done": "[结构化解析已完成，结果已导出为 Markdown / JSON。]",
        "ocr_lang_en": "英语",
        "ocr_lang_ch": "中文",
        "ui_lang_en_US": "English",
        "ui_lang_zh_CN": "简体中文",
        "settings_title": "设置",
        "settings_tab_general": "常规",
        "settings_tab_help": "帮助",
        "settings_tab_about": "关于",
        "settings_language": "界面语言",
        "help_text": (
            "快速开始\n\n"
            "1. 选择图片或 PDF 文件。\n"
            "2. 选择识别模型。\n"
            "   PP-OCRv5：最快，适合纯文本提取。\n"
            "   PP-StructureV3：更适合 PDF、教材和 Markdown 导出。\n"
            "   PaddleOCR-VL：文档理解更强，但模型更重。\n"
            "3. 选择文档识别语言。\n"
            "4. 点击“开始识别”，等待输出目录生成。\n"
            "5. 识别完成后，可直接打开输出目录或 Markdown 文件查看结果。\n\n"
            "补充说明\n\n"
            "- 某个模型第一次运行时，可能需要先下载官方权重，所以会更慢一些。\n"
            "- 官方模型权重下载完成后，后续的 OCR、Structure 和 VL 识别都可以离线本地运行。\n"
            "- 桌面版会把日志、设置和输出结果写入本机本地数据目录，不会打包进安装程序。"
        ),
        "about_text": (
            "{app_name}\n\n"
            "版本：{app_version}\n"
            "发布日期：{release_date}\n"
            "作者：{publisher}\n"
            "基于 PaddleOCR {paddleocr_version} 与 Paddle {paddle_version}\n"
            "GPU：{device_name}\n\n"
            "本地数据目录：\n{data_root}\n\n"
            "项目地址：\n{repo_url}\n\n"
            "这是一个面向 Windows 的本地 PaddleOCR 桌面封装工具。"
        ),
    },
}


MODEL_TEXTS: dict[str, dict[str, dict[str, str]]] = {
    "ppocrv5": {
        "en_US": {
            "label": "PP-OCRv5 | Plain OCR | Fastest",
            "note": "Best for extracting plain text quickly.",
        },
        "zh_CN": {
            "label": "PP-OCRv5 | 纯文本识别 | 最快",
            "note": "适合快速提取连续纯文本内容。",
        },
    },
    "ppstructurev3": {
        "en_US": {
            "label": "PP-StructureV3 | Structured Parsing | Recommended",
            "note": "Best balance for PDFs, textbooks, tables, and Markdown export.",
        },
        "zh_CN": {
            "label": "PP-StructureV3 | 结构化解析 | 推荐",
            "note": "在 PDF、教材、表格和 Markdown 导出之间平衡最好。",
        },
    },
    "vl16": {
        "en_US": {
            "label": "PaddleOCR-VL-1.6 | Flagship Document Model | Heavy",
            "note": "Latest flagship document parser. Larger first download and higher GPU usage.",
        },
        "zh_CN": {
            "label": "PaddleOCR-VL-1.6 | 旗舰文档模型 | 较重",
            "note": "当前更强的官方文档解析模型，首次下载更大，GPU 占用也更高。",
        },
    },
    "vl15": {
        "en_US": {
            "label": "PaddleOCR-VL-1.5 | Previous VL Release",
            "note": "Useful for comparing with VL-1.6.",
        },
        "zh_CN": {
            "label": "PaddleOCR-VL-1.5 | 上一代 VL 版本",
            "note": "适合和 VL-1.6 做速度与质量对比。",
        },
    },
    "vl1": {
        "en_US": {
            "label": "PaddleOCR-VL | First VL Release",
            "note": "Original VL pipeline kept by the official project.",
        },
        "zh_CN": {
            "label": "PaddleOCR-VL | 初代 VL 版本",
            "note": "官方保留的第一代视觉语言解析管线。",
        },
    },
}


@dataclass(frozen=True)
class ModelOption:
    key: str
    family: str
    pipeline_version: str | None = None


MODEL_OPTIONS: dict[str, ModelOption] = {
    "ppocrv5": ModelOption(key="ppocrv5", family="ocr"),
    "ppstructurev3": ModelOption(key="ppstructurev3", family="structure"),
    "vl16": ModelOption(key="vl16", family="vl", pipeline_version="v1.6"),
    "vl15": ModelOption(key="vl15", family="vl", pipeline_version="v1.5"),
    "vl1": ModelOption(key="vl1", family="vl", pipeline_version="v1"),
}


def ensure_data_root() -> Path:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    return DATA_ROOT


def ensure_output_root() -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    return OUTPUT_ROOT


def ensure_log_root() -> Path:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    return LOG_ROOT


def configure_logging() -> None:
    ensure_log_root()
    logging.basicConfig(
        filename=(LOG_ROOT / "app.log").as_posix(),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )


def open_path(path: Path) -> None:
    if path.exists():
        os.startfile(path)  # type: ignore[attr-defined]


def is_pdf(path: Path) -> bool:
    return path.suffix.lower() == ".pdf"


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def installed_paddleocr_version() -> str:
    return str(getattr(paddleocr, "__version__", "0.0.0"))


def fetch_latest_version_from_official_repo(
    timeout: int = 12,
) -> tuple[str | None, str]:
    try:
        response = requests.get(UPDATE_SOURCE_URL, timeout=timeout)
        response.raise_for_status()
    except Exception:
        logging.exception("Failed to check upstream PaddleOCR version")
        return None, "network_error"

    matches = re.findall(
        r"PaddleOCR\s+(\d+\.\d+\.\d+)(?:\s+发布|\s+Released|\b)",
        response.text,
        flags=re.IGNORECASE,
    )
    if not matches:
        logging.warning("Connected to upstream README but could not parse PaddleOCR version")
        return None, "parse_error"

    latest = max((Version(value) for value in matches), default=None)
    return (str(latest), "ok") if latest else (None, "parse_error")


def normalize_ui_language(value: str | None) -> str:
    if value in SUPPORTED_UI_LANGUAGES:
        return value  # type: ignore[return-value]
    if value and value.lower().startswith("zh"):
        return "zh_CN"
    return "en_US"


def detect_system_ui_language() -> str:
    candidates = [
        locale.getlocale()[0],
        os.getenv("LANG"),
        os.getenv("LC_ALL"),
        os.getenv("LC_MESSAGES"),
    ]
    for candidate in candidates:
        normalized = normalize_ui_language(candidate)
        if candidate:
            return normalized
    return "en_US"


def load_settings() -> dict[str, Any]:
    try:
        if SETTINGS_PATH.exists():
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        logging.exception("Failed to load settings")
    return {}


def save_settings(data: dict[str, Any]) -> None:
    try:
        ensure_data_root()
        SETTINGS_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        logging.exception("Failed to save settings")


def get_device_name() -> str:
    try:
        if paddle.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0:
            return paddle.device.cuda.get_device_name(0)
    except Exception:
        logging.exception("Failed to read CUDA device name")
    return "CPU or unavailable"


@dataclass
class JobConfig:
    input_path: Path
    model_key: str
    lang: str


@dataclass
class JobResult:
    output_dir: Path
    preview: str
    primary_text_file: Path | None = None
    markdown_file: Path | None = None
    json_file: Path | None = None


class OCRBackend:
    def __init__(self) -> None:
        self._ocr_pipelines: dict[str, PaddleOCR] = {}
        self._structure_pipelines: dict[str, PPStructureV3] = {}
        self._vl_pipelines: dict[str, PaddleOCRVL] = {}

    def close(self) -> None:
        for pipeline in self._ocr_pipelines.values():
            pipeline.close()
        for pipeline in self._structure_pipelines.values():
            pipeline.close()
        for pipeline in self._vl_pipelines.values():
            pipeline.close()

    def get_ocr_pipeline(self, lang: str) -> PaddleOCR:
        if lang not in self._ocr_pipelines:
            logging.info("Initializing PP-OCRv5 pipeline for lang=%s", lang)
            self._ocr_pipelines[lang] = PaddleOCR(
                lang=lang,
                device="gpu:0",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
        return self._ocr_pipelines[lang]

    def get_structure_pipeline(self, lang: str) -> PPStructureV3:
        if lang not in self._structure_pipelines:
            logging.info("Initializing PP-StructureV3 pipeline for lang=%s", lang)
            self._structure_pipelines[lang] = PPStructureV3(
                lang=lang,
                device="gpu:0",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
        return self._structure_pipelines[lang]

    def get_vl_pipeline(self, pipeline_version: str) -> PaddleOCRVL:
        if pipeline_version not in self._vl_pipelines:
            logging.info("Initializing PaddleOCR-VL pipeline version=%s", pipeline_version)
            self._vl_pipelines[pipeline_version] = PaddleOCRVL(
                pipeline_version=pipeline_version,
                device="gpu:0",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
            )
        return self._vl_pipelines[pipeline_version]

    def run_job(self, config: JobConfig, ui_language: str) -> JobResult:
        option = MODEL_OPTIONS[config.model_key]
        output_dir = ensure_output_root() / f"{config.input_path.stem}_{timestamp()}"
        output_dir.mkdir(parents=True, exist_ok=True)
        logging.info(
            "Starting job model=%s lang=%s input=%s ui_language=%s",
            option.key,
            config.lang,
            config.input_path,
            ui_language,
        )

        if option.family == "ocr":
            return self._run_text_ocr(config, output_dir)
        if option.family == "structure":
            return self._run_structure(config, output_dir, ui_language)
        return self._run_vl(config, output_dir, option, ui_language)

    def _run_text_ocr(self, config: JobConfig, output_dir: Path) -> JobResult:
        pipeline = self.get_ocr_pipeline(config.lang)
        pages: list[dict[str, Any]] = []
        preview_lines: list[str] = []

        with TemporaryDirectory(prefix="paddleocr_pdf_") as temp_dir:
            page_paths = self._prepare_page_inputs(config.input_path, Path(temp_dir))
            for page_number, page_path in enumerate(page_paths, start=1):
                page_result = pipeline.predict(page_path.as_posix())[0]
                texts = list(page_result.get("rec_texts", []))
                scores = list(page_result.get("rec_scores", []))
                joined_text = "\n".join(texts)

                pages.append(
                    {
                        "page": page_number,
                        "image_path": page_path.as_posix(),
                        "texts": texts,
                        "scores": scores,
                    }
                )

                preview_lines.append(f"===== Page {page_number} =====")
                preview_lines.append(joined_text if joined_text else "[No text recognized]")
                preview_lines.append("")

        preview_text = "\n".join(preview_lines).strip()
        text_path = output_dir / "ocr_result.txt"
        md_path = output_dir / "ocr_result.md"
        json_path = output_dir / "ocr_result.json"

        text_path.write_text(preview_text, encoding="utf-8")
        md_path.write_text(preview_text, encoding="utf-8")
        json_path.write_text(
            json.dumps(
                {
                    "input_path": config.input_path.as_posix(),
                    "model": "PP-OCRv5",
                    "lang": config.lang,
                    "pages": pages,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return JobResult(
            output_dir=output_dir,
            preview=preview_text,
            primary_text_file=text_path,
            markdown_file=md_path,
            json_file=json_path,
        )

    def _run_structure(
        self,
        config: JobConfig,
        output_dir: Path,
        ui_language: str,
    ) -> JobResult:
        pipeline = self.get_structure_pipeline(config.lang)
        results = list(pipeline.predict(config.input_path.as_posix()))
        return self._save_markdown_pipeline_results(
            results=results,
            pipeline=pipeline,
            output_dir=output_dir,
            combined_markdown_name="document.md",
            summary_name="document_summary.json",
            model_name="PP-StructureV3",
            input_path=config.input_path,
            ui_language=ui_language,
        )

    def _run_vl(
        self,
        config: JobConfig,
        output_dir: Path,
        option: ModelOption,
        ui_language: str,
    ) -> JobResult:
        pipeline = self.get_vl_pipeline(option.pipeline_version or "v1.6")
        results = list(pipeline.predict(config.input_path.as_posix()))
        return self._save_markdown_pipeline_results(
            results=results,
            pipeline=pipeline,
            output_dir=output_dir,
            combined_markdown_name="document.md",
            summary_name="document_summary.json",
            model_name=f"PaddleOCR-VL-{option.pipeline_version}",
            input_path=config.input_path,
            ui_language=ui_language,
        )

    def _save_markdown_pipeline_results(
        self,
        *,
        results: list[Any],
        pipeline: Any,
        output_dir: Path,
        combined_markdown_name: str,
        summary_name: str,
        model_name: str,
        input_path: Path,
        ui_language: str,
    ) -> JobResult:
        markdown_pages = []

        for page_index, result in enumerate(results, start=1):
            json_path = output_dir / f"page_{page_index:03d}.json"
            md_path = output_dir / f"page_{page_index:03d}.md"
            result.save_to_json(json_path.as_posix())
            result.save_to_markdown(md_path.as_posix())
            markdown_pages.append(result.markdown)

        combined_result = pipeline.concatenate_markdown_pages(markdown_pages)
        combined_md_path = output_dir / combined_markdown_name
        combined_json_path = output_dir / summary_name
        if hasattr(combined_result, "save_to_markdown"):
            combined_result.save_to_markdown(combined_md_path.as_posix())
            preview = combined_result.markdown.get("markdown_texts", "").strip()
        else:
            combined_md_path.write_text(str(combined_result), encoding="utf-8")
            preview = str(combined_result).strip()

        combined_json_path.write_text(
            json.dumps(
                {
                    "input_path": input_path.as_posix(),
                    "model": model_name,
                    "pages": len(results),
                    "markdown_file": combined_md_path.name,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        if not preview:
            preview = self._translate(ui_language, "structured_done")

        return JobResult(
            output_dir=output_dir,
            preview=preview,
            markdown_file=combined_md_path,
            json_file=combined_json_path,
        )

    def _prepare_page_inputs(self, input_path: Path, temp_dir: Path) -> list[Path]:
        if not is_pdf(input_path):
            return [input_path]

        doc = fitz.open(input_path)
        page_paths: list[Path] = []
        try:
            for page_index in range(doc.page_count):
                page = doc.load_page(page_index)
                pix = page.get_pixmap(dpi=200, alpha=False)
                page_path = temp_dir / f"page_{page_index + 1:03d}.png"
                pix.save(page_path.as_posix())
                page_paths.append(page_path)
        finally:
            doc.close()
        return page_paths

    def _translate(self, ui_language: str, key: str, **kwargs: Any) -> str:
        bundle = TEXTS.get(ui_language, TEXTS["en_US"])
        template = bundle.get(key, TEXTS["en_US"].get(key, key))
        return template.format(**kwargs)


class OCRApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.backend = OCRBackend()
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.current_output_dir: Path | None = None
        self.current_markdown_file: Path | None = None
        self.current_json_file: Path | None = None
        self.current_text_file: Path | None = None
        self.current_state = "ready"
        self.is_running_job = False
        self.is_checking_updates = False
        self.settings = load_settings()
        self.ui_language_code = normalize_ui_language(
            self.settings.get("ui_language") or detect_system_ui_language()
        )
        self.device_name = get_device_name()
        self.model_label_to_key: dict[str, str] = {}
        self.ocr_lang_label_to_key: dict[str, str] = {}
        self.ui_lang_label_to_code: dict[str, str] = {}
        self.settings_window: tk.Toplevel | None = None
        self.settings_general_tab: ttk.Frame | None = None
        self.settings_help_tab: ttk.Frame | None = None
        self.settings_about_tab: ttk.Frame | None = None
        self.settings_notebook: ttk.Notebook | None = None
        self.settings_language_label: ttk.Label | None = None
        self.settings_language_var = tk.StringVar()
        self.settings_language_box: ttk.Combobox | None = None
        self.settings_help_box: scrolledtext.ScrolledText | None = None
        self.settings_about_box: scrolledtext.ScrolledText | None = None
        self.settings_close_btn: ttk.Button | None = None

        self.file_var = tk.StringVar()
        self.model_key_var = tk.StringVar(value="ppstructurev3")
        self.model_label_var = tk.StringVar()
        self.lang_var = tk.StringVar(value="en")
        self.lang_label_var = tk.StringVar()
        self.ui_language_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.file_hint_var = tk.StringVar()
        self.model_note_var = tk.StringVar()
        self.update_var = tk.StringVar()
        self.runtime_var = tk.StringVar()

        self.root.geometry("1120x760")
        self.root.minsize(960, 640)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._build_ui()
        self._apply_language(refresh_comboboxes=True)
        self.root.after(150, self._poll_events)
        self._start_update_check()

    def _t(self, key: str, **kwargs: Any) -> str:
        bundle = TEXTS.get(self.ui_language_code, TEXTS["en_US"])
        template = bundle.get(key, TEXTS["en_US"].get(key, key))
        return template.format(**kwargs)

    def _model_label(self, key: str) -> str:
        return MODEL_TEXTS[key][self.ui_language_code]["label"]

    def _model_note(self, key: str) -> str:
        return MODEL_TEXTS[key][self.ui_language_code]["note"]

    def _ocr_language_label(self, key: str) -> str:
        return self._t(f"ocr_lang_{key}")

    def _ui_language_label(self, key: str) -> str:
        return self._t(f"ui_lang_{key}")

    def _current_model_label(self) -> str:
        return self._model_label(self.model_key_var.get().strip() or "ppstructurev3")

    def _refresh_runtime_text(self) -> None:
        device_name = self.device_name
        if device_name == "CPU or unavailable":
            device_name = self._t("runtime_unknown_gpu")
        self.runtime_var.set(
            self._t(
                "runtime",
                app_version=APP_RELEASE_VERSION,
                paddleocr_version=installed_paddleocr_version(),
                paddle_version=paddle.__version__,
                device_name=device_name,
            )
        )

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(main)
        top.pack(fill=tk.X)

        title_block = ttk.Frame(top)
        title_block.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.title_label = ttk.Label(title_block, font=("Segoe UI", 16, "bold"))
        self.title_label.pack(anchor=tk.W)

        self.subtitle_label = ttk.Label(title_block)
        self.subtitle_label.pack(anchor=tk.W, pady=(4, 6))

        language_block = ttk.Frame(top)
        language_block.pack(side=tk.RIGHT, anchor=tk.NE)

        self.ui_language_title_label = ttk.Label(language_block)
        self.ui_language_title_label.pack(anchor=tk.E)

        self.ui_language_box = ttk.Combobox(
            language_block,
            textvariable=self.ui_language_var,
            state="readonly",
            width=16,
        )
        self.ui_language_box.pack(anchor=tk.E, pady=(4, 0))
        self.ui_language_box.bind("<<ComboboxSelected>>", self._on_ui_language_selected)

        self.settings_btn = ttk.Button(language_block, command=self.open_settings)
        self.settings_btn.pack(anchor=tk.E, pady=(8, 0))

        ttk.Label(main, textvariable=self.runtime_var).pack(anchor=tk.W, pady=(6, 0))
        ttk.Label(main, textvariable=self.update_var).pack(anchor=tk.W, pady=(2, 14))

        self.file_frame = ttk.LabelFrame(main, padding=12)
        self.file_frame.pack(fill=tk.X)

        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_var)
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.browse_btn = ttk.Button(self.file_frame, command=self.pick_file)
        self.browse_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.options_frame = ttk.LabelFrame(main, padding=12)
        self.options_frame.pack(fill=tk.X, pady=(12, 0))

        self.model_label = ttk.Label(self.options_frame)
        self.model_label.grid(row=0, column=0, sticky="w")

        self.model_box = ttk.Combobox(
            self.options_frame,
            textvariable=self.model_label_var,
            state="readonly",
            width=46,
        )
        self.model_box.grid(row=0, column=1, sticky="w", padx=(8, 20))
        self.model_box.bind("<<ComboboxSelected>>", self._sync_model_key)

        self.doc_language_label = ttk.Label(self.options_frame)
        self.doc_language_label.grid(row=0, column=2, sticky="w")

        self.doc_language_box = ttk.Combobox(
            self.options_frame,
            textvariable=self.lang_label_var,
            state="readonly",
            width=12,
        )
        self.doc_language_box.grid(row=0, column=3, sticky="w", padx=(8, 0))
        self.doc_language_box.bind("<<ComboboxSelected>>", self._sync_doc_language)

        self.model_note_label = ttk.Label(self.options_frame, textvariable=self.model_note_var)
        self.model_note_label.grid(row=1, column=0, columnspan=4, sticky="w", pady=(10, 0))

        self.veo_note_label = ttk.Label(self.options_frame)
        self.veo_note_label.grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))

        actions = ttk.Frame(main)
        actions.pack(fill=tk.X, pady=(12, 0))

        self.start_btn = ttk.Button(actions, command=self.start_job)
        self.start_btn.pack(side=tk.LEFT)

        self.check_update_btn = ttk.Button(actions, command=self._start_update_check)
        self.check_update_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.open_btn = ttk.Button(
            actions,
            command=self.open_output_dir,
            state=tk.DISABLED,
        )
        self.open_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.open_md_btn = ttk.Button(
            actions,
            command=self.open_markdown,
            state=tk.DISABLED,
        )
        self.open_md_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.open_log_btn = ttk.Button(actions, command=self.open_log)
        self.open_log_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.progress = ttk.Progressbar(actions, mode="indeterminate", length=220)
        self.progress.pack(side=tk.RIGHT)
        self.progress.pack_forget()

        status_frame = ttk.Frame(main)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(status_frame, textvariable=self.status_var).pack(anchor=tk.W)
        ttk.Label(status_frame, textvariable=self.output_var).pack(anchor=tk.W, pady=(4, 0))
        ttk.Label(status_frame, textvariable=self.file_hint_var).pack(anchor=tk.W, pady=(4, 0))

        self.result_frame = ttk.LabelFrame(main, padding=12)
        self.result_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        self.result_box = scrolledtext.ScrolledText(
            self.result_frame,
            wrap=tk.WORD,
            font=("Consolas", 11),
            height=16,
        )
        self.result_box.pack(fill=tk.BOTH, expand=True)

    def _apply_language(self, refresh_comboboxes: bool) -> None:
        self.root.title(self._t("window_title"))
        self.title_label.config(text=self._t("app_title"))
        self.subtitle_label.config(text=self._t("app_subtitle"))
        self.ui_language_title_label.config(text=self._t("ui_language"))
        self.file_frame.config(text=self._t("section_input"))
        self.browse_btn.config(text=self._t("button_browse"))
        self.options_frame.config(text=self._t("section_options"))
        self.model_label.config(text=self._t("label_model"))
        self.doc_language_label.config(text=self._t("label_doc_language"))
        self.veo_note_label.config(text=self._t("note_veo"))
        self.start_btn.config(text=self._t("button_run"))
        self.check_update_btn.config(text=self._t("button_check_updates"))
        self.open_btn.config(text=self._t("button_open_output"))
        self.open_md_btn.config(text=self._t("button_open_markdown"))
        self.open_log_btn.config(text=self._t("button_open_log"))
        self.settings_btn.config(text=self._t("button_settings"))
        self.result_frame.config(text=self._t("section_preview"))

        if refresh_comboboxes:
            self._refresh_ui_language_combobox()
            self._refresh_model_combobox()
            self._refresh_doc_language_combobox()

        self.model_note_var.set(self._model_note(self.model_key_var.get()))
        self._refresh_runtime_text()
        self._refresh_static_status_text()
        self._refresh_settings_window()

    def _refresh_static_status_text(self) -> None:
        if self.current_state == "running":
            self.status_var.set(
                self._t("status_running", model_label=self._current_model_label())
            )
            self.output_var.set(self._t("output_running"))
            self.file_hint_var.set(self._t("files_generating"))
            return

        if self.current_state == "completed":
            self.status_var.set(self._t("status_completed"))
            if self.current_output_dir:
                self.output_var.set(
                    self._t("output_generated", path=self.current_output_dir)
                )
            else:
                self.output_var.set(self._t("output_not_generated"))

            files = []
            if self.current_text_file:
                files.append(self.current_text_file.name)
            if self.current_markdown_file:
                files.append(self.current_markdown_file.name)
            if self.current_json_file:
                files.append(self.current_json_file.name)
            if files:
                self.file_hint_var.set(self._t("files_generated", files=", ".join(files)))
            else:
                self.file_hint_var.set(self._t("files_open_output"))
            return

        if self.current_state == "failed":
            self.status_var.set(self._t("status_failed"))
            self.output_var.set(self._t("output_not_generated"))
            self.file_hint_var.set(self._t("files_not_generated"))
            return

        if not self.status_var.get():
            self.status_var.set(self._t("status_ready"))
        elif self.status_var.get() in {
            TEXTS["en_US"]["status_ready"],
            TEXTS["zh_CN"]["status_ready"],
        }:
            self.status_var.set(self._t("status_ready"))
        elif self.status_var.get() in {
            TEXTS["en_US"]["status_completed"],
            TEXTS["zh_CN"]["status_completed"],
        }:
            self.status_var.set(self._t("status_completed"))
        elif self.status_var.get() in {
            TEXTS["en_US"]["status_failed"],
            TEXTS["zh_CN"]["status_failed"],
        }:
            self.status_var.set(self._t("status_failed"))

        if not self.output_var.get() or self.output_var.get() in {
            TEXTS["en_US"]["output_not_generated"],
            TEXTS["zh_CN"]["output_not_generated"],
        }:
            self.output_var.set(self._t("output_not_generated"))

        if not self.file_hint_var.get() or self.file_hint_var.get() in {
            TEXTS["en_US"]["files_not_generated"],
            TEXTS["zh_CN"]["files_not_generated"],
        }:
            self.file_hint_var.set(self._t("files_not_generated"))

        if self.update_var.get() in {
            "",
            TEXTS["en_US"]["update_starting"],
            TEXTS["zh_CN"]["update_starting"],
        }:
            self.update_var.set(self._t("update_starting"))

    def _refresh_ui_language_combobox(self) -> None:
        values: list[str] = []
        self.ui_lang_label_to_code.clear()
        for code in SUPPORTED_UI_LANGUAGES:
            label = self._ui_language_label(code)
            values.append(label)
            self.ui_lang_label_to_code[label] = code
        self.ui_language_box.config(values=values)
        self.ui_language_var.set(self._ui_language_label(self.ui_language_code))

    def _refresh_model_combobox(self) -> None:
        selected_key = self.model_key_var.get().strip() or "ppstructurev3"
        values: list[str] = []
        self.model_label_to_key.clear()
        for key in MODEL_OPTIONS:
            label = self._model_label(key)
            values.append(label)
            self.model_label_to_key[label] = key
        self.model_box.config(values=values)
        self.model_label_var.set(self._model_label(selected_key))
        self.model_note_var.set(self._model_note(selected_key))

    def _refresh_doc_language_combobox(self) -> None:
        current_lang = self.lang_var.get().strip() or "en"
        values: list[str] = []
        self.ocr_lang_label_to_key.clear()
        for key in ("en", "ch"):
            label = self._ocr_language_label(key)
            values.append(label)
            self.ocr_lang_label_to_key[label] = key
        self.doc_language_box.config(values=values)
        self.lang_label_var.set(self._ocr_language_label(current_lang))

    def _on_ui_language_selected(self, event: tk.Event[Any] | None = None) -> None:
        label = event.widget.get() if event else self.ui_language_var.get()
        code = self.ui_lang_label_to_code.get(label, "en_US")
        if code == self.ui_language_code:
            return
        self.ui_language_code = code
        self.settings["ui_language"] = code
        save_settings(self.settings)
        self._apply_language(refresh_comboboxes=True)

    def _on_settings_ui_language_selected(
        self, event: tk.Event[Any] | None = None
    ) -> None:
        label = event.widget.get() if event else self.settings_language_var.get()
        code = self.ui_lang_label_to_code.get(label, "en_US")
        if code == self.ui_language_code:
            return
        self.ui_language_code = code
        self.settings["ui_language"] = code
        save_settings(self.settings)
        self._apply_language(refresh_comboboxes=True)

    def _sync_model_key(self, event: tk.Event[Any] | None = None) -> None:
        label = event.widget.get() if event else self.model_label_var.get()
        key = self.model_label_to_key.get(label, "ppstructurev3")
        self.model_key_var.set(key)
        self.model_label_var.set(self._model_label(key))
        self.model_note_var.set(self._model_note(key))

    def _sync_doc_language(self, event: tk.Event[Any] | None = None) -> None:
        label = event.widget.get() if event else self.lang_label_var.get()
        key = self.ocr_lang_label_to_key.get(label, "en")
        self.lang_var.set(key)
        self.lang_label_var.set(self._ocr_language_label(key))

    def _set_busy_state(self) -> None:
        is_busy = self.is_running_job or self.is_checking_updates
        if is_busy:
            if not self.progress.winfo_ismapped():
                self.progress.pack(side=tk.RIGHT)
            self.progress.start(12)
            return

        self.progress.stop()
        if self.progress.winfo_ismapped():
            self.progress.pack_forget()

    def _start_update_check(self) -> None:
        if self.is_checking_updates:
            return
        self.is_checking_updates = True
        self.check_update_btn.config(state=tk.DISABLED)
        self.update_var.set(self._t("update_contacting"))
        self._set_busy_state()
        threading.Thread(target=self._check_updates_worker, daemon=True).start()

    def _check_updates_worker(self) -> None:
        local_version = installed_paddleocr_version()
        latest_version, status = fetch_latest_version_from_official_repo()
        self.events.put(("update_info", (local_version, latest_version, status)))

    def _help_text(self) -> str:
        return self._t("help_text")

    def _about_text(self) -> str:
        device_name = self.device_name
        if device_name == "CPU or unavailable":
            device_name = self._t("runtime_unknown_gpu")
        return self._t(
            "about_text",
            app_name=APP_NAME,
            app_version=APP_RELEASE_VERSION,
            release_date=APP_RELEASE_DATE,
            publisher=APP_PUBLISHER,
            paddleocr_version=installed_paddleocr_version(),
            paddle_version=paddle.__version__,
            device_name=device_name,
            data_root=DATA_ROOT,
            repo_url=APP_REPOSITORY_URL,
        )

    def open_settings(self) -> None:
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.deiconify()
            self.settings_window.lift()
            self.settings_window.focus_force()
            return

        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.geometry("680x520")
        self.settings_window.minsize(620, 460)
        self.settings_window.transient(self.root)
        self.settings_window.protocol("WM_DELETE_WINDOW", self._close_settings_window)

        container = ttk.Frame(self.settings_window, padding=14)
        container.pack(fill=tk.BOTH, expand=True)

        self.settings_notebook = ttk.Notebook(container)
        self.settings_notebook.pack(fill=tk.BOTH, expand=True)

        self.settings_general_tab = ttk.Frame(self.settings_notebook, padding=14)
        self.settings_help_tab = ttk.Frame(self.settings_notebook, padding=14)
        self.settings_about_tab = ttk.Frame(self.settings_notebook, padding=14)
        self.settings_notebook.add(self.settings_general_tab)
        self.settings_notebook.add(self.settings_help_tab)
        self.settings_notebook.add(self.settings_about_tab)

        self.settings_language_label = ttk.Label(self.settings_general_tab)
        self.settings_language_label.grid(row=0, column=0, sticky="w")

        self.settings_language_box = ttk.Combobox(
            self.settings_general_tab,
            textvariable=self.settings_language_var,
            state="readonly",
            width=18,
        )
        self.settings_language_box.grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.settings_language_box.bind(
            "<<ComboboxSelected>>", self._on_settings_ui_language_selected
        )

        self.settings_help_box = scrolledtext.ScrolledText(
            self.settings_help_tab,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
        )
        self.settings_help_box.pack(fill=tk.BOTH, expand=True)

        self.settings_about_box = scrolledtext.ScrolledText(
            self.settings_about_tab,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
        )
        self.settings_about_box.pack(fill=tk.BOTH, expand=True)

        footer = ttk.Frame(container)
        footer.pack(fill=tk.X, pady=(10, 0))

        self.settings_close_btn = ttk.Button(footer, command=self._close_settings_window)
        self.settings_close_btn.pack(side=tk.RIGHT)

        self._refresh_settings_window()

    def _refresh_settings_window(self) -> None:
        if not self.settings_window or not self.settings_window.winfo_exists():
            return

        self.settings_window.title(self._t("settings_title"))

        if self.settings_notebook and self.settings_general_tab:
            self.settings_notebook.tab(
                self.settings_general_tab, text=self._t("settings_tab_general")
            )
        if self.settings_notebook and self.settings_help_tab:
            self.settings_notebook.tab(
                self.settings_help_tab, text=self._t("settings_tab_help")
            )
        if self.settings_notebook and self.settings_about_tab:
            self.settings_notebook.tab(
                self.settings_about_tab, text=self._t("settings_tab_about")
            )

        if self.settings_language_label:
            self.settings_language_label.config(text=self._t("settings_language"))
        if self.settings_language_box:
            values = [self._ui_language_label(code) for code in SUPPORTED_UI_LANGUAGES]
            self.settings_language_box.config(values=values)
        self.settings_language_var.set(self._ui_language_label(self.ui_language_code))

        if self.settings_help_box:
            self.settings_help_box.config(state=tk.NORMAL)
            self.settings_help_box.delete("1.0", tk.END)
            self.settings_help_box.insert(tk.END, self._help_text())
            self.settings_help_box.config(state=tk.DISABLED)

        if self.settings_about_box:
            self.settings_about_box.config(state=tk.NORMAL)
            self.settings_about_box.delete("1.0", tk.END)
            self.settings_about_box.insert(tk.END, self._about_text())
            self.settings_about_box.config(state=tk.DISABLED)

        if self.settings_close_btn:
            self.settings_close_btn.config(text=self._t("button_close"))

    def _close_settings_window(self) -> None:
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.destroy()
        self.settings_window = None
        self.settings_general_tab = None
        self.settings_help_tab = None
        self.settings_about_tab = None
        self.settings_notebook = None
        self.settings_language_label = None
        self.settings_language_box = None
        self.settings_help_box = None
        self.settings_about_box = None
        self.settings_close_btn = None

    def pick_file(self) -> None:
        path = filedialog.askopenfilename(
            title=self._t("dialog_choose_input"),
            filetypes=[
                (self._t("dialog_filetypes_primary"), "*.png;*.jpg;*.jpeg;*.bmp;*.webp;*.pdf"),
                (self._t("dialog_filetypes_all"), "*.*"),
            ],
        )
        if path:
            self.file_var.set(path)

    def open_output_dir(self) -> None:
        if self.current_output_dir:
            open_path(self.current_output_dir)

    def open_markdown(self) -> None:
        if self.current_markdown_file:
            open_path(self.current_markdown_file)

    def open_log(self) -> None:
        open_path(LOG_ROOT / "app.log")

    def start_job(self) -> None:
        input_path_text = self.file_var.get().strip()
        if not input_path_text:
            messagebox.showwarning(
                self._t("warn_missing_file_title"),
                self._t("warn_missing_file_body"),
            )
            return

        input_path = Path(input_path_text)
        if not input_path.exists():
            messagebox.showerror(
                self._t("error_missing_file_title"),
                self._t("error_missing_file_body", path=input_path),
            )
            return

        config = JobConfig(
            input_path=input_path,
            model_key=self.model_key_var.get().strip(),
            lang=self.lang_var.get().strip(),
        )
        model_label = self._current_model_label()

        self.current_output_dir = None
        self.current_markdown_file = None
        self.current_json_file = None
        self.current_text_file = None
        self.current_state = "running"
        self.is_running_job = True
        self.output_var.set(self._t("output_running"))
        self.file_hint_var.set(self._t("files_generating"))
        self.status_var.set(self._t("status_running", model_label=model_label))
        self.result_box.delete("1.0", tk.END)
        self.result_box.insert(tk.END, self._t("run_started", model_label=model_label))
        self.start_btn.config(state=tk.DISABLED)
        self.open_btn.config(state=tk.DISABLED)
        self.open_md_btn.config(state=tk.DISABLED)
        self._set_busy_state()

        threading.Thread(
            target=self._run_worker,
            args=(config, self.ui_language_code),
            daemon=True,
        ).start()

    def _run_worker(self, config: JobConfig, ui_language: str) -> None:
        try:
            result = self.backend.run_job(config, ui_language)
            self.events.put(("success", result))
        except Exception as exc:
            logging.exception("Run failed")
            self.events.put(("error", str(exc)))

    def _poll_events(self) -> None:
        while True:
            try:
                event_type, payload = self.events.get_nowait()
            except queue.Empty:
                break

            if event_type == "success":
                result: JobResult = payload
                self.current_output_dir = result.output_dir
                self.current_markdown_file = result.markdown_file
                self.current_json_file = result.json_file
                self.current_text_file = result.primary_text_file
                self.current_state = "completed"
                self.is_running_job = False

                self.status_var.set(self._t("status_completed"))
                self.output_var.set(self._t("output_generated", path=result.output_dir))

                files = []
                if result.primary_text_file:
                    files.append(result.primary_text_file.name)
                if result.markdown_file:
                    files.append(result.markdown_file.name)
                if result.json_file:
                    files.append(result.json_file.name)
                if files:
                    self.file_hint_var.set(self._t("files_generated", files=", ".join(files)))
                else:
                    self.file_hint_var.set(self._t("files_open_output"))

                self.result_box.delete("1.0", tk.END)
                self.result_box.insert(tk.END, result.preview or self._t("no_preview"))
                self.open_btn.config(state=tk.NORMAL)
                if result.markdown_file:
                    self.open_md_btn.config(state=tk.NORMAL)

                self.start_btn.config(state=tk.NORMAL)
                self._set_busy_state()

            elif event_type == "error":
                self.current_state = "failed"
                self.is_running_job = False
                self.status_var.set(self._t("status_failed"))
                self.output_var.set(self._t("output_not_generated"))
                self.file_hint_var.set(self._t("files_not_generated"))
                self.start_btn.config(state=tk.NORMAL)
                self._set_busy_state()
                messagebox.showerror(
                    self._t("run_failed_title"),
                    self._t("run_failed_body", error=payload),
                )

            elif event_type == "update_info":
                local_version, latest_version, status = payload
                self.is_checking_updates = False
                self.check_update_btn.config(state=tk.NORMAL)
                self._set_busy_state()
                if status == "network_error":
                    self.update_var.set(self._t("update_unreachable"))
                elif status == "parse_error":
                    self.update_var.set(self._t("update_unparsed"))
                elif Version(latest_version) > Version(local_version):
                    self.update_var.set(
                        self._t(
                            "update_newer",
                            latest_version=latest_version,
                            local_version=local_version,
                        )
                    )
                else:
                    self.update_var.set(
                        self._t("update_current", local_version=local_version)
                    )

        self.root.after(150, self._poll_events)

    def on_close(self) -> None:
        try:
            self.backend.close()
        finally:
            self._close_settings_window()
            self.root.destroy()


def main() -> None:
    ensure_data_root()
    configure_logging()
    ensure_output_root()
    root = tk.Tk()
    OCRApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
