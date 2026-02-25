"""Test suite for compare_lambda_functions_ast.py"""

import pytest
import tempfile
import yaml
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from compare_lambda_functions_ast import (
    ASTComparator, FunctionConfig, FunctionDependencies, 
    TestResult, FunctionMetrics
)


class TestFunctionConfig:
    """Test FunctionConfig dataclass."""
    
    def test_config_creation(self):
        """Test creating a function configuration."""
        config = FunctionConfig(
            name="test_func",
            runtime="python3.12",
            memory=128,
            timeout=30,
            handler="lambda_function.lambda_handler",
            description="Test function",
            environment_vars={},
            layers=[],
            tracing_enabled=False,
            ephemeral_storage=512,
            architecture="x86_64"
        )
        
        assert config.name == "test_func"
        assert config.runtime == "python3.12"
        assert config.memory == 128


class TestFunctionDependencies:
    """Test FunctionDependencies dataclass."""
    
    def test_dependencies_creation(self):
        """Test creating dependencies."""
        deps = FunctionDependencies(
            python_version="3.12",
            total_packages=3,
            packages=["requests", "boto3", "json"],
            missing_packages=[]
        )
        
        assert deps.total_packages == 3
        assert "requests" in deps.packages


class TestASTComparator:
    """Test ASTComparator class."""
    
    @pytest.fixture
    def temp_functions(self):
        """Create temporary function directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create function 1
            func1 = tmpdir / "func1"
            func1.mkdir()
            (func1 / "src").mkdir()
            (func1 / "src" / "lambda_function.py").write_text("def lambda_handler(event, context):\n    return 'Hello'")
            (func1 / "src" / "requirements.txt").write_text("requests==2.28.0\n")
            (func1 / "template.yml").write_text("""
Resources:
  LambdaFunction:
    Type: AWS::Lambda::Function
    Properties:
      Runtime: python3.12
      MemorySize: 128
      Timeout: 30
      Handler: lambda_function.lambda_handler
""")
            
            # Create function 2
            func2 = tmpdir / "func2"
            func2.mkdir()
            (func2 / "src").mkdir()
            (func2 / "src" / "lambda_function.py").write_text("def lambda_handler(event, context):\n    return 'Hello World'")
            (func2 / "src" / "requirements.txt").write_text("requests==2.28.0\nboto3==1.26.0\n")
            (func2 / "template.yml").write_text("""
Resources:
  LambdaFunction:
    Type: AWS::Lambda::Function
    Properties:
      Runtime: python3.14
      MemorySize: 256
      Timeout: 60
      Handler: lambda_function.lambda_handler
""")
            
            yield func1, func2
    
    def test_comparator_initialization(self, temp_functions):
        """Test initializing comparator."""
        func1, func2 = temp_functions
        comparator = ASTComparator(str(func1), str(func2))
        
        assert comparator.func1_path == func1
        assert comparator.func2_path == func2
    
    def test_comparator_invalid_paths(self):
        """Test comparator with invalid paths."""
        with pytest.raises(ValueError):
            ASTComparator("/nonexistent/path1", "/nonexistent/path2")
    
    def test_extract_function_config(self, temp_functions):
        """Test extracting function configuration."""
        func1, func2 = temp_functions
        comparator = ASTComparator(str(func1), str(func2))
        
        config1 = comparator._extract_function_config("func1", func1)
        config2 = comparator._extract_function_config("func2", func2)
        
        assert config1.runtime == "python3.12"
        assert config2.runtime == "python3.14"
        assert config1.memory == 128
        assert config2.memory == 256
    
    def test_get_requirements(self, temp_functions):
        """Test extracting requirements."""
        func1, func2 = temp_functions
        comparator = ASTComparator(str(func1), str(func2))
        
        deps1 = comparator._get_requirements(func1)
        deps2 = comparator._get_requirements(func2)
        
        assert deps1.total_packages == 1
        assert deps2.total_packages == 2
        assert "boto3==1.26.0" in deps2.packages
    
    def test_compare_configs(self, temp_functions):
        """Test configuration comparison."""
        func1, func2 = temp_functions
        comparator = ASTComparator(str(func1), str(func2))
        
        config1 = comparator._extract_function_config("func1", func1)
        config2 = comparator._extract_function_config("func2", func2)
        
        diffs = comparator._compare_configs(config1, config2)
        
        # Should have differences in runtime, memory, timeout
        assert len(diffs) > 0
        assert any(d['field'] == 'runtime' for d in diffs)
        assert any(d['significance'] == 'CRITICAL' for d in diffs)
    
    def test_compare_dependencies(self, temp_functions):
        """Test dependency comparison."""
        func1, func2 = temp_functions
        comparator = ASTComparator(str(func1), str(func2))
        
        deps1 = comparator._get_requirements(func1)
        deps2 = comparator._get_requirements(func2)
        
        diff = comparator._compare_dependencies(deps1, deps2)
        
        assert diff['total_difference'] == 1
        assert "boto3==1.26.0" in diff['only_in_function2']
    
    def test_calculate_metrics(self, temp_functions):
        """Test metrics calculation."""
        func1, func2 = temp_functions
        comparator = ASTComparator(str(func1), str(func2))
        
        config1 = comparator._extract_function_config("func1", func1)
        deps1 = comparator._get_requirements(func1)
        
        metrics1 = comparator._calculate_metrics(config1, deps1)
        
        assert metrics1.memory_efficiency > 0
        assert metrics1.estimated_coldstart_time > 0
        assert metrics1.code_complexity_score >= 0
    
    def test_compare_metrics(self, temp_functions):
        """Test metrics comparison."""
        func1, func2 = temp_functions
        comparator = ASTComparator(str(func1), str(func2))
        
        config1 = comparator._extract_function_config("func1", func1)
        config2 = comparator._extract_function_config("func2", func2)
        deps1 = comparator._get_requirements(func1)
        deps2 = comparator._get_requirements(func2)
        
        metrics1 = comparator._calculate_metrics(config1, deps1)
        metrics2 = comparator._calculate_metrics(config2, deps2)
        
        comparison = comparator._compare_metrics(metrics1, metrics2)
        
        assert 'coldstart_diff_ms' in comparison
        assert 'coldstart_faster' in comparison
        assert comparison['coldstart_faster'] in ['function1', 'function2']
    
    def test_get_significance(self, temp_functions):
        """Test significance level determination."""
        func1, func2 = temp_functions
        comparator = ASTComparator(str(func1), str(func2))
        
        assert comparator._get_significance('runtime') == 'CRITICAL'
        assert comparator._get_significance('memory') == 'CRITICAL'
        assert comparator._get_significance('environment_vars') == 'IMPORTANT'
        assert comparator._get_significance('description') == 'MINOR'
    
    def test_full_comparison(self, temp_functions):
        """Test complete comparison."""
        func1, func2 = temp_functions
        comparator = ASTComparator(str(func1), str(func2))
        
        result = comparator.compare()
        
        assert result['function1'] == 'func1'
        assert result['function2'] == 'func2'
        assert 'configuration' in result
        assert 'dependencies' in result
        assert 'metrics' in result
        assert 'tests' in result
        assert 'event_sources' in result
    
    def test_generate_report(self, temp_functions):
        """Test report generation."""
        func1, func2 = temp_functions
        comparator = ASTComparator(str(func1), str(func2))
        
        report = comparator.generate_report()
        
        assert 'AST-Level Comparison Report' in report
        assert 'CONFIGURATION COMPARISON' in report
        assert 'DEPENDENCIES COMPARISON' in report
        assert 'PERFORMANCE METRICS' in report
    
    def test_generate_json_report(self, temp_functions):
        """Test JSON report generation."""
        func1, func2 = temp_functions
        comparator = ASTComparator(str(func1), str(func2))
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            json_file = f.name
        
        try:
            comparator.generate_json_report(json_file)
            
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            assert data['function1'] == 'func1'
            assert data['function2'] == 'func2'
            assert 'configuration' in data
        finally:
            Path(json_file).unlink()
    
    def test_load_template_config(self, temp_functions):
        """Test loading SAM template."""
        func1, func2 = temp_functions
        comparator = ASTComparator(str(func1), str(func2))
        
        template = comparator._load_template_config(func1)
        
        assert template is not None
        assert 'Resources' in template
    
    def test_missing_template(self, temp_functions):
        """Test handling missing template."""
        func1, func2 = temp_functions
        comparator = ASTComparator(str(func1), str(func2))
        
        # Create temp dir without template
        with tempfile.TemporaryDirectory() as tmpdir:
            template = comparator._load_template_config(Path(tmpdir))
            assert template is None
    
    def test_get_event_sources(self, temp_functions):
        """Test event source detection."""
        func1, func2 = temp_functions
        comparator = ASTComparator(str(func1), str(func2))
        
        sources = comparator._get_event_sources(func1)
        
        # Should have at least 'Direct Invocation' as default
        assert isinstance(sources, list)
        assert len(sources) >= 1


class TestIntegration:
    """Integration tests."""
    
    def test_end_to_end_comparison(self):
        """Test end-to-end comparison workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create two test functions
            for func_name in ['func_old', 'func_new']:
                func_dir = tmpdir / func_name
                func_dir.mkdir()
                (func_dir / "src").mkdir()
                (func_dir / "src" / "lambda_function.py").write_text(
                    f"# {func_name}\ndef lambda_handler(event, context):\n    return 'OK'"
                )
                (func_dir / "src" / "requirements.txt").write_text("requests==2.28.0\n")
                (func_dir / "template.yml").write_text("""
Resources:
  LambdaFunction:
    Type: AWS::Lambda::Function
    Properties:
      Runtime: python3.12
      MemorySize: 128
      Timeout: 30
      Handler: lambda_function.lambda_handler
""")
            
            func_old = tmpdir / "func_old"
            func_new = tmpdir / "func_new"
            
            # Run comparison
            comparator = ASTComparator(str(func_old), str(func_new))
            result = comparator.compare()
            
            # Verify result structure
            assert result is not None
            assert result['function1'] == 'func_old'
            assert result['function2'] == 'func_new'

            # Generate reports (use delete=False so the file can be reopened on Windows)
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
                report_path = f.name
            try:
                report = comparator.generate_report(report_path)
                assert len(report) > 0
            finally:
                Path(report_path).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
