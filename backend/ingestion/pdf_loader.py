
import fitz


def extract_pdf(file_path):

    document = fitz.open(file_path)

    extracted_pages = []

    for page_number, page in enumerate(document, start=1):

        text = page.get_text("text")

        if text.strip():

            page_data = {
                "page_number": page_number,
                "text": text,
                "source": file_path
            }

            extracted_pages.append(page_data)

    document.close()

    return extracted_pages
