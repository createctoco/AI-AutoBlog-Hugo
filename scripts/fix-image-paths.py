#!/usr/bin/env python3
"""Remove featureimage and thumbnail lines from all posts (fix broken image paths)."""
import os
import re

posts_dir = "content/posts"
count = 0

for fname in os.listdir(posts_dir):
    if not fname.endswith(".md"):
        continue
    fpath = os.path.join(posts_dir, fname)
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    # Remove lines starting with featureimage: or thumbnail: (with any value)
    content = re.sub(r'^\s*featureimage:\s*".*?"\s*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'^\s*thumbnail:\s*".*?"\s*$', '', content, flags=re.MULTILINE)
    # Clean up extra blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)

    if content != original:
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        count += 1
        print(f"Fixed: {fname}")

print(f"\nTotal fixed: {count} posts")
