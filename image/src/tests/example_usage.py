# example_usage.py

import logging
import json
from typing import List, Optional
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.load_config import load_config
from utils.record import Record
from utils.llm_formatter import LLMFormatter
from tasks.preprocessing import Preprocessor

def main():
    config = load_config('src/config/config.yaml')
    formatter = LLMFormatter(config=config)
    # Example 1: Tagged Record with Prefixed ID
    tagged_record = """
    <id=DOC_001>
    <title>Legal Basis for Contract Termination</title>
    <content>This section outlines the legal grounds for terminating a contract under specific conditions.</content>
    </id=DOC_001>
    """
    
    record_obj = Record.parse_record(tagged_record, return_type="record", record_type="DOC")
    if record_obj:
        print("Tagged Record successfully created:")
        print(record_obj.to_json())
    else:
        print("Failed to create Tagged Record.")
    
    # Example 2: JSON Record with Prefixed ID
    json_record = """
    {
        "id": "1",
        "title": "What are the grounds for contract termination?",
        "content": "Question: What are the grounds for contract termination? Answer: The grounds include breach of contract, mutual agreement, and force majeure."
    }
    """
    
    record_obj_json = Record.parse_record(json_record, return_type="record", record_type="QA")
    if record_obj_json:
        print("\nJSON Record successfully created:")
        print(record_obj_json.to_json())
    else:
        print("Failed to create JSON Record.")
    
    # Example 3: Tagged Record with Inconsistent ID
    inconsistent_tagged_record = """
    <id=UNKNOWN>
    <title>Invalid ID Example</title>
    <content>This record has an inconsistent ID format.</content>
    </id=UNKNOWN>
    """
    
    record_obj_inconsistent = Record.parse_record(inconsistent_tagged_record, return_type="record", record_type="DOC")
    if record_obj_inconsistent:
        print("\nInconsistent Tagged Record successfully created with generated ID:")
        print(record_obj_inconsistent.to_json())
    else:
        print("Failed to create Inconsistent Tagged Record.")
    
    # Example 4: Unformatted Record (No ID)
    unformatted_record = """
    This is an unformatted record that lacks explicit ID tags or JSON structure.
    It should be assigned a unique ID automatically.
    """
    
    record_obj_unformatted = Record.parse_record(unformatted_record, return_type="record", record_type="DOC",llm_formatter=formatter)
    if record_obj_unformatted:
        print("\nUnformatted Record successfully created with generated ID:")
        print(record_obj_unformatted.to_json())
    else:
        print("Failed to create Unformatted Record.")

if __name__ == "__main__":
    main()