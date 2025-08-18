# GitHub PR Notifier

A Python script that monitors GitHub pull requests and sends notifications via ntfy.sh when CI/CD checks complete.

## Features

- Monitors all open PRs in a GitHub repository
- Tracks check runs (CI/CD status) for each PR
- Sends push notifications when checks complete (success or failure)
- Automatically handles new PRs and commit updates
- Cleans up closed/merged PRs

## Setup

### 1. Install Dependencies

```bash
pip install requests
```

### 2. Get a GitHub Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate a new token with `repo` scope
3. Copy the token

### 3. Set Environment Variables

**Mac/Linux:**
```bash
export GITHUB_TOKEN="your_github_token_here"
```

**Windows (PowerShell):**
```powershell
$env:GITHUB_TOKEN="your_github_token_here"
```

### 4. Configure ntfy.sh Topic

Edit the `NTFY_TOPIC` variable in `pr-notifier.py` to use your own unique topic name:

```python
NTFY_TOPIC = "your-unique-topic-name-here"
```

### 5. Set Up ntfy.sh on Your Device

1. Install the ntfy app on your phone or visit https://ntfy.sh in your browser
2. Subscribe to your topic name

## Usage

Run the script with a GitHub repository URL:

```bash
python pr-notifier.py https://github.com/owner/repo
```

The script will:
- Start monitoring all open PRs
- Check for updates every 60 seconds (configurable via `POLL_INTERVAL`)
- Send notifications when CI/CD checks complete
- Continue running until stopped with Ctrl+C

## Configuration

You can modify these variables in the script:

- `NTFY_TOPIC`: Your ntfy.sh topic name
- `POLL_INTERVAL`: How often to check for updates (in seconds)

## Example Output

```
🚀 Starting to monitor all PRs in repository: owner/repo
Will check for updates every 60 seconds. Press Ctrl+C to stop.
👀 New PR detected: #123 'Add new feature'. Now monitoring.
🔍 Checking status for 1 open PR(s): [123]
🎉 PR #123 'Add new feature' finished with conclusion: Success
✅ Notification sent successfully for: PR #123 Add new feature Check: Success
```

## Security Notes

- Never hardcode your GitHub token in the script
- Use environment variables for sensitive information
- Choose a unique, hard-to-guess ntfy.sh topic name
- The GitHub token only needs `repo` scope permissions

## Troubleshooting

- Ensure your GitHub token has proper permissions
- Check that the repository URL is correct
- Verify your ntfy.sh topic is properly configured
- Make sure you have internet connectivity for API calls