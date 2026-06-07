name: "AI-AutoBlog Hugo"
description: "Auto-generate SEO blog posts with DeepSeek/OpenAI for Hugo + GitHub Pages. "
url: "[https://github.com/createctoco/AI-AutoBlog-Hugo]"
author: "createctoco
"

keywords:
  - AI blog
  - Hugo
  - auto blog
  - DeepSeek
  - catholic gifts
  - religious wholesale

# AI-AutoBlog Hugo

Fully automated English SEO blog for catholic religious gifts / rosary beads / B2B wholesale traffic. Deploy once, never touch again.

## How It Works

```
Keywords in config.yaml → DeepSeek API generates article → Hugo builds site → GitHub Pages deploys
```

## Quick Start (5 minutes)

### 1. Fork This Repository

Click **Fork** on the top right of this page.

### 2. Add Your API Key

Go to your forked repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Value |
|------------|-------|
| `OPENAI_API_KEY` | Your DeepSeek or OpenAI API key |
| `AI_MODEL` | `deepseek-chat` (for DeepSeek) or `gpt-3.5-turbo` (for OpenAI) |
| `AI_BASE_URL` | `https://api.deepseek.com/v1` (for DeepSeek) or leave empty for OpenAI |

### 3. Edit config.yaml

Open `config.yaml` in your repo and customize:

- **alibaba_store_url**: Your Alibaba store URL
- **alibaba_rosary_url**: Your rosary product URL
- **alibaba_cross_url**: Your cross product URL
- **keywords**: Add your long-tail keywords (50+ recommended)
- **cron**: Schedule frequency (default: daily at 3am UTC)
- **review_mode**: `false` for auto-publish, `true` for manual review

### 4. Enable GitHub Actions

Go to **Actions → auto-generate-post → Enable workflow**

### 5. Enable GitHub Pages

Go to **Settings → Pages → Source: Deploy from a branch → gh-pages / (root)**

### 6. Test

Go to **Actions → auto-generate-post → Run workflow** to manually trigger your first article.

Wait 2-5 minutes, then check your site at `https://yourusername.github.io/AI-AutoBlog-Hugo/`

## Features

- **Fully automated**: Set once, articles generate on schedule forever
- **B2B SEO optimized**: Prompts tuned for wholesale buyer intent
- **Alibaba traffic引流**: Sidebar + article footer + inline links
- **Auto images**: AI-generated featured images for each article
- **SEO ready**: Hugo static site, fast loading, Google-friendly
- **Review mode**: Optional PR-based review before publishing
- **FAQ Schema**: Articles include FAQ sections for rich snippets

## File Structure

```
├── .github/workflows/
│   └── auto-generate-post.yml    # GitHub Actions workflow
├── config.yaml                     # All settings (keywords, cron, prompt, links)
├── layouts/
│   ├── partials/
│   │   └── alibaba-banner.html     # Sidebar Alibaba banner
│   └── _default/
│       └── single.html            # Article page with footer link
├── content/posts/                  # Generated articles go here
├── scripts/
│   └── generate-post.sh            # Post generation script
├── static/                         # Static assets
└── theme.toml                      # PaperMod theme config (via submodule)
```

## Customization

### Change Article Style

Edit the `prompt` section in `.github/workflows/auto-generate-post.yml`

### Change Theme

Update `theme` in `config.yaml`. PaperMod alternatives: Stack, Mainroad, even.

### Change Publish Frequency

Edit `cron` in `config.yaml`:
- `0 3 * * *` — Every day
- `0 3 */2 * *` — Every 2 days
- `0 3 * * 1` — Every Monday

## Cost

- **GitHub Pages**: Free
- **GitHub Actions**: 2000 free minutes/month (plenty for daily posts)
- **DeepSeek API**: ~$0.01-0.02 per article (1200 words)
- **Total**: Under $1/month for daily articles

## Bind Custom Domain

1. Add a `CNAME` file in `static/` with your domain
2. Configure your domain DNS: CNAME → `yourusername.github.io`
3. In repo Settings → Pages → Custom domain: enter your domain

## License

MIT License - Free to use, modify, and distribute.
