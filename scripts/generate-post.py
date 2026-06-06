#!/usr/bin/env python3
"""
Auto-generate a B2B SEO blog post using DeepSeek API.
Saves output as content/posts/YYYY-MM-DD-slug.md
Supports multiple posts per day with unique filenames.
Features:
  - Pexels API for featured images (with local images/ fallback)
  - Markdown output for TOC compatibility
  - Hero image support (Blowfish theme)
"""

import os
import sys
import re
import random
import glob
import yaml
import requests
from datetime import datetime, timezone, timedelta

# ============================================
# Load Configuration
# ============================================
def load_config():
    with open("blog-config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_alibaba(config):
    return {
        "store": config.get("alibaba_store_url", ""),
        "products": config.get("alibaba_products", [])
    }

# ============================================
# Pick Keyword (avoid duplicates, random selection)
# ============================================
def pick_keyword(config):
    keywords = config.get("keywords", [])
    if not keywords:
        print("ERROR: no keywords found in blog-config.yaml")
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
        print("All keywords used, resetting cycle...")
        available = keywords  # all used, restart cycle

    chosen = random.choice(available)
    print(f"Used keywords: {len(used)}/{len(keywords)}")
    print(f"Selected keyword: {chosen}")
    return chosen

# ============================================
# Fetch Featured Image from Pexels API
# ============================================
def fetch_pexels_image(keyword, api_key):
    """Fetch a Pexels image URL (no local download, avoid repo bloat)"""
    if not api_key:
        print("No Pexels API key provided, skipping Pexels")
        return None

    search_terms = [
        keyword.replace("wholesale", "").replace("bulk", "").replace("OEM", "").replace("guide", "").strip(),
        "catholic rosary beads",
        "rosary",
        "catholic prayer"
    ]

    for search_term in search_terms:
        if not search_term.strip():
            continue
        try:
            print(f"Searching Pexels for: {search_term}")
            response = requests.get(
                "https://api.pexels.com/v1/search",
                params={"query": search_term, "per_page": 15, "size": "large"},
                headers={"Authorization": api_key},
                timeout=15
            )
            response.raise_for_status()
            data = response.json()

            if data.get("photos"):
                photo = random.choice(data["photos"])
                image_url = photo["src"]["large2x"]
                photographer = photo.get("photographer", "Pexels")
                print(f"Pexels image URL: {image_url} (by {photographer})")
                return image_url  # Return URL directly, no local download

        except Exception as e:
            print(f"Warning: Pexels search failed for '{search_term}': {e}")
            continue

    print("Warning: Could not fetch any image from Pexels")
    return None

# ============================================
# Fallback: Random Image from Local images/ Folder
# ============================================
def fetch_local_fallback_image():
    """Pick a random image from static/images/ (no copy, avoid repo bloat)"""
    images_dir = "static/images"
    if not os.path.exists(images_dir):
        images_dir = "images"
    if not os.path.exists(images_dir):
        print("No local images/ folder found, skipping fallback")
        return None

    extensions = ('*.jpg', '*.jpeg', '*.png', '*.webp', '*.gif')
    image_files = []
    for ext in extensions:
        image_files.extend(glob.glob(os.path.join(images_dir, ext)))
        image_files.extend(glob.glob(os.path.join(images_dir, ext.upper())))

    if not image_files:
        print("No images found in images/ folder, skipping fallback")
        return None

    chosen = random.choice(image_files)
    basename = os.path.basename(chosen)
    print(f"Local fallback image: {basename}")
    return f"https://rosarysupply.com/images/{basename}"  # Absolute URL for Blowfish hotlinkFeatureImage


# ============================================
# Get Featured Image (Pexels first, local fallback)
# ============================================
def get_featured_image(keyword, pexels_api_key):
    """Try Pexels API first; fallback to local random image if fails"""
    image_url = fetch_pexels_image(keyword, pexels_api_key)
    if image_url:
        return image_url

    print("Pexels failed, trying local images/ fallback...")
    local_image = fetch_local_fallback_image()
    if local_image:
        return local_image

    print("Warning: no feature image available for this post")
    return None

# ============================================
# Call DeepSeek API
# ============================================
def call_api(prompt, api_key, model, api_url, temperature=0.85):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": 2500
    }
    resp = requests.post(
        f"{api_url}/chat/completions",
        headers=headers,
        json=payload,
        timeout=90
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

# ============================================
# Build Prompts
# ============================================
def build_title_prompt(keyword):
    return f"Generate a short, SEO-friendly blog post title about: {keyword}. Output ONLY the title, nothing else."

def build_faq_prompt(keyword, title):
    return f"""Generate 2-3 FAQ items (JSON-LD format) related to the blog post titled "{title}" with keyword "{keyword}".
The topic is Catholic religious goods wholesale/B2B.
Output ONLY valid JSON-LD for a FAQPage (schema.org format), no markdown, no explanation.
Each question should sound like a real buyer would ask. Vary the wording each time.
Example format:
{{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {{
      "@type": "Question",
      "name": "Actual buyer question here?",
      "acceptedAnswer": {{
        "@type": "Answer",
        "text": "Natural sounding answer..."
      }}
    }}
  ]
}}
"""

def build_article_prompt(keyword, alibaba):
    products = alibaba["products"]
    store = alibaba["store"]
    product_list = "\n".join([f"  - {p}" for p in products]) if products else ""

    return f"""You are an experienced B2B content writer for a Catholic rosary beads factory.
花撸AI味根除指令（必须严格执行）：
- 禁止排比句、禁止排比句、禁止排比句（重要事说三遍）
- 禁止在段落开头用「首先/其次/最后」「In conclusion」「To sum up」等模板词
- 禁止每段字数高度一致（要有短段落，甚至单句成段）
- 禁止用「Not only... but also」「Whether you... or」等工整句式
- 允许口语化表达、允许句子不完整、允许语气词
- 写作风格参考真实工厂老板/销售写的博客：直接、带点个人观点、偶尔跑题
- 必须加入具体细节：工厂实际数字、某次出货经历、和客户沟通的细节
- 段落长度随机：有的2-3句，有的只有1句，有的较长
- 用「我们」而不是「该厂」「该工厂」
- 可以适度使用反问句、感叹句

IMPORTANT CONSTRAINT: This is a CATHOLIC/CHRISTIAN religious goods website.
- ONLY write about Catholic and Christian religious items.
- NEVER write about Islamic prayer beads (tasbih, misbaha), Buddhist mala, Hindu jewelry, or any non-Catholic/non-Christian religious topics.

Write a 900-1200 word English blog post targeting: {keyword}

Requirements:
- B2B English, targeting wholesale buyers, importers, church procurement
- Use Markdown: ## for H2, ### for H3
- Do NOT follow a fixed structure — let the content flow naturally
- Vary paragraph length wildly: some 1-sentence paragraphs, some long ones
- Include 3-5 headings total (not always the same number)
- Naturally mention the Alibaba store ({store}) and 2-3 product links in the body:
{product_list}
- End with a conclusion, but keep it natural (no "In conclusion")
- Do NOT include a title (H1) — we add it separately
- Do NOT include meta description or JSON-LD (we add separately)
- Tone: like a real factory owner writing — direct, personal, occasionally imperfect English is OK

Output ONLY the article in Markdown format, no preamble.
"""

# ============================================
# Parse Title
# ============================================
def extract_title(text):
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith('# '):
            title = line.lstrip('# ').strip()
            return title[:80]
        if line and not line.startswith('#') and not line.startswith('---'):
            title = re.sub(r'[*_`#]', '', line)
            return title.strip()[:80]
    return "Untitled"

def slugify(text):
    slug = text.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '-', slug)
    return slug[:60].strip('-')

# ============================================
# Build Markdown File Content
# ============================================
def build_markdown(title, keyword, article_md, alibaba, featured_image, faq_json):
    # Use Beijing time (UTC+8) consistently
    tz_bj = timezone(timedelta(hours=8))
    now = datetime.now(tz_bj)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H%M%S")
    slug = slugify(title)
    filepath = f"content/posts/{date_str}-{slug}.md"

    # If file already exists, append time suffix to avoid collision
    if os.path.exists(filepath):
        filepath = f"content/posts/{date_str}-{time_str}-{slug}.md"

    store = alibaba["store"]
    products = alibaba["products"]
    random_links = random.sample(products, min(2, len(products))) if products else []

    iso_date = now.strftime("%Y-%m-%dT%H:%M:%S+08:00")

    # Escape double quotes in title for safe YAML
    safe_title = title.replace('"', '\\"')
    # Build front matter
    front_matter_lines = [
        '---',
        f'title: "{safe_title}"',
        f'date: {iso_date}',
        'draft: false',
        f'keyword: "{keyword}"',
        'tags: ["wholesale", "catholic", "rosary", "B2B"]',
        'categories: ["Rosary Beads"]',
    ]
    if featured_image:
        front_matter_lines.append(f'featureimage: "{featured_image}"')
        front_matter_lines.append(f'thumbnail: "{featured_image}"')
    # Store FAQ JSON in front matter (YAML multiline string)
    if faq_json and faq_json.strip():
        front_matter_lines.append('faqJson: |')
        for line in faq_json.strip().split('\n'):
            front_matter_lines.append('  ' + line)
    front_matter_lines.append('---')
    front_matter = '\n'.join(front_matter_lines)

    # CTA block in Markdown
    cta = "## Shop Wholesale Rosary Beads\n\n"
    cta += f"Looking for wholesale catholic rosary beads? Visit our **[Alibaba Store]({store})** for factory-direct pricing.\n\n"
    if random_links:
        cta += "### Featured Products\n\n"
        for link in random_links:
            cta += f"- [View Product on Alibaba]({link})\n"

    content = f"""{front_matter}

{article_md}

---

{cta}
"""

    return filepath, content

# ============================================
# Main Flow
# ============================================
def main():
    config = load_config()
    keyword = pick_keyword(config)

    api_key = os.environ.get("OPENAI_API_KEY", "")
    model = os.environ.get("AI_MODEL", "deepseek-chat")
    api_url = os.environ.get("AI_API_URL", "https://api.deepseek.com/v1")
    pexels_api_key = os.environ.get("PEXELS_API_KEY", "")

    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    # 1. Generate title
    print("Generating title...")
    title_raw = call_api(build_title_prompt(keyword), api_key, model, api_url)
    title = title_raw.strip().strip('"').strip("'")
    print(f"Title: {title}")

    # 2. Fetch featured image (Pexels API → local images/ fallback)
    print("Fetching featured image...")
    featured_image = get_featured_image(keyword, pexels_api_key)
    if featured_image:
        print(f"Featured image: {featured_image}")
    else:
        print("No featured image for this post")

    # 3. Generate article (Markdown format for TOC compatibility)
    print("Generating article...")
    alibaba = get_alibaba(config)
    article_md = call_api(build_article_prompt(keyword, alibaba), api_key, model, api_url, temperature=0.85)

    # 3b. Generate FAQ dynamically
    print("Generating FAQ...")
    try:
        faq_raw = call_api(build_faq_prompt(keyword, title), api_key, model, api_url, temperature=0.9)
        # Extract JSON from possible markdown wrapping
        faq_raw = faq_raw.strip()
        if faq_raw.startswith("```"):
            faq_raw = re.sub(r'^```[a-z]*\n|```$', '', faq_raw, flags=re.MULTILINE)
        faq_json = faq_raw.strip()
        # Validate it looks like JSON-LD
        if not faq_json.startswith('{'):
            faq_json = ""
            print("Warning: FAQ output doesn't look like JSON, skipping")
        else:
            print("FAQ generated successfully")
    except Exception as e:
        print(f"Warning: FAQ generation failed: {e}")
        faq_json = ""

    # 4. Save file
    os.makedirs("content/posts", exist_ok=True)
    filepath, content = build_markdown(title, keyword, article_md, alibaba, featured_image, faq_json)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Saved: {filepath}")
    print("Done!")

if __name__ == "__main__":
    main()
