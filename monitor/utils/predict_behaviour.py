# utils/predict_behavior.py

import os
import json
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from together import Together
import re
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
TOGETHER_MODEL = "lgai/exaone-deep-32b"
client = Together(api_key=TOGETHER_API_KEY)

def fetch_web_content(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text(separator=" ", strip=True)[:2000]
    except Exception as e:
        print(f"⚠️ Failed to fetch content: {e}")
        return ""

def analyze_query_together_ai(query, url=None, hour=None):
    context_text = fetch_web_content(url) if url else ""

    prompt = f"""
You are an AI safety analyst. Analyze the following query and website content.

Query: "{query}"
Website Content: "{context_text}"
Current Hour: {hour}

Label the content as one of the following:
- risky (e.g., sexual, suicidal, violent, or inappropriate intent)
- partial_risky (e.g., late-night browsing of entertainment or unrelated non-educational content)
- safe (educational or non-problematic content)

Rules:
- If the query or website is about education, learning, academics, tutorials, study-related topics, politics, current affairs, or technology, it is always considered safe — regardless of time, context, or other factors.
- If the query or content is related to entertainment, games, or non-educational topics and accessed late (after 22:00), mark it as partial_risky.
- Mark as risky only if the intent is harmful (e.g., sexual, suicidal, violent).

Only if the verdict is risky or partial_risky, respond with:

- `verdict`: one of risky, partial_risky, or safe
- `reason`: short reason (3-5 words)
- `summary`: concise explanation of 4-5 lines

Respond in JSON format:
{{
  "verdict": "risky" | "partial_risky" | "safe",
  "reason": "...",
  "summary": "..." (optional, only if verdict is risky)
}}
"""

    try:
        response = client.chat.completions.create(
            model=TOGETHER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        reply = response.choices[0].message.content.strip()
        print(f"📦 LLM Raw Output: {repr(reply)}")

        parsed = extract_json_from_response(reply)
        if not parsed:
            return "safe", "", ""

        verdict = parsed.get("verdict", "safe").strip().lower()
        reason = parsed.get("reason", "").strip()
        summary = parsed.get("summary", "").strip() if verdict == "risky" else ""

        return verdict, reason, summary

    except Exception as e:
        print(f"❌ Together.ai error: {e}")
        return "safe", "", ""

def predict_behavior(input_data):
    query = input_data.get("query", "")
    url = input_data.get("url", "")
    hour = datetime.now().hour

    print(f"\n🧠 Analyzing query with Together.ai: {query}")
    verdict, short_reason, brief_summary = analyze_query_together_ai(query, url, hour)

    # Return all fields as a dictionary for safe unpacking
    return {
        "verdict": verdict,
        "reason": short_reason,
        "summary": brief_summary if verdict == "risky" else ""
    }

def extract_json_from_response(reply: str) -> dict:
    """
    Safely extract and parse JSON from LLM reply, whether it's in triple backticks
    or inline.
    """
    try:
        # Prefer triple backtick JSON block
        code_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", reply, re.DOTALL)
        if code_match:
            return json.loads(code_match.group(1).strip())

        # Otherwise try all JSON-looking blocks and parse the first that works
        matches = re.findall(r'\{.*?\}', reply, re.DOTALL)
        for match in reversed(matches):  # reverse for better chance of full block
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

        print(f"⚠️ No valid JSON block found in: {repr(reply)}")
        return {}
    except Exception as e:
        print(f"❌ JSON extraction failed: {e}")
        return {}
