#!/usr/bin/env python3
"""
Script to check Lambda function runtime versions from template.yml files.
Only shows enabled functions.
"""

import yaml
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    with open("functions.config.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    for f in config.get("functions", []):
        if f.get("enabled", True):  # Only process enabled functions
            name = f["name"]
            memory = f["memory"]
            template_path = Path(f["path"]) / "template.yml"
            
            runtime = f["runtime"]  # fallback to config
            if template_path.exists():
                try:
                    with open(template_path, 'r', encoding='utf-8') as tf:
                        template = yaml.safe_load(tf)
                    for resource in template.get("Resources", {}).values():
                        if resource.get("Type") == "AWS::Serverless::Function":
                            runtime = resource.get("Properties", {}).get("Runtime", runtime)
                            break
                except (FileNotFoundError, yaml.YAMLError, KeyError) as e:
                    logger.warning(f"Failed to load {template_path}: {e}")
                    # Fall back to config value
            
            logger.info(f"  {name} ({runtime}, {memory}MB)")

if __name__ == "__main__":
    main()