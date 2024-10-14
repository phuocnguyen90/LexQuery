# src/main.py
import os
import sys
import logging
from utils.load_config import load_config
from utils.logging_setup import setup_logging
from utils.validation import mask_api_key, load_schema, validate_record
from utils.retry_handler import retry
from tasks.preprocessing import Preprocessor
from tasks.postprocessing import PostProcessor
from utils.input_processor import InputProcessor
from utils.file_handler import output_2_jsonl
def main():
    

    # Load configuration
    try:
        config = load_config('src/config/config.yaml')
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        return
    
    # Load the logger
    setup_logging(config.get("processing").get("log_file"))    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # Set the desired logging level
    


     # Initialize InputProcessor

    try:
        input_processor = InputProcessor(config=config)
    except Exception as e:
        logger.error(f"Failed to initialize InputProcessor: {e}")
        return


    # Initialize Preprocessor
    try:
        preprocessor = Preprocessor(config)
        logger.info("Preprocessor initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Preprocessor: {e}")
        return

    # Define input and output file paths
    #input_file = config['processing']['input_file']
    # input_file="data\\raw\\ND-01-2020.docx"
    input_file="data\\raw\\test_input.txt"
    output_file = config['processing']['preprocessed_file']


    # Process all records

    try:
        records=input_processor.process_input_file(input_file,return_type='dict',record_type='QA')
        logger.info("All records processed successfully.")
        output_2_jsonl(output_file,records)
    except Exception as e:
        logger.error(f"Error processing records: {e}")

if __name__ == "__main__":
    main()