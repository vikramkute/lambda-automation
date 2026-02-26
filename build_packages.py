#!/usr/bin/env python3
"""Helper script to build ZIP packages from Lambda functions with dynamic src_folder configuration."""

import os
import yaml
import zipfile
from pathlib import Path

def main():
    # Load configuration
    config = yaml.safe_load(open('functions.config.yaml'))
    
    # Create packages directory
    os.makedirs('.packages', exist_ok=True)
    
    # Process each enabled function
    for func in config.get('functions', []):
        if not func.get('enabled', True):
            continue
        
        name = func['name']
        path = func['path']
        src_folder = func.get('src_folder', 'src')
        src_path = os.path.join(path, src_folder)
        
        # Check if source path exists
        if not os.path.exists(src_path):
            print(f"    [SKIP] Source path not found: {src_path}")
            continue
        
        print(f"  Creating ZIP for {name}...")
        
        # Create ZIP file
        zip_path = os.path.join('.packages', f'{name}.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(src_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, src_path)
                    zipf.write(file_path, arcname)
        
        print(f"    [OK] Created {zip_path}")

if __name__ == '__main__':
    main()
