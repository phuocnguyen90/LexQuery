from shared_libs.utils.doc_chunker import process_folder

input_folder=r'C:\Users\PC\git\legal_qa_rag\format_service\src\data\raw\1. DOANH NGHIỆP'
output_folder=r'C:\Users\PC\git\legal_qa_rag\format_service\src\data\preprocessed\1. DOANH NGHIỆP'

process_folder(input_folder, output_folder)