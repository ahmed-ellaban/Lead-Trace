# encoding: utf-8

import json
import time
import requests
import pycurl
import io
import certifi
from bs4 import BeautifulSoup
from html2text import HTML2Text
from openai import OpenAI
from prompts import Prompts
from urllib.parse import urlparse

# Configure html2text
html2text = HTML2Text()
html2text.ignore_links = False  # Keep links if needed
html2text.ignore_images = False
html2text.body_width = 0  # Disable text wrapping

client = OpenAI(
    base_url="https://api.aimlapi.com/v1",
    api_key="18a850ef1cb44787933fc6e1260fa48e",
)

TAVILY_API_URL = "https://api.tavily.com/search"
TAVILY_API_KEY = "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"

# List of domains you do not want to scrape
BANNED_DOMAINS = {
    "facebook.com",
    "twitter.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
    "github.com",
    "crunchbase",
    "zoominfo"
}

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
    scraped_texts = []
    for c, buf in zip(curl_handles, buffers):
        try:
            html = buf.getvalue().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"Error decoding response: {e}")
            html = ""

        text = extract_text_from_html(html)[:10000]  # Limit to 10000 chars
        scraped_texts.append(text)
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
    Sends the formatted text to the AI with system prompt.
    Prints usage, tokens, and cost.
    """
    start_time = time.time()

    # If content is extremely large, you might want to truncate or summarize
    max_length = 500_000  # 500k chars
    if len(formatted_text) > max_length:
        print(f"[WARNING] Content is {len(formatted_text)} chars, exceeding {max_length}.")
        print("[INFO] Truncating to first 500k characters.")
        formatted_text = formatted_text[:max_length]

    # We'll use your system prompt from the prompts module if you prefer
    system_prompt = Prompts.system_prompt

    # Make the API call
    response = client.chat.completions.create(
        model="deepseek-chat",
        max_completion_tokens=4000,
        max_tokens=4000,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": formatted_text}
        ]
    )

    # Calculate timing
    elapsed = time.time() - start_time
    print(f"[TIMING] AI agent processing took {elapsed:.2f} seconds.")

    # Get token usage from the response
    usage = response.usage
    prompt_tokens = usage.prompt_tokens
    completion_tokens = usage.completion_tokens
    total_tokens = usage.total_tokens, prompt_tokens + completion_tokens

    # Cost calculations
    # $0.0001544 per 1K prompt tokens
    # $0.0003087 per 1K completion tokens
    # $0.0004631 per call
    cost_per_call = 0.0004631
    cost_prompt = 0.0001544 * (prompt_tokens / 1000.0)
    cost_completion = 0.0003087 * (completion_tokens / 1000.0)
    total_cost = cost_per_call + cost_prompt + cost_completion

    print(f"[TOKENS] Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")
    print(f"[COST] = ${total_cost:.6f} (call: {cost_per_call}, prompt: {cost_prompt:.6f}, completion: {cost_completion:.6f})")

    # Return the final text
    return response.choices[0].message.content

###################################
# MAIN WORKFLOW
###################################
def main(company_name):
    overall_start = time.time()

    # 1. Retrieve search data from Tavily
    search_data = search_company(company_name)
    answer_text = search_data.get("answer", "(No answer provided)")
    results = search_data.get("results", [])

    # 2. Filter out unwanted (banned) domains
    filtered_results = []
    for r in results:
        url = r.get("url", "")
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Quick check to see if domain is in banned list
        # (We might check just the "root domain" part if needed)
        if any(bd in domain for bd in BANNED_DOMAINS):
            # We'll keep the search content but skip scraping
            r["skip_scraping"] = True
        else:
            r["skip_scraping"] = False

        filtered_results.append(r)

    # 3. Build a list of only the URLs we are allowed to scrape
    #    We keep them in the same order so we can align them with results
    scrape_pairs = []  # Will store (index, url)
    for i, fr in enumerate(filtered_results):
        if not fr["skip_scraping"] and fr.get("url"):
            scrape_pairs.append((i, fr["url"]))

    # 4. Scrape in parallel (only allowed URLs)
    scrape_urls = [p[1] for p in scrape_pairs]
    scraped_texts = parallel_scrape(scrape_urls)

    # 5. Put the scraped text back into the correct search result
    #    based on original index
    for (i, _), st in zip(scrape_pairs, scraped_texts):
        filtered_results[i]["extracted_content"] = st

    # 6. Build the final "formatted" text
    # Include the Tavily 'answer'
    formatted_output = [f"[TAVILY ANSWER]\n{answer_text}\n\n"]

    for idx, r in enumerate(filtered_results, start=1):
        url = r.get("url", "")
        search_content = r.get("content", "(No snippet content)")
        extracted_content = r.get("extracted_content", "(No page content)")
        # If skip_scraping is True, we also note it
        skip_flag = "[SKIPPED]" if r.get("skip_scraping") else ""

        section = (
            f"---- PAGE {idx} {skip_flag} ----\n"
            f"URL: {url}\n\n"
            f"Search Content:\n{search_content}\n\n"
            f"Extracted Content:\n{extracted_content}\n\n"
        )
        formatted_output.append(section)

    final_text = "".join(formatted_output)
    print(len(final_text))
    final_text = final_text.replace('*', '').replace('#', '').replace('(', '').replace(')', '').replace('[', '').replace(']', '').replace('\n\n', '\n').replace('   ', '  ')
    print(len(final_text))

    # 7. Send everything to the AI Agent

    result = ai_agent_process(final_text)
    result = json.loads(result.replace('```','').replace('json',''))
    overall_elapsed = time.time() - overall_start
    print(f"[TIMING] TOTAL processing time: {overall_elapsed:.2f} seconds.")

    return result

if __name__ == "__main__":
    company_name = "الزوزة للتجارة والتوزيع Company info"  # or AppsFlyer Aqua Security Armis At-Bay Augury Axonius BigID BigPanda
    result = main(company_name)
    print("----- AI Agent Output -----")
    print(result)
