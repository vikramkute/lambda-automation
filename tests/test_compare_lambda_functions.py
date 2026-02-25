"""Test suite for compare_lambda_functions.py"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
import compare_lambda_functions as clf


class TestReadFile:
    """Test read_file function"""

    def test_read_existing_file(self, tmp_path):
        """Test reading an existing file"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2\n")
        lines = clf.read_file(test_file)
        assert lines == ["line1\n", "line2\n"]

    def test_read_nonexistent_file(self):
        """Test reading non-existent file returns None"""
        result = clf.read_file("/nonexistent/file.txt")
        assert result is None

    def test_read_file_with_unicode(self, tmp_path):
        """Test reading file with unicode content"""
        test_file = tmp_path / "unicode.txt"
        test_file.write_text("Hello 世界\n", encoding='utf-8')
        lines = clf.read_file(test_file)
        assert lines == ["Hello 世界\n"]


class TestCountTotalOrDiffLines:
    """Test count_total_or_diff_lines function"""

    def test_both_files_missing(self):
        """Test when both files are missing"""
        result = clf.count_total_or_diff_lines(None, None)
        assert result == 0

    def test_first_file_missing(self):
        """Test when first file is missing"""
        lines2 = ["line1\n", "line2\n"]
        result = clf.count_total_or_diff_lines(None, lines2)
        assert result == 2

    def test_second_file_missing(self):
        """Test when second file is missing"""
        lines1 = ["line1\n", "line2\n", "line3\n"]
        result = clf.count_total_or_diff_lines(lines1, None)
        assert result == 3

    def test_identical_files(self):
        """Test identical files return 0 diff"""
        lines = ["line1\n", "line2\n"]
        result = clf.count_total_or_diff_lines(lines, lines)
        assert result == 0

    def test_different_files(self):
        """Test different files return correct diff count"""
        lines1 = ["line1\n", "line2\n"]
        lines2 = ["line1\n", "line3\n"]
        result = clf.count_total_or_diff_lines(lines1, lines2)
        assert result > 0


class TestPrintSideBySide:
    """Test print_side_by_side function"""

    def test_identical_content(self, capsys):
        """Test side-by-side comparison of identical content"""
        lines = ["line1\n", "line2\n"]
        clf.print_side_by_side(lines, lines, "func1", "func2")
        captured = capsys.readouterr()
        assert "func1" in captured.out
        assert "func2" in captured.out

    def test_different_content(self, capsys):
        """Test side-by-side comparison of different content"""
        lines1 = ["line1\n"]
        lines2 = ["line2\n"]
        clf.print_side_by_side(lines1, lines2, "func1", "func2")
        captured = capsys.readouterr()
        assert "func1" in captured.out

    def test_with_file_output(self, tmp_path):
        """Test writing comparison to file"""
        output_file = tmp_path / "output.txt"
        lines1 = ["line1\n"]
        lines2 = ["line2\n"]
        with open(output_file, 'w', encoding='utf-8') as f:
            clf.print_side_by_side(lines1, lines2, "func1", "func2", file=f)
        assert output_file.exists()
        content = output_file.read_text(encoding='utf-8')
        assert "func1" in content


class TestCompareFunctions:
    """Test compare_functions function"""

    def test_compare_nonexistent_directories(self):
        """Test comparing non-existent directories raises error"""
        with pytest.raises(ValueError, match="does not exist"):
            clf.compare_functions("/nonexistent1", "/nonexistent2")

    def test_compare_valid_directories(self, tmp_path):
        """Test comparing valid directories"""
        func1 = tmp_path / "func1"
        func2 = tmp_path / "func2"
        func1.mkdir()
        func2.mkdir()
        (func1 / "test.py").write_text("print('hello')")
        (func2 / "test.py").write_text("print('world')")
        
        output_dir = tmp_path / "comparisons"
        clf.compare_functions(str(func1), str(func2), str(output_dir), generate_pdf=False)
        assert output_dir.exists()

    def test_compare_with_identical_functions(self, tmp_path):
        """Test comparing identical functions"""
        func1 = tmp_path / "func1"
        func2 = tmp_path / "func2"
        func1.mkdir()
        func2.mkdir()
        (func1 / "test.py").write_text("print('same')")
        (func2 / "test.py").write_text("print('same')")
        
        output_dir = tmp_path / "comparisons"
        clf.compare_functions(str(func1), str(func2), str(output_dir), generate_pdf=False)
        assert output_dir.exists()

    def test_compare_with_missing_files(self, tmp_path):
        """Test comparing when files are missing in one function"""
        func1 = tmp_path / "func1"
        func2 = tmp_path / "func2"
        func1.mkdir()
        func2.mkdir()
        (func1 / "test.py").write_text("print('hello')")
        
        output_dir = tmp_path / "comparisons"
        clf.compare_functions(str(func1), str(func2), str(output_dir), generate_pdf=False)
        assert output_dir.exists()


class TestCompareFromConfig:
    """Test compare_from_config function"""

    def test_with_missing_config(self, capsys):
        """Test with non-existent config file"""
        clf.compare_from_config("/nonexistent/config.yaml", generate_pdf=False)
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_with_invalid_yaml(self, tmp_path, capsys):
        """Test with invalid YAML config"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content:")
        clf.compare_from_config(str(config_file), generate_pdf=False)
        captured = capsys.readouterr()
        assert "Invalid YAML" in captured.out

    def test_with_empty_comparisons(self, tmp_path, capsys):
        """Test with config containing no comparisons"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("comparisons: []")
        clf.compare_from_config(str(config_file), generate_pdf=False)
        captured = capsys.readouterr()
        assert "No comparisons found" in captured.out

    def test_with_valid_comparisons(self, tmp_path, capsys):
        """Test with valid comparison config"""
        func1 = tmp_path / "func1"
        func2 = tmp_path / "func2"
        func1.mkdir()
        func2.mkdir()
        (func1 / "test.py").write_text("print('hello')")
        (func2 / "test.py").write_text("print('world')")
        
        config_file = tmp_path / "config.yaml"
        config = {
            'comparisons': [
                {'function1': str(func1), 'function2': str(func2)}
            ]
        }
        config_file.write_text(yaml.dump(config))
        
        clf.compare_from_config(str(config_file), str(tmp_path / "output"), generate_pdf=False)
        captured = capsys.readouterr()
        assert "Completed" in captured.out

    def test_with_missing_function_names(self, tmp_path, capsys):
        """Test with config missing function names"""
        config_file = tmp_path / "config.yaml"
        config = {'comparisons': [{'function1': 'func1'}]}
        config_file.write_text(yaml.dump(config))
        
        clf.compare_from_config(str(config_file), generate_pdf=False)
        captured = capsys.readouterr()
        assert "Skipping" in captured.out


class TestValidateFunctionDirs:
    """Test _validate_function_dirs function"""

    def test_with_valid_directories(self, tmp_path):
        """Test validation with valid directories"""
        func1 = tmp_path / "func1"
        func2 = tmp_path / "func2"
        func1.mkdir()
        func2.mkdir()
        
        path1, path2 = clf._validate_function_dirs(str(func1), str(func2))
        assert path1.exists()
        assert path2.exists()

    def test_with_nonexistent_directory(self, tmp_path):
        """Test validation with non-existent directory"""
        func1 = tmp_path / "func1"
        func1.mkdir()
        
        with pytest.raises(ValueError, match="does not exist"):
            clf._validate_function_dirs(str(func1), "/nonexistent")


class TestCollectFunctionFiles:
    """Test _collect_function_files function"""

    def test_collect_from_empty_directories(self, tmp_path):
        """Test collecting files from empty directories"""
        func1 = tmp_path / "func1"
        func2 = tmp_path / "func2"
        func1.mkdir()
        func2.mkdir()
        
        files = clf._collect_function_files(func1, func2)
        assert files == []

    def test_collect_excludes_build_dirs(self, tmp_path):
        """Test that build directories are excluded"""
        func1 = tmp_path / "func1"
        func1.mkdir()
        (func1 / ".aws-sam").mkdir()
        (func1 / ".aws-sam" / "test.py").write_text("test")
        (func1 / "main.py").write_text("main")
        
        files = clf._collect_function_files(func1, func1)
        assert "main.py" in files
        assert ".aws-sam/test.py" not in files

    def test_collect_from_multiple_directories(self, tmp_path):
        """Test collecting files from multiple directories"""
        func1 = tmp_path / "func1"
        func2 = tmp_path / "func2"
        func1.mkdir()
        func2.mkdir()
        (func1 / "file1.py").write_text("test1")
        (func2 / "file2.py").write_text("test2")
        
        files = clf._collect_function_files(func1, func2)
        assert len(files) == 2


class TestGeneratePdfReport:
    """Test generate_pdf_report function"""

    def test_generate_pdf_basic(self, tmp_path):
        """Test basic PDF generation"""
        output_file = tmp_path / "report.txt"
        file_comparisons = [
            ("test.py", "Files are identical", [])
        ]
        
        try:
            pdf_file = clf.generate_pdf_report("func1", "func2", file_comparisons, 0, output_file)
            assert pdf_file.exists()
            assert pdf_file.suffix == '.pdf'
        except ImportError:
            pytest.skip("reportlab not available")

    def test_generate_pdf_with_differences(self, tmp_path):
        """Test PDF generation with differences"""
        output_file = tmp_path / "report.txt"
        file_comparisons = [
            ("test.py", "Lines not matching: 5", [('replace', 'line1', 'line2')])
        ]
        
        try:
            pdf_file = clf.generate_pdf_report("func1", "func2", file_comparisons, 5, output_file)
            assert pdf_file.exists()
        except ImportError:
            pytest.skip("reportlab not available")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
