# legal_qa_rag/rag_service/Dockerfile
# How to build: from root run
# docker build -t rag_service:v1.0.0 -f rag_service/Dockerfile .  
# legal_qa_rag/rag_service/Dockerfile.combined

FROM public.ecr.aws/lambda/python:3.12

# Install Supervisor
RUN yum install -y supervisor

# Set environment variable for build
ENV PYTHONUSERBASE=/tmp/python

# Install API dependencies
COPY rag_service/api_requirements.txt /tmp/api_requirements.txt
RUN pip install --no-cache-dir -r /tmp/api_requirements.txt --target /tmp/python/lib/python3.12/site-packages

# Install Worker dependencies
COPY rag_service/worker_requirements.txt /tmp/worker_requirements.txt
RUN pip install --no-cache-dir -r /tmp/worker_requirements.txt --target /tmp/python/lib/python3.12/site-packages

# Install shared libraries
COPY shared_libs/ /tmp/shared_libs/
RUN pip install -e /tmp/shared_libs --target /tmp/python/lib/python3.12/site-packages

# Copy dependencies to Lambda directories
COPY --from=builder_api /tmp/python/lib/python3.12/site-packages /var/lang/lib/python3.12/site-packages

# Copy shared libraries
COPY shared_libs/ /var/task/shared_libs/

# Copy source code
COPY rag_service/src/ /var/task/

# Set working directory
WORKDIR /var/task


# Define the CMD to point to the handler
CMD ["main.handler"]
