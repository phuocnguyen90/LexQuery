import asyncio
import streamlit as st
import os
import json
import uuid

from services.query_rag_v2 import query_rag # Import generate_embedding from query_rag
from services.qa_formatter import format_qa_record, upload_answer, review_and_upload_answer,refine_and_format_qa_record  # Import format_qa_record from qa_formatter
from models.query_model import QueryModel
from services.qdrant_init import initialize_qdrant
from shared_libs.config import Config
from qdrant_client.http.models import Filter, FieldCondition, MatchText
from shared_libs.utils.logger import Logger
from shared_libs.config.app_config import AppConfigLoader
from shared_libs.config.embedding_config import EmbeddingConfig
from shared_libs.embeddings.embedder_factory import EmbedderFactory


# Load the unified configuration once.
global_config = Config.load()
logger = Logger.get_logger("RAG_GUI")

# Initialize Qdrant client using our central config.
qdrant_client = initialize_qdrant()

# Initialize embedder from global_config.embedding
embedding_config = global_config.embedding
factory = EmbedderFactory(embedding_config)
# Use the active provider (for example, 'local' if overridden via environment variable)
embedding_function = factory.create_embedder(os.getenv('ACTIVE_EMBEDDING_PROVIDER', embedding_config.default_provider))

# Optionally, initialize your LLM provider once (if needed in qa_formatter)

from services.query_rag import initialize_provider
llm_provider = initialize_provider("groq")
logger.debug("LLM provider initialized: %s", llm_provider)  
DEV_LOG_FILE = "developer_logs.log"
TESTER_LOG_FILE = "tester_logs.log"

# Main Streamlit application
def main():
    st.title("RAG Testing GUI with Tabs")

    # Create tabs for the main interface
    tabs = st.tabs(["Query Interaction", "Qdrant Database", "View Logs"])

    with tabs[0]:
        query_interaction()

    with tabs[1]:
        qdrant_database_interaction()

    with tabs[2]:
        view_logs()

def query_interaction():
    """
    This tab allows the user to:
      1. Submit a query.
      2. View the LLM-generated answer.
      3. Review (and optionally edit) the resulting QA record before uploading.
    """
    st.header("Query Interaction")

    query_text = st.text_area("Enter your query:", placeholder="Type your question here...")
    
    # Privilege level selection (for upload vs suggestion)
    privilege = st.radio("Select your privilege level:", options=["Regular", "Admin"], index=0,
                           help="Admin users can directly upload the answer. Regular users can only suggest it.")

    # Additional options
    debug_mode = st.checkbox("Enable Debug Mode", value=False, help="View detailed debug information.")
    rerank_option = st.checkbox("Enable Reranking", value=False, help="Rerank search results to optimize the answer.")
    keyword_gen_option = st.checkbox("Enable Keyword Generator", value=False, help="Automatically generate keywords for the query.")

    if st.button("Submit Query"):
        if not query_text.strip():
            st.error("Please enter a query before submitting.")
            return

        with st.spinner("Processing your query..."):
            try:
                # Run query_rag() to get the raw LLM answer and related search results.
                response_data = asyncio.run(run_query(query_text, debug_mode, rerank_option, keyword_gen_option))
                log_query_data(query_text, response_data)
                display_response(response_data, debug_mode)

                # Here, we call our helper to refine the QA pair into a Record object.
                # This function (refine_and_format_qa_record) takes the original query, generated answer,
                # and additional metadata (if any), and returns a Record object.
                # For this example, we let the moderator supply additional metadata.
                additional_info = st.text_area("Additional Metadata (optional, in JSON):", 
                                               placeholder='{"categories": ["QA"], "notes": "Any extra info"}')
                # Run the refinement process asynchronously.
                record = asyncio.run(refine_and_format_qa_record(query_text, 
                                                                 response_data.get("query_response", {}).get("response_text", ""), 
                                                                 additional_info, 
                                                                 llm_provider))
                if record is None:
                    st.error("Failed to generate a valid record from the LLM answer.")
                    return

                # Display the record attributes for review.
                st.subheader("Review the QA Record Before Upload")
                record_dict = record.to_dict()
                edited_record = {}
                for key, value in record_dict.items():
                    # Display each attribute with a text input (convert value to string)
                    edited_value = st.text_input(f"{key}", value=str(value))
                    # Attempt to convert numeric values if applicable.
                    try:
                        # If the original value was numeric, cast accordingly.
                        if isinstance(value, int):
                            edited_value = int(edited_value)
                        elif isinstance(value, float):
                            edited_value = float(edited_value)
                    except Exception:
                        pass
                    edited_record[key] = edited_value

                st.markdown("### Final Record Preview")
                st.json(edited_record)

                # Provide a button to either upload or suggest the record.
                if privilege == "Admin":
                    if st.button("Upload Record"):
                        upload_answer(json.dumps(edited_record), additional_info, query_text)
                else:
                    if st.button("Suggest Record"):
                        st.success("Your suggestion has been submitted for review.")
            except Exception as e:
                st.error(f"An error occurred: {e}")
                logger.error("Error processing query '%s': %s", query_text, e)

                
async def run_query(query_text: str, debug_mode: bool, rerank: bool, keyword_gen_option: bool) -> dict:
    conversation_history = []
    query_item = QueryModel(query_text=query_text)
    response_data = await query_rag(
        query_item=query_item,
        conversation_history=conversation_history,
        embedding_mode="local",  # Use local mode if desired.
        rerank=rerank,
        keyword_gen=keyword_gen_option
    )
    return response_data

def display_response(response_data: dict, debug_mode: bool):
    query_response = response_data.get("query_response", {})
    retrieved_docs = response_data.get("retrieved_docs", [])

    st.subheader("LLM Generated Answer")
    st.write(query_response.get("response_text", "No answer generated."))

    st.subheader("Extracted Information")
    if retrieved_docs:
        for idx, doc in enumerate(retrieved_docs, start=1):
            st.markdown(f"**Source {idx}:**")
            st.write(f"- **Record ID**: {doc.get('record_id', 'N/A')}")
            st.write(f"- **Document ID**: {doc.get('document_id', 'N/A')}")
            st.write(f"- **Title**: {doc.get('title', 'N/A')}")
            st.write(f"- **Chunk ID**: {doc.get('chunk_id', 'N/A')}")
            st.write(f"- **Content**:\n{doc.get('content', 'No content available.')}")
            st.write("---")
    else:
        st.write("No relevant documents found.")

    if debug_mode:
        st.subheader("Debug Information")
        debug_prompt = st.session_state.get("debug_prompt", "No debug prompt available.")
        st.text_area("Full Prompt", value=debug_prompt, height=300)
        st.subheader("Retrieved Documents Context")
        for idx, doc in enumerate(retrieved_docs, start=1):
            st.markdown(f"**Document {idx}:**")
            st.json(doc)

    st.subheader("Query Metadata")
    st.write(f"**Query**: {query_response.get('query_text', 'N/A')}")
    st.write(f"**Timestamp**: {query_response.get('timestamp', 'N/A')}")

def log_query_data(query_text: str, response_data: dict):
    try:
        query_response = response_data.get("query_response", {})
        retrieved_docs = response_data.get("retrieved_docs", [])
        log_entry = {
            "query": query_text,
            "response": query_response.get("response_text", "No response."),
            "timestamp": query_response.get("timestamp", "N/A"),
            "retrieved_docs": [
                {
                    "record_id": doc.get("record_id", "N/A"),
                    "document_id": doc.get("document_id", "N/A"),
                    "title": doc.get("title", "N/A"),
                    "chunk_id": doc.get("chunk_id", "N/A"),
                    "content": doc.get("content", "No content available."),
                }
                for doc in retrieved_docs
            ],
        }
        logger.info(f"Query Log: {log_entry}")
    except Exception as e:
        logger.error(f"Failed to log query data for '{query_text}': {e}")

def qdrant_database_interaction():
    st.header("Qdrant Database Management")
    action = st.radio("Select an action", ["View Records", "Add Record", "Edit Record", "Delete Record"])
    if action == "View Records":
        view_records_section()
    elif action == "Add Record":
        add_record_section()
    elif action == "Edit Record":
        edit_record_section()
    elif action == "Delete Record":
        delete_record_section()

def view_records_section():
    st.subheader("View Records")
    collection_name = st.text_input("Collection Name:", "default_collection")
    st.markdown("### Filter Options")
    col1, col2 = st.columns(2)
    with col1:
        record_id_filter = st.text_input("Filter by Record ID:", placeholder="Enter Record ID")
    with col2:
        keyword_filter = st.text_input("Search Keyword in 'content':", placeholder="Enter keyword to search in content")

    if st.button("View Records"):
        try:
            from qdrant_client.http.models import Filter, FieldCondition, MatchText
            filter_obj = None
            if record_id_filter.strip() and keyword_filter.strip():
                filter_obj = Filter(
                    must=[
                        FieldCondition(key="record_id", match=MatchText(text=record_id_filter.strip())),
                        FieldCondition(key="content", match=MatchText(text=keyword_filter.strip()))
                    ]
                )
            elif record_id_filter.strip():
                filter_obj = Filter(
                    must=[FieldCondition(key="record_id", match=MatchText(text=record_id_filter.strip()))]
                )
            elif keyword_filter.strip():
                filter_obj = Filter(
                    must=[FieldCondition(key="content", match=MatchText(text=keyword_filter.strip()))]
                )
            if filter_obj:
                points, next_page_token = qdrant_client.scroll(
                    collection_name=collection_name,
                    scroll_filter=filter_obj,
                    limit=100
                )
            else:
                points, next_page_token = qdrant_client.scroll(
                    collection_name=collection_name,
                    scroll_filter=None,
                    limit=100
                )
            st.write(f"Found {len(points)} record(s).")
            if points:
                for point in points:
                    st.json(point.dict())
            else:
                st.info("No records found with the applied filters.")
            if next_page_token:
                st.info("There are more records available. Implement pagination as needed.")
        except Exception as e:
            st.error(f"Failed to retrieve records: {e}")

def add_record_section():
    st.subheader("Add Record")
    collection_name = st.text_input("Collection Name:", "default_collection")
    vector = st.text_area("Vector (comma-separated):", placeholder="e.g., 0.1, 0.2, 0.3")
    payload = st.text_area("Payload (JSON):", placeholder='{"key": "value"}')

    if st.button("Add Record"):
        try:
            vector = [float(x.strip()) for x in vector.split(",") if x.strip()]
            if not vector:
                st.error("Vector cannot be empty or improperly formatted.")
                return
            payload = json.loads(payload)
            record_id = str(uuid.uuid4())
            qdrant_client.upsert(
                collection_name=collection_name,
                points=[{"id": record_id, "vector": vector, "payload": payload}],
            )
            st.success(f"Record added successfully with ID: {record_id}!")
            logger.info(f"Added record with ID: {record_id} to collection: {collection_name}")
        except json.JSONDecodeError:
            st.error("Invalid JSON format for payload.")
        except ValueError:
            st.error("Vector must contain valid floating-point numbers separated by commas.")
        except Exception as e:
            st.error(f"Failed to add record: {e}")
            logger.error(f"Failed to add record to collection '{collection_name}': {e}")

def edit_record_section():
    st.subheader("Edit Record")
    st.info("Editing records is not implemented in this example.")

def delete_record_section():
    st.subheader("Delete Record")
    collection_name = st.text_input("Collection Name:", "default_collection")
    record_id = st.text_input("Record ID to Delete:")

    if st.button("Delete Record"):
        try:
            qdrant_client.delete(
                collection_name=collection_name,
                points_selector={"ids": [record_id.strip()]}
            )
            st.success(f"Record with ID {record_id.strip()} deleted successfully!")
            logger.info(f"Deleted record with ID: {record_id.strip()} from collection: {collection_name}")
        except Exception as e:
            st.error(f"Failed to delete record: {e}")
            logger.error(f"Failed to delete record with ID '{record_id.strip()}' from collection '{collection_name}': {e}")

def view_logs():
    st.header("Log Viewer")
    tabs = st.tabs(["Developer Logs", "Tester Logs"])

    with tabs[0]:
        if os.path.exists(DEV_LOG_FILE):
            with open(DEV_LOG_FILE, "r", encoding="utf-8") as f:
                logs = f.read()
            st.text_area("Developer Logs", value=logs, height=400)
        else:
            st.info("No Developer Logs available.")

    with tabs[1]:
        if os.path.exists(TESTER_LOG_FILE):
            with open(TESTER_LOG_FILE, "r", encoding="utf-8") as f:
                logs = f.read()
            st.text_area("Tester Logs", value=logs, height=400)
        else:
            st.info("No Tester Logs available.")

if __name__ == "__main__":
    main()
