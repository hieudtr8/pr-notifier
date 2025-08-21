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
   - For GitHub Enterprise: Enable SSO if required

3. **Install ntfy app:**
   - Download from App Store/Google Play
   - Subscribe to a unique topic (e.g., `your-name-pr-builds`)

4. **Configure environment:**
   - Create `.env` file based on `.env.example`
   - Set your `GITHUB_TOKEN`
   - Set `NTFY_TOPIC` to your ntfy topic
   - Optionally set `REPO_URL` for default repository (supports both GitHub.com and Enterprise)
   - Optionally set `SPECIFIC_PR_NUMBERS` for monitoring specific PRs only (comma-separated list)

## Usage

**Node.js/TypeScript (recommended):**
```bash
# Monitor specific PR
npm run dev "https://github.com/owner/repo/pull/123"

# Monitor all PRs in repository  
npm start "https://github.com/owner/repo"

# Monitor only specific PR numbers (set SPECIFIC_PR_NUMBERS in .env)
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

## Features

### Monitor Specific PR Numbers

You can configure the application to monitor only specific PR numbers within a repository by setting the `SPECIFIC_PR_NUMBERS` environment variable:

```bash
# In your .env file
SPECIFIC_PR_NUMBERS="123,456,789"
```

When `SPECIFIC_PR_NUMBERS` is set:
- The application will only monitor the specified PR numbers
- Other PRs in the repository will be ignored
- Works only when monitoring a repository (not when monitoring a single PR URL)
- PR numbers should be separated by commas

**Examples:**
- `SPECIFIC_PR_NUMBERS="123"` - Monitor only PR #123
- `SPECIFIC_PR_NUMBERS="123,456,789"` - Monitor PRs #123, #456, and #789
- Leave empty or unset to monitor all PRs in the repository
