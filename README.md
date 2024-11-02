# Legal QA RAG Microservices

## Overview

Legal QA RAG Microservices is a modular, scalable solution designed for Legal Question Answering using Retrieval-Augmented Generation (RAG). It processes legal documents, creates embeddings, and answers user queries in natural language. The system is divided into two main services—**Formatting Service** and **RAG Service**—supported by shared utilities to maximize reusability and reduce redundancy.

### **Why Legal QA RAG Microservices?**

Legal QA RAG Microservices distinguishes itself from other similar projects through several key features and design philosophies:

1. **Back-End Focused for Seamless AWS Deployment:**
   - **Out-of-the-Box AWS Integration:** Designed to run effortlessly on AWS infrastructure, enabling quick and reliable deployment without extensive configuration.
   - **AWS CDK Infrastructure:** Utilizes AWS Cloud Development Kit (CDK) for defining and provisioning cloud infrastructure, ensuring infrastructure as code practices and easy scalability.

2. **Extremely Low Operational Cost:**
   - **Cost-Efficient Services:** Most components are built with cost-efficiency in mind, allowing microbusinesses and small-scale operations to leverage the platform without incurring significant expenses.
   - **AWS Free Tier Compatibility:** Optimized to run on AWS Free Tier services, making it accessible for startups and microbusinesses to deploy and operate without upfront costs.

3. **Modularized Compatibility and Upgradability:**
   - **Flexible LLM Provider Integration:** Supports various Large Language Model (LLM) providers, including OpenAI, Gemini, Groq, and options for local LLMs, allowing users to choose or switch providers based on their needs.
   - **HTTP and WebSocket API Support:** Compatible with both HTTP and WebSocket APIs, facilitating seamless integration with a wide range of front-end services and applications.
   - **Local Inference Capability:** Offers the ability to run local LLMs for on-premises inference, enhancing privacy and reducing dependency on external services.

4. **Optimized Data Formatter for Legal QA:**
   - **Tailored Data Processing:** Includes a basic data formatter optimized specifically for legal question answering, focusing on processing FAQs, legal documents, and citation sources to ensure accurate and relevant responses.
   - **Structured Data Handling:** Efficiently transforms raw legal texts into structured formats, enhancing the quality of embeddings and retrieval processes.

## Project Structure

```
legal_qa_rag/
    |- format_service/           # Handles formatting raw text into structured Record objects
    |- rag_service/              # Processes user queries using Retrieval-Augmented Generation
    |- shared_libs/              # Contains shared utilities, models, prompts, and configurations
    |- rag-cdk/                  # AWS infrastructure definitions for deployment using AWS CDK
    |- Dockerfile                # Base Docker setup for the services
    |- docker-compose.yml        # Config to run multiple services during development
    |- README.md                 # Project overview and instructions
```

## Main Components

- **Format Service:**
  - **Functionality:** Preprocesses raw legal text into structured chunks and stores them in a database.
  - **Capabilities:** Handles text in various forms (raw, structured, or semi-structured), ensuring that data is optimized for efficient retrieval and embedding creation.

- **RAG Service:**
  - **Functionality:** Utilizes Retrieval-Augmented Generation to answer user queries by combining document retrieval and LLM-based generation.
  - **Deployment:** Deployed as microservices using AWS Lambda, ensuring scalability and low latency.

- **Shared Libraries:**
  - **Purpose:** Provides shared components and utilities such as configuration loaders, LLM provider management, embedding creation tools, and prompting templates.
  - **Benefits:** Enhances reusability across services and reduces redundancy, streamlining development and maintenance.

## Features

- **Flexible LLM Providers:**
  - **Support for Multiple Providers:** Integrates with various LLM backends like OpenAI, Gemini, and Groq.
  - **Local LLM Integration:** Offers compatibility with local LLMs for on-premises inference, enhancing privacy and reducing reliance on external services.
  - **Easy Upgradability:** Modular design allows for straightforward addition or replacement of LLM providers as needed.

- **Microservice Architecture:**
  - **Separation of Concerns:** Each service handles distinct responsibilities, promoting maintainability and scalability.
  - **Independent Deployment:** Services can be deployed, updated, and scaled independently, ensuring flexibility in operations.

- **Embedding and Search:**
  - **FastEmbed Integration:** Utilizes FastEmbed for efficient embedding creation of legal texts.
  - **Qdrant for Retrieval:** Employs Qdrant as the vector search engine for rapid and accurate document retrieval based on embeddings.

- **AWS Integration:**
  - **Infrastructure as Code:** Uses AWS CDK for defining and managing cloud infrastructure, ensuring reproducibility and version control.
  - **Serverless Deployment:** Leverages AWS Lambda for deploying services, reducing operational overhead and costs.
  - **DynamoDB for Caching:** Implements DynamoDB for caching responses, enhancing performance and reducing latency.

- **Cost-Efficient Operations:**
  - **Optimized for AWS Free Tier:** Most services are designed to operate within the AWS Free Tier limits, making it affordable for microbusinesses to deploy and run the system.
  - **Low Operational Overhead:** Serverless architecture minimizes maintenance costs and resource usage, ensuring that operational expenses remain low.

- **API Compatibility:**
  - **HTTP and WebSocket Support:** Provides both HTTP and WebSocket APIs, enabling integration with a variety of front-end frameworks and real-time applications.
  - **Versatile Connectivity:** Facilitates connections with different front-end services, catering to diverse application requirements and user experiences.

- **Optimized Data Formatting:**
  - **Legal QA Focused:** Includes a data formatter tailored for legal question answering, emphasizing the processing of FAQs, legal documents, and citation sources.
  - **Enhanced Response Quality:** Structured data formatting ensures that embeddings and retrieval processes yield accurate and contextually relevant responses.

## Getting Started

### Prerequisites

- **AWS Account:** Ensure you have an AWS account with the necessary permissions to deploy services and infrastructure.
- **AWS CLI:** Installed and configured with your AWS credentials.
- **Docker:** Installed for containerization and local development.
- **AWS CDK:** Installed for infrastructure deployment.
- **Python 3.8+:** Required for running the services and scripts.

### Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/legal_qa_rag.git
   cd legal_qa_rag
   ```

2. **Set Up Environment Variables:**

   Create a `.env` file or set environment variables directly. Essential variables include:

   - `AWS_REGION`: AWS region (e.g., `us-east-1`)
   - `CACHE_TABLE_NAME`: DynamoDB table name for caching
   - `SQS_QUEUE_URL`: URL of the SQS queue for processing queries
   - `WORKER_LAMBDA_NAME`: Name of the worker Lambda function
   - `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`: Redis configurations for development mode

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Build and Run Services Locally (Development Mode):**

   Use Docker Compose to run multiple services during development.

   ```bash
   docker-compose up --build
   ```

### Deployment

1. **Deploy AWS Infrastructure Using CDK:**

   Navigate to the `rag-cdk-infra/` directory and deploy the infrastructure.

   ```bash
   cd rag-cdk-infra
   cdk deploy
   ```

2. **Deploy Services:**

   Services are containerized using Docker and can be deployed to AWS Lambda or ECS as per your requirements.

### Usage

1. **Submit a Query:**

   Send a `POST` request to `/submit_query` with `query_text` in the request body.

   ```json
   {
       "query_text": "What is the process for registering a business in Vietnam?"
   }
   ```

2. **Fetch Query Result:**

   Send a `GET` request to `/get_query` with `query_id` as a query parameter.

   ```bash
   GET /get_query?query_id=<your-query-id>
   ```

3. **Local Testing:**

   Use the `/local_test_submit_query` endpoint to test the RAG functionality locally without relying on worker Lambdas.

   ```json
   {
       "query_text": "What are the legal requirements for starting a business?"
   }
   ```

## Deployment Instructions

### AWS Infrastructure Setup

1. **Configure AWS CLI:**

   Ensure that the AWS CLI is installed and configured with your AWS credentials.

   ```bash
   aws configure
   ```

2. **Navigate to Infrastructure Directory:**

   ```bash
   cd rag-cdk-infra
   ```

3. **Bootstrap AWS CDK (If Not Already Bootstrapped):**

   ```bash
   cdk bootstrap
   ```

4. **Deploy Infrastructure:**

   ```bash
   cdk deploy
   ```

### DynamoDB Table Configuration

Ensure that the DynamoDB table (`CACHE_TABLE_NAME`) is set up with the following schema:

- **Primary Key:** `query_id` (String)
- **Global Secondary Index (GSI):** `cache_key-index` on `cache_key` (String)

### SQS Queue Setup

Ensure that the SQS queue (`SQS_QUEUE_URL`) is created and properly configured to receive messages for query processing.

### Lambda Function Deployment

Deploy the worker Lambda function (`WORKER_LAMBDA_NAME`) which will process the queries from the SQS queue.

## Contributing

Contributions are welcome! Please follow these steps to contribute:

1. **Fork the Repository:**

   Click the "Fork" button at the top right of the repository page.

2. **Create a New Branch:**

   ```bash
   git checkout -b feature/YourFeatureName
   ```

3. **Make Your Changes:**

   Implement your feature or bug fix.

4. **Commit Your Changes:**

   ```bash
   git commit -m "Add your descriptive commit message"
   ```

5. **Push to Your Fork:**

   ```bash
   git push origin feature/YourFeatureName
   ```

6. **Create a Pull Request:**

   Navigate to the original repository and create a pull request from your fork.

## License

This project is licensed under the [MIT License](LICENSE).

