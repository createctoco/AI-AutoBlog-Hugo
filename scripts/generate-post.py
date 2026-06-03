#!/usr/bin/env python3
"""
Auto-generate a B2B SEO blog post using DeepSeek API.
Saves output as content/posts/YYYY-MM-DD-slug.md
"""

import os
import sys
import re
import random
import yaml
import requests
from datetime import datetime

# ============================================
# Load Configuration (compatible with all formats)
# ============================================
def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()

# Read keywords (support both top-level and params.keywords)
def get_keywords(config):
    kw = config.get("keywords", [])
    if not kw:
        kw = config.get("params", {}).get("keywords", [])
    return kw

keywords = get_keywords(config)

# Read Alibaba store URL (support both underscore and dot notation)
alibaba_store = config.get("alibaba_store_url", "")
if not alibaba_store:
    alibaba_store = config.get("alibaba", {}).get("store", "https://mecrt.en.alibaba.com/")

# Read Alibaba product URLs (support ALL formats)
def get_products(config):
    products = []

    # Format 1: alibaba_products: ["url1", "url2"]
    raw1 = config.get("alibaba_products", [])
    if raw1:
        for p in raw1:
            if isinstance(p, str):
                products.append(p)
            elif isinstance(p, dict) and "url" in p:
                products.append(p["url"])

    # Format 2: alibaba_product_urls: [{url: "...", anchor: "..."}, ...]
    raw2 = config.get("alibaba_product_urls", [])
    if raw2:
        for p in raw2:
            if isinstance(p, dict) and "url" in p:
                products.append(p["url"])
            elif isinstance(p, str):
                products.append(p)

    # Format 3: alibaba.products: ["url1", "url2"]
    raw3 = config.get("alibaba", {}).get("products", [])
    if raw3:
        for p in raw3:
            if isinstance(p, str):
                products.append(p)

    return products

alibaba_products = get_products(config)

# Pick 2-3 random product links for this article
def pick_random_products(count=2):
    if not alibaba_products:
        return []
    return random.sample(alibaba_products, min(count, len(alibaba_products)))

# ============================================
# AI API Configuration
# ============================================
api_key = os.environ.get("OPENAI_API_KEY", "")
model = os.environ.get("AI_MODEL", "deepseek-chat")
api_url = os.environ.get("AI_API_URL", "https://api.deepseek.com/v1").rstrip("/")

if not api_key:
    print("ERROR: OPENAI_API_KEY environment variable not set")
    sys.exit(1)

# ============================================
# Find Next Unused Keyword
# ============================================
def pick_keyword():
    if not keywords:
        print("ERROR: no keywords found in config.yaml")
        sys.exit(1)

    posts_dir = "content/posts"
    used = set()
    if os.path.exists(posts_dir):
        for fname in os.listdir(posts_dir):
            if not fname.endswith(".md"):
                continue
            filepath = os.path.join(posts_dir, fname)
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("keyword:"):
                        val = line.split(":", 1)[1].strip().strip('"').strip("'")
                        used.add(val)

    available = [k for k in keywords if k not in used]
    if not available:
        available = keywords  # all used, restart

    chosen = available[0]
    print(f"Selected keyword: {chosen}")
    return chosen

# ============================================
# Call DeepSeek API
# ============================================
def call_api(prompt, max_tokens=2000):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }
    try:
        resp = requests.post(
            f"{api_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=90
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"ERROR calling AI API: {e}")
        sys.exit(1)

# ============================================
# Build Prompts
# ============================================
def build_title_prompt(keyword):
    return f"Generate a short, SEO-friendly blog post title about: {keyword}. Output ONLY the title, nothing else."

def build_article_prompt(keyword):
    product_list = ""
    if alibaba_products:
        product_list = "\nNaturally mention 2-3 of these Alibaba product links in the body:\n"
        for url in alibaba_products[:6]:
            product_list += f"  - {url}\n"

    return f"""You are a B2B SEO content writer for a Catholic rosary beads factory.

Write a 900-1200 word English blog post targeting: {keyword}

Requirements:
- Professional B2B English, targeting wholesale buyers, importers, church procurement
- Include a proper title as <h1>...</h1>
- Use <h2> and <h3> subheadings
- {product_list}
- End with a short conclusion
- Do NOT include meta description or JSON-LD (I will add them separately)
- Tone: informative, trust-building, suitable for B2B wholesale buyers

Output the article in clean HTML format (use <h1>, <h2>, <h3>, <p>, <ul>, <li> tags where appropriate).
Output ONLY the article, no preamble.
"""

# ============================================
# Helpers
# ============================================
def extract_title(html):
    match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
    if match:
        title = re.sub(r'<[^>]+>', '', match.group(1))
        return title.strip()[:80]
    for line in html.split('\n'):
        line = line.strip()
        if line and not line.startswith('<'):
            return line[:80]
    return "Untitled"

def slugify(text):
    slug = text.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '-', slug)
    return slug[:60].strip('-')

def build_markdown(title, keyword, article_html):
    today = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(title)
    filepath = f"content/posts/{today}-{slug}.md"

    products = pick_random_products(2)

    # JSON-LD FAQ Schema
    faq = """<script type="application/ld+json">
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

    # CTA block
    cta = f"> **Looking for wholesale rosary beads?**  \n"
    cta += f"> Visit our Alibaba store: [{alibaba_store}]({alibaba_store})  \n"
    for link in products:
        cta += f"> View product: [{link}]({link})  \n"

    content = f"""---
title: "{title}"
date: {today}T00:00:00+08:00
draft: false
keyword: "{keyword}"
tags: ["wholesale", "catholic", "rosary", "B2B"]
categories: ["Rosary Beads"]
---

{faq}

{article_html}

---

{cta}
"""

    return filepath, content

# ============================================
# Main Flow
# ============================================
def main():
    keyword = pick_keyword()

    # Generate title
    print("Generating title...")
    title_raw = call_api(build_title_prompt(keyword), max_tokens=100)
    title = title_raw.strip().strip('"').strip("'")
    print(f"Title: {title}")

    # Generate article
    print("Generating article content...")
    article_html = call_api(build_article_prompt(keyword), max_tokens=3000)
    print("Article generated successfully.")

    # Save
    os.makedirs("content/posts", exist_ok=True)
    filepath, content = build_markdown(title, keyword, article_html)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Saved: {filepath}")
    print("Done!")

if __name__ == "__main__":
    main()
