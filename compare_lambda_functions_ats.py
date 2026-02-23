#!/usr/bin/env python3
"""Compare two Lambda functions at ATS (Application Test Suite) level.

This script provides functional and behavioral comparison of Lambda functions including:
- Configuration and metadata
- Runtime and dependencies
- Test execution results
- Performance characteristics
- Supported event triggers
- Required permissions
"""

import sys
import yaml
import json
import subprocess
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
import tempfile
import io

# Ensure UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


@dataclass
class FunctionConfig:
    """Lambda function configuration."""
    name: str
    runtime: str
    memory: int
    timeout: int
    handler: str
    description: str
    environment_vars: Dict[str, str]
    layers: List[str]
    tracing_enabled: bool
    ephemeral_storage: int
    architecture: str


@dataclass
class FunctionDependencies:
    """Lambda function dependencies and requirements."""
    python_version: str
    total_packages: int
    packages: List[str]
    missing_packages: List[str]


@dataclass
class TestResult:
    """Test execution result."""
    test_name: str
    status: str  # 'PASSED', 'FAILED', 'SKIPPED'
    duration: float
    message: str


@dataclass
class FunctionMetrics:
    """Performance and capability metrics."""
    estimated_coldstart_time: float
    memory_efficiency: float
    dependency_size_mb: float
    code_complexity_score: float
    test_coverage: float


class ATSComparator:
    """Compare Lambda functions at ATS level."""

    def __init__(self, func1_path: str, func2_path: str, config_file: str = "functions.config.yaml"):
        """Initialize ATS comparator.
        
        Args:
            func1_path: Path to first Lambda function directory
            func2_path: Path to second Lambda function directory
            config_file: Path to functions configuration file
        """
        self.func1_path = Path(func1_path).resolve()
        self.func2_path = Path(func2_path).resolve()
        self.config_file = Path(config_file).resolve()
        
        if not self.func1_path.is_dir():
            raise ValueError(f"Function 1 directory not found: {func1_path}")
        if not self.func2_path.is_dir():
            raise ValueError(f"Function 2 directory not found: {func2_path}")

    def _load_config_for_function(self, func_name: str) -> Optional[Dict[str, Any]]:
        """Load function configuration from functions.config.yaml."""
        if not self.config_file.exists():
            return None
        
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            for func in config.get('functions', []):
                if func.get('name') == func_name:
                    return func
            return None
        except (yaml.YAMLError, OSError):
            return None

    def _load_template_config(self, func_path: Path) -> Optional[Dict[str, Any]]:
        """Load SAM template.yml configuration."""
        template_file = func_path / "template.yml"
        if not template_file.exists():
            template_file = func_path / "template.yaml"
        
        if not template_file.exists():
            return None
        
        try:
            with open(template_file, 'r') as f:
                return yaml.safe_load(f)
        except (yaml.YAMLError, OSError):
            return None

    def _extract_function_config(self, func_name: str, func_path: Path) -> FunctionConfig:
        """Extract function configuration."""
        config_dict = self._load_config_for_function(func_name) or {}
        template_dict = self._load_template_config(func_path) or {}
        
        # Extract from SAM template
        resources = template_dict.get('Resources', {})
        lambda_resource = next((v for k, v in resources.items() if v.get('Type') == 'AWS::Lambda::Function'), {})
        props = lambda_resource.get('Properties', {})
        
        return FunctionConfig(
            name=func_name,
            runtime=config_dict.get('runtime') or props.get('Runtime', 'python3.12'),
            memory=config_dict.get('memory', props.get('MemorySize', 128)),
            timeout=config_dict.get('timeout', props.get('Timeout', 30)),
            handler=props.get('Handler', 'lambda_function.lambda_handler'),
            description=config_dict.get('description', props.get('Description', '')),
            environment_vars=props.get('Environment', {}).get('Variables', {}),
            layers=props.get('Layers', []),
            tracing_enabled=props.get('TracingConfig', {}).get('Mode') == 'Active',
            ephemeral_storage=props.get('EphemeralStorage', {}).get('Size', 512),
            architecture=props.get('Architectures', ['x86_64'])[0]
        )

    def _get_requirements(self, func_path: Path) -> FunctionDependencies:
        """Extract function dependencies from requirements.txt."""
        req_file = func_path / "src" / "requirements.txt"
        packages = []
        missing_packages = []
        
        if not req_file.exists():
            return FunctionDependencies(
                python_version="unknown",
                total_packages=0,
                packages=[],
                missing_packages=[]
            )
        
        try:
            with open(req_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        packages.append(line)
        except OSError:
            pass
        
        # Get Python version from handler
        python_version = "3.12"  # default
        lambda_file = func_path / "src" / "lambda_function.py"
        if lambda_file.exists():
            try:
                with open(lambda_file, 'r') as f:
                    content = f.read()
                    if 'sys.version' in content or 'python_version' in content:
                        # Try to extract version info
                        pass
            except OSError:
                pass
        
        return FunctionDependencies(
            python_version=python_version,
            total_packages=len(packages),
            packages=packages,
            missing_packages=missing_packages
        )

    def _run_tests(self, func_name: str, func_path: Path) -> List[TestResult]:
        """Run tests for a function using pytest."""
        results = []
        
        # Find test files that reference this function
        test_dir = Path("tests")
        if not test_dir.exists():
            return results
        
        test_files = list(test_dir.glob("test_*.py"))
        
        for test_file in test_files:
            try:
                # Run pytest for this test file with verbose output
                env = dict(os.environ)
                env['SKIP_SAM_TESTS'] = 'true'
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short", "-x"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    env=env
                )
                
                # Parse output
                for line in result.stdout.split('\n'):
                    if '::test_' in line and ('PASSED' in line or 'FAILED' in line or 'SKIPPED' in line):
                        parts = line.split('::')
                        if len(parts) >= 2:
                            test_name = parts[1].split()[0]
                            if 'PASSED' in line:
                                status = 'PASSED'
                            elif 'FAILED' in line:
                                status = 'FAILED'
                            else:
                                status = 'SKIPPED'
                            
                            results.append(TestResult(
                                test_name=test_name,
                                status=status,
                                duration=0.0,
                                message=line.strip()
                            ))
            except subprocess.TimeoutExpired:
                results.append(TestResult(
                    test_name=test_file.name,
                    status='FAILED',
                    duration=30.0,
                    message="Test execution timeout"
                ))
            except Exception as e:
                results.append(TestResult(
                    test_name=test_file.name,
                    status='FAILED',
                    duration=0.0,
                    message=f"Error running tests: {str(e)}"
                ))
        
        return results

    def _calculate_metrics(self, config: FunctionConfig, deps: FunctionDependencies) -> FunctionMetrics:
        """Calculate function metrics and scores."""
        # Estimate cold start based on dependencies and memory
        dep_size = deps.total_packages * 0.5  # rough estimate
        coldstart = 1000 + (dep_size * 10)  # milliseconds
        if config.memory >= 1024:
            coldstart *= 0.7
        
        # Memory efficiency (higher is better)
        memory_efficiency = config.memory / 128.0
        
        # Code complexity (simplified)
        code_complexity = 50.0
        lambda_file = Path(config.name) / "src" / "lambda_function.py"
        if lambda_file.exists():
            try:
                with open(lambda_file, 'r') as f:
                    lines = len(f.readlines())
                    code_complexity = min(100.0, (lines / 10.0))
            except OSError:
                pass
        
        return FunctionMetrics(
            estimated_coldstart_time=coldstart,
            memory_efficiency=memory_efficiency,
            dependency_size_mb=dep_size,
            code_complexity_score=code_complexity,
            test_coverage=0.0  # would need coverage data
        )

    def _get_event_sources(self, func_path: Path) -> List[str]:
        """Identify event sources from template and code."""
        event_sources = set()
        
        # Check template for event sources
        template_dict = self._load_template_config(func_path)
        if template_dict:
            resources = template_dict.get('Resources', {})
            for resource_name, resource_def in resources.items():
                event_type = resource_def.get('Type', '')
                if 'ApiGateway' in event_type:
                    event_sources.add('API Gateway')
                elif 'S3' in event_type:
                    event_sources.add('S3')
                elif 'DynamoDB' in event_type:
                    event_sources.add('DynamoDB Streams')
                elif 'SQS' in event_type:
                    event_sources.add('SQS')
                elif 'SNS' in event_type:
                    event_sources.add('SNS')
                elif 'CloudWatch' in event_type or 'Schedule' in event_type:
                    event_sources.add('EventBridge/CloudWatch')
        
        # Check code for hints
        lambda_file = func_path / "src" / "lambda_function.py"
        if lambda_file.exists():
            try:
                with open(lambda_file, 'r') as f:
                    content = f.read()
                    if 'Records' in content:
                        if 's3' in content:
                            event_sources.add('S3')
                        if 'dynamodb' in content:
                            event_sources.add('DynamoDB')
                        if 'sqs' in content:
                            event_sources.add('SQS')
            except OSError:
                pass
        
        return sorted(list(event_sources)) if event_sources else ['Direct Invocation']

    def compare(self) -> Dict[str, Any]:
        """Perform ATS-level comparison between two functions."""
        func1_name = self.func1_path.name
        func2_name = self.func2_path.name
        
        # Configuration comparison
        config1 = self._extract_function_config(func1_name, self.func1_path)
        config2 = self._extract_function_config(func2_name, self.func2_path)
        
        # Dependencies comparison
        deps1 = self._get_requirements(self.func1_path)
        deps2 = self._get_requirements(self.func2_path)
        
        # Metrics comparison
        metrics1 = self._calculate_metrics(config1, deps1)
        metrics2 = self._calculate_metrics(config2, deps2)
        
        # Test results
        tests1 = self._run_tests(func1_name, self.func1_path)
        tests2 = self._run_tests(func2_name, self.func2_path)
        
        # Event sources
        events1 = self._get_event_sources(self.func1_path)
        events2 = self._get_event_sources(self.func2_path)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'function1': func1_name,
            'function2': func2_name,
            'configuration': {
                'function1': asdict(config1),
                'function2': asdict(config2),
                'differences': self._compare_configs(config1, config2)
            },
            'dependencies': {
                'function1': asdict(deps1),
                'function2': asdict(deps2),
                'differences': self._compare_dependencies(deps1, deps2)
            },
            'metrics': {
                'function1': asdict(metrics1),
                'function2': asdict(metrics2),
                'comparison': self._compare_metrics(metrics1, metrics2)
            },
            'tests': {
                'function1': [asdict(t) for t in tests1],
                'function2': [asdict(t) for t in tests2],
                'summary': self._compare_test_results(tests1, tests2)
            },
            'event_sources': {
                'function1': events1,
                'function2': events2,
                'differences': list(set(events1) ^ set(events2))
            }
        }

    def _compare_configs(self, config1: FunctionConfig, config2: FunctionConfig) -> List[Dict[str, Any]]:
        """Compare configurations and return differences."""
        differences = []
        
        for field in config1.__dataclass_fields__:
            val1 = getattr(config1, field)
            val2 = getattr(config2, field)
            
            if val1 != val2:
                differences.append({
                    'field': field,
                    'function1': val1,
                    'function2': val2,
                    'significance': self._get_significance(field)
                })
        
        return differences

    def _compare_dependencies(self, deps1: FunctionDependencies, deps2: FunctionDependencies) -> Dict[str, Any]:
        """Compare dependencies."""
        set1 = set(deps1.packages)
        set2 = set(deps2.packages)
        
        return {
            'only_in_function1': sorted(list(set1 - set2)),
            'only_in_function2': sorted(list(set2 - set1)),
            'common': sorted(list(set1 & set2)),
            'total_difference': abs(len(set1) - len(set2))
        }

    def _compare_metrics(self, metrics1: FunctionMetrics, metrics2: FunctionMetrics) -> Dict[str, Any]:
        """Compare metrics."""
        return {
            'coldstart_diff_ms': metrics2.estimated_coldstart_time - metrics1.estimated_coldstart_time,
            'coldstart_faster': 'function1' if metrics1.estimated_coldstart_time < metrics2.estimated_coldstart_time else 'function2',
            'memory_efficiency_ratio': metrics2.memory_efficiency / max(metrics1.memory_efficiency, 0.1),
            'complexity_diff': metrics2.code_complexity_score - metrics1.code_complexity_score,
            'dependency_size_diff_mb': metrics2.dependency_size_mb - metrics1.dependency_size_mb
        }

    def _compare_test_results(self, tests1: List[TestResult], tests2: List[TestResult]) -> Dict[str, Any]:
        """Compare test results."""
        passed1 = sum(1 for t in tests1 if t.status == 'PASSED')
        passed2 = sum(1 for t in tests2 if t.status == 'PASSED')
        failed1 = sum(1 for t in tests1 if t.status == 'FAILED')
        failed2 = sum(1 for t in tests2 if t.status == 'FAILED')
        
        return {
            'function1_passed': passed1,
            'function1_failed': failed1,
            'function1_total': len(tests1),
            'function2_passed': passed2,
            'function2_failed': failed2,
            'function2_total': len(tests2),
            'reliability_difference': (passed2 - passed1) if len(tests2) > 0 else 0
        }

    def _get_significance(self, field: str) -> str:
        """Get significance level of a configuration difference."""
        critical_fields = {'runtime', 'handler', 'memory', 'timeout'}
        important_fields = {'environment_vars', 'layers', 'architecture'}
        
        if field in critical_fields:
            return 'CRITICAL'
        elif field in important_fields:
            return 'IMPORTANT'
        else:
            return 'MINOR'

    def generate_report(self, output_file: Optional[str] = None) -> str:
        """Generate human-readable comparison report."""
        comparison = self.compare()
        
        report = []
        report.append("=" * 80)
        report.append("AWS Lambda Function ATS-Level Comparison Report")
        report.append("=" * 80)
        report.append(f"\nGenerated: {comparison['timestamp']}")
        report.append(f"Function 1: {comparison['function1']}")
        report.append(f"Function 2: {comparison['function2']}\n")
        
        # Configuration comparison
        report.append("\n" + "-" * 80)
        report.append("CONFIGURATION COMPARISON")
        report.append("-" * 80)
        
        config_diffs = comparison['configuration']['differences']
        if not config_diffs:
            report.append("[OK] All configurations are identical")
        else:
            for diff in config_diffs:
                significance = diff['significance']
                symbol = "[!]" if significance == "CRITICAL" else "[~]" if significance == "IMPORTANT" else "[ ]"
                report.append(f"\n{symbol} {diff['field']} ({significance})")
                report.append(f"  {comparison['function1']}: {diff['function1']}")
                report.append(f"  {comparison['function2']}: {diff['function2']}")
        
        # Dependencies comparison
        report.append("\n" + "-" * 80)
        report.append("DEPENDENCIES COMPARISON")
        report.append("-" * 80)
        
        deps_summary = comparison['dependencies']
        report.append(f"\n{comparison['function1']}: {deps_summary['function1']['total_packages']} packages")
        report.append(f"{comparison['function2']}: {deps_summary['function2']['total_packages']} packages")
        report.append(f"Difference: {deps_summary['differences']['total_difference']} packages")
        
        if deps_summary['differences']['only_in_function1']:
            report.append(f"\n[PKG] Only in {comparison['function1']}:")
            for pkg in deps_summary['differences']['only_in_function1'][:5]:
                report.append(f"  - {pkg}")
            if len(deps_summary['differences']['only_in_function1']) > 5:
                report.append(f"  ... and {len(deps_summary['differences']['only_in_function1']) - 5} more")
        
        if deps_summary['differences']['only_in_function2']:
            report.append(f"\n[PKG] Only in {comparison['function2']}:")
            for pkg in deps_summary['differences']['only_in_function2'][:5]:
                report.append(f"  - {pkg}")
            if len(deps_summary['differences']['only_in_function2']) > 5:
                report.append(f"  ... and {len(deps_summary['differences']['only_in_function2']) - 5} more")
        
        # Metrics comparison
        report.append("\n" + "-" * 80)
        report.append("PERFORMANCE METRICS")
        report.append("-" * 80)
        
        metrics = comparison['metrics']
        coldstart_diff = metrics['comparison']['coldstart_diff_ms']
        faster = metrics['comparison']['coldstart_faster']
        report.append(f"\nEstimated Cold Start Time:")
        report.append(f"  {comparison['function1']}: {metrics['function1']['estimated_coldstart_time']:.0f} ms")
        report.append(f"  {comparison['function2']}: {metrics['function2']['estimated_coldstart_time']:.0f} ms")
        if coldstart_diff > 0:
            report.append(f"  [*] {faster} is ~{abs(coldstart_diff):.0f}ms faster")
        
        report.append(f"\nCode Complexity:")
        report.append(f"  {comparison['function1']}: {metrics['function1']['code_complexity_score']:.1f}/100")
        report.append(f"  {comparison['function2']}: {metrics['function2']['code_complexity_score']:.1f}/100")
        
        # Event sources
        report.append("\n" + "-" * 80)
        report.append("EVENT SOURCES & TRIGGERS")
        report.append("-" * 80)
        
        events = comparison['event_sources']
        report.append(f"\n{comparison['function1']}: {', '.join(events['function1'])}")
        report.append(f"{comparison['function2']}: {', '.join(events['function2'])}")
        
        if events['differences']:
            report.append(f"\nDue to differences in supported triggers:")
            for evt in events['differences']:
                report.append(f"  * {evt}")
        
        # Test results
        report.append("\n" + "-" * 80)
        report.append("TEST RESULTS")
        report.append("-" * 80)
        
        tests = comparison['tests']
        summary = tests['summary']
        report.append(f"\n{comparison['function1']}: {summary['function1_passed']}/{summary['function1_total']} passed")
        report.append(f"{comparison['function2']}: {summary['function2_passed']}/{summary['function2_total']} passed")
        
        if summary['reliability_difference'] > 0:
            report.append(f"\n[OK] {comparison['function2']} shows better test reliability (+{summary['reliability_difference']})")
        elif summary['reliability_difference'] < 0:
            report.append(f"\n[OK] {comparison['function1']} shows better test reliability (+{abs(summary['reliability_difference'])})")
        
        report.append("\n" + "=" * 80 + "\n")
        
        report_text = "\n".join(report)
        
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"[OK] Report saved to: {output_file}")
        
        return report_text

    def generate_json_report(self, output_file: str) -> None:
        """Generate comparison data in JSON format."""
        comparison = self.compare()
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2)
        
        print(f"[OK] JSON report saved to: {output_file}")


def _prepare_ats_output_file(output_dir: str, func1_name: str, func2_name: str) -> Path:
    """Prepare output directory and return timestamped file path."""
    output_dir_path = Path(output_dir).resolve()
    try:
        output_dir_path.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        raise ValueError(f"Cannot create output directory {output_dir}: {e}")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir_path / f"ats_comparison_{func1_name}_vs_{func2_name}_{timestamp}.txt"
    
    if not output_file.resolve().is_relative_to(output_dir_path):
        raise ValueError("Invalid output file path")
    
    return output_file


def compare_functions_ats(func1: str, func2: str, output_dir: str = "comparisons-ats") -> None:
    """Compare two Lambda functions at ATS level with automatic file output."""
    try:
        comparator = ATSComparator(func1, func2)
        output_file = _prepare_ats_output_file(output_dir, func1, func2)
        
        # Generate reports
        report = comparator.generate_report(str(output_file))
        print(report)
        
        # Also save JSON
        json_file = output_file.with_suffix('.json')
        comparator.generate_json_report(str(json_file))
    
    except ValueError as e:
        print(f"[ERR] Error: {e}")
        raise
    except Exception as e:
        print(f"[ERR] Unexpected error: {e}")
        raise


def compare_from_config_ats(config_file: str, output_dir: str = "comparisons-ats") -> None:
    """Compare multiple Lambda function pairs from config file."""
    # Validate config file path
    config_path = Path(config_file).resolve()
    if not config_path.is_file():
        print(f"[ERR] Config file not found: {config_file}")
        return
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"[ERR] Invalid YAML in config file: {e}")
        return
    except (OSError, PermissionError) as e:
        print(f"[ERR] Cannot read config file: {e}")
        return
    
    comparisons = config.get('comparisons', [])
    if not comparisons:
        print("No comparisons found in config file")
        return
    
    print(f"\n{'='*80}")
    print(f"Starting {len(comparisons)} ATS comparison(s) from {config_file}")
    print(f"Output directory: {output_dir}")
    print(f"{'='*80}")
    
    for idx, comp in enumerate(comparisons, 1):
        func1 = comp.get('function1')
        func2 = comp.get('function2')
        
        if not func1 or not func2:
            print(f"\n[!] Skipping comparison {idx}: Missing function names")
            continue
        
        print(f"\n\n[{idx}/{len(comparisons)}] Running ATS comparison: {func1} vs {func2}")
        print(f"{'='*80}")
        try:
            compare_functions_ats(func1, func2, output_dir)
        except Exception as e:
            print(f"[ERR] Comparison failed: {e}")
            continue
    
    print(f"\n\n{'='*80}")
    print(f"[OK] Completed all {len(comparisons)} ATS comparison(s)")
    print(f"[OK] Reports saved to: {output_dir}")
    print(f"{'='*80}\n")



def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python compare_lambda_functions_ats.py <config.yaml>")
        print("  python compare_lambda_functions_ats.py <function1> <function2>")
        print("\nExamples:")
        print("  python compare_lambda_functions_ats.py comparison.config.yaml")
        print("  python compare_lambda_functions_ats.py myTestFunction1 myTestFunction2")
        sys.exit(1)
    
    arg1 = sys.argv[1]
    
    # Determine if it's a config file or function names
    if arg1.endswith('.yaml') or arg1.endswith('.yml'):
        # Config file mode
        if not Path(arg1).exists():
            print(f"[ERR] Config file not found: {arg1}")
            sys.exit(1)
        compare_from_config_ats(arg1)
    elif len(sys.argv) >= 3:
        # Two function names
        func1 = arg1
        func2 = sys.argv[2]
        try:
            compare_functions_ats(func1, func2)
        except Exception:
            sys.exit(1)
    else:
        print("[ERR] Invalid arguments")
        print("\nUsage:")
        print("  python compare_lambda_functions_ats.py <config.yaml>")
        print("  python compare_lambda_functions_ats.py <function1> <function2>")
        sys.exit(1)



if __name__ == '__main__':
    main()

