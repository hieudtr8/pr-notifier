import requests
import time
import os
import argparse
import sys
from urllib.parse import urlparse

# --- Configuration ---
# It's highly recommended to set your GitHub token as an environment variable
# for security reasons, rather than hardcoding it here.
# Command for Mac/Linux: export GITHUB_TOKEN="your_token_here"
# Command for Windows (PowerShell): $env:GITHUB_TOKEN="your_token_here"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# Your ntfy.sh topic. This is like a channel name.
# Choose a unique, hard-to-guess name for your topic for privacy.
NTFY_TOPIC = "hieudt-pr-builds-status-channel"

# How often to check for new PRs and status updates (in seconds)
POLL_INTERVAL = 60 # Check every 1 minute

# --- Helper Functions ---

def parse_repo_url(url):
    """Extracts owner and repo from a GitHub repository URL."""
    try:
        path_parts = urlparse(url).path.strip("/").split("/")
        if len(path_parts) >= 2:
            owner = path_parts[0]
            repo = path_parts[1].replace('.git', '')
            return owner, repo
    except (ValueError, IndexError):
        pass
    return None, None

def send_notification(title, message, tags):
    """Sends a push notification to your ntfy.sh topic."""
    if NTFY_TOPIC == "pr-builds-status-channel-replace-this":
        print("!!! WARNING: Default ntfy.sh topic is used. Please change NTFY_TOPIC in the script.")
        return
        
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode('utf-8'),
            headers={
                "Title": title,
                "Priority": "high",
                "Tags": tags
            }
        )
        print(f"✅ Notification sent successfully for: {title}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error sending notification: {e}", file=sys.stderr)

def main():
    """Main function to monitor all PRs in a repository."""
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="Monitor all open GitHub PRs in a repository and send notifications."
    )
    parser.add_argument("repo_url", help="The full URL of the GitHub Repository.")
    args = parser.parse_args()

    # --- Initial Checks ---
    if not GITHUB_TOKEN:
        print("❌ Error: GITHUB_TOKEN environment variable not set.", file=sys.stderr)
        sys.exit(1)

    owner, repo = parse_repo_url(args.repo_url)
    if not all([owner, repo]):
        print(f"❌ Error: Invalid GitHub Repo URL: {args.repo_url}", file=sys.stderr)
        print("Example format: https://github.com/owner/repo", file=sys.stderr)
        sys.exit(1)

    print(f"🚀 Starting to monitor all PRs in repository: {owner}/{repo}")
    print(f"Will check for updates every {POLL_INTERVAL} seconds. Press Ctrl+C to stop.")

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Dictionary to keep track of PRs we are monitoring
    # Format: {pr_number: {"sha": "...", "title": "...", "notified": False}}
    monitored_prs = {}

    # --- Main Monitoring Loop ---
    try:
        while True:
            # --- Fetch all open PRs for the repository ---
            try:
                prs_api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
                response = requests.get(prs_api_url, headers=headers)
                response.raise_for_status()
                open_prs_data = response.json()
                
                # --- Update our list of monitored PRs ---
                current_open_pr_numbers = set()
                for pr in open_prs_data:
                    pr_number = pr["number"]
                    commit_sha = pr["head"]["sha"]
                    pr_title = pr["title"]
                    current_open_pr_numbers.add(pr_number)

                    if pr_number not in monitored_prs:
                        print(f"👀 New PR detected: #{pr_number} '{pr_title}'. Now monitoring.")
                        monitored_prs[pr_number] = {"sha": commit_sha, "title": pr_title, "notified": False}
                    elif monitored_prs[pr_number]["sha"] != commit_sha:
                        print(f"🔄 New commit on PR #{pr_number} '{pr_title}'. Resetting status.")
                        monitored_prs[pr_number] = {"sha": commit_sha, "title": pr_title, "notified": False}
                    else:
                        # Also update the title in case it was edited on GitHub
                        monitored_prs[pr_number]["title"] = pr_title


                # --- Clean up closed/merged PRs ---
                closed_prs = set(monitored_prs.keys()) - current_open_pr_numbers
                for pr_number in closed_prs:
                    print(f"🚮 PR #{pr_number} is closed or merged. Removing from monitoring.")
                    del monitored_prs[pr_number]

                # --- Check status for each monitored PR ---
                if not monitored_prs:
                    print("No open PRs to monitor. Waiting...")
                else:
                    print(f"🔍 Checking status for {len(monitored_prs)} open PR(s): {list(monitored_prs.keys())}")
                
                for pr_number, data in monitored_prs.items():
                    if data["notified"]:
                        continue # Already sent a notification for this commit

                    commit_sha = data["sha"]
                    check_runs_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}/check-runs"
                    
                    check_response = requests.get(check_runs_url, headers=headers)
                    check_response.raise_for_status()
                    check_data = check_response.json()

                    total_checks = check_data.get("total_count", 0)
                    if total_checks == 0:
                        continue # Checks haven't started yet

                    check_runs = check_data.get("check_runs", [])
                    completed_checks = [run for run in check_runs if run["status"] == "completed"]

                    if len(completed_checks) == total_checks:
                        failures = [run for run in completed_checks if run["conclusion"] not in ["success", "skipped", "neutral"]]
                        
                        if failures:
                            conclusion = "Failure"
                            tags = "x"
                            failed_names = ", ".join([f'"{f["name"]}"' for f in failures])
                            message = f"Checks failed: {failed_names}"
                        else:
                            conclusion = "Success"
                            tags = "tada"
                            message = f"All {total_checks} checks passed!"

                        pr_title = data.get("title", "")
                        print(f"🎉 PR #{pr_number} '{pr_title}' finished with conclusion: {conclusion}")
                        title = f"PR #{pr_number} {pr_title} Check: {conclusion}"
                        send_notification(title, message, tags)
                        
                        # Mark as notified to avoid duplicate messages
                        monitored_prs[pr_number]["notified"] = True

            except requests.exceptions.RequestException as e:
                print(f"❌ An API error occurred: {e}. Retrying...", file=sys.stderr)
            
            # Wait for the next poll
            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user.")
        sys.exit(0)

if __name__ == "__main__":
    main()
