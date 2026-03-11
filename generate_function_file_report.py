#!/usr/bin/env python3
"""Generate an Excel report of file counts and line counts per configured Lambda function."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from openpyxl import Workbook


@dataclass
class FileRecord:
    function_name: str
    function_enabled: bool
    function_path: str
    src_path: str
    file_name: str
    relative_file_path: str
    absolute_file_path: str
    lines: int


EXCLUDED_DIRS = {".git", ".venv", "venv", "__pycache__", ".terraform", "htmlcov", ".build", ".packages"}
EXCLUDED_FILE_NAMES = {"requirements.txt"}


def load_config(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def find_source_under_base(base_path: Path, preferred_src_folder: str) -> Path | None:
    if not base_path.exists() or not base_path.is_dir():
        return None

    preferred = base_path / preferred_src_folder
    if preferred.exists() and preferred.is_dir():
        return preferred

    default_src = base_path / "src"
    if default_src.exists() and default_src.is_dir():
        return default_src

    lambda_at_root = base_path / "lambda_function.py"
    if lambda_at_root.exists() and lambda_at_root.is_file():
        return base_path

    candidates: list[Path] = []
    for child in sorted(base_path.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir() or child.name in EXCLUDED_DIRS:
            continue
        has_lambda = (child / "lambda_function.py").exists()
        has_requirements = (child / "requirements.txt").exists()
        if has_lambda or has_requirements:
            candidates.append(child)

    return candidates[0] if candidates else None


def resolve_src_path(workspace_root: Path, function_config: dict[str, Any]) -> tuple[Path, str]:
    function_name = function_config.get("name", "")
    function_path = Path(function_config["path"])
    preferred_src_folder = function_config.get("src_folder", "src")

    configured_function_dir = workspace_root / function_path
    configured_src = configured_function_dir / preferred_src_folder
    if configured_src.exists() and configured_src.is_dir():
        return configured_src, "configured_path"

    configured_dir_detected = find_source_under_base(configured_function_dir, preferred_src_folder)
    if configured_dir_detected:
        return configured_dir_detected, "configured_dir_auto"

    if function_name:
        for candidate in workspace_root.rglob(function_name):
            if not candidate.is_dir():
                continue
            if any(part in EXCLUDED_DIRS for part in candidate.parts):
                continue
            detected = find_source_under_base(candidate, preferred_src_folder)
            if detected:
                return detected, "workspace_search"

    return configured_src, "missing"


def count_file_lines(file_path: Path) -> int:
    try:
        with file_path.open("r", encoding="utf-8") as file:
            return sum(1 for _ in file)
    except UnicodeDecodeError:
        with file_path.open("r", encoding="utf-8", errors="ignore") as file:
            return sum(1 for _ in file)


def collect_records(
    workspace_root: Path,
    functions: list[dict[str, Any]],
    include_disabled: bool,
) -> tuple[list[dict[str, Any]], list[FileRecord]]:
    summary_rows: list[dict[str, Any]] = []
    file_rows: list[FileRecord] = []

    for function in functions:
        enabled = function.get("enabled", True)
        if not include_disabled and not enabled:
            continue

        name = function.get("name", "unknown")
        function_path = function.get("path", "")
        src_path, resolution = resolve_src_path(workspace_root, function)

        total_files = 0
        total_lines = 0
        file_names: list[str] = []
        missing_src = not src_path.exists()

        if not missing_src:
            for file_path in sorted(p for p in src_path.rglob("*") if p.is_file()):
                if file_path.name.lower() in EXCLUDED_FILE_NAMES:
                    continue
                lines = count_file_lines(file_path)
                total_files += 1
                total_lines += lines
                file_names.append(file_path.name)
                file_rows.append(
                    FileRecord(
                        function_name=name,
                        function_enabled=enabled,
                        function_path=function_path,
                        src_path=str(src_path),
                        file_name=file_path.name,
                        relative_file_path=str(file_path.relative_to(src_path)),
                        absolute_file_path=str(file_path),
                        lines=lines,
                    )
                )

        summary_rows.append(
            {
                "function_name": name,
                "enabled": enabled,
                "function_path": function_path,
                "src_path": str(src_path),
                "src_resolution": resolution,
                "total_files": total_files,
                "total_lines": total_lines,
                "file_names": ", ".join(sorted(set(file_names))),
                "src_exists": not missing_src,
            }
        )

    return summary_rows, file_rows


def write_excel_report(output_path: Path, summary_rows: list[dict[str, Any]], file_rows: list[FileRecord]) -> None:
    workbook = Workbook()

    summary_sheet = workbook.active
    summary_sheet.title = "Summary"
    summary_sheet.append(
        [
            "Function Name",
            "Enabled",
            "Function Path",
            "Source Path",
            "Source Resolution",
            "Source Exists",
            "Total Files",
            "Total Lines",
            "File Names",
        ]
    )
    for row in summary_rows:
        summary_sheet.append(
            [
                row["function_name"],
                row["enabled"],
                row["function_path"],
                row["src_path"],
                row["src_resolution"],
                row["src_exists"],
                row["total_files"],
                row["total_lines"],
                row["file_names"],
            ]
        )

    files_sheet = workbook.create_sheet("Files")
    files_sheet.append(
        [
            "Function Name",
            "Enabled",
            "Function Path",
            "Source Path",
            "File Name",
            "Relative File Path",
            "Absolute File Path",
            "Line Count",
        ]
    )
    for row in file_rows:
        files_sheet.append(
            [
                row.function_name,
                row.function_enabled,
                row.function_path,
                row.src_path,
                row.file_name,
                row.relative_file_path,
                row.absolute_file_path,
                row.lines,
            ]
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Count files and lines for Lambda source folders in functions.config.yaml and export to Excel"
    )
    parser.add_argument(
        "--config",
        default="functions.config.yaml",
        help="Path to configuration file (default: functions.config.yaml)",
    )
    parser.add_argument(
        "--output",
        default="function_file_report.xlsx",
        help="Path to output Excel report (default: function_file_report.xlsx)",
    )
    parser.add_argument(
        "--include-disabled",
        action="store_true",
        help="Include disabled functions from config",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workspace_root = Path.cwd()
    config_path = workspace_root / args.config
    output_path = workspace_root / args.output

    config = load_config(config_path)
    functions = config.get("functions", [])

    summary_rows, file_rows = collect_records(
        workspace_root=workspace_root,
        functions=functions,
        include_disabled=args.include_disabled,
    )
    write_excel_report(output_path, summary_rows, file_rows)

    print(f"Report generated: {output_path}")
    print(f"Functions analyzed: {len(summary_rows)}")
    print(f"Files counted: {len(file_rows)}")


if __name__ == "__main__":
    main()
