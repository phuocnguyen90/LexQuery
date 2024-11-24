import asyncio
import streamlit as st
from services.query_rag import query_rag
from models.query_model import QueryModel  


# Main Streamlit application
def main():
    st.title("RAG Testing GUI")

    # Input for user query
    query_text = st.text_area("Enter your query:", placeholder="Type your question here...")

    # Checkbox to enable debug mode
    debug_mode = st.checkbox("Enable Debug Mode", value=False, help="Show raw prompt and context details for debugging.")

    # Button to submit query
    if st.button("Submit Query"):
        if not query_text.strip():
            st.error("Please enter a query before submitting.")
            return

        # Run the RAG query and display the result
        with st.spinner("Processing your query..."):
            try:
                response_data = asyncio.run(run_query(query_text, debug_mode))
                display_response(response_data, debug_mode)
            except Exception as e:
                st.error(f"An error occurred: {e}")


# Asynchronous function to execute the RAG query
async def run_query(query_text: str, debug_mode: bool) -> dict:
    conversation_history=[]
    query_item = QueryModel(query_text=query_text)
    response_data = await query_rag(query_item=query_item,conversation_history=conversation_history)
    if debug_mode:
        st.session_state["debug_prompt"] = response_data.get("debug_prompt", None)
        st.session_state["retrieved_docs"] = response_data.get("retrieved_docs", [])
    return response_data


# Function to display the query response
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


# Run the Streamlit application
if __name__ == "__main__":
    main()
