from shared_libs.utils.doc_chunker import process_folder, retrieve_section_text_from_folder,identify_and_segment_document

input_folder=r'C:\Users\PC\git\legal_qa_rag\format_service\src\data\raw\1. DOANH NGHIỆP'
output_folder=r'C:\Users\PC\git\legal_qa_rag\format_service\src\data\preprocessed\1. DOANH NGHIỆP'


if __name__ == "__main__":
    # process the whole folder
    process_folder(input_folder, output_folder)

    # find a section by id
    section_id ="01/2021/TT-BKHĐT_appendix_101"
    section_text = retrieve_section_text_from_folder(section_id,output_folder)

    if section_text:
        print("Reconstructed Text for Section ID:", section_id)
        print(section_text)
    else:
        print(f"No text found for section id: {section_id}")