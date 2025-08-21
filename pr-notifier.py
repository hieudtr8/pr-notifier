import requests
import time
import os
import argparse
import sys
from urllib.parse import urlparse
from dotenv import load_dotenv

# --- Load configuration from .env file ---
load_dotenv()

# --- Configuration ---
# The script prioritizes environment variables, falling back to the .env file.
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
NTFY_TOPIC = os.getenv("NTFY_TOPIC")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 60))
GITHUB_ENTERPRISE_URL = os.getenv("GITHUB_ENTERPRISE_URL")
REPO_URL_FROM_ENV = os.getenv("REPO_URL")


# --- Helper Functions ---

def get_api_base_url(repo_url_str):
    """Determines the correct API base URL for public or enterprise GitHub."""
    if GITHUB_ENTERPRISE_URL:
        return f"{GITHUB_ENTERPRISE_URL}/api/v3"
    
    parsed_url = urlparse(repo_url_str)
    if parsed_url.hostname and parsed_url.hostname != "github.com":
        return f"{parsed_url.scheme}://{parsed_url.hostname}/api/v3"
        
    return "https://api.github.com"

def parse_repo_url(url):
    """Extracts the owner and repository name from a repository URL."""
    try:
        path_parts = urlparse(url).path.strip("/").split("/")
        if len(path_parts) >= 2:
            owner = path_parts[0]
            repo = path_parts[1].replace('.git', '')
            return owner, repo
    except (ValueError, IndexError):
        pass
    return None, None

def parse_pr_url(url):
    """Extracts the owner, repository, and PR number from a pull request URL."""
    try:
        path_parts = urlparse(url).path.strip("/").split("/")
        if len(path_parts) >= 4 and path_parts[2] == "pull":
            owner = path_parts[0]
            repo = path_parts[1]
            pr_number = int(path_parts[3])
            return owner, repo, pr_number
    except (ValueError, IndexError):
        pass
    return None, None, None

def is_pr_url(url):
    """Checks if the given URL is a pull request URL."""
    try:
        path = urlparse(url).path
        return "/pull/" in path
    except:
        return False

def send_notification(title, message, tags):
    """Sends a push notification via ntfy.sh."""
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode('utf-8'),
            headers={"Title": title, "Priority": "high", "Tags": tags}
        )
        print(f"✅ Notification sent successfully for: {title}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error sending notification: {e}", file=sys.stderr)

def check_and_notify(api_base_url, owner, repo, pr_number, pr_title, commit_sha, headers):
    """Checks the status of a specific commit and sends a notification upon completion."""
    check_runs_url = f"{api_base_url}/repos/{owner}/{repo}/commits/{commit_sha}/check-runs"
    check_response = requests.get(check_runs_url, headers=headers)
    check_response.raise_for_status()
    check_data = check_response.json()

    total_checks = check_data.get("total_count", 0)
    if total_checks == 0:
        return "pending", False # No checks initiated yet, not completed

    check_runs = check_data.get("check_runs", [])
    completed_checks = [run for run in check_runs if run["status"] == "completed"]

    if len(completed_checks) == total_checks:
        failures = [run for run in completed_checks if run["conclusion"] not in ["success", "skipped", "neutral"]]
        
        if failures:
            conclusion, tags = "Failure", "x"
            failed_names = ", ".join([f'"{f["name"]}"' for f in failures])
            message = f"Checks failed: {failed_names}"
        else:
            conclusion, tags = "Success", "tada"
            message = f"All {total_checks} checks passed!"

        print(f"🎉 PR #{pr_number} '{pr_title}' finished with conclusion: {conclusion}")
        title = f"PR #{pr_number} {pr_title} Check: {conclusion}"
        send_notification(title, message, tags)
        return conclusion, True # Completed and notification sent
    
    return "in_progress", False # Still in progress

def monitor_single_pr(pr_url, headers, api_base_url):
    """Monitors a single PR, automatically detecting new commits."""
    owner, repo, pr_number = parse_pr_url(pr_url)
    if not all([owner, repo, pr_number]):
        print(f"❌ Error: Invalid GitHub PR URL: {pr_url}", file=sys.stderr)
        return

    print(f"🚀 Starting to monitor single PR: {owner}/{repo} #{pr_number}")
    
    monitored_commit_sha = None
    notified_shas = set()

    try:
        while True:
            pr_api_url = f"{api_base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
            response = requests.get(pr_api_url, headers=headers)
            response.raise_for_status()
            pr_data = response.json()
            
            latest_commit_sha = pr_data["head"]["sha"]
            pr_title = pr_data["title"]

            # Stop if the PR has been closed or merged
            if pr_data.get("state") != "open":
                print(f"🚮 PR #{pr_number} is closed or merged. Stopping.")
                break

            if monitored_commit_sha != latest_commit_sha:
                monitored_commit_sha = latest_commit_sha
                print(f"🔗 Now monitoring commit SHA: {monitored_commit_sha[:7]} for PR '{pr_title}'")

            if monitored_commit_sha in notified_shas:
                print(f"✅ Status for commit {monitored_commit_sha[:7]} already sent. Waiting for new commits...")
            else:
                print(f"🔍 Checking status for commit {monitored_commit_sha[:7]}...")
                conclusion, is_completed = check_and_notify(api_base_url, owner, repo, pr_number, pr_title, monitored_commit_sha, headers)
                if is_completed:
                    notified_shas.add(monitored_commit_sha)

            time.sleep(POLL_INTERVAL)
            
    except requests.exceptions.RequestException as e:
        # Handle cases where the PR is deleted
        if e.response and e.response.status_code == 404:
            print(f"❌ PR #{pr_number} not found. It might have been deleted. Stopping.")
        else:
            print(f"❌ An API error occurred: {e}.", file=sys.stderr)
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user.")

def monitor_repository(repo_url, headers, api_base_url):
    """Monitors all open PRs within a repository."""
    owner, repo = parse_repo_url(repo_url)
    if not all([owner, repo]):
        print(f"❌ Error: Invalid GitHub Repo URL: {repo_url}", file=sys.stderr)
        return
        
    print(f"🚀 Starting to monitor all PRs in repository: {owner}/{repo}")
    monitored_prs = {}

    try:
        while True:
            try:
                prs_api_url = f"{api_base_url}/repos/{owner}/{repo}/pulls"
                response = requests.get(prs_api_url, headers=headers)
                response.raise_for_status()
                open_prs_data = response.json()
                
                current_open_pr_numbers = set()
                for pr in open_prs_data:
                    pr_number, commit_sha, pr_title = pr["number"], pr["head"]["sha"], pr["title"]
                    current_open_pr_numbers.add(pr_number)

                    if pr_number not in monitored_prs:
                        print(f"👀 New PR detected: #{pr_number} '{pr_title}'. Now monitoring.")
                        monitored_prs[pr_number] = {"sha": commit_sha, "title": pr_title, "notified": False}
                    elif monitored_prs[pr_number]["sha"] != commit_sha:
                        print(f"🔄 New commit on PR #{pr_number} '{pr_title}'. Resetting status.")
                        monitored_prs[pr_number] = {"sha": commit_sha, "title": pr_title, "notified": False}
                    else:
                        monitored_prs[pr_number]["title"] = pr_title

                for pr_number in list(monitored_prs.keys()):
                    if pr_number not in current_open_pr_numbers:
                        print(f"🚮 PR #{pr_number} is closed or merged. Removing from monitoring.")
                        del monitored_prs[pr_number]

                if not monitored_prs:
                    print("No open PRs to monitor. Waiting...")
                else:
                    print(f"🔍 Checking status for {len(monitored_prs)} open PR(s): {list(monitored_prs.keys())}")
                
                for pr_number, data in monitored_prs.items():
                    if data["notified"]:
                        continue
                    conclusion, is_completed = check_and_notify(api_base_url, owner, repo, pr_number, data["title"], data["sha"], headers)
                    if is_completed:
                        monitored_prs[pr_number]["notified"] = True

            except requests.exceptions.RequestException as e:
                print(f"❌ An API error occurred: {e}. Retrying...", file=sys.stderr)
            
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user.")

def main():
    parser = argparse.ArgumentParser(description="Monitor GitHub PRs and send notifications.")
    parser.add_argument("url", nargs='?', default=None, help="The full URL of the GitHub Repository or a specific Pull Request. Reads from .env if not provided.")
    args = parser.parse_args()

    # --- Validate required configuration ---
    if not GITHUB_TOKEN:
        print("❌ Error: GITHUB_TOKEN not found. Please set it in your environment or a .env file.")
        sys.exit(1)

    if not NTFY_TOPIC:
        print("❌ Error: NTFY_TOPIC not found. Please set it in your environment or a .env file.")
        sys.exit(1)

    target_url = args.url if args.url else REPO_URL_FROM_ENV
    if not target_url:
        print("❌ Error: No URL provided via command line or in .env file (REPO_URL).")
        sys.exit(1)

    api_base_url = get_api_base_url(target_url)
    print(f"✅ API Endpoint set to: {api_base_url}")

    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    if is_pr_url(target_url):
        monitor_single_pr(target_url, headers, api_base_url)
    else:
        monitor_repository(target_url, headers, api_base_url)

if __name__ == "__main__":
    main()
