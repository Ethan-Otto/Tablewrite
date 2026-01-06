import os
import fitz  # PyMuPDF

from config import PROJECT_ROOT
from logging_config import setup_logging

logger = setup_logging(__name__)

def get_toc():
    """
    This script extracts the table of contents from the PDF file.
    """
    pdf_file_path = os.path.join(PROJECT_ROOT, "data", "pdfs", "Lost_Mine_of_Phandelver.pdf")
    doc = fitz.open(pdf_file_path)
    toc = doc.get_toc()
    doc.close()

    if toc:
        logger.info("Table of Contents:")
        for item in toc:
            level, title, page = item
            logger.info(f"  Level {level}: {title} (Page {page})")
    else:
        logger.info("No table of contents found in the PDF")

if __name__ == "__main__":
    get_toc()

