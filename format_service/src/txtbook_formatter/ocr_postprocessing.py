# rag_service/src/services/postprocess_ocr.py

from dataclasses import dataclass
from typing import List
import time
import os
import asyncio

# Imports from shared_libs
from shared_libs.llm_providers import ProviderFactory
from shared_libs.utils.logger import Logger
from shared_libs.config.app_config import AppConfigLoader
from shared_libs.config.prompt_config import PromptConfigLoader
from shared_libs.config.embedding_config import EmbeddingConfig
from shared_libs.embeddings.embedder_factory import EmbedderFactory

# Import GroqProvider
from shared_libs.llm_providers.groq_provider import GroqProvider

# Load configuration
config_loader = AppConfigLoader()
config = config_loader.config



# Configure logging
logger = Logger.get_logger(module_name=__name__)

# Load the default LLM provider using ProviderFactory
default_provider_name = config.get('llm', {}).get('provider', 'groq')
default_llm_settings = config.get('llm', {}).get(default_provider_name, {})
llm_provider = ProviderFactory.get_provider(name=default_provider_name, config=default_llm_settings)

@dataclass
class OCRProcessConfig:
    input_file: str
    output_file: str
    max_words: int = 600
    max_paragraphs: int = 8
    max_tokens_per_minute: int = 20000
    max_requests_per_minute: int = 30
    max_tokens_per_request: int = 2048

class OCRProcessor:
    def __init__(self, config: OCRProcessConfig, provider: GroqProvider):
        self.config = config
        self.provider = provider
        self.prompt_template = (
            """hãy phục hồi nội dung OCR bị lỗi sau đây, với các yêu cầu bắt buộc tuân theo: Đảm bảo phần trả lời có đầy đủ nội dung gốc; Chỉ được trả lời với nội dung OCR sau khi phục hồi; Không được thêm bất cứ hội thoại nào khác (Ví dụ như: sau đây là nội dung được phục hồi); Giữ nguyên cách đánh số đầu mục, gạch đầu dòng, số trang... nếu có xuất hiện trong đoạn văn.\n
            Dưới đây là đoạn văn cần OCR:"""
        )
        self.rate_limit_semaphore = asyncio.Semaphore(self.config.max_requests_per_minute)
        self.tokens_sent = 0
        self.requests_sent = 0
        self.window_start = time.time()

    def split_into_chunks(self, text: str) -> List[str]:
        """
        Splits the input text into chunks based on maximum words or maximum paragraphs.

        Args:
            text (str): The input text to be split.

        Returns:
            List[str]: A list of text chunks.
        """
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_words = 0
        current_paragraphs = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            para_words = len(para.split())
            if (current_words + para_words > self.config.max_words) or (current_paragraphs + 1 > self.config.max_paragraphs):
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_words = para_words
                current_paragraphs = 1
            else:
                current_chunk.append(para)
                current_words += para_words
                current_paragraphs += 1

        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    async def process_chunk(self, chunk: str, idx: int, total_chunks: int) -> str:
        """
        Processes a single chunk by sending it to Groq's API and returning the response.

        Args:
            chunk (str): The text chunk to process.
            idx (int): The index of the chunk.
            total_chunks (int): Total number of chunks.

        Returns:
            str: The processed response from Groq's API.
        """
        await self.rate_limit_semaphore.acquire()
        try:
            current_time = time.time()
            elapsed = current_time - self.window_start
            if elapsed >= 60:
                # Reset counters
                self.tokens_sent = 0
                self.requests_sent = 0
                self.window_start = current_time

            # Estimate tokens for the chunk
            chunk_words = len(chunk.split())
            estimated_input_tokens = int(chunk_words * 1.3)
            estimated_output_tokens = self.config.max_tokens_per_request
            total_estimated_tokens = estimated_input_tokens + estimated_output_tokens

            if (self.requests_sent + 1 > self.config.max_requests_per_minute) or (self.tokens_sent + total_estimated_tokens > self.config.max_tokens_per_minute):
                # Wait until the window resets
                wait_time = 60 - elapsed
                wait_time = max(wait_time, 1)  # Ensure at least 1 second wait
                logger.info(f"Rate limit reached. Waiting for {int(wait_time)+1} seconds...")
                await asyncio.sleep(wait_time + 1)  # Wait a bit more to ensure the window has reset
                # Reset counters
                self.tokens_sent = 0
                self.requests_sent = 0
                self.window_start = time.time()

            # Prepare the prompt
            prompt = f"{self.prompt_template}\n\n{chunk}"

            # Create the completion request
            response = await self.send_completion_request(prompt)

            logger.info(f"Processed chunk {idx}/{total_chunks}")

            # Update rate limiting counters
            self.requests_sent += 1
            self.tokens_sent += total_estimated_tokens

            return response

        except Exception as e:
            logger.error(f"Error processing chunk {idx}: {e}")
            return ""
        finally:
            self.rate_limit_semaphore.release()

    async def send_completion_request(self, prompt: str) -> str:
        """
        Sends a completion request to Groq's API.

        Args:
            prompt (str): The prompt to send.

        Returns:
            str: The response from the API.
        """
        try:
            response_text = await self.provider.send_single_message(prompt=prompt)
            if not response_text:
                logger.warning("Empty response received from Groq API.")
            return response_text
        except Exception as e:
            logger.error(f"Failed to process prompt: {e}")
            return ""

    async def postprocess_ocr(self):
        """
        Main function to handle the OCR post-processing.
        """
        input_path = self.config.input_file
        output_path = self.config.output_file

        # Check if input file exists
        if not os.path.exists(input_path):
            logger.error(f"Input file '{input_path}' does not exist.")
            return

        # Read the input file
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            logger.error(f"Failed to read input file '{input_path}': {e}")
            return

        # Split into chunks
        chunks = self.split_into_chunks(text)
        total_chunks = len(chunks)
        logger.info(f"Total chunks to process: {total_chunks}")

        # Create a list to hold the responses
        responses = ["" for _ in range(total_chunks)]

        # Create a list of tasks
        tasks = [
            self.process_chunk(chunk, idx, total_chunks)
            for idx, chunk in enumerate(chunks, 1)
        ]

        # Execute all tasks concurrently while respecting rate limits
        try:
            responses = await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error during asynchronous processing: {e}")
            return

        # Write all responses to the output file in order
        try:
            with open(output_path, 'w', encoding='utf-8') as out_f:
                for response in responses:
                    out_f.write(response + '\n\n')
            logger.info("OCR post-processing completed successfully.")
        except Exception as e:
            logger.error(f"Failed to write to output file '{output_path}': {e}")
            return

async def main():
    # Example usage
    ocr_config = OCRProcessConfig(
        input_file=r'C:\Users\PC\git\legal_qa_rag\format_service\src\data\raw\GT ky nang pt 3.txt',    # Replace with actual input file path
        output_file='output_post_ocr_pt_3_v1.txt'   # Replace with desired output file path
    )

    # Initialize the GroqProvider with configuration
    groq_config = config.get('llm', {}).get('groq', {})
    if not groq_config:
        logger.error("Groq configuration not found in the application config.")
        return

    groq_provider = GroqProvider(config=groq_config)

    # Initialize the OCR processor with the Groq provider
    ocr_processor = OCRProcessor(config=ocr_config, provider=groq_provider)

    # Run the post-processing
    await ocr_processor.postprocess_ocr()

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
