import requests
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from openai import OpenAI

client = OpenAI(
    base_url="https://api.aimlapi.com/v1",

    # Insert your AIML API Key in the quotation marks instead of <YOUR_API_KEY>.
    api_key="18a850ef1cb44787933fc6e1260fa48e",
)

TAVILY_API_URL = "https://api.tavily.com/search"
TAVILY_API_KEY = "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"  # Replace with your real key


def get_prompt(company_name):
    prompt = f"""
        Search for and extract the following details about the company named "{company_name}" with as much detail as possible.

        Use the following **search strategy** to ensure that all links, emails, and phone numbers are **valid** and **not** returning 404 or other error statuses:

        1. **Official Company Website**:
           - Look for "About Us," "Contact," or "Press" pages for logo, emails, phone numbers, and leadership info.
           - If any link returns a 404 or error, discard it and find a working alternative.

        2. **Official Social Media Profiles** (LinkedIn, Twitter/X, Facebook, Instagram, YouTube, TikTok, GitHub, etc.):
           - Verify that each profile link is active and does not lead to a removed or suspended page.

        3. **Reputable Business Directories & Databases** (Crunchbase, ZoomInfo, Bloomberg, AngelList):
           - If official info is missing, use these directories for approximate data (revenue, company size, leadership).
           - Ensure the directory links provided are valid and publicly accessible.

        4. **News & Press Releases** (company press statements, reputable news outlets, PR Newswire):
           - Check for recent announcements, leadership changes, or expansions.
           - Avoid linking to archived or removed pages.

        5. **Regulatory or Government Websites**:
           - For business registrations or legal filings if publicly available.
           - Verify any external link is live and not erroring.

        6. **Fallback to Well-Known Aggregators** (e.g., Wikipedia, corporate wikis, archives):
           - Use these if no direct official or reputable source can confirm a detail.
           - Confirm any aggregator link is working (no 404 or outdated references).

        If conflicting data appears, **prioritize official sources** first. 
        If no official sources are found, return the **most widely recognized** alternative. 
        If any detail remains unavailable, set it to `null`, `""`, or `[]`.

        ---

        ### Required Information:

        1. **Official Website**  
           - The primary domain representing the company.  
           - If unavailable, provide a widely used unofficial website.

        2. **Company Logo**  
           - Direct URL to the company's logo (from the official site if possible, or a trusted source).  
           - Must be a publicly accessible link (not leading to 404).

        3. **Social Media Profiles**  
           - Direct links to active and working profiles on LinkedIn, Twitter/X, Facebook, Instagram, YouTube, TikTok, GitHub, etc.  
           - No suspended or inactive pages.

        4. **Contact Details**  
           - Official & Unofficial Emails (General, Support, Sales, HR).
           - Phone Numbers (Local & International).
           - Fax Number (if available).
           - WhatsApp Business Number (if available).
           - Live Chat URL (if applicable).
           - Press Contact Page (if applicable).
           - If an official email or phone number does not exist, return a reliable working alternative.

        5. **Core Company Information**  
           - Short Description (company overview).
           - Full Legal Name and Alternative Names/Acronyms.
           - Industry or Sector.
           - Founded Year (plus brief foundation story if available).
           - Headquarters Location (City, Country).
           - Business Type (Public, Private, Nonprofit, etc.).
           - Company Size (approximate employees).
           - Annual Revenue (if publicly disclosed).
           - Registration Number (if available).
           - Stock Ticker & IPO Date (if publicly traded).

        6. **Leadership & Key People**  
           - CEO Full Name, LinkedIn, email, phone number (if available).
           - Other Key Leadership (Founders, Board Members, Executives).
           - If official contact details are missing, provide an alternative method (assistant or press contact).

        7. **Business & Operations**  
           - Branch or Subsidiary Locations.
           - Parent Company & Major Subsidiaries.
           - Notable Competitors.
           - Key Partnerships or Affiliates.
           - Major Milestones or Awards.

        8. **Career & Hiring**  
           - Job Openings or Careers Page URL.
           - Business Hours (if relevant).

        9. **News & Press**  
           - Recent Press Releases or Headlines (if available).
           - Media or Press Kit Page (if applicable).

        10. **Sources & References**  
           - A list of all URLs used to gather this data.
           - Include official sources first, then reputable or widely accepted sources.
           - Ensure each listed URL is live (not returning 404 or errors).

        ---

        ### Strict JSON Format for Output:
        ```json
        {{
          "company": "",
          "logo": "",
          "alternative_names": [],
          "description": "",
          "foundation_story": "",
          "industry": "",
          "founded_year": "",
          "headquarters": "",
          "business_type": "",
          "company_size": "",
          "revenue": "",
          "stock_ticker": "",
          "ipo_date": "",
          "website": "",
          "social_media": {{
            "linkedin": "",
            "twitter": "",
            "facebook": "",
            "instagram": "",
            "youtube": "",
            "tiktok": "",
            "github": ""
          }},
          "contact_details": {{
            "emails": {{
              "general": "",
              "support": "",
              "sales": "",
              "hr": ""
            }},
            "phone_numbers": [],
            "fax": "",
            "whatsapp": "",
            "live_chat": "",
            "press_contact": ""
          }},
          "leadership": {{
            "ceo": {{
              "full_name": "",
              "linkedin": "",
              "email": "",
              "phone_numbers": []
            }},
            "founders": [],
            "board_members": []
          }},
          "business_info": {{
            "registration_number": "",
            "parent_company": "",
            "subsidiaries": [],
            "competitors": [],
            "partnerships": []
          }},
          "milestones_awards": [],
          "careers": {{
            "job_openings_url": "",
            "business_hours": ""
          }},
          "news": {{
            "recent_press_releases": [],
            "media_kit_url": ""
          }},
          "sources": []
        }}
        Final Instructions:
        Return only this JSON object with no extra text.
        Discard any 404 or invalid links and find a working alternative instead.
        If any detail is unavailable, set it to null, "", or []. """
    return prompt


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
                "content": "You are an AI assistant who knows everything.",
            },
            {
                "role": "user",
                "content": "Tell me, why is the sky blue?"
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
