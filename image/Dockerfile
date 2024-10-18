FROM public.ecr.aws/lambda/python:3.10

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

RUN pip install --upgrade pip

# Install the specified packages
RUN pip install -r requirements.txt

# For local testing.
EXPOSE 8000

# Set IS_USING_IMAGE_RUNTIME Environment Variable
ENV IS_USING_IMAGE_RUNTIME=True

# Copy .env file for environment variable access (if needed during runtime)
COPY src/config/.env ${LAMBDA_TASK_ROOT}/.env

# Copy all files in ./src
COPY src/* ${LAMBDA_TASK_ROOT}
COPY src/rag ${LAMBDA_TASK_ROOT}/rag
COPY src/data/ ${LAMBDA_TASK_ROOT}/data/

# Load environment variables from .env at runtime
RUN python -m pip install python-dotenv

# Set environment variables from .env file for runtime use
ENV PYTHON_ENV_FILE=${LAMBDA_TASK_ROOT}/.env

# Command to run during the container startup
CMD [ "uvicorn", "app_api_handler:app", "--host", "0.0.0.0", "--port", "8000" ]