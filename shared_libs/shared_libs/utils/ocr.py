import os
from typing import Union
from pdf2image import convert_from_path
from paddleocr import PaddleOCR
import json

from typing import Union, Optional
from PIL import Image
import pytesseract
import tempfile
from tqdm import tqdm


def paddle_ocr(pdf_path: str, 
                       output_txt_path: str = None, 
                       language: str = 'vi', 
                       dpi: int = 300) -> Union[str, None]:
    """
    Perform OCR on a PDF file using PaddleOCR and return the extracted text.
    
    Parameters:
    - pdf_path (str): Path to the input PDF file.
    - output_txt_path (str, optional): Path to save the extracted text. 
                                       If None, the text is returned as a string.
    - language (str): Language(s) for OCR. Default is English ('en'). 
                      For multiple languages, pass a list like ['en', 'ch'].
    - dpi (int): Resolution for converting PDF pages to images. Higher DPI 
                 results in better OCR accuracy but increases processing time.
                 
    Returns:
    - str: Extracted text if `output_txt_path` is None.
    - None: If the text is written to a file.
    """
    try:
        # Initialize PaddleOCR
        ocr = PaddleOCR(lang=language, use_angle_cls=True, rec=True, det=True, use_gpu=True)
        
        # Convert PDF to images
        with tempfile.TemporaryDirectory() as path:
            images = convert_from_path(pdf_path, dpi=dpi, output_folder=path, fmt='png')
        
        extracted_text = []
        
        for page_num, image in enumerate(images, start=1):
            print(f"Processing page {page_num}/{len(images)}...")
            # Perform OCR on the image
            result = ocr.ocr(image, rec=True, cls=True)
            
            page_text = []
            for line in result:
                # Each line is a list containing bounding box and text info
                line_text = line[1][0]
                page_text.append(line_text)
            
            extracted_text.append('\n'.join(page_text))
        
        full_text = '\n\n'.join(extracted_text)
        
        if output_txt_path:
            with open(output_txt_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
            print(f"OCR completed. Text saved to {output_txt_path}.")
            return None
        else:
            return full_text
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    
import os
from typing import Union
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import tempfile

def tesseract_ocr(
    pdf_path: str, 
    output_txt_path: Optional[str] = None, 
    language: str = 'vie', 
    dpi: int = 300, 
    tesseract_cmd: Optional[str] = None,
    starting_page: Optional[int] = None,
    ending_page: Optional[int] = None
) -> Union[str, None]:
    """
    Perform OCR on a PDF file using Tesseract OCR and return the extracted text.

    Parameters:
    - pdf_path (str): Path to the input PDF file.
    - output_txt_path (str, optional): Path to save the extracted text. 
                                       If None, the text is returned as a string.
    - language (str): Language(s) for OCR (e.g., 'eng', 'eng+chi_sim'). 
                      Ensure the corresponding language data is installed.
    - dpi (int): Resolution for converting PDF pages to images. Higher DPI 
                 results in better OCR accuracy but increases processing time.
    - tesseract_cmd (str, optional): Path to the Tesseract executable.
                                     If None, assumes Tesseract is in PATH.
    - starting_page (int, optional): The first page to start OCR (1-based index).
    - ending_page (int, optional): The last page to perform OCR on.

    Returns:
    - str: Extracted text if `output_txt_path` is None.
    - None: If the text is written to a file.
    """
    try:
        # Configure Tesseract executable path if provided
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            print(f"Using Tesseract executable at: {tesseract_cmd}")
        else:
            print("Using Tesseract from system PATH.")

        # Determine total number of pages if possible
        from pdf2image.pdf2image import pdfinfo_from_path
        try:
            pdf_info = pdfinfo_from_path(pdf_path, userpw=None, poppler_path=None)
            total_pages = pdf_info["Pages"]
        except Exception as e:
            print(f"Could not determine total number of pages: {e}")
            total_pages = None

        # Convert PDF to images
        with tempfile.TemporaryDirectory() as path:
            print(f"Converting PDF to images at {dpi} DPI...")
            images = convert_from_path(
                pdf_path, 
                dpi=dpi, 
                output_folder=path, 
                fmt='png', 
                first_page=starting_page, 
                last_page=ending_page
            )

            num_pages = len(images)
            if total_pages and (starting_page or ending_page):
                actual_start = starting_page if starting_page else 1
                actual_end = ending_page if ending_page else total_pages
                print(f"Performing OCR from page {actual_start} to {actual_end} (Total: {num_pages} pages)")
            else:
                print(f"Performing OCR on {num_pages} pages")

            # Create a temporary file to store OCR results
            with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', delete=False) as temp_file:
                temp_file_path = temp_file.name
                print(f"Temporary file created at: {temp_file_path}")

                # Initialize tqdm progress bar
                with tqdm(total=num_pages, desc="Processing Pages", unit="page") as pbar:
                    for image in images:
                        # Optional: Preprocess the image for better OCR accuracy
                        # Example: Convert to grayscale
                        # image = image.convert('L')

                        # Perform OCR using pytesseract
                        text = pytesseract.image_to_string(image, lang=language)

                        # Append the text to the temporary file
                        temp_file.write(text + '\n\n')

                        # Update the progress bar
                        pbar.update(1)

            # Decide whether to write to output_txt_path or return the text
            if output_txt_path:
                # Move the temp file to the desired output path
                os.replace(temp_file_path, output_txt_path)
                print(f"OCR completed. Text saved to {output_txt_path}.")
                return None
            else:
                # Read the content from the temp file and delete it
                with open(temp_file_path, 'r', encoding='utf-8') as f:
                    full_text = f.read()
                os.remove(temp_file_path)
                return full_text

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def setup_persistent_temp_dir(base_dir: str) -> str:
    """
    Set up a persistent temporary directory for OCR processing.

    Parameters:
    - base_dir (str): The base directory where the temp directory will be created.

    Returns:
    - str: Path to the persistent temporary directory.
    """
    import os

    persistent_dir = os.path.join(base_dir, "ocr_temp")
    os.makedirs(persistent_dir, exist_ok=True)
    images_dir = os.path.join(persistent_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    progress_log_path = os.path.join(persistent_dir, "progress.json")
    if not os.path.exists(progress_log_path):
        with open(progress_log_path, 'w', encoding='utf-8') as log_file:
            json.dump({"processed_pages": []}, log_file)

    print(f"Persistent temporary directory set up at: {persistent_dir}")
    return persistent_dir


"""pdf_file = r'E:\Books\Giao trinh Ky nang LS.pdf'
output_text_file = 'output_text.txt'
tesseract_ocr(pdf_file, output_txt_path=output_text_file)"""

import os
import pytesseract
from PIL import Image
import logging

def ocr_folder_resumable(folder_path, output_text_path, log_file_path='processed_pages.log'):
    """
    Perform OCR on all PNG images in the specified folder using Vietnamese language settings
    and compile the text into a single file. The function is resumable; it keeps track of 
    processed images in a log file.

    :param folder_path: Path to the folder containing PNG images.
    :param output_text_path: Path to the output text file.
    :param log_file_path: Path to the log file tracking processed images.
    """
    
    # Configure logging
    logging.basicConfig(
        filename='ocr_process.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Ensure the folder exists
    if not os.path.isdir(folder_path):
        logging.error(f"The folder {folder_path} does not exist.")
        raise FileNotFoundError(f"The folder {folder_path} does not exist.")
    
    # Get list of all PNG files in the folder
    all_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.png')]
    
    if not all_files:
        logging.warning(f"No PNG files found in {folder_path}.")
        return
    
    # Sort files based on the numeric suffix before the .png extension
    def sort_key(filename):
        try:
            # Extract the part after the last hyphen and before .png
            number_part = filename.rsplit('-', 1)[-1].split('.png')[0]
            return int(number_part)
        except (IndexError, ValueError):
            # If sorting fails, return a high number to place it at the end
            return float('inf')
    
    sorted_files = sorted(all_files, key=sort_key)
    
    logging.info(f"Found {len(sorted_files)} PNG files to process.")
    
    # Load the set of already processed files
    processed_files = set()
    if os.path.exists(log_file_path):
        with open(log_file_path, 'r', encoding='utf-8') as log_file:
            processed_files = set(line.strip() for line in log_file if line.strip())
        logging.info(f"Loaded {len(processed_files)} already processed files from log.")
    
    # Define Tesseract configuration
    tesseract_config = r'--oem 3 --psm 3'
    ocr_language = 'vie'  # Vietnamese language code
    pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
    
    # Open the output text file in append mode
    with open(output_text_path, 'a', encoding='utf-8') as output_file, \
         open(log_file_path, 'a', encoding='utf-8') as log_file:
        
        for filename in sorted_files:
            if filename in processed_files:
                logging.info(f"Skipping already processed file: {filename}")
                continue  # Skip already processed files
            
            image_path = os.path.join(folder_path, filename)
            try:
                logging.info(f"Processing file: {filename}")
                # Open the image file
                with Image.open(image_path) as img:
                    # Perform OCR using Tesseract with specified language and config
                    text = pytesseract.image_to_string(img, lang=ocr_language, config=tesseract_config)
                
                # Write the extracted text to the output file
                output_file.write(f"\n\n--- Page: {filename} ---\n\n")
                output_file.write(text)
                
                # Flush to ensure text is written to disk
                output_file.flush()
                
                # Log the processed file
                log_file.write(f"{filename}\n")
                log_file.flush()
                
                logging.info(f"Successfully processed and logged file: {filename}")
            
            except Exception as e:
                logging.error(f"Error processing file {filename}: {e}")
                # Optionally, you can choose to break or continue based on the error
                continue  # Continue with the next file

    logging.info("OCR processing completed.")

# Example usage:
input_folder=r'C:\Users\PC\AppData\Local\Temp\tmp0mpmmace'
output_text_file = 'output_text.txt'
ocr_folder_resumable(input_folder, output_text_file)


