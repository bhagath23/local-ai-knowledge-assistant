
def extract_txt(file_path):

    extracted_data = []

    with open(file_path, "r", encoding="utf-8") as file:

        text = file.read()

        if text.strip():

            extracted_data.append({
                "text": text,
                "source": file_path
            })

    return extracted_data
