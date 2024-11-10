#!/bin/bash

# Entrypoint script to switch between Production and Development modes

# Check the DEVELOPMENT_MODE environment variable
if [ "$DEVELOPMENT_MODE" = "True" ]; then
    echo "Running in Development Mode..."

    # Determine which handler to run based on the CMD_HANDLER environment variable
    case "$CMD_HANDLER" in
        api)
            echo "Starting API with Uvicorn..."
            # Start the FastAPI server with Uvicorn
            uvicorn handlers.api_handler:app --host 0.0.0.0 --port 8000 --reload
            ;;
        worker)
            echo "Starting Worker..."
            # Start the Worker process
            python handlers.work_handler.py
            ;;
        combined)
            echo "Starting both API and Worker with Supervisor..."
            # Start Supervisor to manage both processes
            supervisord -c /etc/supervisord.conf
            ;;
        *)
            echo "CMD_HANDLER not set or unrecognized. Please set CMD_HANDLER to 'api', 'worker', or 'combined'."
            exit 1
            ;;
    esac
else
    echo "Running in Production Mode..."
    # Delegate to the AWS Lambda entrypoint
    exec /lambda-entrypoint.sh "$@"
fi
