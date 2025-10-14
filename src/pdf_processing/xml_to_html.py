import os
import xml.etree.ElementTree as ET
from datetime import datetime
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logging_config import setup_logging

# Project root is three levels up from the script's directory (pdf_processing -> src -> root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = setup_logging(__name__)

def xml_to_html_content(xml_path):
    """Converts the content of an XML file to an HTML string."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        html_content = ""

        for elem in root.iter():
            if elem.tag == 'title':
                html_content += f"<h1>{elem.text}</h1>\n"
            elif elem.tag == 'heading':
                html_content += f"<h2>{elem.text}</h2>\n"
            elif elem.tag == 'paragraph':
                html_content += f"<p>{elem.text}</p>\n"
            elif elem.tag == 'list':
                html_content += "<ul>\n"
                for item in elem.findall('item'):
                    html_content += f"  <li>{item.text}</li>\n"
                html_content += "</ul>\n"
        
        return html_content
    except ET.ParseError as e:
        logger.error(f"Error parsing {xml_path}: {e}")
        return f"<h2>Error parsing {os.path.basename(xml_path)}</h2><p>{e}</p>"

def generate_html_page(xml_path, nav_links, output_path):
    """Generates a full HTML page from an XML file."""
    html_content = xml_to_html_content(xml_path)
    
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
        h1, h2 { color: #333; }
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