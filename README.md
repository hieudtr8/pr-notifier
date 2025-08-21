# GitHub PR Notifier

Monitor GitHub PR checks and get push notifications on your phone when builds complete. Supports both GitHub.com and GitHub Enterprise.

## Setup

1. **Install dependencies:**
   ```bash
   # For Node.js/TypeScript (recommended)
   npm install
   
   # For Python (legacy)
   pip install requests python-dotenv
   ```

2. **Create GitHub token:**
   - Go to GitHub Settings > Developer settings > Personal access tokens
   - Generate new token with `repo` scope
   - For Enterprise: Enable SSO if required

3. **Install ntfy app:**
   - Download from App Store/Google Play
   - Subscribe to a unique topic (e.g., `your-name-pr-builds`)

4. **Configure environment:**
   - Create `.env` file
   - Set your `GITHUB_TOKEN`
   - Set `NTFY_TOPIC` to your ntfy topic
   - Set `GITHUB_ENTERPRISE_URL` if using Enterprise
   - Optionally set `REPO_URL` for default repository

## Usage

**Node.js/TypeScript (recommended):**
```bash
# Monitor specific PR
npm run dev "https://github.com/owner/repo/pull/123"

# Monitor all PRs in repository  
npm start "https://github.com/owner/repo"

# Use default repo from .env
npm run dev
```

**Python (legacy):**
```bash
# Monitor specific PR
python scripts/pr-notifier.py "https://github.com/owner/repo/pull/123"

# Monitor all PRs in repository  
python scripts/pr-notifier.py "https://github.com/owner/repo"
```

Press `Ctrl+C` to stop monitoring.
