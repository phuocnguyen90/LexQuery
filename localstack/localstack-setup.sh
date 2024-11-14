#!/bin/bash
set -e

# Wait until LocalStack is ready
until awslocal sqs list-queues; do
  echo "Waiting for LocalStack SQS service..."
  sleep 2
done

# Create SQS Queue
echo "Creating SQS Queue..."
awslocal sqs create-queue --queue-name legal-rag-qa

# Create IAM Role for Lambda
echo "Creating IAM Role for Lambda..."
ROLE_ARN=$(awslocal iam create-role --role-name lambda-ex --assume-role-policy-document file://trust-policy.json | jq -r '.Role.Arn')

# Attach basic execution policy to the role
echo "Attaching execution policy to IAM Role..."
awslocal iam attach-role-policy --role-name lambda-ex --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Package the worker Lambda function
echo "Packaging Worker Lambda Function..."
cd /var/task  # Adjust this path if necessary
zip -r /tmp/worker.zip .

# Create Lambda Function
echo "Creating Lambda Function..."
awslocal lambda create-function \
    --function-name RagWorker \
    --runtime python3.8 \
    --role "$ROLE_ARN" \
    --handler work_handler.lambda_handler \
    --zip-file fileb:///tmp/worker.zip

echo "LocalStack setup completed."
