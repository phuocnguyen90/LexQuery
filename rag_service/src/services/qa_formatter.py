import asyncio
import streamlit as st
import os
import json
import uuid

# Import your Record class and unique ID generator from record_model
from shared_libs.models.record_model import Record, generate_unique_id

from services.query_rag import  generate_embedding, extract_keywords, initialize_provider

from services.qdrant_init import initialize_qdrant
from shared_libs.config import Config

from shared_libs.utils.logger import Logger
from shared_libs.config.app_config import AppConfigLoader
from shared_libs.config.embedding_config import EmbeddingConfig
from shared_libs.embeddings.embedder_factory import EmbedderFactory
from shared_libs.llm_providers import ProviderFactory

# Load configuration and initialize Qdrant client and embedder as before
config = Config.load()
config_loader = AppConfigLoader()
qdrant_client = initialize_qdrant()
logger = Logger.get_logger("QA formatter")

embedding_config = EmbeddingConfig.from_config_loader(config_loader)
factory = EmbedderFactory(embedding_config)
embedding_function = factory.create_embedder('local')  # or 'api' as needed
default_provider_name = config_loader.get('llm', {}).get('provider', 'groq')
default_llm_settings = config_loader.get('llm', {}).get(default_provider_name, {})
llm_provider = ProviderFactory.get_provider(name=default_provider_name, config=default_llm_settings)


# ------------------ Helper Function to Format a QA Record ------------------
async def refine_question(question: str, answer: str, provider: any) -> str:
    """
    Use the LLM to determine if the question is optimal for the given answer.
    If no changes are needed, the LLM should return "No change".
    Otherwise, it should return the revised question.
    """
    prompt = (
    "You are an expert legal assistant tasked with verifying the appropriateness of a question-answer pair. "
    "Determine if the provided question clearly aligns with the given answer. "
    "Respond exclusively with either 'No change' if the original question is appropriate, "
    "or provide a succinctly revised version of the question if necessary. "
    "Do NOT include explanations, debug logs, or additional context."
    f"\n\nQuestion: {question}\nAnswer: {answer}\n"
    )

    if provider:
        refined = await provider.send_single_message(prompt=prompt)
        logger.debug("Question refined with given provider: %s", refined)
    else:
        refined = await llm_provider.send_single_message(prompt=prompt)
        logger.debug("Question refined with default LLM: %s", refined)
    return refined.strip()

async def refine_and_format_qa_record(original_question: str, answer_text: str, additional_info: str, provider: any) -> Record:
    """
    Refine the original question using an LLM, extract keywords from the combined QA text,
    and create a unified Record object.
    """
    # Parse additional metadata
    try:
        additional_data = json.loads(additional_info) if additional_info.strip() else {}
    except json.JSONDecodeError:
        st.error("Invalid JSON format in Additional Metadata. Please correct it or leave it empty.")
        return None

    # Refine the question using the LLM helper
    refined_question = await refine_question(original_question, answer_text, provider)
    if refined_question.lower() == "no change":
        final_question = original_question
    else:
        final_question = refined_question

    # Extract keywords from the combined QA text
    combined_text = original_question + " " + answer_text
    keywords = await extract_keywords(combined_text, provider, top_k=10)
    
    # Merge any existing categories with the extracted keywords (ensuring uniqueness)
    categories = additional_data.get("categories", [])
    if not categories:
        categories = keywords if keywords else ["QA"]
    else:
        categories = list(set(categories + keywords))

    # Generate a unique record ID based on the final question and answer
    record_id = generate_unique_id(final_question, answer_text, prefix="QA")
    record_dict = {
        "record_id": record_id,
        "document_id": "QA",  # Fixed value for QA records
        "title": f"Answer for: {final_question}",
        "content": answer_text,
        "chunk_id": record_id,
        "hierarchy_level": 1,
        "categories": categories,
        "relationships": additional_data.get("relationships", []),
        "published_date": additional_data.get("published_date"),
        "source": additional_data.get("source"),
        "processing_timestamp": None,  # Will be auto-assigned by Record constructor if omitted
        "validation_status": True,
        "language": additional_data.get("language", "vi"),
        "summary": additional_data.get("summary", "")
    }
    record = Record.from_json(record_dict)
    return record


def format_qa_record(query_text: str, answer_text: str, additional_info: str) -> Record:
    """
    Create a Record object for a QA pair by unifying the query and answer,
    along with any additional metadata provided (as a JSON string).
    """
    try:
        additional_data = json.loads(additional_info) if additional_info.strip() else {}
    except json.JSONDecodeError:
        st.error("Invalid JSON format in Additional Metadata. Please correct it or leave it empty.")
        return None

    # Generate a unique record ID based on the query and answer.
    record_id = generate_unique_id(query_text, answer_text, prefix="QA")
    record_dict = {
        "record_id": record_id,
        "document_id": "QA",  # Fixed value for QA records
        "title": f"Answer for: {query_text}",
        "content": answer_text,
        "chunk_id": record_id,
        "hierarchy_level": 1,
        "categories": additional_data.get("categories", ["QA"]),
        "relationships": additional_data.get("relationships", []),
        "published_date": additional_data.get("published_date"),
        "source": additional_data.get("source"),
        "processing_timestamp": None,  # Will be auto-assigned by Record constructor if omitted
        "validation_status": True,
        "language": additional_data.get("language", "vi"),
        "summary": additional_data.get("summary", "")
    }
    record = Record.from_json(record_dict)
    return record

# ------------------ Updated Upload Function ------------------

def upload_answer(answer_text: str, additional_info: str, query_text: str):
    """
    Compute the embedding for the answer, refine the QA pair into a Record object,
    and upsert it into the Qdrant collection.
    """
    # Obtain an LLM provider instance for refinement
    provider_llm = initialize_provider()  # Uses default LLM provider

    collection_name = st.text_input("Collection Name:", os.getenv("QA_COLLECTION_NAME", "legal_qa"), key="upload_collection")
    if not answer_text.strip():
        st.error("Please provide an answer before uploading.")
        return

    with st.spinner("Uploading answer..."):
        # Compute the embedding vector for the answer text
        embedding_vector = asyncio.run(generate_embedding(answer_text, embedding_function))
        if embedding_vector is None:
            st.error("Failed to compute the embedding vector for the answer.")
            return

        # Refine the question and format the QA record (using our new async helper)
        record = asyncio.run(refine_and_format_qa_record(query_text, answer_text, additional_info, provider_llm))
        if record is None:
            st.error("Failed to create a valid record from the provided data.")
            return

        payload = record.to_dict()
        try:
            qdrant_client.upsert(
                collection_name=collection_name,
                points=[{"id": record.record_id, "vector": embedding_vector.tolist(), "payload": payload}],
            )
            st.success(f"Answer uploaded successfully with Record ID: {record.record_id}!")
            logger.info(f"Uploaded answer with Record ID: {record.record_id} to collection: {collection_name}")
        except Exception as e:
            st.error(f"Failed to upload answer: {e}")
            logger.error(f"Error during answer upload: {e}")

# ------------------ Updated Query Interaction Functions ------------------


def review_and_upload_answer(response_data: dict, privilege: str, query_text: str):
    """
    Allow the user to review and optionally upload (or suggest) the generated answer.
    This function leverages the QA refinement process to unify the QA pair.
    """
    st.subheader("Review & Upload Answer")
    query_response = response_data.get("query_response", {})
    # Pre-fill the answer text area with the generated answer so the user can edit if needed.
    answer_text = st.text_area("Review Answer Text:", value=query_response.get("response_text", ""), height=200)
    additional_info = st.text_area("Additional Metadata (optional, JSON format):", 
                                   placeholder='{"categories": ["QA"], "notes": "any additional info"}')

    # Display the appropriate button based on user privilege
    if privilege == "Admin": 
        if st.button("Upload Answer"):
            upload_answer(answer_text, additional_info, query_text)
    else:
        if st.button("Suggest Answer"):
            logger.info("User suggestion received for answer: %s", answer_text)
            st.success("Your answer suggestion has been submitted for review.")
