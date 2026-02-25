"""Test suite for check_runtime_versions.py"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
import check_runtime_versions


class TestCheckRuntimeVersions:
    """Test check_runtime_versions.py functionality"""

    def test_main_with_enabled_functions(self, tmp_path, caplog):
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'enabled': True},
                {'name': 'func2', 'path': './func2', 'runtime': 'python3.12', 'memory': 256, 'enabled': False}
            ]
        }
        config_file = tmp_path / "functions.config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with caplog.at_level('INFO'):
            with patch('check_runtime_versions.open', side_effect=lambda f, *args, **kwargs: open(config_file, *args, **kwargs)):
                check_runtime_versions.main()
                assert 'func1' in caplog.text
                assert 'func2' not in caplog.text

    def test_main_with_missing_template(self, tmp_path, caplog):
        config = {'functions': [{'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'enabled': True}]}
        config_file = tmp_path / "functions.config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with caplog.at_level('INFO'):
            with patch('check_runtime_versions.open', side_effect=lambda f, *args, **kwargs: open(config_file, *args, **kwargs)):
                check_runtime_versions.main()
                assert 'func1' in caplog.text

    def test_main_displays_memory_info(self, tmp_path, caplog):
        config = {'functions': [{'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'enabled': True}]}
        config_file = tmp_path / "functions.config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with caplog.at_level('INFO'):
            with patch('check_runtime_versions.open', side_effect=lambda f, *args, **kwargs: open(config_file, *args, **kwargs)):
                check_runtime_versions.main()
                assert '128MB' in caplog.text


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
