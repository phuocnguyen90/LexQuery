import asyncio
import streamlit as st
import os
import pandas as pd
import numpy as np
from services.query_rag import query_rag
from models.query_model import QueryModel
from services.qdrant_init import initialize_qdrant
from shared_libs.config import Config
from qdrant_client.http.models import Filter, FieldCondition, MatchText
from shared_libs.utils.logger import Logger
from shared_libs.config.app_config import AppConfigLoader

# Load configuration from shared_libs
config = Config.load()
config_loader = AppConfigLoader()

# Initialize Qdrant client (replace with your Qdrant setup)

qdrant_client = initialize_qdrant()

# Developer log file is set by the logger; tester (raw) log file is defined as:
DEV_LOG_FILE = "/tmp/local_data/project_logs.log"
TESTER_LOG_FILE = "/tmp/local_data/raw_response.log"

logger = Logger.get_logger("RAG_GUI")

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
                # Log the raw query text at debug level if needed
                logger.debug("Sending raw query text: %s", query_text)
                
                # Execute the RAG query (which itself logs raw input/output)
                response_data = asyncio.run(run_query(query_text, debug_mode, rerank_option, keyword_gen_option))
                
                # Optionally, log or process additional fields here...
                log_query_data(query_text, response_data)
                display_response(response_data, debug_mode)
            except Exception as e:
                st.error(f"An error occurred: {e}")
                logger.error("Error processing query '%s': %s", query_text, e)

async def run_query(query_text: str, debug_mode: bool, rerank: bool, keyword_gen_option: bool) -> dict:
    conversation_history = []
    query_item = QueryModel(query_text=query_text)
    response_data = await query_rag(
        query_item=query_item, 
        conversation_history=conversation_history, 
        rerank=rerank, 
        keyword_gen=keyword_gen_option
    )
    return response_data

def display_response(response_data: dict, debug_mode: bool):
    query_response = response_data["query_response"]
    retrieved_docs = response_data.get("retrieved_docs", [])

    st.subheader("Generated Answer")
    st.write(query_response.response_text)

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
    st.write(f"**Query**: {query_response.query_text}")
    st.write(f"**Timestamp**: {query_response.timestamp}")

def log_query_data(query_text: str, response_data: dict):
    # Example logging to the developer log (if desired)
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
        if not collection_name.strip():
            st.error("Please enter a collection name.")
            return

        try:
            filter_obj = None
            if record_id_filter.strip() and keyword_filter.strip():
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
                filter_obj = Filter(
                    must=[
                        FieldCondition(
                            key="record_id",
                            match=MatchText(text=record_id_filter.strip())
                        )
                    ]
                )
            elif keyword_filter.strip():
                filter_obj = Filter(
                    must=[
                        FieldCondition(
                            key="content",
                            match=MatchText(text=keyword_filter.strip())
                        )
                    ]
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
        if not collection_name.strip():
            st.error("Please enter a collection name.")
            return
        try:
            vector = [float(x.strip()) for x in vector.split(",") if x.strip()]
            if not vector:
                st.error("Vector cannot be empty or improperly formatted.")
                return
            import json, uuid
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
            logger.info(f"Deleted record with ID: {record_id.strip()} from collection: {collection_name}")
        except Exception as e:
            st.error(f"Failed to delete record: {e}")
            logger.error(f"Failed to delete record with ID '{record_id.strip()}' from collection '{collection_name}': {e}")

def view_logs():
    st.header("Log Viewer")
    # Create two sub-tabs: one for Developer Logs and one for Tester Logs
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
