# embedding_service/Dockerfile
# How to build: from root run the following build
# docker build -t embedding_service:v1.0.0 -f embedding_service/Dockerfile .
# Stage 1: Builder
FROM python:3.9-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    bzip2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Rust and Cargo using rustup
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Verify Rust and Cargo installation
RUN rustc --version && cargo --version

# Install Python dependencies
COPY embedding_service/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create necessary directories for shared_libs
RUN mkdir -p shared_libs/utils shared_libs/config shared_libs/models shared_libs/embeddings

# Copy only the necessary shared_libs modules
COPY shared_libs/shared_libs/utils/logger.py shared_libs/utils/logger.py
COPY shared_libs/shared_libs/config/ shared_libs/config/
COPY shared_libs/shared_libs/models/embed_models.py shared_libs/models/embed_models.py
COPY shared_libs/shared_libs/embeddings/ shared_libs/embeddings/
COPY shared_libs/shared_libs/__init__.py shared_libs/__init__.py
COPY shared_libs/setup.py shared_libs/setup.py

# Install shared_libs as an editable package
RUN pip install --no-cache-dir -e shared_libs

# Copy application code
COPY embedding_service/src/ src/

# Copy utils/download_model.py
COPY embedding_service/src/utils/ utils/

# Run model download
RUN python utils/download_model.py

# Stage 2: Runtime
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl-dev \
    libffi-dev \
    bzip2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from builder
COPY --from=builder /app/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy shared_libs from builder
COPY --from=builder /app/shared_libs /app/shared_libs

# Copy application code from builder
COPY --from=builder /app/src /app/src

# Copy utils from builder
COPY --from=builder /app/utils /app/utils

# Set PYTHONPATH to include shared_libs
ENV PYTHONPATH="/app/shared_libs:${PYTHONPATH}"

# Create a non-root user for security
RUN useradd -m appuser
USER appuser

# Expose port
EXPOSE 8000

# Start the server
CMD ["gunicorn", "src.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
