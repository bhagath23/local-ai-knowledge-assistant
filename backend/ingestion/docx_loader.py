
from docx import Document


def extract_docx(file_path):

    document = Document(file_path)

    extracted_data = []

    for paragraph_number, paragraph in enumerate(
        document.paragraphs, start=1
    ):

        text = paragraph.text.strip()

        if text:

            paragraph_data = {
                "paragraph_number": paragraph_number,
                "text": text,
                "source": file_path
            }

            extracted_data.append(paragraph_data)

    return extracted_data
