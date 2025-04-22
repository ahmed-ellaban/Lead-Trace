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
    base_url="https://api.deepseek.com",
    api_key="sk-931953d29d5947f28369b837910669d4",  # Example key; replace with real
)

bing_search = (
    "https://shtyqkcm5jvmc37bwo45yqx43i0qnbwz.lambda-url.us-east-2.on.aws/bing"
)

# Domains to skip scraping
BANNED_DOMAINS = {
    "facebook.com",
    "twitter.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
    "github.com",
    "crunchbase",
    "zoominfo",
}

###################################
# 1. SEARCH AGENT
###################################
def search_company(company_name, max_results=20):
    """
    Sends a POST request to the Bing Search API with a given company name.
    Returns the entire search response (JSON), including new fields:
      - search_results.answer_block
      - search_results.sidebar
      - search_results.results
      - search_results.questions_answers
    """
    start_time = time.time()

    payload = {
        "query": f"{company_name} Company info",
    }

    response = requests.get(bing_search, params=payload)
    response.raise_for_status()
    data = response.json()

    elapsed = time.time() - start_time
    print(f"[TIMING] Bing Search API completed in {elapsed:.2f} seconds.")
    return data

###################################
# 2. BROWSING PAGES AGENT
###################################
def extract_text_from_html(html_content):
    """
    Extracts text from the <body> tag (removing scripts, styles, etc.),
    then converts cleaned HTML to markdown using html2text.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    body = soup.body if soup.body else soup  # Fallback to entire doc if no body tag

    # Remove unnecessary tags for cleanliness
    for tag in body.find_all(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    cleaned_html = str(body)
    markdown_text = html2text.handle(cleaned_html)
    return markdown_text

def parallel_scrape(urls):
    """
    Concurrently fetches a list of URLs using pycurl's multi interface,
    extracts relevant text, and returns a list of extracted texts.
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
        # Human-like headers
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

        # Limit text length if needed
        text = extract_text_from_html(html)[:50000]
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
def ai_agent_process(final_text):
    """
    Sends final_text to the AI with system prompt, prints token usage & cost.
    """
    start_time = time.time()

    # Truncation if extremely large
    max_length = 500_000
    if len(final_text) > max_length:
        print(f"[WARNING] Content is {len(final_text)} chars (exceeds {max_length}). Truncating.")
        final_text = final_text[:max_length]

    system_prompt = Prompts.system_prompt  # from your prompts.py

    response = client.chat.completions.create(
        model="deepseek-chat",
        max_completion_tokens=4000,
        max_tokens=4000,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": final_text}
        ]
    )

    elapsed = time.time() - start_time
    print(f"[TIMING] AI agent processing took {elapsed:.2f} seconds.")

    # Token usage & cost
    usage = response.usage
    prompt_tokens = usage.prompt_tokens
    completion_tokens = usage.completion_tokens
    total_tokens = usage.total_tokens

    cost_per_call = 0
    cost_prompt = 0.27* (prompt_tokens / 1000_0000)
    cost_completion = 1.10 * (completion_tokens / 1000_0000)
    total_cost = cost_per_call + cost_prompt + cost_completion

    print(f"[TOKENS] Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")
    print(f"[COST] = ${total_cost:.6f} (call: {cost_per_call}, prompt: {cost_prompt:.6f}, completion: {cost_completion:.6f})")

    return response.choices[0].message.content

###################################
# MAIN WORKFLOW
###################################
def main(company_name):
    overall_start = time.time()

    # 1. Retrieve Bing data
    data = search_company(company_name)
    search_res = data.get("search_results", {})

    # Extract new Bing fields
    answer_block = search_res.get("answer_block", "")
    sidebar = search_res.get("sidebar", "")
    raw_results = search_res.get("results", [])
    questions_answers = search_res.get("questions_answers", [])

    # 2. Filter out banned domains from raw_results
    filtered_results = []
    for r in raw_results:
        link = r.get("link", "")
        parsed = urlparse(link)
        domain = parsed.netloc.lower()
        r["skip_scraping"] = any(bd in domain for bd in BANNED_DOMAINS)
        filtered_results.append(r)

    # 3. Build a list of up to 20 allowed URLs
    scrape_pairs = []
    allowed_count = 0
    for i, fr in enumerate(filtered_results):
        if not fr["skip_scraping"] and fr.get("link") and allowed_count < 20:
            scrape_pairs.append((i, fr["link"]))
            allowed_count += 1

    print(f"Scraping {len(scrape_pairs)} URLs out of {len(filtered_results)} results (limit 20).")

    # 4. Scrape in parallel
    scrape_urls = [p[1] for p in scrape_pairs]
    scraped_texts = parallel_scrape(scrape_urls)

    # 5. Assign scraped content back to the correct result
    for (i, _), st in zip(scrape_pairs, scraped_texts):
        filtered_results[i]["extracted_content"] = st

    # 6. Build final text to send to AI
    final_output_parts = []

    # 6a. Add top-level answer_block & sidebar
    final_output_parts.append(f"--- Bing Answer Block ---\n{answer_block}\n")
    final_output_parts.append(f"--- Bing Sidebar ---\n{sidebar}\n")

    # 6b. Show the normal search results
    for idx, fr in enumerate(filtered_results, start=1):
        link = fr.get("link", "")
        title = fr.get("title", "(No Title)")
        snippet = fr.get("snippet", "(No snippet)")
        date_str = fr.get("date", "")
        skip_flag = "[SKIPPED]" if fr.get("skip_scraping") else ""
        content = fr.get("extracted_content", "(No page content)")

        section = (
            f"---- Result #{idx} {skip_flag} ----\n"
            f"Title: {title}\n"
            f"Link: {link}\n"
            f"Date: {date_str}\n"
            f"Snippet:\n{snippet}\n\n"
            f"Extracted Content:\n{content}\n\n"
        )
        final_output_parts.append(section)

    # 6c. Include Q&A data if any
    if questions_answers:
        final_output_parts.append("--- Bing Questions & Answers ---\n")
        for q_idx, qa in enumerate(questions_answers, start=1):
            q_title = qa.get("question_title", "")
            ans = qa.get("answer", "")
            src = qa.get("source", "")
            src_url = qa.get("source_url", "")

            q_section = (
                f"Q&A #{q_idx}\n"
                f"Question Title: {q_title}\n"
                f"Answer:\n{ans}\n"
                f"Source: {src}\n"
                f"Source URL: {src_url}\n\n"
            )
            final_output_parts.append(q_section)

    # Combine everything
    final_text = "\n".join(final_output_parts)

    # Cleanup formatting
    # (Remove unwanted chars, extra whitespace, etc. as needed)
    final_text = (
        final_text.replace('*', '')
                   .replace('#', '')
                   .replace('(', '')
                   .replace(')', '')
                   .replace('[', '')
                   .replace(']', '')
    )

    print(f"Final text length (chars): {len(final_text)}")

    # 7. Send to AI Agent
    ai_response = ai_agent_process(final_text)

    # 8. Convert response from JSON (if the AI's answer is JSON)
    #    Otherwise, handle strings or partial JSON as needed
    try:
        result_data = json.loads(ai_response.replace('```','').replace('json',''))
    except json.JSONDecodeError:
        print("[WARNING] AI response did not parse as JSON. Returning raw text.")
        result_data = {"ai_response_raw": ai_response}

    overall_elapsed = time.time() - overall_start
    print(f"[TIMING] TOTAL processing time: {overall_elapsed:.2f} seconds.")
    result_data['time_used'] = overall_elapsed
    return result_data

if __name__ == "__main__":
    company_name = "upwork"  # Example
    output = main(company_name)
    print("----- AI Agent Output -----")
    print(output)
    # save output to json file
    with open(f"{company_name}.json", "w") as f:
        json.dump(output, f, indent=4)
