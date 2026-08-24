import pandas as pd


# =========================================================
# CSV DATAFRAME
# =========================================================

def load_csv_dataframe(file_path):
    """
    Load a CSV file into a pandas DataFrame.

    Used by the Smart CSV/XLSX Data Analysis feature.
    """

    return pd.read_csv(
        file_path,
        encoding_errors="replace"
    )


# =========================================================
# XLSX DATAFRAMES
# =========================================================

def load_xlsx_dataframes(file_path):
    """
    Load every sheet from an Excel workbook.

    Returns:
        {
            "Sheet1": dataframe,
            "Sheet2": dataframe,
            ...
        }
    """

    excel_file = pd.ExcelFile(file_path)

    dataframes = {}

    for sheet_name in excel_file.sheet_names:

        dataframe = pd.read_excel(
            file_path,
            sheet_name=sheet_name
        )

        dataframes[sheet_name] = dataframe

    return dataframes


# =========================================================
# CSV TEXT EXTRACTION
# =========================================================

def extract_csv_text(file_path):
    """
    Extract CSV data as searchable text.

    This function is kept for the existing RAG pipeline.

    Returns:
        list of dictionaries containing:
        - text
        - location
    """

    dataframe = load_csv_dataframe(
        file_path
    )

    extracted_data = []

    for index, row in dataframe.iterrows():

        row_values = []

        for column in dataframe.columns:

            value = row[column]

            if pd.notna(value):

                row_values.append(
                    f"{column}: {value}"
                )

        if row_values:

            extracted_data.append(
                {
                    "text": " | ".join(row_values),
                    "location": index + 2
                }
            )

    return extracted_data


# =========================================================
# XLSX TEXT EXTRACTION
# =========================================================

def extract_xlsx_text(file_path):
    """
    Extract Excel workbook data as searchable text.

    Every sheet and row is converted into searchable text.

    This function is kept for the existing RAG pipeline.

    Returns:
        list of dictionaries containing:
        - text
        - location
    """

    dataframes = load_xlsx_dataframes(
        file_path
    )

    extracted_data = []

    for sheet_name, dataframe in dataframes.items():

        for index, row in dataframe.iterrows():

            row_values = []

            for column in dataframe.columns:

                value = row[column]

                if pd.notna(value):

                    row_values.append(
                        f"{column}: {value}"
                    )

            if row_values:

                extracted_data.append(
                    {
                        "text": (
                            f"Sheet: {sheet_name}\n"
                            + " | ".join(row_values)
                        ),
                        "location": (
                            f"{sheet_name}, "
                            f"Row {index + 2}"
                        )
                    }
                )

    return extracted_data