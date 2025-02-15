import requests
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from openai import OpenAI
from prompts import Prompts
import pycurl
import io
import certifi

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
    Parses HTML content and extracts only the main 'about' content.
    This function removes unnecessary elements like scripts, styles,
    headers, footers, navigation, and sidebars, and then attempts to extract
    content from a <main> tag or a designated 'about' section.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove unwanted tags
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    # Try to extract content from the <main> tag if present
    main_content = soup.find("main")
    if main_content:
        return main_content.get_text(separator=" ", strip=True)

    # Fallback: Look for a div with an 'about' identifier (either class or id)
    about_section = soup.find("div", class_="about") or soup.find("div", id="about")
    if about_section:
        return about_section.get_text(separator=" ", strip=True)

    # Final fallback: Use the body content
    if soup.body:
        return soup.body.get_text(separator=" ", strip=True)

    # If no body tag exists, return all text
    return soup.get_text(separator=" ", strip=True)


def parallel_scrape(urls):
    """
    Given a list of URLs, fetch them all concurrently using pycurl's multi interface,
    extract the relevant text from each HTML page, and return the texts.
    """
    multi = pycurl.CurlMulti()
    curl_handles = []
    buffers = []

    # Setup individual Curl handles for each URL
    for url in urls:
        buf = io.BytesIO()
        c = pycurl.Curl()
        c.setopt(pycurl.URL, url)
        c.setopt(pycurl.WRITEDATA, buf)
        c.setopt(pycurl.FOLLOWLOCATION, True)
        c.setopt(pycurl.TIMEOUT, 10)  # optional timeout
        c.setopt(pycurl.CAINFO, certifi.where())
        multi.add_handle(c)
        curl_handles.append(c)
        buffers.append(buf)

    # Execute all requests concurrently
    num_active = 1
    while num_active:
        ret, num_active = multi.perform()
        if ret != pycurl.E_CALL_MULTI_PERFORM:
            break

    # Wait for all transfers to complete
    while num_active:
        multi.select(1.0)
        while True:
            ret, num_active = multi.perform()
            if ret != pycurl.E_CALL_MULTI_PERFORM:
                break

    texts = []
    # Process each handle's result
    for c, buf in zip(curl_handles, buffers):
        try:
            html = buf.getvalue().decode('utf-8', errors='ignore')
        except Exception as e:
            print("Error decoding response:", e)
            html = ""
        # Use your extraction function to get the desired text
        text = extract_text_from_html(html)
        texts.append(text)
        multi.remove_handle(c)
        c.close()

    multi.close()
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
        model="deepseek-chat",
        max_completion_tokens=4000,
        max_tokens=4000,
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
    text_blocks = parallel_scrape(urls)

    # 3. Send data to AI agent for further processing/analysis
    results = ai_agent_process(text_blocks)
    return results


if __name__ == "__main__":
    company_name = "Microsoft"  # Example
    ai_input_text = main(company_name)
    print(f"AI Agent Input:\n{ai_input_text[:500]}...")  # Print first 500 chars for brevity
