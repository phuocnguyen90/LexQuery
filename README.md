# Legal QA RAG Microservices

This project is a modular, scalable microservices-based solution for Legal Question Answering using Retrieval-Augmented Generation (RAG). It processes legal documents, creates embeddings, and answers user queries in natural language. The system is divided into two main services—**Formatting Service** and **RAG Service**—supported by shared utilities to maximize reusability and reduce redundancy.

## Project Structure

```
legal_qa_rag/
    |- format_service/           # Handles formatting raw text into structured Record objects
    |- rag_service/              # Processes user queries using Retrieval-Augmented Generation
    |- shared_libs/              # Contains shared utilities, models, prompts, and configurations
    |- rag-cdk-infra/            # AWS infrastructure definitions for deployment using AWS CDK
    |- Dockerfile                # Base Docker setup for the services
    |- docker-compose.yml        # Config to run multiple services during development
    |- README.md                 # Project overview and instructions
```

### Main Components
- **Format Service**: Preprocesses raw legal text into structured chunks and stores them in a database. Handles text in different forms (raw, structured, or semi-structured).
- **RAG Service**: Uses Retrieval-Augmented Generation to answer user queries by combining document retrieval and LLM-based generation. Deployed as microservices using AWS Lambda.
- **Shared Libraries**: Shared components for utilities like configuration loading, LLM provider management, embedding creation, and prompting templates.

### Features
- **Flexible LLM Providers**: Supports various LLM backends such as OpenAI, Gemini, and Groq through configurable providers.
- **Microservice Design**: Each service has its own responsibilities, promoting separation of concerns and scalability.
- **Embedding and Search**: Uses FastEmbed and Qdrant to embed legal text and perform document retrieval.
- **AWS Integration**: Deployable to AWS using Lambda and DynamoDB, with infrastructure defined via AWS CDK.

## Getting Started
### Prerequisites
- **Python 3.10+**
- **Docker** and **Docker Compose**
- **AWS CLI** and **AWS CDK** for deployment

### Local Setup
1. **Clone the Repo**:
   ```bash
   git clone https://github.com/yourusername/legal_qa_rag.git
   cd legal_qa_rag
   ```
2. **Install Dependencies**:
   - Install shared libraries:
     ```bash
     cd shared_libs && pip install -e .
     ```
   - Install service dependencies via Docker:
     ```bash
     docker-compose build
     ```

3. **Environment Setup**:
   - Update `.env` files for each service in `shared_libs/config` to include API keys and other configuration details.

4. **Run Services Locally**:
   ```bash
   docker-compose up
   ```

### Deployment
- **Infrastructure as Code**: Deploy to AWS with `cdk deploy` in `rag-cdk-infra`. Ensure AWS credentials are set up and all required environment variables are configured in AWS Secrets Manager or `.env` files.

## Usage
- **Formatting Service**: Submit raw legal text to format into structured chunks.
- **RAG Service**: Send user queries to receive detailed answers with relevant citations from legal documents.

### Example Request (RAG Service)
```json
POST /submit_query
{
  "query_text": "Doanh nghiệp có được đặt tên bằng tiếng Anh không?"
}
```

### Response Example
```json
{
  "query_text": "Doanh nghiệp có được đặt tên bằng tiếng Anh không?",
  "response_text": "Theo quy định trong [Mã tài liệu: QA_750F0D91], doanh nghiệp có thể đặt tên bằng tiếng Anh.",
  "sources": ["QA_750F0D91"]
}
```

## Contributing
Feel free to submit issues, create pull requests, or suggest features. Contributions are welcome!

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

