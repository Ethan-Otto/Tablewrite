
import fitz  # PyMuPDF
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logging_config import setup_logging

# Project root is three levels up from the script's directory (pdf_processing -> src -> root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = setup_logging(__name__)

def split_pdf_by_chapters():
    """
    This script splits the PDF file into chapters based on the table of contents,
    and saves them in a directory named after the PDF.
    """
    pdf_file_path = os.path.join(PROJECT_ROOT, "data", "pdfs", "Lost_Mine_of_Phandelver.pdf")
    base_output_dir = os.path.join(PROJECT_ROOT, "pdf_sections")
    
    # Get the PDF name for the subdirectory
    pdf_filename = os.path.splitext(os.path.basename(pdf_file_path))[0]
    output_dir = os.path.join(base_output_dir, pdf_filename)
    
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    doc = fitz.open(pdf_file_path)

    # Define the sections based on the extracted TOC
    sections = [
        (2, 5, "01_Introduction"),
        (6, 13, "02_Part_1_Goblin_Arrows"),
        (14, 26, "03_Part_2_Phandalin"),
        (27, 41, "04_Part_3_The_Spiders_Web"),
        (42, 50, "05_Part_4_Wave_Echo_Cave"),
        (51, 51, "06_Conclusion"),
        (52, 53, "07_Appendix_A_Magic_Items"),
        (54, 63, "08_Appendix_B_Monsters"),
        (64, len(doc), "09_Rules_Index"),
    ]

    logger.info(f"Splitting PDF into {len(sections)} sections in {output_dir}")

    for start_page, end_page, title in sections:
        start_page_0_indexed = start_page - 1
        end_page_0_indexed = end_page - 1

        if end_page_0_indexed >= len(doc):
            end_page_0_indexed = len(doc) - 1

        output_pdf_path = os.path.join(output_dir, f"{title}.pdf")
        new_doc = fitz.open()  # Create a new empty PDF
        new_doc.insert_pdf(doc, from_page=start_page_0_indexed, to_page=end_page_0_indexed)
        new_doc.save(output_pdf_path)
        new_doc.close()
        logger.debug(f"Created: {output_pdf_path}")

    doc.close()
    logger.info("PDF splitting complete")

if __name__ == "__main__":
    split_pdf_by_chapters()
