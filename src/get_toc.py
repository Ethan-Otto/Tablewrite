import os
import fitz  # PyMuPDF

# Project root is two levels up from the script's directory (src -> root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_toc():
    """
    This script extracts the table of contents from the PDF file.
    """
    pdf_file_path = os.path.join(PROJECT_ROOT, "data", "pdfs", "Lost_Mine_of_Phandelver.pdf")
    doc = fitz.open(pdf_file_path)
    toc = doc.get_toc()
    doc.close()

    if toc:
        print("Table of Contents:")
        for item in toc:
            level, title, page = item
            print(f"  Level {level}: {title} (Page {page})")
    else:
        print("No table of contents found in the PDF.")

if __name__ == "__main__":
    get_toc()