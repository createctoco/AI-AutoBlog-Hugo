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
import shutil
import glob
import yaml
import requests
from datetime import datetime, timezone

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
    """Try to fetch a relevant image from Pexels API"""
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
                # Pick a random image from top results
                photo = random.choice(data["photos"])
                image_url = photo["src"]["large2x"]

                # Download the image
                img_response = requests.get(image_url, timeout=30)
                img_response.raise_for_status()

                # Save to static/images/
                os.makedirs("static/images", exist_ok=True)
                timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}-pexels.jpg"
                filepath = f"static/images/{filename}"

                with open(filepath, "wb") as f:
                    f.write(img_response.content)

                photographer = photo.get("photographer", "Pexels")
                print(f"Pexels image saved: {filepath} (by {photographer})")
                return f"/images/{filename}"

        except Exception as e:
            print(f"Warning: Pexels search failed for '{search_term}': {e}")
            continue

    print("Warning: Could not fetch any image from Pexels")
    return None

# ============================================
# Fallback: Random Image from Local images/ Folder
# ============================================
def fetch_local_fallback_image():
    """Pick a random image from the repo's images/ folder as fallback when Pexels API fails"""
    images_dir = "images"
    if not os.path.exists(images_dir):
        print("No local images/ folder found, skipping fallback")
        return None

    # Supported image extensions
    extensions = ('*.jpg', '*.jpeg', '*.png', '*.webp', '*.gif')
    image_files = []
    for ext in extensions:
        image_files.extend(glob.glob(os.path.join(images_dir, ext)))
        image_files.extend(glob.glob(os.path.join(images_dir, ext.upper())))

    if not image_files:
        print("No images found in images/ folder, skipping fallback")
        return None

    # Pick a random image
    chosen = random.choice(image_files)
    basename = os.path.basename(chosen)
    print(f"Using local fallback image: {basename}")

    # Copy to static/images/ with a unique name
    os.makedirs("static/images", exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    ext = os.path.splitext(chosen)[1].lower()
    filename = f"{timestamp}-local{ext}"
    dest = f"static/images/{filename}"

    shutil.copy2(chosen, dest)
    print(f"Local image copied to: {dest}")
    return f"/images/{filename}"

# ============================================
# Get Featured Image (Pexels first, local fallback)
# ============================================
def get_featured_image(keyword, pexels_api_key):
    """Try Pexels API first, fall back to local images/ folder"""
    # 1. Try Pexels API
    image_path = fetch_pexels_image(keyword, pexels_api_key)
    if image_path:
        return image_path

    # 2. Fallback to local images/ folder
    print("Pexels failed or unavailable, using local fallback from images/ folder...")
    image_path = fetch_local_fallback_image()
    if image_path:
        return image_path

    # 3. No image at all
    print("Warning: No featured image available for this post")
    return None

# ============================================
# Call DeepSeek API
# ============================================
def call_api(prompt, api_key, model, api_url):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
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

def build_article_prompt(keyword, alibaba):
    products = alibaba["products"]
    store = alibaba["store"]
    product_list = "\n".join([f"  - {p}" for p in products]) if products else ""

    return f"""You are a B2B SEO content writer for a Catholic rosary beads factory.

IMPORTANT CONSTRAINT: This is a CATHOLIC/CHRISTIAN religious goods website.
- ONLY write about Catholic and Christian religious items.
- NEVER write about Islamic prayer beads (tasbih, misbaha), Buddhist mala, Hindu jewelry, or any non-Catholic/non-Christian religious topics.
- If the keyword is about non-Catholic content, interpret it from a Catholic wholesale supplier's perspective ONLY, or write about a related Catholic product instead.

Write a 900-1200 word English blog post targeting: {keyword}

Requirements:
- Professional B2B English, targeting wholesale buyers, importers, church procurement
- Use Markdown format: ## for H2 headings, ### for H3 headings
- Use proper Markdown: **bold**, *italic*, bullet lists with - or *
- Include 4-6 sections with ## headings (each section 150-250 words)
- Naturally mention the Alibaba store ({store}) and 2-3 product links in the body:
{product_list}
- End with a short conclusion section
- Do NOT include a title (H1) - we add it separately
- Do NOT include meta description or JSON-LD
- Tone: informative, trust-building, suitable for B2B wholesale buyers

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
def build_markdown(title, keyword, article_md, alibaba, featured_image):
    now = datetime.now(timezone.utc)
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

    # Build front matter
    front_matter_lines = [
        '---',
        f'title: "{title}"',
        f'date: {iso_date}',
        'draft: false',
        f'keyword: "{keyword}"',
        'tags: ["wholesale", "catholic", "rosary", "B2B"]',
        'categories: ["Rosary Beads"]',
    ]
    if featured_image:
        front_matter_lines.append(f'featureimage: "{featured_image}"')
        front_matter_lines.append(f'thumbnail: "{featured_image}"')
    front_matter_lines.append('---')
    front_matter = '\n'.join(front_matter_lines)

    # JSON-LD FAQ
    faq = '<script type="application/ld+json">\n'
    faq += '{\n'
    faq += '  "@context": "https://schema.org",\n'
    faq += '  "@type": "FAQPage",\n'
    faq += '  "mainEntity": [\n'
    faq += '    {\n'
    faq += '      "@type": "Question",\n'
    faq += '      "name": "Where can I buy wholesale catholic rosary beads?",\n'
    faq += '      "acceptedAnswer": {\n'
    faq += '        "@type": "Answer",\n'
    faq += '        "text": "You can buy wholesale catholic rosary beads directly from factory on Alibaba. We supply churches, distributors, and retailers worldwide."\n'
    faq += '      }\n'
    faq += '    },\n'
    faq += '    {\n'
    faq += '      "@type": "Question",\n'
    faq += '      "name": "Do you support custom rosary beads OEM?",\n'
    faq += '      "acceptedAnswer": {\n'
    faq += '        "@type": "Answer",\n'
    faq += '        "text": "Yes, we support custom rosary beads with your logo, packaging, and material requirements. MOQ applies."\n'
    faq += '      }\n'
    faq += '    }\n'
    faq += '  ]\n'
    faq += '}\n'
    faq += '</script>'

    # CTA block in Markdown
    cta = "## Shop Wholesale Rosary Beads\n\n"
    cta += f"Looking for wholesale catholic rosary beads? Visit our **[Alibaba Store]({store})** for factory-direct pricing.\n\n"
    if random_links:
        cta += "### Featured Products\n\n"
        for link in random_links:
            cta += f"- [View Product on Alibaba]({link})\n"

    content = f"""{front_matter}

{faq}

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
    article_md = call_api(build_article_prompt(keyword, alibaba), api_key, model, api_url)

    # 4. Save file
    os.makedirs("content/posts", exist_ok=True)
    filepath, content = build_markdown(title, keyword, article_md, alibaba, featured_image)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Saved: {filepath}")
    print("Done!")

if __name__ == "__main__":
    main()
