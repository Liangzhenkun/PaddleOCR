from __future__ import annotations

import json
import logging
import os
import queue
import re
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


APP_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = APP_DIR / "outputs"
LOG_ROOT = APP_DIR / "logs"
UPDATE_SOURCE_URL = (
    "https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/readme/README_cn.md"
)


@dataclass(frozen=True)
class ModelOption:
    key: str
    label: str
    family: str
    pipeline_version: str | None = None
    note: str = ""


MODEL_OPTIONS: dict[str, ModelOption] = {
    "ppocrv5": ModelOption(
        key="ppocrv5",
        label="PP-OCRv5 | Plain OCR | Fastest",
        family="ocr",
        note="Best for extracting plain text quickly.",
    ),
    "ppstructurev3": ModelOption(
        key="ppstructurev3",
        label="PP-StructureV3 | Structured Parsing | Recommended",
        family="structure",
        note="Best balance for PDFs, textbooks, tables, and Markdown export.",
    ),
    "vl16": ModelOption(
        key="vl16",
        label="PaddleOCR-VL-1.6 | Flagship Document Model | Heavy",
        family="vl",
        pipeline_version="v1.6",
        note="Latest flagship document parser. Larger first download and higher GPU usage.",
    ),
    "vl15": ModelOption(
        key="vl15",
        label="PaddleOCR-VL-1.5 | Previous VL Release",
        family="vl",
        pipeline_version="v1.5",
        note="Useful for comparing with VL-1.6.",
    ),
    "vl1": ModelOption(
        key="vl1",
        label="PaddleOCR-VL | First VL Release",
        family="vl",
        pipeline_version="v1",
        note="Original VL pipeline kept by the official project.",
    ),
}

MODEL_LABEL_TO_KEY = {option.label: option.key for option in MODEL_OPTIONS.values()}


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


def fetch_latest_version_from_official_repo(timeout: int = 12) -> str | None:
    try:
        response = requests.get(UPDATE_SOURCE_URL, timeout=timeout)
        response.raise_for_status()
    except Exception:
        logging.exception("Failed to check upstream PaddleOCR version")
        return None

    match = re.search(r"PaddleOCR\s+(\d+\.\d+\.\d+)\s+发布", response.text)
    if not match:
        match = re.search(r"PaddleOCR\s+(\d+\.\d+\.\d+)\s+Released", response.text)
    return match.group(1) if match else None


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

    def run_job(self, config: JobConfig) -> JobResult:
        option = MODEL_OPTIONS[config.model_key]
        output_dir = ensure_output_root() / f"{config.input_path.stem}_{timestamp()}"
        output_dir.mkdir(parents=True, exist_ok=True)
        logging.info(
            "Starting job model=%s lang=%s input=%s",
            option.key,
            config.lang,
            config.input_path,
        )

        if option.family == "ocr":
            return self._run_text_ocr(config, output_dir)
        if option.family == "structure":
            return self._run_structure(config, output_dir)
        return self._run_vl(config, output_dir, option)

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

    def _run_structure(self, config: JobConfig, output_dir: Path) -> JobResult:
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
        )

    def _run_vl(
        self, config: JobConfig, output_dir: Path, option: ModelOption
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
            preview = "[Structured parsing completed. Results were exported to Markdown/JSON.]"

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


class OCRApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.backend = OCRBackend()
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.current_output_dir: Path | None = None
        self.current_markdown_file: Path | None = None
        self.current_json_file: Path | None = None
        self.current_text_file: Path | None = None

        self.root.title("PaddleOCR Desktop Tool")
        self.root.geometry("1060x800")
        self.root.minsize(920, 680)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.file_var = tk.StringVar()
        self.model_key_var = tk.StringVar(value="ppstructurev3")
        self.model_label_var = tk.StringVar(value=MODEL_OPTIONS["ppstructurev3"].label)
        self.lang_var = tk.StringVar(value="en")
        self.status_var = tk.StringVar(value="Ready")
        self.output_var = tk.StringVar(value="Output folder: not generated")
        self.file_hint_var = tk.StringVar(value="Result files: not generated")
        self.model_note_var = tk.StringVar(value=MODEL_OPTIONS["ppstructurev3"].note)
        self.update_var = tk.StringVar(value="Update check: starting")
        self.runtime_var = tk.StringVar(
            value=(
                f"Local runtime: paddleocr {installed_paddleocr_version()} | "
                f"paddle {paddle.__version__} | GPU: {paddle.device.cuda.get_device_name(0)}"
            )
        )

        self._build_ui()
        self.root.after(150, self._poll_events)
        self._start_update_check()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            main,
            text="PaddleOCR Desktop Tool",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor=tk.W)

        ttk.Label(
            main,
            text=(
                "Local GPU document OCR and parsing tool with Markdown export, "
                "official model selection, and update checks."
            ),
        ).pack(anchor=tk.W, pady=(4, 6))

        ttk.Label(main, textvariable=self.runtime_var).pack(anchor=tk.W)
        ttk.Label(main, textvariable=self.update_var).pack(anchor=tk.W, pady=(2, 14))

        file_frame = ttk.LabelFrame(main, text="1. Choose Input File", padding=12)
        file_frame.pack(fill=tk.X)

        ttk.Entry(file_frame, textvariable=self.file_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(file_frame, text="Browse", command=self.pick_file).pack(
            side=tk.LEFT, padx=(10, 0)
        )

        options = ttk.LabelFrame(main, text="2. Parsing Options", padding=12)
        options.pack(fill=tk.X, pady=(12, 0))

        ttk.Label(options, text="Model").grid(row=0, column=0, sticky="w")
        model_box = ttk.Combobox(
            options,
            textvariable=self.model_label_var,
            values=list(MODEL_LABEL_TO_KEY.keys()),
            state="readonly",
            width=46,
        )
        model_box.grid(row=0, column=1, sticky="w", padx=(8, 20))
        model_box.bind("<<ComboboxSelected>>", self._sync_model_key)

        ttk.Label(options, text="Language").grid(row=0, column=2, sticky="w")
        ttk.Combobox(
            options,
            textvariable=self.lang_var,
            values=["ch", "en"],
            state="readonly",
            width=10,
        ).grid(row=0, column=3, sticky="w", padx=(8, 0))

        ttk.Label(options, textvariable=self.model_note_var).grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(10, 0)
        )
        ttk.Label(
            options,
            text=(
                "Note: Veo 3 is not an official PaddleOCR model, so it is not included. "
                "Official PaddleOCR-VL variants are included."
            ),
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))

        actions = ttk.Frame(main)
        actions.pack(fill=tk.X, pady=(12, 0))

        self.start_btn = ttk.Button(actions, text="Run", command=self.start_job)
        self.start_btn.pack(side=tk.LEFT)

        self.check_update_btn = ttk.Button(
            actions, text="Check Updates", command=self._start_update_check
        )
        self.check_update_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.open_btn = ttk.Button(
            actions,
            text="Open Output Folder",
            command=self.open_output_dir,
            state=tk.DISABLED,
        )
        self.open_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.open_md_btn = ttk.Button(
            actions,
            text="Open Markdown",
            command=self.open_markdown,
            state=tk.DISABLED,
        )
        self.open_md_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.open_log_btn = ttk.Button(
            actions,
            text="Open Log",
            command=self.open_log,
        )
        self.open_log_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.progress = ttk.Progressbar(actions, mode="indeterminate", length=220)
        self.progress.pack(side=tk.RIGHT)

        status_frame = ttk.Frame(main)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(status_frame, textvariable=self.status_var).pack(anchor=tk.W)
        ttk.Label(status_frame, textvariable=self.output_var).pack(anchor=tk.W, pady=(4, 0))
        ttk.Label(status_frame, textvariable=self.file_hint_var).pack(anchor=tk.W, pady=(4, 0))

        result_frame = ttk.LabelFrame(main, text="3. Preview", padding=12)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        self.result_box = scrolledtext.ScrolledText(
            result_frame,
            wrap=tk.WORD,
            font=("Consolas", 11),
        )
        self.result_box.pack(fill=tk.BOTH, expand=True)

    def _sync_model_key(self, event: tk.Event[Any] | None = None) -> None:
        label = event.widget.get() if event else self.model_label_var.get()
        key = MODEL_LABEL_TO_KEY.get(label, "ppstructurev3")
        self.model_key_var.set(key)
        self.model_note_var.set(MODEL_OPTIONS[key].note)

    def _start_update_check(self) -> None:
        self.update_var.set("Update check: contacting upstream PaddleOCR repo")
        threading.Thread(target=self._check_updates_worker, daemon=True).start()

    def _check_updates_worker(self) -> None:
        local_version = installed_paddleocr_version()
        latest_version = fetch_latest_version_from_official_repo()
        self.events.put(("update_info", (local_version, latest_version)))

    def pick_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose image or PDF",
            filetypes=[
                ("Images or PDF", "*.png;*.jpg;*.jpeg;*.bmp;*.webp;*.pdf"),
                ("All files", "*.*"),
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
            messagebox.showwarning("Missing file", "Please choose an image or PDF first.")
            return

        input_path = Path(input_path_text)
        if not input_path.exists():
            messagebox.showerror("File not found", f"Could not find:\n{input_path}")
            return

        config = JobConfig(
            input_path=input_path,
            model_key=self.model_key_var.get().strip(),
            lang=self.lang_var.get().strip(),
        )
        option = MODEL_OPTIONS[config.model_key]

        self.current_output_dir = None
        self.current_markdown_file = None
        self.current_json_file = None
        self.current_text_file = None
        self.output_var.set("Output folder: running")
        self.file_hint_var.set("Result files: generating")
        self.status_var.set(f"Running... Current model: {option.label}")
        self.result_box.delete("1.0", tk.END)
        self.result_box.insert(
            tk.END,
            (
                f"Job started: {option.label}\n"
                "The first run of a model may take longer because official weights may need to be downloaded.\n"
            ),
        )
        self.start_btn.config(state=tk.DISABLED)
        self.open_btn.config(state=tk.DISABLED)
        self.open_md_btn.config(state=tk.DISABLED)
        self.progress.start(12)

        threading.Thread(target=self._run_worker, args=(config,), daemon=True).start()

    def _run_worker(self, config: JobConfig) -> None:
        try:
            result = self.backend.run_job(config)
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

                self.status_var.set("Completed")
                self.output_var.set(f"Output folder: {result.output_dir}")

                files = []
                if result.primary_text_file:
                    files.append(result.primary_text_file.name)
                if result.markdown_file:
                    files.append(result.markdown_file.name)
                if result.json_file:
                    files.append(result.json_file.name)
                self.file_hint_var.set(
                    "Result files: " + (", ".join(files) if files else "open the output folder")
                )

                self.result_box.delete("1.0", tk.END)
                self.result_box.insert(tk.END, result.preview or "[No preview text]")
                self.open_btn.config(state=tk.NORMAL)
                if result.markdown_file:
                    self.open_md_btn.config(state=tk.NORMAL)

                self.progress.stop()
                self.start_btn.config(state=tk.NORMAL)

            elif event_type == "error":
                self.status_var.set("Failed")
                self.output_var.set("Output folder: not generated")
                self.file_hint_var.set("Result files: not generated")
                self.progress.stop()
                self.start_btn.config(state=tk.NORMAL)
                messagebox.showerror(
                    "Run failed",
                    payload + "\n\nSee logs/app.log for more details.",
                )

            elif event_type == "update_info":
                local_version, latest_version = payload
                if not latest_version:
                    self.update_var.set("Update check: could not reach the official PaddleOCR repo")
                elif Version(latest_version) > Version(local_version):
                    self.update_var.set(
                        f"Update check: newer release available ({latest_version}), local is {local_version}"
                    )
                else:
                    self.update_var.set(
                        f"Update check: local version is current ({local_version})"
                    )

        self.root.after(150, self._poll_events)

    def on_close(self) -> None:
        try:
            self.backend.close()
        finally:
            self.root.destroy()


def main() -> None:
    configure_logging()
    ensure_output_root()
    root = tk.Tk()
    OCRApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
