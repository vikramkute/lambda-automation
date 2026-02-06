#!/usr/bin/env python3
"""Compare two Lambda functions and generate a difference report."""

import sys
import difflib
import yaml
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT

def read_file(path):
    """Read file and return lines."""
    try:
        # Resolve to absolute path and validate
        resolved_path = Path(path).resolve()
        # Ensure path exists and is a file
        if not resolved_path.is_file():
            return None
        with open(resolved_path, 'r', encoding='utf-8') as f:
            return f.readlines()
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return None

def count_total_or_diff_lines(lines1, lines2):
    """Count total lines when one is missing, otherwise count differing lines."""
    if lines1 is None or lines2 is None:
        return max(len(lines1 or []), len(lines2 or []))
    
    diff = difflib.unified_diff(lines1, lines2, lineterm='')
    return sum(1 for line in diff if line.startswith(('+', '-')) and not line.startswith(('+++', '---')))

def _output_equal_lines(lines1, lines2, i1, i2, j1, j2, width, file, pdf_data):
    """Output equal lines in side-by-side comparison."""
    for i, j in zip(range(i1, i2), range(j1, j2)):
        left = lines1[i][:width-1]
        right = lines2[j][:width-1]
        line = f"{left:<{width}} | {right}"
        print(line)
        if file:
            file.write(line + '\n')
        if pdf_data is not None:
            pdf_data.append(('equal', left, right))

def _output_deleted_lines(lines1, i1, i2, width, file, pdf_data):
    """Output deleted lines in side-by-side comparison."""
    for i in range(i1, i2):
        left = lines1[i][:width-1]
        print(f"\033[91m{left:<{width}}\033[0m | ")
        if file:
            file.write(f"➖ {left}\n")
        if pdf_data is not None:
            pdf_data.append(('delete', left, ''))

def _output_inserted_lines(lines2, j1, j2, width, file, pdf_data):
    """Output inserted lines in side-by-side comparison."""
    for j in range(j1, j2):
        right = lines2[j][:width-1]
        print(f"{'':<{width}} | \033[92m{right}\033[0m")
        if file:
            file.write(f"{'':<{width}} | ➕ {right}\n")
        if pdf_data is not None:
            pdf_data.append(('insert', '', right))

def _output_replaced_lines(lines1, lines2, i1, i2, j1, j2, width, file, pdf_data):
    """Output replaced lines in side-by-side comparison."""
    max_lines = max(i2-i1, j2-j1)
    for k in range(max_lines):
        left = lines1[i1+k][:width-1] if i1+k < i2 and i1+k < len(lines1) else ''
        right = lines2[j1+k][:width-1] if j1+k < j2 and j1+k < len(lines2) else ''
        left_color = f"\033[91m{left:<{width}}\033[0m" if left else f"{'':<{width}}"
        right_color = f"\033[92m{right}\033[0m" if right else ''
        print(f"{left_color} | {right_color}")
        if file:
            left_marker = f"➖ {left}" if left else left
            right_marker = f"➕ {right}" if right else right
            file.write(f"{left_marker:<{width}} | {right_marker}\n")
        if pdf_data is not None:
            pdf_data.append(('replace', left, right))

def print_side_by_side(lines1, lines2, func1, func2, width=70, file=None, pdf_data=None):
    """Print side-by-side comparison with colors."""
    lines1 = [l.rstrip('\n') for l in (lines1 or [])]
    lines2 = [l.rstrip('\n') for l in (lines2 or [])]
    
    matcher = difflib.SequenceMatcher(None, lines1, lines2)
    
    header = f"\n{func1:<{width}} | {func2}"
    separator = f"{'-'*width}-+-{'-'*width}"
    print(header)
    print(separator)
    if file:
        file.write(header + '\n')
        file.write(separator + '\n')
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            _output_equal_lines(lines1, lines2, i1, i2, j1, j2, width, file, pdf_data)
        elif tag == 'delete':
            _output_deleted_lines(lines1, i1, i2, width, file, pdf_data)
        elif tag == 'insert':
            _output_inserted_lines(lines2, j1, j2, width, file, pdf_data)
        elif tag == 'replace':
            _output_replaced_lines(lines1, lines2, i1, i2, j1, j2, width, file, pdf_data)

def _create_pdf_table(func1, func2, pdf_data, styles, pdf_data_limit=100):
    """Create PDF table from comparison data."""
    if pdf_data is None:
        pdf_data = []
    
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=8, textColor=colors.white, alignment=TA_LEFT)
    table_data = [[Paragraph(f"<b>{func1}</b>", header_style), Paragraph(f"<b>{func2}</b>", header_style)]]
    
    for tag, left, right in pdf_data[:pdf_data_limit]:
        if tag == 'delete':
            table_data.append([Paragraph(f"<font color='red'>➖ {left}</font>", styles['Code']), Paragraph("", styles['Code'])])
        elif tag == 'insert':
            table_data.append([Paragraph("", styles['Code']), Paragraph(f"<font color='green'>➕ {right}</font>", styles['Code'])])
        elif tag == 'replace':
            left_text = f"<font color='red'>➖ {left}</font>" if left else ""
            right_text = f"<font color='green'>➕ {right}</font>" if right else ""
            table_data.append([Paragraph(left_text, styles['Code']), Paragraph(right_text, styles['Code'])])
        else:
            table_data.append([Paragraph(left, styles['Code']), Paragraph(right, styles['Code'])])
    
    table = Table(table_data, colWidths=[3.5*inch, 3.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a4a4a')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Courier'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))
    return table

def generate_pdf_report(func1, func2, file_comparisons, total_diff_lines, output_file):
    """Generate PDF report with highlighted differences."""
    pdf_file = output_file.with_suffix('.pdf')
    doc = SimpleDocTemplate(str(pdf_file), pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#1a1a1a'))
    story.append(Paragraph("Lambda Function Comparison Report", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Metadata
    meta_style = ParagraphStyle('Meta', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#555555'))
    story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", meta_style))
    story.append(Paragraph(f"<b>Function 1:</b> {func1}", meta_style))
    story.append(Paragraph(f"<b>Function 2:</b> {func2}", meta_style))
    story.append(Paragraph(f"<b>Total lines not matching:</b> {total_diff_lines}", meta_style))
    story.append(Spacer(1, 0.3*inch))
    
    # File comparisons
    pdf_data_limit = 100
    for file_name, status, pdf_data in file_comparisons:
        story.append(Paragraph(f"<b>File: {file_name}</b>", styles['Heading2']))
        story.append(Paragraph(status, styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
        
        if pdf_data:
            if len(pdf_data) > pdf_data_limit:
                truncate_msg = f"Showing first {pdf_data_limit} differences ({len(pdf_data)} total)"
                story.append(Paragraph(f"<i>{truncate_msg}</i>", styles['Normal']))
                story.append(Spacer(1, 0.05*inch))
            
            table = _create_pdf_table(func1, func2, pdf_data, styles, pdf_data_limit)
            story.append(table)
        
        story.append(Spacer(1, 0.2*inch))
    
    doc.build(story)
    return pdf_file

def _compare_file_pair(file, path1, path2, func1, func2, f, generate_pdf):
    """Compare a single file pair and return diff count and comparison data."""
    # Sanitize file path to prevent path traversal
    try:
        file_path1 = (path1 / file).resolve()
        file_path2 = (path2 / file).resolve()
        
        # Validate paths are within function directories
        if not file_path1.is_relative_to(path1) or not file_path2.is_relative_to(path2):
            return 0, None
    except (ValueError, OSError):
        return 0, None
    
    lines1 = read_file(file_path1)
    lines2 = read_file(file_path2)
    
    section = f"\n{'─'*80}\nFile: {file}\n{'─'*80}"
    print(section)
    f.write(section + '\n')
    
    if lines1 is None and lines2 is None:
        msg = "❌ Missing in both functions"
        print(msg)
        f.write(msg + '\n')
        return 0, None
    elif lines1 is None:
        msg = f"❌ Missing in {func1}\nLines in {func2}: {len(lines2)}"
        print(msg)
        f.write(msg + '\n')
        return len(lines2), (file, msg, []) if generate_pdf else None
    elif lines2 is None:
        msg = f"❌ Missing in {func2}\nLines in {func1}: {len(lines1)}"
        print(msg)
        f.write(msg + '\n')
        return len(lines1), (file, msg, []) if generate_pdf else None
    
    diff_lines = count_total_or_diff_lines(lines1, lines2)
    
    if diff_lines == 0:
        msg = "✓ Files are identical"
        print(msg)
        f.write(msg + '\n')
        return 0, (file, msg, []) if generate_pdf else None
    
    msg = f"⚠ Lines not matching: {diff_lines}"
    print(msg)
    f.write(msg + '\n')
    pdf_data = [] if generate_pdf else None
    print_side_by_side(lines1, lines2, func1, func2, file=f, pdf_data=pdf_data)
    return diff_lines, (file, msg, pdf_data) if generate_pdf else None

def _validate_function_dirs(func1, func2):
    """Validate function directories exist and return resolved paths."""
    try:
        path1 = Path(func1).resolve()
        path2 = Path(func2).resolve()
    except (ValueError, OSError) as e:
        raise ValueError(f"Invalid directory path: {e}")
    
    if not path1.is_dir():
        raise ValueError(f"Function directory does not exist: {func1}")
    if not path2.is_dir():
        raise ValueError(f"Function directory does not exist: {func2}")
    
    return path1, path2

def _collect_function_files(path1, path2):
    """Collect all files from both function directories."""
    files1 = {str(f.relative_to(path1)) for f in path1.rglob('*') if f.is_file() and not any(x in str(f) for x in ['.aws-sam', '.build', '__pycache__'])}
    files2 = {str(f.relative_to(path2)) for f in path2.rglob('*') if f.is_file() and not any(x in str(f) for x in ['.aws-sam', '.build', '__pycache__'])}
    return sorted(files1 | files2)

def _prepare_output_file(output_dir, path1, path2):
    """Prepare output directory and file path."""
    output_dir_path = Path(output_dir).resolve()
    try:
        output_dir_path.mkdir(exist_ok=True)
    except (OSError, PermissionError) as e:
        raise ValueError(f"Cannot create output directory {output_dir}: {e}")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir_path / f"comparison_{path1.name}_vs_{path2.name}_{timestamp}.txt"
    
    if not output_file.resolve().is_relative_to(output_dir_path):
        raise ValueError("Invalid output file path")
    
    return output_file

def _write_comparison_report(output_file, func1, func2, files, path1, path2, generate_pdf):
    """Write comparison report to file and return results."""
    header = f"\n{'='*80}\nLambda Function Comparison Report\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nFunction 1: {func1}\nFunction 2: {func2}\n{'='*80}\n"
    print(header)
    
    total_diff_lines = 0
    file_comparisons = []
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(header)
            
            for file in files:
                diff_count, comparison_data = _compare_file_pair(file, path1, path2, func1, func2, f, generate_pdf)
                total_diff_lines += diff_count
                if comparison_data:
                    file_comparisons.append(comparison_data)
            
            footer = f"\n{'='*80}\nTotal lines not matching: {total_diff_lines}\n{'='*80}\n"
            print(footer)
            f.write(footer)
    except (OSError, PermissionError) as e:
        raise ValueError(f"Cannot write to output file {output_file}: {e}")
    
    return total_diff_lines, file_comparisons

def _generate_pdf_if_requested(generate_pdf, func1, func2, file_comparisons, total_diff_lines, output_file):
    """Generate PDF report if requested."""
    if generate_pdf:
        try:
            pdf_file = generate_pdf_report(func1, func2, file_comparisons, total_diff_lines, output_file)
            print(f"✓ PDF report saved to: {pdf_file}")
        except Exception as e:
            print(f"⚠ Failed to generate PDF: {e}")

def compare_functions(func1, func2, output_dir="comparisons", generate_pdf=True):
    """Compare two Lambda functions."""
    path1, path2 = _validate_function_dirs(func1, func2)
    files = _collect_function_files(path1, path2)
    output_file = _prepare_output_file(output_dir, path1, path2)
    
    total_diff_lines, file_comparisons = _write_comparison_report(output_file, func1, func2, files, path1, path2, generate_pdf)
    
    print(f"\n✓ Report saved to: {output_file}")
    _generate_pdf_if_requested(generate_pdf, func1, func2, file_comparisons, total_diff_lines, output_file)

def compare_from_config(config_file, output_dir="comparisons", generate_pdf=True):
    """Compare multiple Lambda function pairs from config file."""
    # Validate config file path to prevent path traversal
    config_path = Path(config_file).resolve()
    if not config_path.is_file():
        print(f"❌ Config file not found: {config_file}")
        return
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"❌ Invalid YAML in config file: {e}")
        return
    except (OSError, PermissionError) as e:
        print(f"❌ Cannot read config file: {e}")
        return
    
    comparisons = config.get('comparisons', [])
    if not comparisons:
        print("No comparisons found in config file")
        return
    
    print(f"\n{'='*80}")
    print(f"Starting {len(comparisons)} comparison(s) from {config_file}")
    print(f"Output directory: {output_dir}")
    print(f"{'='*80}")
    
    for idx, comp in enumerate(comparisons, 1):
        func1 = comp.get('function1')
        func2 = comp.get('function2')
        
        if not func1 or not func2:
            print(f"\n⚠ Skipping comparison {idx}: Missing function names")
            continue
        
        print(f"\n\n[{idx}/{len(comparisons)}] Comparing {func1} vs {func2}")
        print(f"{'='*80}")
        try:
            compare_functions(func1, func2, output_dir, generate_pdf)
        except ValueError as e:
            print(f"❌ Comparison failed: {e}")
            continue
    
    print(f"\n\n{'='*80}")
    print(f"✓ Completed all {len(comparisons)} comparison(s)")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    generate_pdf = '--no-pdf' not in sys.argv
    args = [arg for arg in sys.argv[1:] if arg != '--no-pdf']
    
    if len(args) == 1:
        compare_from_config(args[0], generate_pdf=generate_pdf)
    elif len(args) == 2:
        compare_functions(args[0], args[1], generate_pdf=generate_pdf)
    else:
        print("Usage:")
        print("  python compare_lambda_functions.py <config.yaml> [--no-pdf]")
        print("  python compare_lambda_functions.py <function1> <function2> [--no-pdf]")
        sys.exit(1)
