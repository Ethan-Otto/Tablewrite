import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logging_config import setup_logging

# Project root is three levels up from the script's directory (pdf_processing -> src -> root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = setup_logging(__name__)

def convert_markdown_to_html(text):
    """
    Converts Markdown formatting to HTML tags.
    - **text** → <strong>text</strong>
    - *text* → <em>text</em>
    """
    if not text:
        return text

    # Convert bold first (to avoid conflicts with italic)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Then convert italic
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)

    return text

def xml_to_html_content(xml_path, include_footers=False):
    """
    Converts the content of an XML file to an HTML string.

    Args:
        xml_path: Path to the XML file
        include_footers: If False, excludes <footer> and <header> tags from output (default: False)
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        html_content = ""

        # Process elements recursively to preserve structure
        def process_element(elem, depth=0):
            result = ""

            # Skip footer and header if include_footers is False
            if not include_footers and elem.tag in ['footer', 'header']:
                return ""

            # Handle different element types
            # Semantic heading tags (Chapter > Section > Subsection hierarchy)
            if elem.tag == 'chapter_title':
                # Chapter title -> h1
                text = convert_markdown_to_html(elem.text if elem.text else "")
                result += f"<h1>{text}</h1>\n"
            elif elem.tag == 'title':
                # General title -> h1
                text = convert_markdown_to_html(elem.text if elem.text else "")
                result += f"<h1>{text}</h1>\n"
            elif elem.tag == 'section':
                # Section is a container - process children
                # If it has direct text, output as h2
                if elem.text and elem.text.strip():
                    text = convert_markdown_to_html(elem.text.strip())
                    result += f"<h2>{text}</h2>\n"
                # Process all children
                for child in elem:
                    result += process_element(child, depth + 1)
            elif elem.tag == 'subsection':
                # Subsection is a container - process children
                # If it has direct text, output as h3
                if elem.text and elem.text.strip():
                    text = convert_markdown_to_html(elem.text.strip())
                    result += f"<h3>{text}</h3>\n"
                # Process all children
                for child in elem:
                    result += process_element(child, depth + 1)
            elif elem.tag == 'subsubsection':
                # Sub-subsection is a container - process children
                # If it has direct text, output as h4
                if elem.text and elem.text.strip():
                    text = convert_markdown_to_html(elem.text.strip())
                    result += f"<h4>{text}</h4>\n"
                # Process all children
                for child in elem:
                    result += process_element(child, depth + 1)
            elif elem.tag == 'p':
                text = convert_markdown_to_html(elem.text if elem.text else "")
                result += f"<p>{text}</p>\n"
            elif elem.tag == 'list':
                result += "<ul>\n"
                for item in elem.findall('item'):
                    item_text = convert_markdown_to_html(item.text if item.text else "")
                    result += f"  <li>{item_text}</li>\n"
                result += "</ul>\n"
            elif elem.tag == 'boxed_text':
                result += '<div class="boxed-text">\n'
                for child in elem:
                    result += process_element(child, depth + 1)
                result += '</div>\n'
            elif elem.tag == 'table':
                result += '<table border="1">\n'
                for child in elem:
                    result += process_element(child, depth + 1)
                result += '</table>\n'
            elif elem.tag == 'table_row':
                result += '  <tr>\n'
                for child in elem:
                    result += process_element(child, depth + 1)
                result += '  </tr>\n'
            elif elem.tag == 'table_cell':
                text = convert_markdown_to_html(elem.text if elem.text else "")
                result += f'    <td>{text}</td>\n'
            elif elem.tag == 'definition_list':
                result += '<dl>\n'
                for child in elem:
                    result += process_element(child, depth + 1)
                result += '</dl>\n'
            elif elem.tag == 'definition_item':
                for child in elem:
                    result += process_element(child, depth + 1)
            elif elem.tag == 'term':
                text = convert_markdown_to_html(elem.text if elem.text else "")
                result += f'  <dt>{text}</dt>\n'
            elif elem.tag == 'definition':
                text = convert_markdown_to_html(elem.text if elem.text else "")
                result += f'  <dd>{text}</dd>\n'
            # Skip structural/metadata tags that shouldn't be rendered
            elif elem.tag in ['page', 'footer', 'header', 'page_number']:
                for child in elem:
                    result += process_element(child, depth + 1)

            return result

        # Process all children of root
        for child in root:
            html_content += process_element(child)

        return html_content
    except ET.ParseError as e:
        logger.error(f"Error parsing {xml_path}: {e}")
        return f"<h2>Error parsing {os.path.basename(xml_path)}</h2><p>{e}</p>"

def generate_html_page(xml_path, nav_links, output_path, include_footers=False):
    """
    Generates a full HTML page from an XML file.

    Args:
        xml_path: Path to the XML file
        nav_links: List of (text, href) tuples for navigation
        output_path: Path to write the HTML file
        include_footers: If False, excludes <footer> and <header> tags from output (default: False)
    """
    html_content = xml_to_html_content(xml_path, include_footers=include_footers)
    
    nav_html = "<nav>\n"
    for link_text, link_href in nav_links:
        nav_html += f'  <a href="{link_href}">{link_text}</a>\n'
    nav_html += "</nav>\n"

    # Basic CSS for a clean look
    css_style = """<style>
        body { font-family: sans-serif; line-height: 1.6; margin: 2em; }
        nav { background-color: #f2f2f2; padding: 1em; }
        nav a { text-decoration: none; color: #333; padding: 0.5em 1em; }
        nav a:hover { background-color: #ddd; }
        h1, h2, h3, h4 { color: #333; }
        .boxed-text { background-color: #f9f9f9; border: 2px solid #ddd; padding: 1em; margin: 1em 0; }
        table { border-collapse: collapse; margin: 1em 0; }
        table td { padding: 0.5em; }
        dl { margin: 1em 0; }
        dt { font-weight: bold; margin-top: 0.5em; }
        dd { margin-left: 2em; margin-bottom: 0.5em; }
    </style>"""

    full_html = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{os.path.splitext(os.path.basename(xml_path))[0]}</title>
        {css_style}
    </head>
    <body>
        {nav_html}
        <main>
            {html_content}
        </main>
    </body>
    </html>"""
    
    with open(output_path, "w") as f:
        f.write(full_html)
    logger.debug(f"Successfully created HTML file: {output_path}")

def main(input_dir, output_dir):
    """Main function to convert all XML files in a directory to HTML."""
    xml_files = sorted([f for f in os.listdir(input_dir) if f.endswith(".xml")])
    
    os.makedirs(output_dir, exist_ok=True)

    nav_links = []
    for xml_file in xml_files:
        link_text = os.path.splitext(xml_file)[0]
        link_href = f"{link_text}.html"
        nav_links.append((link_text, link_href))

    for xml_file in xml_files:
        xml_path = os.path.join(input_dir, xml_file)
        logger.info(f"Processing {xml_path}")
        html_filename = f"{os.path.splitext(xml_file)[0]}.html"
        output_path = os.path.join(output_dir, html_filename)
        generate_html_page(xml_path, nav_links, output_path)

if __name__ == "__main__":
    runs_dir = os.path.join(PROJECT_ROOT, "output", "runs")
    latest_run = sorted(os.listdir(runs_dir))[-1]
    latest_run_docs_dir = os.path.join(runs_dir, latest_run, "documents")
    
    html_output_dir = os.path.join(latest_run_docs_dir, "html")

    main(latest_run_docs_dir, html_output_dir)