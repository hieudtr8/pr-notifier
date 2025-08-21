import requests
import time
import os
import argparse
import sys
from urllib.parse import urlparse

# --- Configuration ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
NTFY_TOPIC = "hieudt-pr-builds-status-channel"
POLL_INTERVAL = 60 # Check every 1 minute

# --- NEW: Configuration for GitHub Enterprise ---
# If you are using GitHub Enterprise, set this to your enterprise URL.
# Otherwise, leave it as None to default to public GitHub.
# Example: GITHUB_ENTERPRISE_URL = "https://code.in.spdigital.sg"
GITHUB_ENTERPRISE_URL = "https://code.in.spdigital.sg"

# --- Helper Functions ---

def get_api_base_url(repo_url_str):
    """Determines the correct API base URL for public or enterprise GitHub."""
    if GITHUB_ENTERPRISE_URL:
        return f"{GITHUB_ENTERPRISE_URL}/api/v3"
    
    # Fallback for public github.com
    parsed_url = urlparse(repo_url_str)
    if parsed_url.hostname and parsed_url.hostname != "github.com":
         # If the repo URL is an enterprise URL but the config is not set, use it.
        return f"{parsed_url.scheme}://{parsed_url.hostname}/api/v3"
        
    return "https://api.github.com"


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
        sys.exit(1)

    API_BASE_URL = get_api_base_url(args.repo_url)
    print(f"✅ API Endpoint set to: {API_BASE_URL}")

    print(f"🚀 Starting to monitor all PRs in repository: {owner}/{repo}")
    print(f"Will check for updates every {POLL_INTERVAL} seconds. Press Ctrl+C to stop.")

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    monitored_prs = {}

    # --- Main Monitoring Loop ---
    try:
        while True:
            try:
                # --- MODIFIED: Use the dynamic API_BASE_URL ---
                prs_api_url = f"{API_BASE_URL}/repos/{owner}/{repo}/pulls"
                response = requests.get(prs_api_url, headers=headers)
                response.raise_for_status()
                open_prs_data = response.json()
                
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
                        monitored_prs[pr_number]["title"] = pr_title

                closed_prs = set(monitored_prs.keys()) - current_open_pr_numbers
                for pr_number in closed_prs:
                    print(f"🚮 PR #{pr_number} is closed or merged. Removing from monitoring.")
                    del monitored_prs[pr_number]

                if not monitored_prs:
                    print("No open PRs to monitor. Waiting...")
                else:
                    print(f"🔍 Checking status for {len(monitored_prs)} open PR(s): {list(monitored_prs.keys())}")
                
                for pr_number, data in monitored_prs.items():
                    if data["notified"]:
                        continue

                    commit_sha = data["sha"]
                    # --- MODIFIED: Use the dynamic API_BASE_URL ---
                    check_runs_url = f"{API_BASE_URL}/repos/{owner}/{repo}/commits/{commit_sha}/check-runs"
                    
                    check_response = requests.get(check_runs_url, headers=headers)
                    check_response.raise_for_status()
                    check_data = check_response.json()

                    total_checks = check_data.get("total_count", 0)
                    if total_checks == 0:
                        continue

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
                        
                        monitored_prs[pr_number]["notified"] = True

            except requests.exceptions.RequestException as e:
                print(f"❌ An API error occurred: {e}. Retrying...", file=sys.stderr)
            
            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user.")
        sys.exit(0)

if __name__ == "__main__":
    main()
