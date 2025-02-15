import time
import requests
import pycurl
import io
import certifi
from bs4 import BeautifulSoup
from html2text import HTML2Text
from openai import OpenAI
from prompts import Prompts

# Configure html2text
html2text = HTML2Text()
html2text.ignore_links = False  # Keep links if needed
html2text.ignore_images = False
html2text.body_width = 0  # Disable text wrapping

client = OpenAI(
    base_url="https://api.aimlapi.com/v1",
    # Insert your AIML API Key.
    api_key="18a850ef1cb44787933fc6e1260fa48e",
)

TAVILY_API_URL = "https://api.tavily.com/search"
TAVILY_API_KEY = "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"  # Replace with your real key

###################################
# 1. SEARCH AGENT
###################################
def search_company(company_name, max_results=20):
    """
    Sends a POST request to the Tavily Search API with a given company name.
    Returns the entire search response (JSON), including 'answer' & 'results'.
    """
    start_time = time.time()
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
    response.raise_for_status()
    data = response.json()

    elapsed = time.time() - start_time
    print(f"[TIMING] Tavily search completed in {elapsed:.2f} seconds.")
    return data

###################################
# 2. BROWSING PAGES AGENT
###################################
def extract_text_from_html(html_content):
    """
    Extracts text from the <body> tag (removing scripts, styles, etc.),
    then converts the cleaned HTML to markdown using html2text.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    body = soup.body if soup.body else soup  # Fallback to entire doc if no body tag

    # Remove unnecessary tags inside the body
    for tag in body.find_all(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    cleaned_html = str(body)
    markdown_text = html2text.handle(cleaned_html)
    return markdown_text
banned_domains = ("linkedin.com", "facebook.com", "twitter.com", "instagram.com", "youtube.com", "github.com", "tiktok.com", "crunchbase", "zoominfo")
def url_filter(url):
    for domain in banned_domains:
        if domain in url:
            return True
    return False

def parallel_scrape(urls):
    """
    Given a list of URLs, fetch them all concurrently using pycurl's multi interface,
    extract relevant text from each HTML page, and return a list of page texts.
    """
    if not urls:
        return []

    start_time = time.time()

    multi = pycurl.CurlMulti()
    curl_handles = []
    buffers = []

    for url in urls:
        buf = io.BytesIO()
        c = pycurl.Curl()
        c.setopt(pycurl.URL, url)
        c.setopt(pycurl.WRITEDATA, buf)
        c.setopt(pycurl.FOLLOWLOCATION, True)
        c.setopt(pycurl.TIMEOUT, 10)  # optional timeout
        c.setopt(pycurl.CAINFO, certifi.where())
        # Optionally set human-like headers
        c.setopt(pycurl.HTTPHEADER, [
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/90.0.4430.93 Safari/537.36",
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language: en-US,en;q=0.9"
        ])
        multi.add_handle(c)
        curl_handles.append(c)
        buffers.append(buf)

    # Perform requests concurrently
    num_active = 1
    while num_active:
        ret, num_active = multi.perform()
        if ret != pycurl.E_CALL_MULTI_PERFORM:
            break

    while num_active:
        multi.select(1.0)
        while True:
            ret, num_active = multi.perform()
            if ret != pycurl.E_CALL_MULTI_PERFORM:
                break

    # Process results
    scraped_texts = {}
    for c, buf in zip(curl_handles, buffers):
        try:
            html = buf.getvalue().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"Error decoding response: {e}")
            html = ""

        text = extract_text_from_html(html)[:10000]  # Limit to 10000 chars
        scraped_texts[url] = text
        multi.remove_handle(c)
        c.close()

    multi.close()

    elapsed = time.time() - start_time
    print(f"[TIMING] Parallel scrape of {len(urls)} URLs took {elapsed:.2f} seconds.")
    return scraped_texts

###################################
# 3. AI AGENT
###################################
def ai_agent_process(formatted_text):
    """
    Send the formatted text to the AI with a system prompt or instructions.
    """
    # We time the AI call
    start_time = time.time()

    # If content is extremely large, you might want to truncate or summarize
    max_length = 500_000  # 500k chars
    if len(formatted_text) > max_length:
        print(f"[WARNING] Content is {len(formatted_text)} chars, exceeding {max_length} limit.")
        print("[INFO] Truncating to first 500k characters to fit in the request.")
        formatted_text = formatted_text[:max_length]

    system_prompt = """You are a research assistant. 
    The user is providing a collection of text about a company from multiple sources. 
    Please read through the content carefully and summarize key details accurately.
    """

    response = client.chat.completions.create(
        model="deepseek-chat",
        max_completion_tokens=4000,
        max_tokens=4000,
        messages=[
            {"role": "system", "content": Prompts.system_prompt},
            {"role": "user", "content": formatted_text}
        ]
    )

    elapsed = time.time() - start_time
    print(f"[TIMING] AI agent processing took {elapsed:.2f} seconds.")

    return response.choices[0].message.content

###################################
# MAIN WORKFLOW
###################################
def main(company_name):
    overall_start = time.time()

    # 1. Get data from Tavily search
    search_data = search_company(company_name)

    # 2. Extract the short answer + results from the Tavily response
    answer_text = search_data.get("answer", "(No answer provided)")
    results = search_data.get("results", [])

    # 3. Collect URLs from the search results
    urls = [r["url"] for r in results if r.get("url") and not url_filter(r["url"])]
    print(f"[INFO] Found {len(urls)} URLs for '{company_name}'")

    # 4. Scrape those URLs in parallel
    scraped_texts = parallel_scrape(urls)

    # 5. Build the final "formatted" text
    formatted_output = [f"[TAVILY ANSWER]\n{answer_text}\n\n"]

    for i, r in enumerate(results):
        page_num = i + 1
        url = r.get("url", "")

        search_content = r.get("content", "(No snippet content)")
        # If we have fewer scraped texts than results, handle gracefully
        extracted_content = scraped_texts[i] if i < len(scraped_texts) else "(No page content)"

        section = (
            f"---- PAGE {page_num} ----\n"
            f"URL: {url}\n\n"
            f"Search Content:\n{search_content}\n\n"
            f"Extracted Content:\n{extracted_content}\n\n"
        )
        formatted_output.append(section)

    final_text = "".join(formatted_output)

    # 6. Send it to the AI Agent for further processing
    result = ai_agent_process(final_text)

    overall_elapsed = time.time() - overall_start
    print(f"[TIMING] TOTAL processing time: {overall_elapsed:.2f} seconds.")

    return result

if __name__ == "__main__":
    company_name = "BigPanda Company info"  # or AppsFlyer Aqua Security Armis At-Bay Augury Axonius BigID BigPanda
    result = main(company_name)
    print("----- AI Agent Output -----")
    print(result)
