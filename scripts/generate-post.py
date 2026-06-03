#!/usr/bin/env python3
import os
import sys
import re
import random
import yaml
import requests
from datetime import datetime

# ====== 配置 ======
def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_keywords(config):
    return config.get("keywords", [])

def get_alibaba(config):
    return {
        "store": config.get("alibaba_store", ""),
        "products": config.get("alibaba_products", [])
    }

# ====== 选关键词 ======
def pick_keyword(config):
    keywords = get_keywords(config)
    if not keywords:
        print("ERROR: no keywords found in config.yaml")
        sys.exit(1)

    # 读取已用的关键词
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
        available = keywords  # 全部用过了，重新轮询

    chosen = available[0]
    print(f"Selected keyword: {chosen}")
    return chosen

# ====== 调用 DeepSeek API ======
def call_api(prompt, api_key, model, api_url):
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
        timeout=90
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

# ====== 构建 Prompt ======
def build_title_prompt(keyword):
    return f"Generate a short, SEO-friendly blog post title about: {keyword}. Output ONLY the title, nothing else."

def build_article_prompt(keyword, alibaba):
    products = alibaba["products"]
    store = alibaba["store"]
    product_list = "\n".join([f"  - {p}" for p in products]) if products else ""

    return f"""You are a B2B SEO content writer for a Catholic rosary beads factory.

Write a 900-1200 word English blog post targeting: {keyword}

Requirements:
- Professional B2B English, targeting wholesale buyers, importers, church procurement
- Include a proper title as <h1>...</h1>
- Use <h2> and <h3> subheadings
- Output in clean HTML (use <p>, <ul>, <li>, <h2>, <h3> tags)
- Naturally mention 2-3 Alibaba product links in the body (use these if available):
{product_list}
- End with a short conclusion
- Do NOT include meta description or JSON-LD
- Tone: informative, trust-building, B2B wholesale focused

Output the article in HTML format.
"""

# ====== 解析标题 ======
def extract_title(html):
    match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
    if match:
        title = re.sub(r'<[^>]+>', '', match.group(1))
        return title.strip()[:80]
    # fallback: 取第一行非空的
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

# ====== 构建 Markdown 文件内容 ======
def build_markdown(title, keyword, article_html, alibaba):
    today = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(title)
    filepath = f"content/posts/{today}-{slug}.md"

    store = alibaba["store"]
    products = alibaba["products"]
    random_links = random.sample(products, min(2, len(products))) if products else []

    # JSON-LD FAQ
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

    # 文章末尾 CTA
    cta = "> **Looking for wholesale rosary beads?**  \n"
    cta += f"> Visit our Alibaba store: [{store}]({store})  \n"
    for link in random_links:
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

# ====== 主流程 ======
def main():
    config = load_config()
    keyword = pick_keyword(config)

    api_key = os.environ.get("OPENAI_API_KEY", "")
    model = os.environ.get("AI_MODEL", "deepseek-chat")
    api_url = os.environ.get("AI_API_URL", "https://api.deepseek.com/v1")

    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    # 1. 生成标题
    print("Generating title...")
    title_raw = call_api(build_title_prompt(keyword), api_key, model, api_url)
    title = title_raw.strip().strip('"').strip("'")
    print(f"Title: {title}")

    # 2. 生成正文
    print("Generating article...")
    alibaba = get_alibaba(config)
    article_html = call_api(build_article_prompt(keyword, alibaba), api_key, model, api_url)

    # 3. 保存文件
    os.makedirs("content/posts", exist_ok=True)
    filepath, content = build_markdown(title, keyword, article_html, alibaba)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Saved: {filepath}")
    print("Done!")

if __name__ == "__main__":
    main()
