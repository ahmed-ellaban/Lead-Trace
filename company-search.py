import requests
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from openai import OpenAI
from prompts import Prompts
client = OpenAI(
    base_url="https://api.aimlapi.com/v1",

    # Insert your AIML API Key in the quotation marks instead of <YOUR_API_KEY>.
    api_key="18a850ef1cb44787933fc6e1260fa48e",
)

TAVILY_API_URL = "https://api.tavily.com/search"
TAVILY_API_KEY = "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"  # Replace with your real key



#####################################
# 1. SEARCH AGENT
#####################################
def search_company(company_name, max_results=20):
    """
    Sends a POST request to the Tavily Search API with a given company name.
    Returns a list of search result URLs.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TAVILY_API_KEY}"
    }

    payload = {
        "query": company_name,
        "include_answer": "advanced",
        "max_results": max_results
    }

    response = requests.post(TAVILY_API_URL, headers=headers, json=payload)
    response.raise_for_status()  # Raises an error if the request fails
    data = response.json()

    # Extract URLs from the search results (adjust according to actual API response structure)
    urls = [item.get("url") for item in data.get("results", []) if item.get("url")]
    return urls


#####################################
# 2. BROWSING PAGES AGENT
#####################################
async def fetch_url(session, url):
    """
    Asynchronously fetches the content of a URL.
    Returns the raw HTML text.
    """
    try:
        async with session.get(url, timeout=10) as response:
            return await response.text()
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return ""


def extract_text_from_html(html_content):
    """
    Parses HTML content and extracts just the text.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator=" ", strip=True)


async def parallel_scrape(urls):
    """
    Given a list of URLs, fetch them all asynchronously and return extracted text for each.
    """
    # Use a semaphore to limit concurrent requests if needed (e.g., 5 at a time)
    # sem = asyncio.Semaphore(5)
    texts = []

    async with aiohttp.ClientSession() as session:
        tasks = []
        for url in urls:
            tasks.append(fetch_url(session, url))

        html_pages = await asyncio.gather(*tasks)

    # Extract text from each HTML page
    for html in html_pages:
        text = extract_text_from_html(html)
        texts.append(text)

    return texts


#####################################
# 3. AI AGENT
#####################################
def ai_agent_process(text_blocks):
    """
    Combine or process all the text from the URLs.
    For example, you could summarize them or extract key info.
    Here, we'll just combine them into one string as a placeholder.
    """
    combined_text = "\n\n".join(text_blocks)
    response = client.chat.completions.create(
        model="deepseek-ai/deepseek-llm-67b-chat",
        messages=[
            {
                "role": "system",
                "content": Prompts.system_prompt,
            },
            {
                "role": "user",
                "content": Prompts.user_prompt.format(extracted_text=combined_text),
            },
        ],
    )

    result = response.choices[0].message.content

    return result


#####################################
# MAIN WORKFLOW
#####################################
def main(company_name):
    # 1. Search for the company
    urls = search_company(company_name)
    print(f"Found {len(urls)} URLs for '{company_name}'")

    # 2. Scrape URLs in parallel
    text_blocks = asyncio.run(parallel_scrape(urls))

    # 3. Send data to AI agent for further processing/analysis
    results = ai_agent_process(text_blocks)
    return results


if __name__ == "__main__":
    company_name = "Microsoft"  # Example
    ai_input_text = main(company_name)
    print(f"AI Agent Input:\n{ai_input_text[:500]}...")  # Print first 500 chars for brevity
