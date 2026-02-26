#!/usr/bin/env python3
"""
Download multiple AWS Lambda functions by name.
"""

import argparse
import os
from pathlib import Path
import sys
import urllib.request
import zipfile

import boto3
import yaml


def load_function_names(config_path: Path) -> list[str]:
    if not config_path.exists():
        return []

    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    names = []
    for func in config.get("functions", []):
        if func.get("enabled", True):
            name = func.get("name")
            if name:
                names.append(name)
    return names


def download_zip(url: str, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, target_path.open("wb") as handle:
        handle.write(response.read())


def extract_zip(zip_path: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(dest_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download multiple Lambda functions."
    )
    parser.add_argument(
        "--functions",
        help="Comma-separated Lambda function names.",
    )
    parser.add_argument(
        "--config",
        default="functions.config.yaml",
        help="Config file to load enabled function names from.",
    )
    parser.add_argument(
        "--out",
        default="downloaded",
        help="Output directory for downloaded functions.",
    )
    parser.add_argument(
        "--region",
        help="AWS region (defaults to environment or AWS config).",
    )
    parser.add_argument(
        "--no-extract",
        action="store_true",
        help="Keep ZIPs only; do not extract source files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    config_path = Path(args.config)
    function_names: list[str] = []
    if args.functions:
        function_names = [name.strip() for name in args.functions.split(",") if name.strip()]
    else:
        function_names = load_function_names(config_path)

    if not function_names:
        print("No function names provided or found in config.")
        return 1

    session = boto3.Session(region_name=args.region) if args.region else boto3.Session()
    lambda_client = session.client("lambda")

    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)

    for name in function_names:
        try:
            response = lambda_client.get_function(FunctionName=name)
        except Exception as exc:
            print(f"[ERROR] Failed to fetch {name}: {exc}")
            continue

        code = response.get("Code", {})
        code_url = code.get("Location")

        if not code_url:
            print(f"[ERROR] No download URL for {name}")
            continue

        function_dir = output_dir / name
        function_dir.mkdir(parents=True, exist_ok=True)

        zip_path = function_dir / f"{name}.zip"
        print(f"[INFO] Downloading {name} -> {zip_path}")
        download_zip(code_url, zip_path)

        if not args.no_extract:
            src_dir = function_dir / "src"
            extract_zip(zip_path, src_dir)
            zip_path.unlink()
            print(f"[OK] Extracted to {src_dir} and ZIP deleted")
        else:
            print(f"[OK] Downloaded ZIP only: {zip_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
