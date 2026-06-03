#!/usr/bin/env python3
"""
Auto-generate a B2B SEO blog post using DeepSeek API.
Saves output as content/posts/YYYY-MM-DD-slug.md
"""

import os
import sys
import json
import yaml
import requests
from datetime import datetime

# ---------- helpers ----------
def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def pick_keyword(config):
    keywords = config.get("keywords", [])
    posts_dir = "content/posts"
    existing = set()
    if os.path.exists(posts_dir):
        for fname in os.listdir(posts_dir):
            if fname.endswith(".md"):
                with open(os.path.join(posts_dir, fname), "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("keyword:"):
                            val = line.split(":", 1)[1].strip().strip('"').strip("'")
                            existing.add(val)
    available = [k for k in keywords if k not in existing]
    if not available:
        available = keywords
    return available[0]

def call_deepseek(api_key, model, api_url, prompt):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    resp = requests.post(
        f"{api_url}/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def build_prompt(keyword, config):
    alibaba = config.get("alibaba", {})
    product_links = alibaba.get("products", [])
    store_link = alibaba.get("store", "https://www.alibaba.com")

    return f"""You are a B2B SEO content writer for a Catholic rosary beads factory.

Write a 1100-1300 word English blog post targeting: {keyword}

Requirements:
- Write in professional B2B English, targeting wholesale buyers, importers, church procurement officers
- Include a proper title (H1)
- Use H2 and H3 subheadings
- Naturally mention 2-3 of these Alibaba product links in the body:
  {chr(10).join(['  - ' + link for link in product_links])}
- End with a conclusion
- Do NOT write meta description or JSON-LD (I will add them separately)
- The tone should be informative, trust-building, suitable for B2B wholesale buyers

Output the article in clean HTML format (use <h1>, <h2>, <h3>, <p>, <ul>, <li> tags where appropriate).
"""

def extract_title(article_text):
    import re
    match = re.search(r'<h1[^>]*>(.*?)</h1>', article_text, re.IGNORECASE)
    if match:
        return re.sub(r'<[^>]+>', '', match.group(1)).strip()
    lines = article_text.split('\n')
    for line in lines:
        line = line.strip()
        if line:
            return line[:80]
    return "Untitled"

def random_product_links(config, count=2):
    import random
    products = config.get("alibaba", {}).get("products", [])
    if not products:
        return []
    return random.sample(products, min(count, len(products)))

def build_markdown(title, keyword, article_html, config):
    today = datetime.now().strftime("%Y-%m-%d")
    slug = title.lower().replace(" ", "-").replace("&", "and")[:60]
    # Remove special chars from slug
    import re
    slug = re.sub(r'[^a-z0-9\-]', '', slug)

    store_link = config.get("alibaba", {}).get("store", "https://www.alibaba.com")
    product_links = random_product_links(config, 2)

    # Build JSON-LD FAQ (SEO)
    faq_json_ld = """<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Where can I buy wholesale catholic rosary beads?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "You can buy wholesale catholic rosary beads directly from factory on Alibaba. We supply churches, distributors, and retailers worldwide."
      }
    },
    {
      "@type": "Question",
      "name": "Do you support custom rosary beads OEM?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes, we support custom rosary beads with your logo, packaging, and material requirements. MOQ applies."
      }
    }
  ]
}
</script>"""

    # Alibaba CTA block
    cta_block = f"""
> **Looking for wholesale catholic rosary beads?**  
> Visit our Alibaba store: [{store_link}]({store_link})  
> {" ".join([f'[View Product]({link})' for link in product_links])}
"""

    content = f"""---
title: "{title}"
date: {today}T00:00:00+08:00
draft: false
keyword: "{keyword}"
tags: ["wholesale", "catholic", "rosary", "B2B"]
categories: ["Rosary Beads"]
---

{faq_json_ld}

{article_html}

---

{cta_block}
"""

    filepath = f"content/posts/{today}-{slug}.md"
    return filepath, content

# ---------- main ----------
def main():
    config = load_config()
    keyword = pick_keyword(config)
    print(f"Selected keyword: {keyword}")

    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("AI_MODEL", "deepseek-chat")
    api_url = os.environ.get("AI_API_URL", "https://api.deepseek.com/v1")

    if not api_key:
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    print("Generating title...")
    title_prompt = f"Generate a short, SEO-friendly blog post title about: {keyword}. Output ONLY the title, nothing else."
    title = call_deepseek(api_key, model, api_url, title_prompt)
    title = title.strip().strip('"').strip("'")
    print(f"Article title: {title}")

    print("Generating article content...")
    article_prompt = build_prompt(keyword, config)
    article_html = call_deepseek(api_key, model, api_url, article_prompt)

    filepath, content = build_markdown(title, keyword, article_html, config)

    # Ensure content/posts directory exists
    os.makedirs("content/posts", exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Saved to {filepath}")
    print("Done!")

if __name__ == "__main__":
    main()
