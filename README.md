# Lead-Trace

Lead-Trace is a Python service that gathers company information from search results, scrapes page content, and uses an LLM to generate structured output.

## Features
- Company search aggregation
- Parallel page scraping and text extraction
- AI-powered response generation
- FastAPI endpoint for API access
- AWS Lambda handler support

## Project Structure
- `/company_search.py` – core workflow (search, scrape, AI processing)
- `/app.py` – FastAPI server with `/search` endpoint
- `/lambda_function.py` – AWS Lambda entry point
- `/prompts.py` – AI system prompt definitions
- `/requirements.txt` – Python dependencies

## Requirements
- Python 3.10+
- pip

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running Locally (FastAPI)

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Then call:

```bash
curl "http://localhost:8000/search?company=OpenAI"
```

## Running the Script Directly

```bash
python company_search.py
```

## AWS Lambda

Use `lambda_function.lambda_handler` as the handler and pass `company` through API Gateway query parameters.

## Notes
- Configure your LLM API credentials securely before production use.
- Some domains are intentionally excluded from scraping in `BANNED_DOMAINS`.
