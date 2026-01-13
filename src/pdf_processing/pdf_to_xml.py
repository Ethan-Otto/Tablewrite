import os
from datetime import datetime
import concurrent.futures
import fitz  # PyMuPDF
import xml.etree.ElementTree as ET
import re
from typing import List, Tuple, Optional
import tempfile
import time
import io
from PIL import Image
import pytesseract
import json
from collections import Counter

from config import PROJECT_ROOT
from logging_config import setup_logging, get_run_logger
from util.gemini import GeminiAPI, GeminiFileContext
from pdf_processing.valid_xml_tags import APPROVED_XML_TAGS, get_approved_tags_text
from models.xml_document import XMLDocument

# Initialize logger (will be reconfigured in main() with run directory)
logger = setup_logging(__name__)

# Global Gemini API instance
gemini_api = None

def validate_xml_tags(xml_content: str, page_number: int = None) -> Tuple[bool, List[str]]:
    """
    Validates that all tags in the XML content are in the approved list.
    Returns (is_valid, list_of_unknown_tags).
    """
    try:
        root = ET.fromstring(xml_content)
        unknown_tags = set()

        for elem in root.iter():
            if elem.tag not in APPROVED_XML_TAGS:
                unknown_tags.add(elem.tag)

        if unknown_tags:
            page_info = f" on page {page_number}" if page_number else ""
            logger.error(f"Unknown XML tags found{page_info}: {', '.join(sorted(unknown_tags))}")
            return False, list(unknown_tags)

        return True, []
    except ET.ParseError as e:
        logger.error(f"XML parsing error during validation: {e}")
        return False, ["PARSE_ERROR"]

def validate_xml_with_model(xml_content: str) -> Tuple[bool, Optional[str]]:
    """
    Validates XML content by attempting to parse it with the XMLDocument model.
    This catches schema errors early before downstream processing.

    Args:
        xml_content: The XML content string to validate

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if XML is valid and can be parsed by XMLDocument model
        - error_message: None if valid, otherwise contains error details
    """
    try:
        # Attempt to parse with XMLDocument model
        XMLDocument.from_xml(xml_content)
        logger.debug("XML content successfully validated with XMLDocument model")
        return True, None
    except ET.ParseError as e:
        error_msg = f"XML parsing error: {str(e)}"
        logger.error(f"XMLDocument validation failed: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"XMLDocument model validation error: {str(e)}"
        logger.error(f"XMLDocument validation failed: {error_msg}")
        return False, error_msg

def configure_gemini():
    """Configures the Gemini API with the API key from environment variables."""
    global gemini_api
    gemini_api = GeminiAPI()
    return gemini_api

def sanitize_xml_element_name(name: str) -> str:
    """
    Sanitizes a string to be a valid XML element name.
    XML element names must start with a letter or underscore, not a digit.
    """
    # If the name starts with a digit, prefix with 'Chapter_'
    if name and name[0].isdigit():
        return f"Chapter_{name}"
    return name

def count_words(text: str) -> int:
    """Counts the words in a given string, excluding common XML tags."""
    # Remove XML tags from the text
    text_no_tags = re.sub(r'<[^>]+>', '', text)
    words = re.findall(r'\b\w+\b', text_no_tags)
    return len(words)

def get_word_frequencies(text: str) -> dict:
    """Calculates the frequency of each word in a given string, excluding common XML tags."""
    # Remove XML tags from the text
    text_no_tags = re.sub(r'<[^>]+>', '', text)
    words = re.findall(r'\b\w+\b', text_no_tags.lower())
    return Counter(words)

def verify_and_correct_xml(xml_content: str, original_text: str, chapter_name: str, log_dir: str) -> str:
    """
    Uses Gemini to verify the XML content against the original text and correct it if necessary.
    """
    logger.info(f"Verifying and correcting XML for chapter: {chapter_name}...")
    try:
        prompt = f"""
        Please verify that the following XML content is a faithful and complete representation of the original text.
        If there are any discrepancies, please correct the XML.
        The corrected output should be only the valid XML, starting with the <{chapter_name}> tag.

        Original Text:
        ---
        {original_text}
        ---

        XML Content:
        ---
        {xml_content}
        ---
        """

        response = gemini_api.generate_content(prompt)
        
        if response and response.text:
            # Use regex to find the chapter block, stripping everything else
            escaped_chapter = re.escape(chapter_name)
            chapter_pattern = rf'<{escaped_chapter}(?:\s[^>]*)?>.*?</{escaped_chapter}>'
            match = re.search(chapter_pattern, response.text, re.DOTALL)
            if not match:
                raise ValueError("Verification failed: Could not find valid XML in response.")
            
            corrected_xml = match.group(0)
            ET.fromstring(corrected_xml)  # Validate the corrected XML
            
            corrected_xml_path = os.path.join(log_dir, f"{chapter_name}_corrected.xml")
            with open(corrected_xml_path, "w") as f:
                f.write(corrected_xml)
            logger.info(f"Successfully verified and corrected XML for chapter: {chapter_name}.")
            return corrected_xml
        else:
            raise ValueError("Verification failed: No response from model.")

    except Exception as e:
        logger.error(f"Failed to verify and correct XML for chapter {chapter_name}: {e}")
        return xml_content # Return the original XML if correction fails


def correct_xml_with_gemini(malformed_xml: str, original_text: str, page_number: int, log_dir: str) -> str:
    """
    Uses Gemini to correct malformed XML, using the original text as a reference.
    """
    logger.info(f"Attempting to correct malformed XML for page {page_number} with Gemini...")
    try:
        prompt = f"""
        The following XML is malformed. Please correct it based on the original text provided below.
        Ensure all tags are properly closed and the structure is valid.
        Do not add any new content or alter the existing text.
        The corrected output should be only the valid XML, starting with the <page> tag.

        Original Text:
        ---
        {original_text}
        ---

        Malformed XML:
        ---
        {malformed_xml}
        ---
        """

        response = gemini_api.generate_content(prompt)
        
        if response and response.text:
            # Use regex to find the <page> block, stripping everything else
            match = re.search(r'<page(?:\s[^>]*)?>.*?</page>', response.text, re.DOTALL)
            if not match:
                raise ValueError("Correction failed: Could not find valid <page> XML in response.")
            
            corrected_xml = match.group(0)
            ET.fromstring(corrected_xml)  # Validate the corrected XML
            
            corrected_xml_path = os.path.join(log_dir, "pages", f"page_{page_number}_corrected.xml")
            with open(corrected_xml_path, "w") as f:
                f.write(corrected_xml)
            logger.info(f"Successfully corrected XML for page {page_number}.")
            return corrected_xml
        else:
            raise ValueError("Correction failed: No response from model.")

    except Exception as e:
        logger.error(f"Failed to correct XML for page {page_number}: {e}")
        return f"<page><error>Failed to correct malformed XML. Error: {e}</error></page>"

def is_text_legible(text: str) -> bool:
    """
    Checks if a string is likely to be legible text.
    Falls back if more than 10 words are longer than 20 characters.
    """
    long_words = [word for word in text.split() if len(word) > 20]
    if len(long_words) > 10:
        logger.debug(f"Legibility check failed: Found {len(long_words)} words longer than 20 characters.")
        return False
    return True

def get_legible_text_from_page(page_bytes: bytes, page_number: int, log_dir: str) -> Tuple[str, str]:
    """
    Tries to extract legible text from a PDF page, first from embedded text,
    then falling back to local OCR if the embedded text seems corrupted.
    """
    embedded_text = ""
    # 1. Try embedded text
    try:
        with fitz.open("pdf", page_bytes) as pdf_page_doc:
            embedded_text = pdf_page_doc[0].get_text()
            embedded_output_path = os.path.join(log_dir, "pages", f"page_{page_number}_embedded.txt")
            with open(embedded_output_path, "w") as f:
                f.write(embedded_text)

            if is_text_legible(embedded_text):
                logger.debug(f"Page {page_number}: Using embedded text.")
                return embedded_text, "embedded"
            else:
                logger.warning(f"Page {page_number}: Embedded text seems corrupted. Falling back to OCR.")
    except Exception as e:
        logger.warning(f"Could not extract embedded text from page {page_number}: {e}. Falling back to OCR.")

    # 2. Fallback to local OCR
    try:
        with fitz.open("pdf", page_bytes) as pdf_page_doc:
            pix = pdf_page_doc[0].get_pixmap()
            img_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_bytes))
            ocr_text = pytesseract.image_to_string(image)
            ocr_output_path = os.path.join(log_dir, "pages", f"page_{page_number}_ocr.txt")
            os.makedirs(os.path.dirname(ocr_output_path), exist_ok=True)
            with open(ocr_output_path, "w") as f:
                f.write(ocr_text)
            
            logger.debug(f"Page {page_number}: Using OCR text.")
            return ocr_text, "ocr"
    except Exception as e:
        logger.error(f"Local OCR failed for page {page_number}: {e}")
        return embedded_text, "ocr_failed"

def get_xml_for_page(page_info: tuple) -> str:
    """
    Converts a single PDF page to XML, using a robust text extraction method.
    Now uses a pre-uploaded PDF file to avoid repeated uploads.
    """
    page_bytes, page_number, log_dir, uploaded_pdf_file = page_info
    display_name = f"page_{page_number}"
    max_retries = 3
    backoff_factor = 2

    page_pdf_path = os.path.join(log_dir, "pages", f"{display_name}.pdf")
    with open(page_pdf_path, "wb") as f:
        f.write(page_bytes)

    legible_text, text_source = get_legible_text_from_page(page_bytes, page_number, log_dir)
    pdf_word_count = count_words(legible_text)

    for attempt in range(max_retries):
        try:
            logger.debug(f"Processing {display_name} from uploaded PDF (Attempt {attempt + 1})...")

            # Get approved tags list for prompt
            approved_tags_text = get_approved_tags_text()

            prompt = f"""
            You are a highly skilled document analyst. Your task is to convert page {page_number} of the provided Dungeons & Dragons module PDF into a well-structured XML format.

            IMPORTANT: Process ONLY page {page_number} of the PDF. Ignore all other pages.

            ## APPROVED XML TAGS
            You MUST use ONLY the following XML tags. Using any other tags will result in an error:

            {approved_tags_text}

            ## FORMATTING RULES
            - The root element must be `<page>`
            - Do not wrap the XML in markdown fences like ```xml
            - **PRESERVE ALL FORMATTING from the source PDF:**
              - If text is italicized in the PDF, use Markdown: `*italic text*`
              - If text is bold in the PDF, use Markdown: `**bold text**`
              - If text is both bold AND italic, use: `***bold italic***`
            - All XML tags must be properly closed
            - Escape special characters (&, <, >)
            - Preserve the semantic structure of the document

            **CRITICAL**: Do NOT omit italics or bold formatting. Every word that appears italic or bold in the PDF must be preserved in the XML output using Markdown syntax.

            ## DISTINGUISHING HEADINGS FROM BOLD TEXT
            **CRITICAL**: `<section>`, `<subsection>`, and `<subsubsection>` tags should ONLY be used for actual headings.

            A heading is text that is:
            1. **Visually larger** than normal paragraph text (increased font size)
            2. Usually bold or emphasized
            3. Stands alone on its own line
            4. Introduces a new topic or section

            **DO NOT use heading tags for:**
            - Bold text that is the SAME SIZE as normal text (use `<p>**bold text**</p>` instead)
            - Labels or terms in definition lists (use `<term>` instead)
            - Emphasis within paragraphs (use **bold** markdown)

            **Example of correct usage:**
            - Large heading text → `<section>Combat Encounters</section>`
            - Bold text same size as paragraph → `<p>**Important:** Do not forget this rule.</p>`
            - NPC names in lists → `<term>Toblen Stonehill</term>` not `<subsection>`

            ## HEADING HIERARCHY AND CONTEXT
            **CRITICAL**: Font size alone does NOT determine hierarchy level. A heading can be LARGER than normal text but still be a subsection or subsubsection based on CONTEXT.

            **Consider the semantic structure:**
            - If a heading introduces a topic WITHIN an existing section, it's a `<subsection>` (even if larger than body text)
            - If a heading introduces a detail WITHIN a subsection, it's a `<subsubsection>` (even if larger than body text)
            - Use `<section>` only for major topic changes or new top-level areas

            **Example:**
            If you're processing content about "Cragmaw Hideout" (a section), and you encounter:
            - "1. Cave Mouth" (larger text) → This is a `<subsection>` (a location within the hideout), NOT a new `<section>`
            - "Treasure" (larger text under "1. Cave Mouth") → This is a `<subsubsection>` (detail within the location)

            **Read the full page context** to understand where you are in the document structure. Don't promote headings to higher levels just because they're visually prominent.

            ## IDENTIFYING HEADERS AND FOOTERS
            - **Footers** are typically small text at the bottom of the page (page numbers, chapter names, copyright info)
            - **Headers** are typically text at the top of the page (chapter titles, section names)
            - If text appears in the same position on multiple pages with same/similar content, it's likely a header or footer
            - Tag repeating bottom text as `<footer>`, repeating top text as `<header>`
            - Page numbers should be tagged as `<page_number>` within the footer or header

            ## STAT BLOCK TAGGING
            **CRITICAL**: Tag all D&D 5e stat blocks with: `<stat_block name="Creature Name">raw text</stat_block>`

            - **Preserve COMPLETE original stat block text** inside the tag
            - Do NOT parse or structure the stat block - keep it as raw text
            - Stat blocks are typically boxed sections with creature stats:
              - Name and type/size (e.g., "GOBLIN / Small humanoid")
              - Armor Class, Hit Points, Speed
              - Ability scores (STR, DEX, CON, INT, WIS, CHA)
              - Challenge rating
              - Traits and actions

            **Example stat block tagging:**
            ```xml
            <stat_block name="Goblin">
            GOBLIN
            Small humanoid (goblinoid), neutral evil

            Armor Class 15 (leather armor, shield)
            Hit Points 7 (2d6)
            Speed 30 ft.

            STR     DEX     CON     INT     WIS     CHA
            8 (-1)  14 (+2) 10 (+0) 10 (+0) 8 (-1)  8 (-1)

            Challenge 1/4 (50 XP)

            Nimble Escape. The goblin can take the Disengage or Hide action...

            ACTIONS
            Scimitar. Melee Weapon Attack: +4 to hit...
            </stat_block>
            ```

            ## EXAMPLES
            - Headings (semantic): `<chapter_title>Chapter Title</chapter_title>`, `<section>Section Title</section>`, `<subsection>Subsection Title</subsection>`
            - Paragraphs: `<p>This is a paragraph with **bold** and *italic* text.</p>`
            - Lists: `<list><item>Item 1</item><item>Item 2</item></list>`
            - Boxed text: `<boxed_text><p>Special content in a box</p></boxed_text>`
            - Tables: `<table><table_row><table_cell>Cell 1</table_cell><table_cell>Cell 2</table_cell></table_row></table>`
            - Definition lists: `<definition_list><definition_item><term>Term</term><definition>Definition text</definition></definition_item></definition_list>`

            Do not include any text, comments, or data outside the root `<page>` element.
            """

            logger.debug(f"Generating XML for {display_name}")
            # Use the pre-uploaded file
            response = gemini_api.generate_content(prompt, uploaded_pdf_file)

            cleaned_xml = ""
            if response and response.text:
                raw_response_text = response.text
                raw_output_path = os.path.join(log_dir, "pages", f"{display_name}_attempt_{attempt + 1}_raw.xml")
                with open(raw_output_path, "w") as f:
                    f.write(raw_response_text)

                # Use regex to find the <page> block, stripping everything else
                match = re.search(r'<page(?:\s[^>]*)?>.*?</page>', raw_response_text, re.DOTALL)
                if not match:
                    raise ValueError("Could not find valid <page> XML in response.")

                cleaned_response_text = match.group(0)

                temp_xml = re.sub(r'<i>(.*?)</i>', r'*\1*', cleaned_response_text, flags=re.DOTALL)
                temp_xml = re.sub(r'<b>(.*?)</b>', r'**\1**', temp_xml, flags=re.DOTALL)
                temp_xml = re.sub(r'<italic>(.*?)</italic>', r'*\1*', temp_xml, flags=re.DOTALL)

                try:
                    ET.fromstring(temp_xml)  # Validate the cleaned XML
                    cleaned_xml = temp_xml
                except ET.ParseError as e:
                    logger.warning(f"Malformed XML detected on page {page_number}: {e}")
                    cleaned_xml = correct_xml_with_gemini(temp_xml, legible_text, page_number, log_dir)

                # Validate XML tags
                is_valid, unknown_tags = validate_xml_tags(cleaned_xml, page_number)
                if not is_valid:
                    raise ValueError(f"Unknown XML tags detected on page {page_number}: {', '.join(unknown_tags)}. Only approved tags are allowed.")

            else:
                raise ValueError("Failed to generate content.")

            if pdf_word_count >= 30:
                xml_word_count = count_words(cleaned_xml)
                difference = abs(pdf_word_count - xml_word_count)
                if pdf_word_count > 0:
                    percentage_diff = (difference / pdf_word_count) * 100
                    if percentage_diff > 15:
                        raise ValueError(f"Word count mismatch ({text_source}) for page {page_number} is over 15% ({percentage_diff:.2f}%).")
                elif xml_word_count > 0:
                    raise ValueError(f"Word count mismatch ({text_source}): PDF has 0 words, XML has {xml_word_count} words.")

            page_xml_path = os.path.join(log_dir, "pages", f"{display_name}.xml")
            with open(page_xml_path, "w") as f:
                f.write(cleaned_xml)

            return cleaned_xml

        except Exception as e:
            logger.warning(f"An error occurred on attempt {attempt + 1} for page {page_number}: {e}")
            if "Word count mismatch" in str(e):
                # Generate and save word frequency analysis only for word count errors
                pdf_word_freq = get_word_frequencies(legible_text)
                xml_word_freq = get_word_frequencies(cleaned_xml)

                pdf_freq_log_path = os.path.join(log_dir, "pages", f"{display_name}_pdf_word_frequencies.json")
                with open(pdf_freq_log_path, "w") as f:
                    json.dump(pdf_word_freq, f, indent=4)
                logger.debug(f"PDF word frequency analysis for page {page_number} saved to {pdf_freq_log_path}")

                xml_freq_log_path = os.path.join(log_dir, "pages", f"{display_name}_xml_word_frequencies.json")
                with open(xml_freq_log_path, "w") as f:
                    json.dump(xml_word_freq, f, indent=4)
                logger.debug(f"XML word frequency analysis for page {page_number} saved to {xml_freq_log_path}")

            if attempt < max_retries - 1:
                sleep_time = backoff_factor ** attempt
                logger.warning(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                logger.error(f"Failed to process page {page_number} after {max_retries} attempts.")
                error_xml_root = ET.Element("page")
                error_tag = ET.SubElement(error_xml_root, "error")
                error_tag.text = f"Failed to process after multiple retries. Last error: {e}"
                return ET.tostring(error_xml_root, encoding='unicode')

    return "<page><error>An unexpected error occurred in the processing loop.</error></page>"

def process_chapter(pdf_path: str, output_xml_path: str, base_log_dir: str) -> List[str]:
    """
    Orchestrates the page-by-page conversion and merges them into a single XML file.
    If any page fails, the entire chapter is marked as failed.
    Now optimized to upload the PDF once and reuse it for all pages.
    """
    chapter_name = os.path.splitext(os.path.basename(pdf_path))[0]
    log_dir = os.path.join(base_log_dir, chapter_name)
    os.makedirs(os.path.join(log_dir, "pages"), exist_ok=True)
    page_errors = []

    logger.info(f"Starting processing for chapter: {chapter_name} ---")
    pdf_document = fitz.open(pdf_path)
    page_infos = []
    pdf_text = ""
    for page_num in range(len(pdf_document)):
        doc = fitz.open()
        doc.insert_pdf(pdf_document, from_page=page_num, to_page=page_num)
        page_bytes = doc.write()
        page_text, _ = get_legible_text_from_page(page_bytes, page_num + 1, log_dir)
        pdf_text += page_text
        doc.close()
        # Don't add uploaded_file yet - will add it after upload
        page_infos.append((page_bytes, page_num + 1, log_dir, None))
    pdf_document.close()

    # Upload the full PDF once and reuse for all pages
    logger.info(f"Uploading full PDF for chapter: {chapter_name}")
    with GeminiFileContext(gemini_api, pdf_path, f"chapter_{chapter_name}") as uploaded_pdf:
        # Update all page_infos with the uploaded file
        page_infos = [(pb, pn, ld, uploaded_pdf) for pb, pn, ld, _ in page_infos]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            page_xmls = list(executor.map(get_xml_for_page, page_infos))

    # Sanitize chapter name for use as XML element name
    xml_element_name = sanitize_xml_element_name(chapter_name)
    chapter_root = ET.Element(xml_element_name)
    logger.info(f"Merging {len(page_xmls)} XML pages into a single document...")
    has_page_errors = False
    for i, page_xml_str in enumerate(page_xmls):
        try:
            page_root = ET.fromstring(page_xml_str)
            page_root.set('number', str(i + 1))
            chapter_root.append(page_root)
            if page_root.find('error') is not None:
                has_page_errors = True
                error_message = page_root.find('error').text
                page_errors.append(f"Page {i + 1}: {error_message}")
        except ET.ParseError as e:
            has_page_errors = True
            page_num = i + 1
            error_msg = f"Page {page_num}: Failed to parse XML. Error: {e}"
            logger.warning(f" {error_msg}")
            page_errors.append(error_msg)
            error_page = ET.SubElement(chapter_root, "page", {'number': str(page_num), 'parse_error': 'true'})
            error_message_tag = ET.SubElement(error_page, "error")
            error_message_tag.text = "Failed to parse XML content from Gemini."
            page_xml_path = os.path.join(log_dir, "pages", f"page_{page_num}_parse_error.xml")
            with open(page_xml_path, "w") as f:
                f.write(page_xml_str)

    if has_page_errors:
        raise Exception(f"Chapter failed due to page errors: {', '.join(page_errors)}")

    try:
        ET.indent(chapter_root)
    except AttributeError:
        pass
    final_xml_content = ET.tostring(chapter_root, encoding='unicode')

    with open(os.path.join(log_dir, "final_unverified.xml"), "w") as f:
        f.write(final_xml_content)

    try:
        verify_final_word_count(pdf_path, final_xml_content, log_dir)
    except ValueError as e:
        if "Final word count mismatch" in str(e):
            final_xml_content = verify_and_correct_xml(final_xml_content, pdf_text, xml_element_name, log_dir)
            verify_final_word_count(pdf_path, final_xml_content, log_dir)

    # Validate XML with XMLDocument model before saving
    logger.info(f"Validating final XML with XMLDocument model for chapter: {xml_element_name}")
    is_valid, error_msg = validate_xml_with_model(final_xml_content)
    if not is_valid:
        # Log to dedicated validation errors file
        error_file = os.path.join(log_dir, "validation_errors.txt")
        with open(error_file, 'a') as f:
            f.write(f"\n\n=== {xml_element_name} ===\n")
            f.write(f"Validation Error: {error_msg}\n")
            f.write(f"XML Content Preview:\n{final_xml_content[:1000]}\n")
        raise Exception(f"XMLDocument validation failed for chapter {xml_element_name}: {error_msg}")

    with open(output_xml_path, "w") as f:
        f.write(final_xml_content)
    logger.info(f"Successfully created final merged XML file: {output_xml_path}")
    return page_errors

def verify_final_word_count(pdf_path: str, final_xml_content: str, log_dir: str):
    """
    Compares the word count of the source PDF and the generated XML content.
    """
    logger.info("Verifying final word count...")
    # This function now uses the more robust get_legible_text_from_page for its source
    pdf_document = fitz.open(pdf_path)
    pdf_text = ""
    page_log_dir = os.path.join(log_dir, "final_verification_pages")
    os.makedirs(page_log_dir, exist_ok=True)

    for page_num in range(len(pdf_document)):
        doc = fitz.open()
        doc.insert_pdf(pdf_document, from_page=page_num, to_page=page_num)
        page_text, _ = get_legible_text_from_page(doc.write(), page_num + 1, page_log_dir)
        pdf_text += page_text
        doc.close()
    pdf_document.close()
    pdf_word_count = count_words(pdf_text)

    xml_word_count = count_words(final_xml_content)

    if pdf_word_count == 0:
        if xml_word_count > 0:
             raise ValueError("PDF word count is 0, but XML has content.")
        logger.info("Both PDF and XML appear to have no text content. Skipping verification.")
        return

    difference = abs(pdf_word_count - xml_word_count)
    percentage_diff = (difference / pdf_word_count) * 100 if pdf_word_count > 0 else 0

    logger.info(f"PDF word count (from legible text): {pdf_word_count}")
    logger.info(f"Final XML word count: {xml_word_count}")
    logger.info(f"Difference: {difference} words ({percentage_diff:.2f}%)")

    if percentage_diff > 15: # Loosen final threshold slightly
        # Generate and save word frequency analysis in two separate files
        pdf_word_freq = get_word_frequencies(pdf_text)
        xml_word_freq = get_word_frequencies(final_xml_content)
        chapter_name = os.path.splitext(os.path.basename(pdf_path))[0]

        pdf_freq_log_path = os.path.join(log_dir, f"{chapter_name}_final_pdf_word_frequencies.json")
        with open(pdf_freq_log_path, "w") as f:
            json.dump(pdf_word_freq, f, indent=4)
        logger.debug(f"Final PDF word frequency analysis saved to {pdf_freq_log_path}")

        xml_freq_log_path = os.path.join(log_dir, f"{chapter_name}_final_xml_word_frequencies.json")
        with open(xml_freq_log_path, "w") as f:
            json.dump(xml_word_freq, f, indent=4)
        logger.debug(f"Final XML word frequency analysis saved to {xml_freq_log_path}")

        raise ValueError(
            f"Final word count mismatch for {os.path.basename(pdf_path)}. "
            f"Difference is {percentage_diff:.2f}%, which is over the 15% threshold."
        )
    else:
        logger.info("Final word count verification passed.")

def write_error_report(run_dir: str, all_errors: dict):
    """Writes a summary of all processing errors to a text file."""
    report_path = os.path.join(run_dir, "error_report.txt")
    with open(report_path, "w") as f:
        if not all_errors:
            f.write("All chapters processed successfully.\n")
            return

        f.write("--- D&D Module Generation Error Report ---")
        for chapter, data in all_errors.items():
            f.write(f"Chapter: {chapter}\n")
            f.write(f"  Status: {data['status']}\n")
            f.write(f"  Details: {data['details']}\n")
            if data.get('page_errors'):
                f.write("  Page-Specific Errors:\n")
                for err in data['page_errors']:
                    f.write(f"    - {err}\n")
            f.write("\n")
    logger.info(f"Error report saved to: {report_path}")

import argparse

def main(input_dir: str, base_output_dir: str, single_file: str = None):
    """
    Main function to convert all PDF files in a directory to XML in parallel.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(base_output_dir, timestamp)
    output_dir = os.path.join(run_dir, "documents")
    log_dir = os.path.join(run_dir, "intermediate_logs")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    # Reconfigure logger to write to run directory
    global logger
    from pathlib import Path
    logger = get_run_logger("pdf_to_xml", Path(run_dir))

    all_errors = {}
    if single_file:
        pdf_files = [single_file]
    else:
        pdf_files = sorted([f for f in os.listdir(input_dir) if f.endswith(".pdf")])
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_pdf = {}
        for pdf_file in pdf_files:
            pdf_path = os.path.join(input_dir, pdf_file)
            pdf_basename = os.path.splitext(pdf_file)[0]
            xml_output_path = os.path.join(output_dir, f"{pdf_basename}.xml")
            
            future = executor.submit(process_chapter, pdf_path, xml_output_path, log_dir)
            future_to_pdf[future] = pdf_basename

        for future in concurrent.futures.as_completed(future_to_pdf):
            pdf_basename = future_to_pdf[future]
            try:
                page_errors = future.result()
                if page_errors:
                    all_errors[pdf_basename] = {
                        "status": "Completed with page-level errors",
                        "details": "One or more pages failed to process correctly.",
                        "page_errors": page_errors
                    }
            except Exception as e:
                logger.error(f"FATAL: Chapter {pdf_basename} failed to process: {e}")
                all_errors[pdf_basename] = {
                    "status": "Failed",
                    "details": str(e),
                    "page_errors": []
                }
    
    write_error_report(run_dir, all_errors)

if __name__ == "__main__":
    configure_gemini()

    parser = argparse.ArgumentParser(description="Convert D&D module PDFs to XML.")
    parser.add_argument("--file", type=str, help="The name of a single PDF file to process.")
    args = parser.parse_args()

    pdf_sections_dir = os.path.join(PROJECT_ROOT, "data", "pdf_sections", "Lost_Mine_of_Phandelver")
    runs_output_dir = os.path.join(PROJECT_ROOT, "output", "runs")

    main(pdf_sections_dir, runs_output_dir, single_file=args.file)
