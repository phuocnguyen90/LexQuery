import asyncio
import streamlit as st
import logging
import os
import pandas as pd
import numpy as np
from services.query_rag import query_rag
from models.query_model import QueryModel
from services.qdrant_init import initialize_qdrant
from shared_libs.config import Config
from qdrant_client.http.models import Filter, FieldCondition, MatchText

from shared_libs.config.app_config import AppConfigLoader

# Load configuration from shared_libs
config = Config.load()
config_loader = AppConfigLoader()

# Configure logging
LOG_FILE = "query_logs.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Initialize Qdrant client (replace with your Qdrant setup)
qdrant_client = initialize_qdrant()

# Main Streamlit application
def main():
    st.title("RAG Testing GUI with Tabs")

    # Create tabs
    tabs = st.tabs(["Query Interaction", "Qdrant Database", "View Logs"])

    # Query Interaction Tab
    with tabs[0]:
        query_interaction()

    # Qdrant Database Tab
    with tabs[1]:
        qdrant_database_interaction()

    # View Logs Tab
    with tabs[2]:
        view_logs()


def query_interaction():
    """Tab for query interaction."""
    st.header("Query Interaction")

    query_text = st.text_area("Enter your query:", placeholder="Type your question here...")
    debug_mode = st.checkbox("Enable Debug Mode", value=False, help="View detailed debug information.")
    rerank_option = st.checkbox("Enable Reranking", value=False, help="Xếp hạng lại kết quả tra cứu để tối ưu câu trả lời.")
    keyword_gen_option = st.checkbox("Enable Keyword Generator", value=False, help="Tự động tạo nhiều keyword hơn để tra cứu.")
    if st.button("Submit Query"):
        if not query_text.strip():
            st.error("Please enter a query before submitting.")
            return

        with st.spinner("Processing your query..."):
            try:
                response_data = asyncio.run(run_query(query_text, debug_mode, rerank_option, keyword_gen_option))
                log_query_data(query_text, response_data)
                display_response(response_data, debug_mode)
            except Exception as e:
                st.error(f"An error occurred: {e}")
                logging.error(f"Error processing query '{query_text}': {e}")


async def run_query(query_text: str, debug_mode: bool, rerank: bool, keyword_gen_option: bool) -> dict:
    conversation_history = []
    query_item = QueryModel(query_text=query_text)
    response_data = await query_rag(query_item=query_item, conversation_history=conversation_history, rerank=rerank,keyword_gen=keyword_gen_option)
    return response_data


def display_response(response_data: dict, debug_mode: bool):
    query_response = response_data["query_response"]
    retrieved_docs = response_data.get("retrieved_docs", [])

    # Display the generated answer
    st.subheader("Generated Answer")
    st.write(query_response.response_text)

    # Display extracted information
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

    # Debug Mode: Display raw prompt and document context
    if debug_mode:
        st.subheader("Debug Information")
        st.write("### Full Prompt Sent to LLM:")
        debug_prompt = st.session_state.get("debug_prompt", "No debug prompt available.")
        st.text_area("Full Prompt", value=debug_prompt, height=300)

        st.write("### Retrieved Documents Context:")
        for idx, doc in enumerate(retrieved_docs, start=1):
            st.markdown(f"**Document {idx}:**")
            st.json(doc)

    # Display query metadata
    st.subheader("Query Metadata")
    st.write(f"**Query**: {query_response.query_text}")
    st.write(f"**Timestamp**: {query_response.timestamp}")


# Function to log query data to a file
def log_query_data(query_text: str, response_data: dict):
    try:
        query_response = response_data["query_response"]
        retrieved_docs = response_data.get("retrieved_docs", [])
        log_entry = {
            "query": query_text,
            "response": query_response.response_text,
            "timestamp": query_response.timestamp,
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
        logging.info(f"Query Log: {log_entry}")
    except Exception as e:
        logging.error(f"Failed to log query data for '{query_text}': {e}")


def qdrant_database_interaction():
    """Tab for interacting with the Qdrant database."""
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
    """Sub-section for viewing records with filtering options."""
    st.subheader("View Records")

    collection_name = st.text_input("Collection Name:", "default_collection")

    # Filter Options
    st.markdown("### Filter Options")
    col1, col2 = st.columns(2)

    with col1:
        record_id_filter = st.text_input("Filter by Record ID:", placeholder="Enter Record ID")
    with col2:
        keyword_filter = st.text_input("Search Keyword in 'content':", placeholder="Enter keyword to search in content")

    if st.button("View Records"):
        if not collection_name.strip():
            st.error("Please enter a collection name.")
            return

        try:
            # Initialize filter
            filter_obj = None

            # Build filter based on user input
            if record_id_filter.strip() and keyword_filter.strip():
                # Both Record ID and Keyword filters
                filter_obj = Filter(
                    must=[
                        FieldCondition(
                            key="record_id",
                            match=MatchText(text=record_id_filter.strip())
                        ),
                        FieldCondition(
                            key="content",
                            match=MatchText(text=keyword_filter.strip())
                        )
                    ]
                )
            elif record_id_filter.strip():
                # Only Record ID filter
                filter_obj = Filter(
                    must=[
                        FieldCondition(
                            key="record_id",
                            match=MatchText(text=record_id_filter.strip())
                        )
                    ]
                )
            elif keyword_filter.strip():
                # Only Keyword filter
                filter_obj = Filter(
                    must=[
                        FieldCondition(
                            key="content",
                            match=MatchText(text=keyword_filter.strip())
                        )
                    ]
                )

            # Fetch records with or without filter
            if filter_obj:
                points, next_page_token = qdrant_client.scroll(
                    collection_name=collection_name,
                    scroll_filter=filter_obj,
                    limit=100
                )
            else:
                # No filters applied, fetch all records
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

            # Optional: Handle pagination if needed
            if next_page_token:
                st.info("There are more records available. Implement pagination as needed.")

        except Exception as e:
            st.error(f"Failed to retrieve records: {e}")


def add_record_section():
    """Sub-section for adding a new record."""
    st.subheader("Add Record")

    collection_name = st.text_input("Collection Name:", "default_collection")
    vector = st.text_area("Vector (comma-separated):", placeholder="e.g., 0.1, 0.2, 0.3")
    payload = st.text_area("Payload (JSON):", placeholder='{"key": "value"}')

    if st.button("Add Record"):
        if not collection_name.strip():
            st.error("Please enter a collection name.")
            return

        try:
            # Safely parse the vector
            vector = [float(x.strip()) for x in vector.split(",") if x.strip()]
            if not vector:
                st.error("Vector cannot be empty or improperly formatted.")
                return

            # Safely parse the JSON payload
            payload = json.loads(payload)

            # Generate a unique ID for the new record
            record_id = str(uuid.uuid4())

            qdrant_client.upsert(
                collection_name=collection_name,
                points=[
                    {"id": record_id, "vector": vector, "payload": payload}
                ],
            )
            st.success(f"Record added successfully with ID: {record_id}!")
            logging.info(f"Added record with ID: {record_id} to collection: {collection_name}")
        except json.JSONDecodeError:
            st.error("Invalid JSON format for payload.")
        except ValueError:
            st.error("Vector must contain valid floating-point numbers separated by commas.")
        except Exception as e:
            st.error(f"Failed to add record: {e}")
            logging.error(f"Failed to add record to collection '{collection_name}': {e}")


def edit_record_section():
    """Sub-section for editing an existing record."""
    st.subheader("Edit Record")
    st.info("Editing records is not implemented in this example.")
    # Implement editing functionality based on your requirements
    # This could involve fetching a record by ID, displaying current data, allowing modifications, and updating the record.


def delete_record_section():
    """Sub-section for deleting a record."""
    st.subheader("Delete Record")

    collection_name = st.text_input("Collection Name:", "default_collection")
    record_id = st.text_input("Record ID to Delete:")

    if st.button("Delete Record"):
        if not collection_name.strip():
            st.error("Please enter a collection name.")
            return
        if not record_id.strip():
            st.error("Please enter a Record ID to delete.")
            return

        try:
            qdrant_client.delete(
                collection_name=collection_name,
                points_selector={"ids": [record_id.strip()]}
            )
            st.success(f"Record with ID {record_id.strip()} deleted successfully!")
            logging.info(f"Deleted record with ID: {record_id.strip()} from collection: {collection_name}")
        except Exception as e:
            st.error(f"Failed to delete record: {e}")
            logging.error(f"Failed to delete record with ID '{record_id.strip()}' from collection '{collection_name}': {e}")


def view_logs():
    """Tab for viewing logs."""
    st.header("Log Viewer")

    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as log_file:
            logs = log_file.readlines()
        st.text_area("Application Logs", value="".join(logs), height=400)
    else:
        st.info("No logs available.")


if __name__ == "__main__":
    main()
