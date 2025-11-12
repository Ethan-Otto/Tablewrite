#!/usr/bin/env python3
"""
Generate a Mermaid ERD diagram showing local Python file imports.

Usage:
    python scripts/generate_import_diagram.py
    python scripts/generate_import_diagram.py --source-dir src --output-dir output/diagrams
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, Set, Tuple
import argparse


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def extract_imports(file_path: Path, project_root: Path) -> Set[str]:
    """
    Extract local imports from a Python file.

    Returns a set of module paths that are imported from within the project.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"Warning: Could not parse {file_path}: {e}", file=sys.stderr)
        return set()

    imports = set()

    for node in ast.walk(tree):
        # Handle "import module" and "import module.submodule"
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.split('.')[0]
                imports.add(module_name)

        # Handle "from module import something"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_name = node.module.split('.')[0]
                imports.add(module_name)
            # Handle relative imports (from . import X, from .. import Y)
            elif node.level > 0:
                # Resolve relative import to absolute module path
                relative_path = resolve_relative_import(file_path, node.level, project_root)
                if relative_path:
                    imports.add(relative_path)

    return imports


def resolve_relative_import(file_path: Path, level: int, project_root: Path) -> str:
    """
    Resolve relative imports like 'from . import X' or 'from .. import Y'.

    Args:
        file_path: Path to the current Python file
        level: Number of dots in the relative import (1 for '.', 2 for '..', etc.)
        project_root: Root directory of the project

    Returns:
        Module name as it would appear in the project structure
    """
    # Get the directory of the current file
    current_dir = file_path.parent

    # Go up 'level' directories
    target_dir = current_dir
    for _ in range(level):
        target_dir = target_dir.parent

    # Convert to module path relative to project root
    try:
        relative = target_dir.relative_to(project_root)
        # Convert path to module notation (replace / with .)
        module_path = str(relative).replace(os.sep, '.')
        return module_path if module_path != '.' else ''
    except ValueError:
        # target_dir is not relative to project_root
        return ''


def is_local_module(module_name: str, project_root: Path, source_dirs: list) -> bool:
    """
    Check if a module is local to the project (not an external package).

    Args:
        module_name: Name of the module (e.g., 'pdf_processing', 'foundry')
        project_root: Root directory of the project
        source_dirs: List of source directories to check (e.g., ['src', 'scripts'])

    Returns:
        True if the module is local to the project
    """
    # Check if module exists as a directory or file in any source directory
    for source_dir in source_dirs:
        base_path = project_root / source_dir

        # Check if it's a package (directory with __init__.py)
        package_path = base_path / module_name
        if package_path.is_dir() and (package_path / '__init__.py').exists():
            return True

        # Check if it's a single file module
        file_path = base_path / f"{module_name}.py"
        if file_path.is_file():
            return True

        # Check nested modules (e.g., 'pdf_processing.split_pdf')
        if '.' in module_name:
            parts = module_name.split('.')
            nested_path = base_path / '/'.join(parts[:-1]) / f"{parts[-1]}.py"
            if nested_path.is_file():
                return True

    return False


def get_module_name(file_path: Path, project_root: Path) -> str:
    """
    Convert a file path to a module name.

    Examples:
        src/pdf_processing/split_pdf.py -> pdf_processing.split_pdf
        scripts/generate_scene_art.py -> scripts.generate_scene_art
    """
    relative = file_path.relative_to(project_root)
    # Remove .py extension
    module_path = str(relative.with_suffix(''))
    # Convert to dot notation
    return module_path.replace(os.sep, '.')


def build_dependency_graph(source_dir: Path, project_root: Path,
                          source_dirs: list) -> Dict[str, Set[str]]:
    """
    Build a dependency graph of all local Python imports.

    Returns:
        Dict mapping module names to sets of modules they import
    """
    graph = {}

    # Find all Python files
    py_files = list(source_dir.rglob('*.py'))

    for py_file in py_files:
        # Skip __pycache__ and hidden files
        if '__pycache__' in str(py_file) or py_file.name.startswith('.'):
            continue

        module_name = get_module_name(py_file, project_root)
        imports = extract_imports(py_file, project_root)

        # Filter to only local imports
        local_imports = {
            imp for imp in imports
            if is_local_module(imp, project_root, source_dirs)
        }

        if local_imports:  # Only add if there are local imports
            graph[module_name] = local_imports

    return graph


def sanitize_node_name(name: str) -> str:
    """
    Sanitize module name for Mermaid syntax.
    Replace dots with underscores and wrap in quotes if needed.
    """
    return name.replace('.', '_')


def group_modules_by_folder(modules: Set[str]) -> Dict[str, list]:
    """
    Group modules by their parent folder.

    Example:
        src.actors.parse_stat_blocks -> 'actors': ['src.actors.parse_stat_blocks', ...]
        src.foundry.client -> 'foundry': ['src.foundry.client', ...]
    """
    groups = {}

    for module in modules:
        parts = module.split('.')

        # Determine the group name
        if len(parts) == 1:
            # Top-level module (e.g., 'util', 'logging_config')
            group_name = 'root'
        elif parts[0] == 'src':
            # For src.X.Y, group by X (e.g., 'actors', 'foundry', 'pdf_processing')
            if len(parts) > 1:
                group_name = parts[1]
            else:
                group_name = 'src'
        else:
            # For other structures, use first part
            group_name = parts[0]

        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append(module)

    return groups


def generate_graphviz_dot(graph: Dict[str, Set[str]]) -> str:
    """
    Generate Graphviz DOT format from dependency graph with proper clustering.

    Format: A -> B means "B imports from A" (arrow points to dependent)
    """
    lines = ['digraph ImportDependencies {']
    lines.append('    // Graph settings')
    lines.append('    rankdir=LR;')
    lines.append('    bgcolor="#0f172a";')
    lines.append('    node [shape=box, style=filled, fontname="Arial", fontsize=14, height=0.5];')
    lines.append('    edge [color="#22d3ee", penwidth=3, arrowsize=1.2];')
    lines.append('    compound=true;')
    lines.append('    newrank=true;')
    lines.append('')

    # Collect all unique modules
    all_modules = set()
    for importer, imported_modules in graph.items():
        all_modules.add(importer)
        all_modules.update(imported_modules)

    # Group modules by folder
    groups = group_modules_by_folder(all_modules)

    # Color schemes for different groups
    colors = {
        'root': {'fill': '#dc2626', 'border': '#fca5a5'},
        'actors': {'fill': '#7c3aed', 'border': '#c4b5fd'},
        'foundry': {'fill': '#0891b2', 'border': '#67e8f9'},
        'pdf_processing': {'fill': '#ea580c', 'border': '#fdba74'}
    }

    # Create clusters for each group
    for group_idx, (group_name, modules) in enumerate(sorted(groups.items())):
        color_scheme = colors.get(group_name, colors['root'])
        group_label = group_name.replace('_', ' ').title()

        lines.append(f'    subgraph cluster_{group_idx} {{')
        lines.append(f'        label="{group_label}";')
        lines.append(f'        style=filled;')
        lines.append(f'        bgcolor="#1e293b";')
        lines.append(f'        color="{color_scheme["border"]}";')
        lines.append(f'        penwidth=3;')
        lines.append(f'        fontcolor="white";')
        lines.append(f'        fontsize=16;')
        lines.append('')

        # Define nodes within this cluster
        for module in sorted(modules):
            safe_name = sanitize_node_name(module)
            display_name = module.split('.')[-1]
            lines.append(f'        {safe_name} [label="{display_name}", fillcolor="{color_scheme["fill"]}", color="{color_scheme["border"]}", fontcolor="white", penwidth=2];')

        lines.append('    }')
        lines.append('')

    # Add edges
    for importer, imported_modules in sorted(graph.items()):
        safe_importer = sanitize_node_name(importer)
        for imported in sorted(imported_modules):
            safe_imported = sanitize_node_name(imported)
            # Arrow points FROM imported TO importer
            lines.append(f'    {safe_imported} -> {safe_importer};')

    lines.append('}')
    return '\n'.join(lines)


def generate_mermaid_erd(graph: Dict[str, Set[str]]) -> str:
    """
    Generate Mermaid flowchart from dependency graph with color-coded nodes.

    Format: A --> B means "A imports from B"
    """
    lines = ["%%{init: {'theme':'dark', 'themeVariables': { 'fontSize':'20px'}, 'flowchart': {'curve': 'basis', 'padding': 30, 'nodeSpacing': 100, 'rankSpacing': 150}}}%%"]
    lines.append("graph LR")

    # Define color schemes for different groups
    lines.append("    classDef rootClass fill:#dc2626,stroke:#fca5a5,stroke-width:4px,color:#fff,font-size:18px")
    lines.append("    classDef actorsClass fill:#7c3aed,stroke:#c4b5fd,stroke-width:4px,color:#fff,font-size:18px")
    lines.append("    classDef foundryClass fill:#0891b2,stroke:#67e8f9,stroke-width:4px,color:#fff,font-size:18px")
    lines.append("    classDef pdfClass fill:#ea580c,stroke:#fdba74,stroke-width:4px,color:#fff,font-size:18px")
    lines.append("")

    # Collect all unique modules
    all_modules = set()
    for importer, imported_modules in graph.items():
        all_modules.add(importer)
        all_modules.update(imported_modules)

    # Group modules by folder
    groups = group_modules_by_folder(all_modules)

    # Color mapping
    color_map = {
        'root': 'rootClass',
        'actors': 'actorsClass',
        'foundry': 'foundryClass',
        'pdf_processing': 'pdfClass'
    }

    # Track which nodes belong to which class
    node_classes = {}

    # Define all nodes with labels
    for group_name, modules in sorted(groups.items()):
        class_name = color_map.get(group_name, 'rootClass')
        for module in sorted(modules):
            safe_name = sanitize_node_name(module)
            display_name = module.split('.')[-1]
            # Add group prefix for clarity
            if group_name != 'root':
                label = f"{group_name.replace('_', ' ').title()}: {display_name}"
            else:
                label = display_name
            lines.append(f'    {safe_name}["{label}"]')
            node_classes[safe_name] = class_name

    lines.append("")

    # Add edges (A --> B means "A imports from B")
    for importer, imported_modules in sorted(graph.items()):
        safe_importer = sanitize_node_name(importer)
        for imported in sorted(imported_modules):
            safe_imported = sanitize_node_name(imported)
            # Arrow points FROM imported TO importer (showing dependency direction)
            lines.append(f'    {safe_imported} ==> {safe_importer}')

    lines.append("")

    # Apply classes to nodes
    for class_name in set(node_classes.values()):
        nodes_in_class = [node for node, cls in node_classes.items() if cls == class_name]
        if nodes_in_class:
            nodes_str = ','.join(nodes_in_class)
            lines.append(f'    class {nodes_str} {class_name}')

    # Style all links to be bright cyan and very thick for visibility
    lines.append("")
    lines.append("    linkStyle default stroke:#22d3ee,stroke-width:6px")

    return '\n'.join(lines)


def save_mermaid_markdown(mermaid_code: str, output_path: Path):
    """Save Mermaid diagram as markdown file."""
    content = f"""# Python Import Dependencies

This diagram shows the import relationships between Python modules in the project.

**Legend:** `B --> A` means "Module A imports from Module B" (arrow points from dependency to dependent)

```mermaid
{mermaid_code}
```

---
*Generated by `scripts/generate_import_diagram.py`*
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✓ Saved Mermaid markdown to: {output_path}")


def convert_to_png(markdown_path: Path, output_png_path: Path) -> bool:
    """
    Convert Mermaid diagram to PNG using mermaid-cli (mmdc).

    Returns True if successful, False otherwise.
    """
    import subprocess

    # Check if mmdc is installed
    try:
        subprocess.run(['mmdc', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\n⚠ Warning: mermaid-cli (mmdc) not found.")
        print("To generate PNG diagrams, install it with:")
        print("  npm install -g @mermaid-js/mermaid-cli")
        print("\nAlternatively, you can:")
        print("  1. Copy the markdown content from the .md file")
        print("  2. Paste it into https://mermaid.live")
        print("  3. Export as PNG from there")
        return False

    try:
        # Extract just the mermaid code (without markdown wrapper)
        with open(markdown_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract mermaid code block
        start = content.find('```mermaid\n') + len('```mermaid\n')
        end = content.find('```', start)
        mermaid_code = content[start:end].strip()

        # Create temp .mmd file
        temp_mmd = markdown_path.with_suffix('.mmd')
        with open(temp_mmd, 'w', encoding='utf-8') as f:
            f.write(mermaid_code)

        # Convert to PNG with higher resolution and better settings
        subprocess.run([
            'mmdc',
            '-i', str(temp_mmd),
            '-o', str(output_png_path),
            '-b', '#0f172a',  # Dark background
            '-w', '4800',  # Width in pixels (increased)
            '-H', '3200',  # Height in pixels (increased)
            '-s', '3'  # Scale factor (increased)
        ], check=True, capture_output=True)

        # Clean up temp file
        temp_mmd.unlink()

        print(f"✓ Saved PNG diagram to: {output_png_path}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"✗ Error converting to PNG: {e}")
        print(f"  stderr: {e.stderr.decode() if e.stderr else 'N/A'}")
        return False


def convert_dot_to_png(dot_path: Path, output_png_path: Path) -> bool:
    """
    Convert Graphviz DOT file to PNG.

    Returns True if successful, False otherwise.
    """
    import subprocess

    # Check if dot is installed
    try:
        subprocess.run(['dot', '-V'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\n⚠ Warning: Graphviz (dot) not found.")
        print("To generate PNG diagrams, install it with:")
        print("  macOS: brew install graphviz")
        print("  Ubuntu/Debian: sudo apt-get install graphviz")
        print("  Windows: choco install graphviz")
        return False

    try:
        # Convert DOT to PNG
        subprocess.run([
            'dot',
            '-Tpng',
            str(dot_path),
            '-o', str(output_png_path),
            '-Gdpi=300'  # High resolution
        ], check=True, capture_output=True)

        print(f"✓ Saved PNG diagram to: {output_png_path}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"✗ Error converting to PNG: {e}")
        print(f"  stderr: {e.stderr.decode() if e.stderr else 'N/A'}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Generate Mermaid ERD showing Python import dependencies'
    )
    parser.add_argument(
        '--source-dir',
        type=str,
        default='src',
        help='Source directory to analyze (default: src)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='output/diagrams',
        help='Output directory for diagrams (default: output/diagrams)'
    )
    parser.add_argument(
        '--include-scripts',
        action='store_true',
        help='Also analyze scripts/ directory'
    )
    parser.add_argument(
        '--no-png',
        action='store_true',
        help='Skip PNG generation (only create markdown)'
    )

    args = parser.parse_args()

    project_root = get_project_root()
    source_dir = project_root / args.source_dir
    output_dir = project_root / args.output_dir

    if not source_dir.exists():
        print(f"Error: Source directory not found: {source_dir}")
        sys.exit(1)

    # Determine which directories to consider as "local"
    source_dirs = [args.source_dir]
    if args.include_scripts:
        source_dirs.append('scripts')

    print(f"Analyzing Python imports in: {source_dir}")

    # Build dependency graph
    graph = build_dependency_graph(source_dir, project_root, source_dirs)

    if not graph:
        print("No local imports found!")
        sys.exit(0)

    print(f"Found {len(graph)} modules with local imports")

    # Generate Graphviz DOT diagram
    dot_code = generate_graphviz_dot(graph)

    # Save DOT file
    dot_path = output_dir / 'import_dependencies.dot'
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(dot_path, 'w', encoding='utf-8') as f:
        f.write(dot_code)
    print(f"✓ Saved Graphviz DOT to: {dot_path}")

    # Convert to PNG using Graphviz
    if not args.no_png:
        png_path = output_dir / 'import_dependencies.png'
        convert_dot_to_png(dot_path, png_path)

    # Also generate Mermaid for markdown viewing
    mermaid_code = generate_mermaid_erd(graph)
    markdown_path = output_dir / 'import_dependencies.md'
    save_mermaid_markdown(mermaid_code, markdown_path)

    print("\n✓ Done!")


if __name__ == '__main__':
    main()
