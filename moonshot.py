import time
from typing import *
import os
import json

from openai import OpenAI
from openai.types.chat.chat_completion import Choice

client = OpenAI(
    api_key="sk-GcD3OHWHbR11VdVLIYPl9mX21AbmU6bldRQtsX3dmydXkpZs",
    # Replace with your API Key from the Moonshot open platform
    base_url="https://api.moonshot.cn/v1",
)


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


def search_impl(arguments: Dict[str, Any]) -> Any:
    """
    When using the search tool provided by Moonshot AI, simply return the arguments unchanged.

    If you want to use another model and retain the web search functionality,
    modify this implementation accordingly while keeping the function signature unchanged.

    This ensures maximum compatibility across different models without breaking the code.
    """
    return arguments


def chat(messages) -> Choice:
    completion = client.chat.completions.create(
        model="moonshot-v1-128k",
        messages=messages,
        temperature=0.3,
        tools=[
            {
                "type": "builtin_function",
                "function": {
                    "name": "$web_search",
                },
            }
        ]
    )
    return completion.choices[0]


def company_search(company_name: str = "Apple Inc."):
    messages = [
        {"role": "system",
         "content": "You are Vitural Assitant that will search the web for information about a company, and return only json response in english."},
    ]

    messages.append({
        "role": "user",
        "content": get_prompt(company_name),
    })

    finish_reason = None
    while finish_reason is None or finish_reason == "tool_calls":
        choice = chat(messages)
        finish_reason = choice.finish_reason
        if finish_reason == "tool_calls":
            messages.append(choice.message)
            for tool_call in choice.message.tool_calls:
                tool_call_name = tool_call.function.name
                tool_call_arguments = json.loads(tool_call.function.arguments)
                if tool_call_name == "$web_search":
                    tool_result = search_impl(tool_call_arguments)
                else:
                    tool_result = f"Error: unable to find tool by name '{tool_call_name}'"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call_name,
                    "content": json.dumps(tool_result),
                })

    print(choice.message.content)


if __name__ == '__main__':
    start = time.time()
    result =company_search("360 home offers")
    print(result)
    print(f"Time taken: {time.time() - start:.2f} seconds")
