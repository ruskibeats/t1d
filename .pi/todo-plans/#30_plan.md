# Todo #30: Add rate limiting to the chat API endpoint

Status: in_progress
Owner: @worker
Tags: #backend #feature #security
Branch: main

Review the chat API endpoint at `app/api/chat.py`. Research FastAPI rate limiting options (e.g., slowapi). Implement rate limiting on `/api/v1/chat` and `/api/v1/chat/stream`. Add configuration for rate limit values.
