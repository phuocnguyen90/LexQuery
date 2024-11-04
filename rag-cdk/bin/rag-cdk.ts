// bin/rag-cdk.ts

import * as cdk from 'aws-cdk-lib';
import { RagCdkStack } from '../lib/rag-cdk-stack';
import * as dotenv from 'dotenv';
import * as path from 'path';
import * as fs from 'fs';

// Load environment variables from .env file
const envPath = path.resolve(__dirname, '../shared_libs/shared_libs/config/.env');
if (fs.existsSync(envPath)) {
  dotenv.config({ path: envPath });
} else {
  console.warn(`.env file not found at path: ${envPath}. Using default values.`);
}

// Retrieve the AWS_REGION from environment variables or default to 'us-east-1'
const region = process.env.AWS_REGION || 'us-east-1';

// Optionally, retrieve the AWS account ID
const account = process.env.CDK_DEFAULT_ACCOUNT || process.env.AWS_ACCOUNT_ID;

if (!account) {
  throw new Error('AWS account ID not found. Set CDK_DEFAULT_ACCOUNT or AWS_ACCOUNT_ID in your environment.');
}

// Initialize the CDK App
const app = new cdk.App();

// Instantiate the Stack with the specified environment
new RagCdkStack(app, 'RagCdkStack', {
  env: {
    account: account,
    region: region,
  },
});

app.synth();
