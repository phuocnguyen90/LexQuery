# embedding_service/Dockerfile
# How to build: from root run the following build
# docker build -t embedding_service:v1.0.0 -f embedding_service/Dockerfile .

FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies needed for Rust, Cargo, and Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    bzip2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Rust and Cargo using rustup
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y

# Add Cargo to PATH
ENV PATH="/root/.cargo/bin:${PATH}"

# Verify Rust and Cargo installation
RUN rustc --version && cargo --version

# Install Python dependencies
COPY embedding_service/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy only the necessary shared_libs modules
COPY embedding_service/src /app/src

# Copy only the necessary shared_libs modules
COPY shared_libs/shared_libs/utils/logger.py /app/shared_libs/utils/logger.py
COPY shared_libs/shared_libs/config /app/shared_libs/config
COPY shared_libs/shared_libs/embeddings /app/shared_libs/embeddings
COPY shared_libs/setup.py /app/shared_libs/setup.py
COPY shared_libs/shared_libs/models/embed_models.py /app/shared_libs/models/embed_models.py
COPY shared_libs/shared_libs/__init__.py /app/shared_libs/__init__.py


RUN pip install -e ./shared_libs

RUN python /app/src/utils/download_model.py

RUN pip install gunicorn 

# Expose port
EXPOSE 8000

# Start the server
CMD ["gunicorn", "src.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
