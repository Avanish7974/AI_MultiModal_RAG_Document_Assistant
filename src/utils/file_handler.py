from pathlib import Path

UPLOAD_DIR = Path("data/uploads")


def save_uploaded_file(uploaded_file):
    """
    Save an uploaded file to the uploads directory.
    """

    # Create folder if it doesn't exist
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    file_path = UPLOAD_DIR / uploaded_file.name

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return file_path