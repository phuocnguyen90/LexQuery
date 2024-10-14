# Legal QA Preprocessing Microservice

## Overview

The **Legal QA Preprocessing Microservice** is a crucial component of the larger **Vietnamese Legal QA Chatbot** project. This microservice is designed to format and standardize legal question-and-answer texts, ensuring they are uniformly structured for efficient retrieval and storage. By preprocessing the legal content, it enhances the chatbot's ability to provide accurate and relevant responses to user inquiries.

## Features

- **Personally Identifiable Information (PII) Removal**: Automatically detects and removes any PII from the legal texts to ensure data privacy and compliance.
- **Content Cleaning**: Strips out irrelevant, incoherent, or promotional content, focusing solely on the information pertinent to the legal questions and answers.
- **Title Optimization**: Rephrases titles to better generalize the content, improving the organization and retrieval of information.
- **Language Compliance**: Ensures all processed content is in Vietnamese, maintaining consistency across the dataset while preserving JSON property names.
- **Schema Validation**: Validates processed records against predefined JSON schemas to maintain data integrity and consistency.
- **API Integration**: Interfaces with various API providers (e.g., Groq, Google Gemini) to leverage advanced processing capabilities.

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/phuocnguyen90/Legal_QA_format.git
   ```

2. **Install Dependencies**

   Ensure you have Python 3.10+ installed.

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**

   Create a `.env` file in the `config` directory and add your API keys:

   ```env
   GROQ_API_KEY=your_groq_api_key
   OPENAI_API_KEY=your_openai_api_key
   GEMINI_API_KEY=your_gemini_api_key
   ```

4. **Configure `config.yaml`**

   Edit the `config/config.yaml` file to set up file paths, provider configurations, and processing parameters as needed.

## Usage

Run the preprocessing service using the main entry point:

```bash
python main.py
```

This command will initiate the preprocessing pipeline, which will:

1. Load raw legal QA data from the specified input file.
2. Apply preprocessing steps such as PII removal, content cleaning, and title optimization.
3. Validate the processed data against the predefined JSON schema.
4. Store the cleaned and standardized data in the designated output files for retrieval and storage.

## Configuration

The microservice relies on the `config.yaml` file for its configuration settings. Key configurations include:

- **Provider Settings**: API keys and model configurations for providers like Groq and Google Gemini.
- **File Paths**: Locations for input data, preprocessed data, processed data, final output, and logs.
- **Processing Parameters**: Settings such as delay between API requests and JSON schema definitions.
- **Schema Paths**: Paths to the preprocessing and postprocessing YAML schema files.

Ensure all paths and configurations are correctly specified to enable smooth operation of the microservice.

## Contributing

Contributions are welcome! If you have suggestions for improvements or encounter any issues, please open an issue or submit a pull request.

1. Fork the repository.
2. Create a new branch for your feature or bugfix.
3. Commit your changes with clear messages.
4. Push to your fork and submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgements

- Built with Python and various open-source libraries.
- Utilizes API providers like Groq and Google Gemini for advanced text processing.

---

