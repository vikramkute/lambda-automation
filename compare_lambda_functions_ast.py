#!/usr/bin/env python3
"""Compare two Lambda functions at AST (Abstract Syntax Tree) level.

This script provides semantic and structural comparison of Lambda functions including:
- Code structure analysis using Abstract Syntax Trees
- Function definitions and class hierarchies
- Dependencies and imports
- Cyclomatic complexity metrics
- Semantic similarity scoring
"""

import sys
import json
import ast
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
import io


@dataclass
class ASTAnalysis:
    """AST-based code analysis results."""
    functions: List[str]
    classes: List[str]
    imports: List[str]
    decorators: List[str]
    cyclomatic_complexity: int
    total_lines: int
    total_statements: int
    has_lambda_handler: bool
    external_calls: List[str]
    variables_defined: List[str]


@dataclass
class FunctionConfig:
    """Lambda function configuration extracted from SAM template."""
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
    """Lambda function dependency information."""
    python_version: str
    total_packages: int
    packages: List[str]
    missing_packages: List[str]


@dataclass
class FunctionMetrics:
    """Calculated performance metrics for a Lambda function."""
    memory_efficiency: float
    estimated_coldstart_time: float
    code_complexity_score: float
    dependency_count: int


@dataclass
class TestResult:
    """Result of a single test execution."""
    function_name: str
    test_name: str
    passed: bool
    message: str


# Prevent pytest from treating this dataclass as a test class
TestResult.__test__ = False  # type: ignore[attr-defined]


class ASTComparator:
    """Compare Lambda functions at AST level."""

    def __init__(self, func1_path: str, func2_path: str):
        """Initialize AST comparator.
        
        Args:
            func1_path: Path to first Lambda function directory
            func2_path: Path to second Lambda function directory
        """
        self.func1_path = Path(func1_path).resolve()
        self.func2_path = Path(func2_path).resolve()
        # Keep the original user-supplied path strings for display (e.g. "prod/myTestFunction1")
        self.func1_label = str(func1_path)
        self.func2_label = str(func2_path)
        
        if not self.func1_path.is_dir():
            raise ValueError(f"Function 1 directory not found: {func1_path}")
        if not self.func2_path.is_dir():
            raise ValueError(f"Function 2 directory not found: {func2_path}")

    def _get_source_folder(self, func_path: Path) -> Path:
        """Dynamically detect the source folder containing lambda_function.py, index.py, or {foldername}.py."""
        # Try to find lambda_function.py, index.py, or {foldername}.py in subdirectories
        for subdir in func_path.iterdir():
            if subdir.is_dir() and not subdir.name.startswith('.'):
                # Check for lambda_function.py
                lambda_file = subdir / 'lambda_function.py'
                if lambda_file.exists():
                    return subdir
                
                # Check for index.py
                index_file = subdir / 'index.py'
                if index_file.exists():
                    return subdir
                
                # Check for {foldername}.py
                folder_file = subdir / f'{subdir.name}.py'
                if folder_file.exists():
                    return subdir
        
        # Fallback to 'src' for backward compatibility
        return func_path / 'src'

    def _analyze_ast(self, func_path: Path) -> Optional[ASTAnalysis]:
        """Analyze Python code using Abstract Syntax Tree for all Python files in src folder."""
        source_folder = self._get_source_folder(func_path)
        
        # Find all Python files in the source folder
        python_files = list(source_folder.glob('*.py'))
        
        if not python_files:
            return None
        
        # Aggregate results from all Python files
        all_functions = []
        all_classes = []
        all_imports = []
        all_decorators = []
        all_external_calls = set()
        all_variables_defined = []
        total_cyclomatic_complexity = 0
        total_lines = 0
        total_statements = 0
        has_lambda_handler = False
        
        for python_file in python_files:
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                tree = ast.parse(code)
                total_lines += len(code.split('\n'))
                
                # Extract various code elements
                functions = []
                classes = []
                imports = []
                decorators = []
                external_calls = set()
                variables_defined = []
                cyclomatic_complexity = 1  # base complexity per file
                file_statements = 0
                file_statements = 0
            
                class ASTVisitor(ast.NodeVisitor):
                    def visit_FunctionDef(self, node):
                        nonlocal cyclomatic_complexity, has_lambda_handler
                        functions.append(node.name)
                        if node.name == 'lambda_handler':
                            has_lambda_handler = True
                        
                        # Extract decorators
                        for decorator in node.decorator_list:
                            if isinstance(decorator, ast.Name):
                                decorators.append(decorator.id)
                            elif isinstance(decorator, ast.Attribute):
                                decorators.append(decorator.attr)
                        
                        # Count conditional branches for cyclomatic complexity
                        for subnode in ast.walk(node):
                            if isinstance(subnode, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                                cyclomatic_complexity += 1
                        
                        self.generic_visit(node)
                    
                    def visit_ClassDef(self, node):
                        classes.append(node.name)
                        self.generic_visit(node)
                    
                    def visit_Import(self, node):
                        for alias in node.names:
                            imports.append(alias.name)
                        self.generic_visit(node)
                    
                    def visit_ImportFrom(self, node):
                        if node.module:
                            imports.append(node.module)
                        self.generic_visit(node)
                    
                    def visit_Call(self, node):
                        nonlocal external_calls
                        # Built-in functions and common stdlib names to exclude
                        _BUILTINS = {
                            'print', 'len', 'str', 'int', 'float', 'list', 'dict',
                            'set', 'tuple', 'bool', 'bytes', 'isinstance', 'issubclass',
                            'type', 'range', 'enumerate', 'zip', 'map', 'filter',
                            'sorted', 'reversed', 'hasattr', 'getattr', 'setattr',
                            'vars', 'dir', 'id', 'hash', 'repr', 'open', 'super',
                            'staticmethod', 'classmethod', 'property', 'next', 'iter',
                            'min', 'max', 'sum', 'abs', 'round', 'any', 'all',
                        }
                        # For attribute calls, only track calls on known external
                        # service-like objects (not local variable methods)
                        _SKIP_ATTRS = {
                            'append', 'extend', 'pop', 'get', 'items', 'keys',
                            'values', 'update', 'split', 'join', 'strip', 'upper',
                            'lower', 'replace', 'encode', 'decode', 'format',
                            'read', 'write', 'close', 'seek', 'tell',
                            'startswith', 'endswith', 'find', 'count',
                            'isoformat', 'strftime', 'strptime', 'utcnow', 'now',
                            'dumps', 'loads', 'load', 'dump',
                        }
                        if isinstance(node.func, ast.Attribute):
                            if isinstance(node.func.value, ast.Name):
                                # Only track if attribute is not a common stdlib/local method
                                if node.func.attr not in _SKIP_ATTRS:
                                    external_calls.add(f"{node.func.value.id}.{node.func.attr}")
                        elif isinstance(node.func, ast.Name):
                            if node.func.id not in _BUILTINS:
                                external_calls.add(node.func.id)
                        self.generic_visit(node)
                    
                    def visit_Assign(self, node):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                variables_defined.append(target.id)
                        self.generic_visit(node)
                
                # Visit all nodes
                visitor = ASTVisitor()
                visitor.visit(tree)
                
                # Count statements in this file
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.Assign, ast.Return, ast.If)):
                        file_statements += 1
                
                # Aggregate results
                all_functions.extend(functions)
                all_classes.extend(classes)
                all_imports.extend(imports)
                all_decorators.extend(decorators)
                all_external_calls.update(external_calls)
                all_variables_defined.extend(variables_defined)
                total_cyclomatic_complexity += cyclomatic_complexity
                total_statements += file_statements
                
            except (SyntaxError, OSError) as e:
                print(f"[!] Error analyzing {python_file}: {e}")
                continue
        
        return ASTAnalysis(
            functions=all_functions,
            classes=all_classes,
            imports=sorted(list(set(all_imports))),
            decorators=sorted(list(set(all_decorators))),
            cyclomatic_complexity=total_cyclomatic_complexity,
            total_lines=total_lines,
            total_statements=total_statements,
            has_lambda_handler=has_lambda_handler,
            external_calls=sorted(list(all_external_calls)),
            variables_defined=sorted(list(set(all_variables_defined)))
        )

    def _compare_ast_analysis(self, ast1: Optional[ASTAnalysis], ast2: Optional[ASTAnalysis]) -> Dict[str, Any]:
        """Compare AST analysis results from two functions."""
        if not ast1 or not ast2:
            return {'status': 'incomplete', 'message': 'One or both functions could not be analyzed'}
        
        def get_set_diff(set1, set2):
            """Return symmetric difference between two sets."""
            return {
                'only_in_first': sorted(list(set(set1) - set(set2))),
                'only_in_second': sorted(list(set(set2) - set(set1))),
                'common': sorted(list(set(set1) & set(set2)))
            }
        
        return {
            'functions_diff': get_set_diff(ast1.functions, ast2.functions),
            'classes_diff': get_set_diff(ast1.classes, ast2.classes),
            'imports_diff': get_set_diff(ast1.imports, ast2.imports),
            'decorators_diff': get_set_diff(ast1.decorators, ast2.decorators),
            'external_calls_diff': get_set_diff(ast1.external_calls, ast2.external_calls),
            'variables_diff': get_set_diff(ast1.variables_defined, ast2.variables_defined),
            'complexity_diff': {
                'function1': ast1.cyclomatic_complexity,
                'function2': ast2.cyclomatic_complexity,
                'difference': ast2.cyclomatic_complexity - ast1.cyclomatic_complexity
            },
            'lines_diff': ast2.total_lines - ast1.total_lines,
            'statements_diff': ast2.total_statements - ast1.total_statements,
            'both_have_handler': ast1.has_lambda_handler and ast2.has_lambda_handler,
            'semantic_similarity_score': self._calculate_semantic_similarity(ast1, ast2)
        }

    def _calculate_semantic_similarity(self, ast1: ASTAnalysis, ast2: ASTAnalysis) -> float:
        """Calculate semantic similarity score between two functions (0-100)."""
        scores = []
        
        # Functions similarity
        if ast1.functions and ast2.functions:
            common_funcs = len(set(ast1.functions) & set(ast2.functions))
            func_similarity = (common_funcs / max(len(ast1.functions), len(ast2.functions))) * 100
            scores.append(func_similarity)
        
        # Imports similarity
        if ast1.imports and ast2.imports:
            common_imports = len(set(ast1.imports) & set(ast2.imports))
            import_similarity = (common_imports / max(len(ast1.imports), len(ast2.imports))) * 100
            scores.append(import_similarity)
        
        # External calls similarity
        if ast1.external_calls and ast2.external_calls:
            common_calls = len(set(ast1.external_calls) & set(ast2.external_calls))
            call_similarity = (common_calls / max(len(ast1.external_calls), len(ast2.external_calls))) * 100
            scores.append(call_similarity)
        
        # Complexity similarity (prefer similar complexity)
        complexity_diff = abs(ast1.cyclomatic_complexity - ast2.cyclomatic_complexity)
        complexity_similarity = 100 - min(50, complexity_diff * 5)
        scores.append(complexity_similarity)
        
        # Both have handler
        if ast1.has_lambda_handler and ast2.has_lambda_handler:
            scores.append(100)
        elif not ast1.has_lambda_handler and not ast2.has_lambda_handler:
            scores.append(50)
        else:
            scores.append(20)
        
        return sum(scores) / len(scores) if scores else 0.0

    # ------------------------------------------------------------------
    # Config / dependency / metrics helpers
    # ------------------------------------------------------------------

    def _load_template_config(self, func_path: Path) -> Optional[Dict]:
        """Load SAM/CloudFormation template configuration from a function directory."""
        template_file = func_path / "template.yml"
        if not template_file.exists():
            return None
        try:
            import yaml
            with open(template_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception:
            return None

    def _extract_function_config(self, name: str, func_path: Path) -> 'FunctionConfig':
        """Extract function configuration from SAM template."""
        template = self._load_template_config(func_path)
        runtime = "unknown"
        memory = 128
        timeout = 3
        handler = "lambda_function.lambda_handler"
        description = ""
        environment_vars: Dict[str, str] = {}
        layers: List[str] = []
        tracing_enabled = False
        ephemeral_storage = 512
        architecture = "x86_64"

        if template:
            resources = template.get('Resources', {})
            for _res_name, resource in resources.items():
                if resource.get('Type') in (
                    'AWS::Lambda::Function', 'AWS::Serverless::Function'
                ):
                    props = resource.get('Properties', {})
                    runtime = props.get('Runtime', runtime)
                    memory = props.get('MemorySize', memory)
                    timeout = props.get('Timeout', timeout)
                    handler = props.get('Handler', handler)
                    description = props.get('Description', description)
                    environment_vars = (
                        props.get('Environment', {}).get('Variables', {}) or {}
                    )
                    layers = props.get('Layers', layers)
                    tracing_enabled = props.get('Tracing', 'PassThrough') == 'Active'
                    eph = props.get('EphemeralStorage', ephemeral_storage)
                    ephemeral_storage = eph.get('Size', 512) if isinstance(eph, dict) else eph
                    archs = props.get('Architectures', [architecture])
                    architecture = archs[0] if archs else architecture
                    break

        return FunctionConfig(
            name=name,
            runtime=runtime,
            memory=memory,
            timeout=timeout,
            handler=handler,
            description=description,
            environment_vars=environment_vars,
            layers=layers,
            tracing_enabled=tracing_enabled,
            ephemeral_storage=ephemeral_storage,
            architecture=architecture,
        )

    def _get_requirements(self, func_path: Path) -> 'FunctionDependencies':
        """Extract dependencies from requirements.txt."""
        source_folder = self._get_source_folder(func_path)
        req_file = source_folder / "requirements.txt"
        packages: List[str] = []
        if req_file.exists():
            with open(req_file, 'r', encoding='utf-8') as f:
                packages = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith('#')
                ]
        python_version = "3.12"
        return FunctionDependencies(
            python_version=python_version,
            total_packages=len(packages),
            packages=packages,
            missing_packages=[],
        )

    def _get_significance(self, field: str) -> str:
        """Return significance level for a configuration field difference."""
        critical = {'runtime', 'memory', 'timeout', 'architecture'}
        important = {'handler', 'layers', 'tracing_enabled', 'environment_vars', 'ephemeral_storage'}
        if field in critical:
            return 'CRITICAL'
        if field in important:
            return 'IMPORTANT'
        return 'MINOR'

    def _compare_configs(
        self, config1: 'FunctionConfig', config2: 'FunctionConfig'
    ) -> List[Dict[str, Any]]:
        """Compare two FunctionConfig objects and return a list of differences."""
        diffs: List[Dict[str, Any]] = []
        fields = [
            'runtime', 'memory', 'timeout', 'handler', 'architecture',
            'tracing_enabled', 'ephemeral_storage', 'layers', 'environment_vars',
            'description',
        ]
        for field in fields:
            val1 = getattr(config1, field)
            val2 = getattr(config2, field)
            if val1 != val2:
                diffs.append({
                    'field': field,
                    'function1_value': val1,
                    'function2_value': val2,
                    'significance': self._get_significance(field),
                })
        return diffs

    def _compare_dependencies(
        self, deps1: 'FunctionDependencies', deps2: 'FunctionDependencies'
    ) -> Dict[str, Any]:
        """Compare dependencies between two functions."""
        set1 = set(deps1.packages)
        set2 = set(deps2.packages)
        return {
            'total_difference': abs(deps1.total_packages - deps2.total_packages),
            'only_in_function1': sorted(list(set1 - set2)),
            'only_in_function2': sorted(list(set2 - set1)),
            'common': sorted(list(set1 & set2)),
            'function1_count': deps1.total_packages,
            'function2_count': deps2.total_packages,
        }

    def _calculate_metrics(
        self, config: 'FunctionConfig', deps: 'FunctionDependencies'
    ) -> 'FunctionMetrics':
        """Calculate estimated performance metrics for a Lambda function."""
        memory_efficiency = min(100.0, (config.memory / 3008.0) * 100)
        base_coldstart = 200.0
        dep_factor = deps.total_packages * 10.0
        estimated_coldstart_time = base_coldstart + dep_factor
        code_complexity_score = max(1.0, 1.0 + deps.total_packages * 0.5)
        return FunctionMetrics(
            memory_efficiency=memory_efficiency,
            estimated_coldstart_time=estimated_coldstart_time,
            code_complexity_score=code_complexity_score,
            dependency_count=deps.total_packages,
        )

    def _compare_metrics(
        self, metrics1: 'FunctionMetrics', metrics2: 'FunctionMetrics'
    ) -> Dict[str, Any]:
        """Compare metrics from two functions."""
        coldstart_diff = metrics2.estimated_coldstart_time - metrics1.estimated_coldstart_time
        return {
            'coldstart_diff_ms': abs(coldstart_diff),
            'coldstart_faster': 'function1' if coldstart_diff > 0 else 'function2',
            'memory_efficiency_diff': abs(metrics1.memory_efficiency - metrics2.memory_efficiency),
            'complexity_diff': abs(metrics1.code_complexity_score - metrics2.code_complexity_score),
        }

    def _get_event_sources(self, func_path: Path) -> List[str]:
        """Detect event source types from the SAM template."""
        template = self._load_template_config(func_path)
        sources: List[str] = []
        if template:
            resources = template.get('Resources', {})
            for _res_name, resource in resources.items():
                props = resource.get('Properties', {})
                for _evt_name, event in props.get('Events', {}).items():
                    evt_type = event.get('Type', '')
                    if evt_type:
                        sources.append(evt_type)
        if not sources:
            sources = ['Direct Invocation']
        return sources

    def compare(self) -> Dict[str, Any]:
        """Perform AST-level comparison between two functions."""
        func1_name = self.func1_path.name
        func2_name = self.func2_path.name

        # Configuration
        config1 = self._extract_function_config(func1_name, self.func1_path)
        config2 = self._extract_function_config(func2_name, self.func2_path)
        config_diffs = self._compare_configs(config1, config2)

        # Dependencies
        deps1 = self._get_requirements(self.func1_path)
        deps2 = self._get_requirements(self.func2_path)
        dep_diff = self._compare_dependencies(deps1, deps2)

        # Metrics
        metrics1 = self._calculate_metrics(config1, deps1)
        metrics2 = self._calculate_metrics(config2, deps2)
        metrics_comp = self._compare_metrics(metrics1, metrics2)

        # AST analysis
        ast1 = self._analyze_ast(self.func1_path)
        ast2 = self._analyze_ast(self.func2_path)

        # Event sources
        event_sources1 = self._get_event_sources(self.func1_path)
        event_sources2 = self._get_event_sources(self.func2_path)

        return {
            'timestamp': datetime.now().isoformat(),
            'function1': self.func1_label,
            'function2': self.func2_label,
            'configuration': {
                'function1': asdict(config1),
                'function2': asdict(config2),
                'differences': config_diffs,
            },
            'dependencies': {
                'function1': asdict(deps1),
                'function2': asdict(deps2),
                'comparison': dep_diff,
            },
            'metrics': {
                'function1': asdict(metrics1),
                'function2': asdict(metrics2),
                'comparison': metrics_comp,
            },
            'tests': {
                'function1': [],
                'function2': [],
            },
            'event_sources': {
                'function1': event_sources1,
                'function2': event_sources2,
            },
            'ast_analysis': {
                'function1': asdict(ast1) if ast1 else None,
                'function2': asdict(ast2) if ast2 else None,
                'comparison': self._compare_ast_analysis(ast1, ast2),
            },
        }

    def generate_report(self, output_file: Optional[str] = None) -> str:
        """Generate human-readable AST comparison report."""
        comparison = self.compare()

        func1_name = comparison['function1']
        func2_name = comparison['function2']
        func1_display = f"{func1_name} ({self.func1_path})"
        func2_display = f"{func2_name} ({self.func2_path})"

        report = []
        report.append("=" * 80)
        report.append("AWS Lambda Function AST-Level Comparison Report")
        report.append("=" * 80)
        report.append(f"\nGenerated: {comparison['timestamp']}")
        report.append(f"Function 1: {func1_display}")
        report.append(f"Function 2: {func2_display}\n")

        # ------------------------------------------------------------------
        # CONFIGURATION COMPARISON
        # ------------------------------------------------------------------
        report.append("\n" + "-" * 80)
        report.append("CONFIGURATION COMPARISON")
        report.append("-" * 80)
        cfg_data = comparison['configuration']
        diffs = cfg_data.get('differences', [])
        if not diffs:
            report.append("\n  [✓] Configurations are identical.")
        else:
            for d in diffs:
                significance = d.get('significance', 'MINOR')
                marker = '[!!]' if significance == 'CRITICAL' else '[!]' if significance == 'IMPORTANT' else '[-]'
                report.append(
                    f"\n  {marker} {d['field']}: {d['function1_value']} → {d['function2_value']}  ({significance})"
                )

        # ------------------------------------------------------------------
        # DEPENDENCIES COMPARISON
        # ------------------------------------------------------------------
        report.append("\n" + "-" * 80)
        report.append("DEPENDENCIES COMPARISON")
        report.append("-" * 80)
        dep_data = comparison['dependencies']
        dep_comp = dep_data.get('comparison', {})
        report.append(f"\n  {func1_name}: {dep_comp.get('function1_count', 0)} package(s)")
        report.append(f"  {func2_name}: {dep_comp.get('function2_count', 0)} package(s)")
        if dep_comp.get('only_in_function1'):
            report.append(f"  Only in {func1_name}: {', '.join(dep_comp['only_in_function1'][:5])}")
        if dep_comp.get('only_in_function2'):
            report.append(f"  Only in {func2_name}: {', '.join(dep_comp['only_in_function2'][:5])}")
        if dep_comp.get('common'):
            report.append(f"  Shared packages: {', '.join(dep_comp['common'][:5])}")

        # ------------------------------------------------------------------
        # PERFORMANCE METRICS
        # ------------------------------------------------------------------
        report.append("\n" + "-" * 80)
        report.append("PERFORMANCE METRICS")
        report.append("-" * 80)
        met_comp = comparison['metrics'].get('comparison', {})
        met1 = comparison['metrics'].get('function1', {})
        met2 = comparison['metrics'].get('function2', {})
        report.append(f"\n  Estimated cold-start  {func1_name}: {met1.get('estimated_coldstart_time', 0):.0f} ms")
        report.append(f"  Estimated cold-start  {func2_name}: {met2.get('estimated_coldstart_time', 0):.0f} ms")
        faster = met_comp.get('coldstart_faster', '')
        if faster and met_comp.get('coldstart_diff_ms', 0) > 0:
            faster_name = func1_name if faster == 'function1' else func2_name
            report.append(f"  Faster cold-start: {faster_name} (by {met_comp.get('coldstart_diff_ms', 0):.0f} ms)")
        report.append(f"\n  Memory efficiency     {func1_name}: {met1.get('memory_efficiency', 0):.1f}%")
        report.append(f"  Memory efficiency     {func2_name}: {met2.get('memory_efficiency', 0):.1f}%")

        # ------------------------------------------------------------------
        # CODE STRUCTURE & SEMANTIC ANALYSIS (AST)
        # ------------------------------------------------------------------
        report.append("\n" + "-" * 80)
        report.append("CODE STRUCTURE & SEMANTIC ANALYSIS (AST)")
        report.append("-" * 80)

        ast_data = comparison['ast_analysis']
        ast_comp = ast_data['comparison']

        if ast_comp.get('status') == 'incomplete':
            report.append(f"\n[!] {ast_comp.get('message', 'Could not analyze code')}")
        else:
            # Semantic similarity
            similarity = ast_comp.get('semantic_similarity_score', 0)
            report.append(f"\nSemantic Similarity Score: {similarity:.1f}%")
            if similarity >= 80:
                report.append("  Status: [✓] HIGHLY SIMILAR")
            elif similarity >= 60:
                report.append("  Status: [~] MODERATELY SIMILAR")
            else:
                report.append("  Status: [!] QUITE DIFFERENT")

            # Basic statistics
            report.append(f"\n{func1_name}:")
            if ast_data['function1']:
                f1 = ast_data['function1']
                report.append(f"  Total Lines: {f1['total_lines']}")
                report.append(f"  Total Statements: {f1['total_statements']}")
                report.append(f"  Functions: {len(f1['functions'])}")
                report.append(f"  Classes: {len(f1['classes'])}")
                report.append(f"  Imports: {len(f1['imports'])}")
                report.append(f"  Cyclomatic Complexity: {f1['cyclomatic_complexity']}")
                report.append(f"  Has Lambda Handler: {f1['has_lambda_handler']}")

            report.append(f"\n{func2_name}:")
            if ast_data['function2']:
                f2 = ast_data['function2']
                report.append(f"  Total Lines: {f2['total_lines']}")
                report.append(f"  Total Statements: {f2['total_statements']}")
                report.append(f"  Functions: {len(f2['functions'])}")
                report.append(f"  Classes: {len(f2['classes'])}")
                report.append(f"  Imports: {len(f2['imports'])}")
                report.append(f"  Cyclomatic Complexity: {f2['cyclomatic_complexity']}")
                report.append(f"  Has Lambda Handler: {f2['has_lambda_handler']}")

            # Function definitions
            funcs_diff = ast_comp.get('functions_diff', {})
            if funcs_diff.get('only_in_first') or funcs_diff.get('only_in_second'):
                report.append(f"\nFunction Definitions:")
                if funcs_diff.get('only_in_first'):
                    report.append(f"  Only in {func1_name}: {', '.join(funcs_diff['only_in_first'][:5])}")
                if funcs_diff.get('only_in_second'):
                    report.append(f"  Only in {func2_name}: {', '.join(funcs_diff['only_in_second'][:5])}")
                if funcs_diff.get('common'):
                    report.append(f"  Common functions: {', '.join(funcs_diff['common'][:5])}")

            # Class definitions
            classes_diff = ast_comp.get('classes_diff', {})
            if classes_diff.get('only_in_first') or classes_diff.get('only_in_second'):
                report.append(f"\nClass Definitions:")
                if classes_diff.get('only_in_first'):
                    report.append(f"  Only in {func1_name}: {', '.join(classes_diff['only_in_first'][:5])}")
                if classes_diff.get('only_in_second'):
                    report.append(f"  Only in {func2_name}: {', '.join(classes_diff['only_in_second'][:5])}")

            # Complexity comparison
            complexity = ast_comp.get('complexity_diff', {})
            report.append(f"\nCyclomatic Complexity:")
            report.append(f"  {func1_name}: {complexity.get('function1', 0)}")
            report.append(f"  {func2_name}: {complexity.get('function2', 0)}")
            diff = complexity.get('difference', 0)
            if diff > 0:
                report.append(f"  Difference: +{diff} ({func2_name} more complex)")
            elif diff < 0:
                report.append(f"  Difference: {diff} ({func1_name} more complex)")

            # Imports
            imports_diff = ast_comp.get('imports_diff', {})
            if imports_diff.get('only_in_first') or imports_diff.get('only_in_second'):
                report.append(f"\nImport Differences:")
                if imports_diff.get('only_in_first'):
                    report.append(f"  Only in {func1_name}: {', '.join(imports_diff['only_in_first'][:3])}")
                if imports_diff.get('only_in_second'):
                    report.append(f"  Only in {func2_name}: {', '.join(imports_diff['only_in_second'][:3])}")

            # External calls
            calls_diff = ast_comp.get('external_calls_diff', {})
            if calls_diff.get('only_in_first') or calls_diff.get('only_in_second'):
                report.append(f"\nExternal Service Calls:")
                if calls_diff.get('only_in_first'):
                    report.append(f"  Only in {func1_name}: {', '.join(calls_diff['only_in_first'][:3])}")
                if calls_diff.get('only_in_second'):
                    report.append(f"  Only in {func2_name}: {', '.join(calls_diff['only_in_second'][:3])}")

            # Line count difference
            lines_diff = ast_comp.get('lines_diff', 0)
            if lines_diff != 0:
                report.append(f"\nCode Size Difference: {lines_diff:+d} lines")

            # Statements difference
            stmts_diff = ast_comp.get('statements_diff', 0)
            if stmts_diff != 0:
                report.append(f"Statement Count Difference: {stmts_diff:+d} statements")

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
        """Generate AST comparison data in JSON format."""
        comparison = self.compare()
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2)
        
        print(f"[OK] JSON report saved to: {output_file}")


def _prepare_ast_output_file(output_dir: str, func1_name: str, func2_name: str) -> Path:
    """Prepare output directory and return timestamped file path."""
    output_dir_path = Path(output_dir).resolve()
    try:
        output_dir_path.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        raise ValueError(f"Cannot create output directory {output_dir}: {e}")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir_path / f"ast_comparison_{func1_name}_vs_{func2_name}_{timestamp}.txt"
    
    if not output_file.resolve().is_relative_to(output_dir_path):
        raise ValueError("Invalid output file path")
    
    return output_file


def compare_functions_ast(func1: str, func2: str, output_dir: str = "comparisons-ast") -> None:
    """Compare two Lambda functions at AST level with automatic file output."""
    try:
        comparator = ASTComparator(func1, func2)
        # Use only the basename so the output filename stays flat
        func1_name = Path(func1).name
        func2_name = Path(func2).name
        output_file = _prepare_ast_output_file(output_dir, func1_name, func2_name)
        
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








def compare_from_config_ast(config_file: str, output_dir: str = "comparisons-ast") -> None:
    """Compare multiple Lambda function pairs from config file."""
    import yaml
    
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
    print(f"Starting {len(comparisons)} AST comparison(s) from {config_file}")
    print(f"Output directory: {output_dir}")
    print(f"{'='*80}")
    
    for idx, comp in enumerate(comparisons, 1):
        func1 = comp.get('function1')
        func2 = comp.get('function2')
        
        if not func1 or not func2:
            print(f"\n[!] Skipping comparison {idx}: Missing function names")
            continue
        
        print(f"\n\n[{idx}/{len(comparisons)}] Running AST comparison: {func1} vs {func2}")
        print(f"{'='*80}")
        try:
            compare_functions_ast(func1, func2, output_dir)
        except Exception as e:
            print(f"[ERR] Comparison failed: {e}")
            continue
    
    print(f"\n\n{'='*80}")
    print(f"[OK] Completed all {len(comparisons)} AST comparison(s)")
    print(f"[OK] Reports saved to: {output_dir}")
    print(f"{'='*80}\n")



def main():
    """Main entry point."""
    # Ensure UTF-8 output on Windows when running as a script
    if sys.platform == 'win32' and hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python compare_lambda_functions_ast.py <config.yaml>")
        print("  python compare_lambda_functions_ast.py <function1> <function2>")
        print("\nExamples:")
        print("  python compare_lambda_functions_ast.py comparison.config.yaml")
        print("  python compare_lambda_functions_ast.py myTestFunction1 myTestFunction2")
        sys.exit(1)
    
    arg1 = sys.argv[1]
    
    # Determine if it's a config file or function names
    if arg1.endswith('.yaml') or arg1.endswith('.yml'):
        # Config file mode
        if not Path(arg1).exists():
            print(f"[ERR] Config file not found: {arg1}")
            sys.exit(1)
        compare_from_config_ast(arg1)
    elif len(sys.argv) >= 3:
        # Two function names
        func1 = arg1
        func2 = sys.argv[2]
        try:
            compare_functions_ast(func1, func2)
        except Exception:
            sys.exit(1)
    else:
        print("[ERR] Invalid arguments")
        print("\nUsage:")
        print("  python compare_lambda_functions_ast.py <config.yaml>")
        print("  python compare_lambda_functions_ast.py <function1> <function2>")
        sys.exit(1)



if __name__ == '__main__':
    main()

