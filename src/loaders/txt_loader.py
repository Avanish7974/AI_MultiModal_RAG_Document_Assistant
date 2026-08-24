def extract_txt_text(file_path):
    """
    Extract text from TXT files.

    Returns:
        list of dictionaries containing:
        - text
        - location (line number)
    """

    extracted_data = []

    # =====================================================
    # TRY COMMON ENCODINGS
    # =====================================================

    encodings = [
        "utf-8",
        "utf-8-sig",
        "cp1252",
        "latin-1"
    ]

    content = None

    for encoding in encodings:

        try:

            with open(
                file_path,
                "r",
                encoding=encoding
            ) as file:

                content = file.readlines()

            break

        except UnicodeDecodeError:

            continue

    if content is None:

        raise ValueError(
            "Could not decode the TXT file."
        )

    # =====================================================
    # EXTRACT NON-EMPTY LINES
    # =====================================================

    for line_number, line in enumerate(
        content,
        start=1
    ):

        text = line.strip()

        if text:

            extracted_data.append(
                {
                    "text": text,
                    "location": line_number
                }
            )

    return extracted_data