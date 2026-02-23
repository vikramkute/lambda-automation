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

# Ensure UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


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
        
        if not self.func1_path.is_dir():
            raise ValueError(f"Function 1 directory not found: {func1_path}")
        if not self.func2_path.is_dir():
            raise ValueError(f"Function 2 directory not found: {func2_path}")

    def _analyze_ast(self, func_path: Path) -> Optional[ASTAnalysis]:
        """Analyze Python code using Abstract Syntax Tree."""
        lambda_file = func_path / "src" / "lambda_function.py"
        if not lambda_file.exists():
            return None
        
        try:
            with open(lambda_file, 'r') as f:
                code = f.read()
            
            tree = ast.parse(code)
            
            # Extract various code elements
            functions = []
            classes = []
            imports = []
            decorators = []
            external_calls = set()
            variables_defined = []
            cyclomatic_complexity = 1  # base complexity
            total_statements = 0
            has_lambda_handler = False
            
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
                    if isinstance(node.func, ast.Attribute):
                        if isinstance(node.func.value, ast.Name):
                            external_calls.add(f"{node.func.value.id}.{node.func.attr}")
                    elif isinstance(node.func, ast.Name):
                        # Only track calls to external modules, not built-ins
                        if node.func.id not in {'print', 'len', 'str', 'int', 'list', 'dict', 'set'}:
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
            
            # Count statements
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.Assign, ast.Return, ast.If)):
                    total_statements += 1
            
            return ASTAnalysis(
                functions=functions,
                classes=classes,
                imports=sorted(list(set(imports))),
                decorators=sorted(list(set(decorators))),
                cyclomatic_complexity=cyclomatic_complexity,
                total_lines=len(code.split('\n')),
                total_statements=total_statements,
                has_lambda_handler=has_lambda_handler,
                external_calls=sorted(list(external_calls)),
                variables_defined=sorted(list(set(variables_defined)))
            )
        except (SyntaxError, OSError) as e:
            print(f"[!] Error analyzing {lambda_file}: {e}")
            return None

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

    def compare(self) -> Dict[str, Any]:
        """Perform AST-level comparison between two functions."""
        func1_name = self.func1_path.name
        func2_name = self.func2_path.name
        
        # AST analysis
        ast1 = self._analyze_ast(self.func1_path)
        ast2 = self._analyze_ast(self.func2_path)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'function1': {
                'name': func1_name,
                'path': str(self.func1_path)
            },
            'function2': {
                'name': func2_name,
                'path': str(self.func2_path)
            },
            'ast_analysis': {
                'function1': asdict(ast1) if ast1 else None,
                'function2': asdict(ast2) if ast2 else None,
                'comparison': self._compare_ast_analysis(ast1, ast2)
            }
        }

    def generate_report(self, output_file: Optional[str] = None) -> str:
        """Generate human-readable AST comparison report."""
        comparison = self.compare()
        
        func1_name = comparison['function1']['name']
        func2_name = comparison['function2']['name']
        func1_display = f"{func1_name} ({comparison['function1']['path']})"
        func2_display = f"{func2_name} ({comparison['function2']['path']})"
        
        report = []
        report.append("=" * 80)
        report.append("AWS Lambda Function AST-Level Comparison Report")
        report.append("=" * 80)
        report.append(f"\nGenerated: {comparison['timestamp']}")
        report.append(f"Function 1: {func1_display}")
        report.append(f"Function 2: {func2_display}\n")
        
        # AST Analysis
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
        output_file = _prepare_ast_output_file(output_dir, func1, func2)
        
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

