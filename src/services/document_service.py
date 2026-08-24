import os

from src.loaders.pdf_loader import extract_pdf_text
from src.loaders.docx_loader import extract_docx_text
from src.loaders.pptx_loader import extract_pptx_text
from src.loaders.txt_loader import extract_txt_text
from src.loaders.spreadsheet_loader import (
    extract_csv_text,
    extract_xlsx_text
)
from src.loaders.image_loader import extract_image_text

from src.splitter.text_splitter import split_text
from src.vectorstore.chroma_store import add_documents


# =========================================================
# PROCESS EXTRACTED DATA
# =========================================================

def _process_extracted_data(
    extracted_data,
    file_name,
    collection
):
    """
    Common processing pipeline for all document types.

    Extracted data
        ↓
    Chunking
        ↓
    ChromaDB
    """

    all_chunks = []

    for item in extracted_data:

        text = item["text"]

        location = item.get(
            "location",
            "Unknown"
        )

        chunks = split_text(text)

        for chunk in chunks:

            all_chunks.append(
                {
                    "text": chunk,
                    "page": location
                }
            )

    if all_chunks:

        add_documents(
            collection=collection,
            chunks=all_chunks,
            file_name=file_name
        )

    return all_chunks


# =========================================================
# PDF
# =========================================================

def process_pdf(
    file_path,
    file_name,
    collection
):
    """
    Process PDF page by page.
    """

    pages = extract_pdf_text(
        file_path
    )

    extracted_data = []

    for page_data in pages:

        extracted_data.append(
            {
                "text": page_data["text"],
                "location": page_data["page"]
            }
        )

    return _process_extracted_data(
        extracted_data,
        file_name,
        collection
    )


# =========================================================
# DOCX
# =========================================================

def process_docx(
    file_path,
    file_name,
    collection
):
    """
    Process DOCX paragraphs and tables.
    """

    extracted_data = extract_docx_text(
        file_path
    )

    return _process_extracted_data(
        extracted_data,
        file_name,
        collection
    )


# =========================================================
# PPTX
# =========================================================

def process_pptx(
    file_path,
    file_name,
    collection
):
    """
    Process PPTX slide content.
    """

    extracted_data = extract_pptx_text(
        file_path
    )

    return _process_extracted_data(
        extracted_data,
        file_name,
        collection
    )


# =========================================================
# TXT
# =========================================================

def process_txt(
    file_path,
    file_name,
    collection
):
    """
    Process TXT files.
    """

    extracted_data = extract_txt_text(
        file_path
    )

    return _process_extracted_data(
        extracted_data,
        file_name,
        collection
    )


# =========================================================
# CSV
# =========================================================

def process_csv(
    file_path,
    file_name,
    collection
):
    """
    Process CSV files.
    """

    extracted_data = extract_csv_text(
        file_path
    )

    return _process_extracted_data(
        extracted_data,
        file_name,
        collection
    )


# =========================================================
# XLSX
# =========================================================

def process_xlsx(
    file_path,
    file_name,
    collection
):
    """
    Process Excel files.
    """

    extracted_data = extract_xlsx_text(
        file_path
    )

    return _process_extracted_data(
        extracted_data,
        file_name,
        collection
    )


# =========================================================
# IMAGE
# =========================================================

# =========================================================
# IMAGE
# =========================================================

def process_image(
    file_path,
    file_name,
    collection
):
    """
    Process an image using:

    1. EasyOCR
    2. Gemini Vision

    Both OCR text and visual analysis are stored
    in ChromaDB.
    """

    # -----------------------------------------------------
    # OCR
    # -----------------------------------------------------

    ocr_data = extract_image_text(
        file_path
    )

    # -----------------------------------------------------
    # GEMINI VISION
    # -----------------------------------------------------

    from src.services.vision_service import analyze_image

    visual_description = analyze_image(
        image_path=file_path
    )

    # -----------------------------------------------------
    # COMBINE RESULTS
    # -----------------------------------------------------

    extracted_data = []

    # -----------------------------------------------------
    # OCR RESULTS
    # -----------------------------------------------------

    for item in ocr_data:

        extracted_data.append(
            {
                "text": (
                    "OCR TEXT:\n"
                    f"{item['text']}"
                ),
                "location": item.get(
                    "location",
                    "OCR"
                )
            }
        )

    # -----------------------------------------------------
    # VISION RESULT
    # -----------------------------------------------------

    if visual_description:

        extracted_data.append(
            {
                "text": (
                    "VISUAL ANALYSIS:\n"
                    f"{visual_description}"
                ),
                "location": "Visual Analysis"
            }
        )

    # -----------------------------------------------------
    # STORE IN CHROMADB
    # -----------------------------------------------------

    return _process_extracted_data(
        extracted_data,
        file_name,
        collection
    )


# =========================================================
# GENERIC DOCUMENT PROCESSOR
# =========================================================

def process_document(
    file_path,
    file_name,
    collection
):
    """
    Automatically detect the file type and process it.

    Supported:
        PDF
        DOCX
        PPTX
        TXT
        CSV
        XLSX
        PNG
        JPG
        JPEG
    """

    extension = os.path.splitext(
        file_name
    )[1].lower()

    if extension == ".pdf":

        return process_pdf(
            file_path,
            file_name,
            collection
        )

    elif extension == ".docx":

        return process_docx(
            file_path,
            file_name,
            collection
        )

    elif extension == ".pptx":

        return process_pptx(
            file_path,
            file_name,
            collection
        )

    elif extension == ".txt":

        return process_txt(
            file_path,
            file_name,
            collection
        )

    elif extension == ".csv":

        return process_csv(
            file_path,
            file_name,
            collection
        )

    elif extension in [".xlsx", ".xls"]:

        return process_xlsx(
            file_path,
            file_name,
            collection
        )

    elif extension in [
        ".png",
        ".jpg",
        ".jpeg"
    ]:

        return process_image(
            file_path,
            file_name,
            collection
        )

    else:

        raise ValueError(
            f"Unsupported file type: {extension}"
        )