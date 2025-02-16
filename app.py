from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# Import your "main" function from the existing script (company_search.py)
# Adjust the import path based on your actual filename/module
from company_search import main

app = FastAPI(title="Company Search API")


@app.get("/search")
def search_company(company: str = Query(..., description="Company name to search")):
    """
    Fetch details for a given company name using the existing 'main' function
    from your project. Returns JSON with structured info.
    """
    if not company:
        raise HTTPException(
            status_code=400, detail="Missing 'company' query parameter."
        )

    try:
        # Call your existing main() logic
        result = main(company)
        # result is presumably a dict if you return JSON. If it's a string,
        # wrap it in a dict, e.g., {"ai_result": result}

        return JSONResponse(content=result, status_code=200)
    except Exception as e:
        # Return a 500 on unexpected errors
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# You can add more endpoints as needed
# e.g., /healthcheck, /docs, etc.

if __name__ == "__main__":
    # Run app via: python app.py
    # or: uvicorn app:app --host 0.0.0.0 --port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
