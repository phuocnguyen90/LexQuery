# legal_qa_rag/rag_service/Dockerfile
# How to build: from root run
# docker build -t rag_service:v1.0.0 -f rag_service/Dockerfile .  
# legal_qa_rag/rag_service/Dockerfile.combined

FROM public.ecr.aws/lambda/python:3.12

# Install common dependencies
COPY rag_service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt --target /tmp/python/lib/python3.12/site-packages

# Install API dependencies
COPY rag_service/api_requirements.txt /tmp/api_requirements.txt
RUN pip install --no-cache-dir -r /tmp/api_requirements.txt --target /tmp/python/lib/python3.12/site-packages

# Install Worker dependencies
COPY rag_service/worker_requirements.txt /tmp/worker_requirements.txt
RUN pip install --no-cache-dir -r /tmp/worker_requirements.txt --target /tmp/python/lib/python3.12/site-packages

# Install shared libraries
COPY shared_libs/ ${LAMBDA_TASK_ROOT}
RUN pip install -e shared_libs

COPY rag_service/src/ ${LAMBDA_TASK_ROOT}/
COPY rag_service/src/bin/uvicorn /var/lang/bin

# Set the working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Define the CMD to point to the handler
CMD ["main.handler"]
