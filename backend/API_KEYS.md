# TruthPod Backend - API Key Configuration Guide

This document explains where to configure all API keys and credentials for the TruthPod backend.

## Overview

The TruthPod backend integrates with several external services:
- **NewsAPI** - For fetching real news data
- **Google Cloud (Speech & Text-to-Speech)** - For voice interactions
- **AWS S3** - For storing and serving TTS audio files
- **Sentry** - For error monitoring (optional)
- **Verification API (Gemini/Vertex)** - For news confidence scoring

## Configuration Locations

### 1. Local Development (.env file)

For local development, create a `.env` file in the `backend/` directory:

```bash
# News API
NEWSAPI_KEY=your_newsapi_key_here

# Google Cloud (Speech-to-Text and Text-to-Speech)
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# AWS S3 (for TTS audio storage)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
S3_BUCKET_NAME=your-s3-bucket-name

# Verification Provider (Gemini or Vertex AI)
GEMINI_API_URL=https://your-gemini-proxy.example.com/verify
GEMINI_API_KEY=your_gemini_api_key
# OR for Vertex AI:
VERTEX_API_ENDPOINT=https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT/locations/LOCATION/models/MODEL:predict
VERTEX_API_KEY=your_vertex_api_key

# Monitoring (optional)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_TRACES_SAMPLE_RATE=0.1

# Security
SECRET_KEY=your-secret-key-for-jwt
```

**Important**: Never commit the `.env` file to version control. It's already in `.gitignore`.

### 2. Render Deployment (Dashboard)

When deploying to Render, set these environment variables in the Render dashboard:

1. Go to your service → Environment tab
2. Add the following key-value pairs:

```
NEWSAPI_KEY = your_newsapi_key_here
GOOGLE_CLOUD_PROJECT = your-gcp-project-id
AWS_REGION = us-east-1
AWS_ACCESS_KEY_ID = your_aws_access_key
AWS_SECRET_ACCESS_KEY = your_aws_secret_key (mark as secret)
S3_BUCKET_NAME = your-s3-bucket-name
GEMINI_API_KEY = your_gemini_api_key (mark as secret)
GEMINI_API_URL = https://your-gemini-proxy.example.com/verify
SENTRY_DSN = https://your-sentry-dsn@sentry.io/project-id
SECRET_KEY = auto-generated-by-render (or your own)
```

**For Google Cloud credentials**: Since `GOOGLE_APPLICATION_CREDENTIALS` expects a file path, you have two options:
- **Option A**: Use Render's persistent disk and upload the JSON file
- **Option B**: Use [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation) and set `GOOGLE_APPLICATION_CREDENTIALS_JSON` with the entire JSON content as a secret

The `render.yaml` blueprint includes commented placeholders for all these keys.

### 3. GitHub Actions (Repository Secrets)

For CI/CD workflows that need to test provider integrations:

1. Go to your GitHub repository → Settings → Secrets and variables → Actions
2. Add repository secrets:

```
NEWSAPI_KEY
GEMINI_API_KEY
GEMINI_API_URL
VERTEX_API_KEY (if using Vertex AI)
VERTEX_API_ENDPOINT (if using Vertex AI)
GOOGLE_CLOUD_PROJECT
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
S3_BUCKET_NAME
```

The CI workflow (`.github/workflows/test.yml`) uses these secrets only when they're configured, allowing tests to run with mocks otherwise.

## How to Obtain API Keys

### NewsAPI
1. Go to [newsapi.org](https://newsapi.org/)
2. Click "Get API Key"
3. Sign up for a free account (70 requests/day) or paid plan
4. Copy your API key from the dashboard

### Google Cloud (Speech & TTS)
1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable **Cloud Speech-to-Text API** and **Cloud Text-to-Speech API**
3. Create a service account with appropriate permissions
4. Download the JSON key file
5. Set `GOOGLE_CLOUD_PROJECT` to your project ID
6. Set `GOOGLE_APPLICATION_CREDENTIALS` to the path of the JSON file

**Alternative for serverless**: Use Application Default Credentials (ADC) or Workload Identity.

### AWS S3
1. Create an AWS account and log in to the [AWS Console](https://console.aws.amazon.com/)
2. Create an S3 bucket for TTS audio files
3. Go to IAM → Users → Create user
4. Attach policy: `AmazonS3FullAccess` (or create a custom policy with only S3 permissions)
5. Create access key and save the key ID and secret
6. Set the environment variables with your credentials and bucket name

### Gemini/Vertex AI (News Verification)
1. **Gemini API**: Sign up for Google AI Studio or use a proxy endpoint
2. **Vertex AI**: Enable Vertex AI API in your Google Cloud project, configure a model endpoint
3. Set the appropriate URL and API key based on your provider

### Sentry (Optional)
1. Go to [sentry.io](https://sentry.io/)
2. Create a project for your backend
3. Copy the DSN from Project Settings → Client Keys (DSN)
4. Set `SENTRY_DSN` to enable error monitoring

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEWSAPI_KEY` | No | - | NewsAPI key for fetching real news. Falls back to mock news if not set. |
| `GOOGLE_CLOUD_PROJECT` | No | - | GCP project ID for Speech/TTS services |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | - | Path to GCP service account JSON key |
| `AWS_REGION` | No | `us-east-1` | AWS region for S3 bucket |
| `AWS_ACCESS_KEY_ID` | No | - | AWS access key for S3 |
| `AWS_SECRET_ACCESS_KEY` | No | - | AWS secret key for S3 |
| `S3_BUCKET_NAME` | No | - | S3 bucket name for TTS audio storage |
| `GEMINI_API_URL` | No | - | Gemini verification API endpoint |
| `GEMINI_API_KEY` | No | - | Gemini API key |
| `VERTEX_API_ENDPOINT` | No | - | Vertex AI model endpoint (alternative to Gemini) |
| `VERTEX_API_KEY` | No | - | Vertex AI API key |
| `SENTRY_DSN` | No | - | Sentry DSN for error monitoring |
| `SENTRY_TRACES_SAMPLE_RATE` | No | `0.1` | Fraction of transactions to trace (0.0-1.0) |
| `SECRET_KEY` | Yes | - | Secret key for JWT token signing |
| `DATABASE_URL` | No | `sqlite:///./truthpod.db` | Database connection URL |
| `REDIS_URL` | No | - | Redis URL for caching and rate limiting |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ALLOW_ORIGINS` | No | `*` | CORS allowed origins (comma-separated or `*`) |
| `RATE_LIMIT_ENABLED` | No | `0` | Set to `1` to enable rate limiting |
| `HTTPS_ENFORCE` | No | `0` | Set to `1` to reject non-HTTPS requests |

## Testing Without API Keys

The backend is designed to work gracefully without external API keys:

- **NewsAPI**: Falls back to mock news data with sample headlines
- **Google Cloud Speech/TTS**: Uses deterministic fallbacks (echoes input for STT, returns sample audio for TTS)
- **Verification**: Returns default confidence score (0.75)
- **S3**: Stores TTS audio locally in `media/tts/` directory

This allows you to develop and test core functionality without incurring API costs.

## Security Best Practices

1. **Never commit API keys** to version control
2. **Use secrets management** for production (Render's secret env vars, AWS Secrets Manager, etc.)
3. **Rotate keys regularly**, especially if they're accidentally exposed
4. **Use IAM roles** instead of access keys when running on cloud platforms (AWS, GCP)
5. **Limit permissions** for service accounts and API keys to only what's needed
6. **Enable monitoring** to detect unusual API usage patterns

## Troubleshooting

### NewsAPI not returning results
- Check that `NEWSAPI_KEY` is set correctly
- Verify your API key is active on [newsapi.org](https://newsapi.org/)
- Check rate limits (free tier: 100 requests/day)
- Look for error messages in logs: `ERROR: NewsAPI request failed`

### Google Cloud Speech/TTS not working
- Verify `GOOGLE_CLOUD_PROJECT` and `GOOGLE_APPLICATION_CREDENTIALS` are set
- Ensure the service account has `Cloud Speech Client` and `Cloud Text-to-Speech Client` roles
- Check that APIs are enabled in GCP Console
- Test with: `python -c "from google.cloud import speech; print('OK')"`

### S3 presigned URLs failing
- Verify AWS credentials are correct: `aws s3 ls s3://your-bucket-name`
- Check bucket permissions allow PutObject and GetObject
- Ensure bucket exists in the specified region
- Test with: `python -c "import boto3; s3 = boto3.client('s3'); print(s3.list_buckets())"`

### JWT authentication failing
- Ensure `SECRET_KEY` is set and consistent across all instances
- Check that device tokens are being stored correctly in the database
- Look for `401 Unauthorized` responses and check logs for details

## Support

For issues with API integrations, check:
1. Backend logs (`LOG_LEVEL=DEBUG` for detailed output)
2. Test suite: `pytest tests/ -v` (includes provider fallback tests)
3. Provider documentation links above
4. TruthPod project documentation: `TruthPod-Complete-Project-Document-V2.md`
