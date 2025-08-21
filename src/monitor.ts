import { GitHubClient } from './github.js';
import { NotificationService } from './notifier.js';
import { MonitoredPR, PRData } from './types.js';
import { sleep, parsePrUrl, parseRepoUrl } from './utils';

export class PRMonitor {
  private githubClient: GitHubClient;
  private notifier: NotificationService;
  private pollInterval: number;
  private specificPrNumbers?: number[];

  constructor(
    githubClient: GitHubClient,
    notifier: NotificationService,
    pollInterval: number,
    specificPrNumbers?: number[]
  ) {
    this.githubClient = githubClient;
    this.notifier = notifier;
    this.pollInterval = pollInterval * 1000; // Convert to milliseconds
    this.specificPrNumbers = specificPrNumbers;
  }

  async monitorSinglePR(prUrl: string): Promise<void> {
    const parsed = parsePrUrl(prUrl);
    if (!parsed) {
      console.error(`❌ Error: Invalid GitHub PR URL: ${prUrl}`);
      return;
    }

    const { owner, repo, prNumber } = parsed;
    console.log(
      `🚀 Starting to monitor single PR: ${owner}/${repo} #${prNumber}`
    );

    let monitoredCommitSha: string | null = null;
    const notifiedShas = new Set<string>();

    try {
      while (true) {
        const prData = await this.githubClient.getPR(owner, repo, prNumber);

        const latestCommitSha = prData.head.sha;
        const prTitle = prData.title;

        // Stop if the PR has been closed or merged
        if (prData.state !== 'open') {
          console.log(`🚮 PR #${prNumber} is closed or merged. Stopping.`);
          break;
        }

        if (monitoredCommitSha !== latestCommitSha) {
          monitoredCommitSha = latestCommitSha;
          console.log(
            `🔗 Now monitoring commit SHA: ${monitoredCommitSha.substring(
              0,
              7
            )} for PR '${prTitle}'`
          );
        }

        if (notifiedShas.has(monitoredCommitSha)) {
          console.log(
            `✅ Status for commit ${monitoredCommitSha.substring(
              0,
              7
            )} already sent. Waiting for new commits...`
          );
        } else {
          console.log(
            `🔍 Checking status for commit ${monitoredCommitSha.substring(
              0,
              7
            )}...`
          );
          const result = await this.githubClient.checkCommitStatus(
            owner,
            repo,
            prNumber,
            prTitle,
            monitoredCommitSha
          );

          if (result.isCompleted && result.message && result.conclusion) {
            console.log(
              `🎉 PR #${prNumber} '${prTitle}' finished with conclusion: ${result.conclusion}`
            );
            const title = `PR #${prNumber} ${prTitle} Check: ${result.conclusion}`;
            const tags = result.status === 'success' ? 'tada' : 'x';
            await this.notifier.sendNotification(title, result.message, tags);
            notifiedShas.add(monitoredCommitSha);
          }
        }

        await sleep(this.pollInterval);
      }
    } catch (error: any) {
      if (error.response && error.response.status === 404) {
        console.log(
          `❌ PR #${prNumber} not found. It might have been deleted. Stopping.`
        );
      } else {
        console.error(`❌ An API error occurred: ${error}`);
      }
    }
  }

  async monitorRepository(repoUrl: string): Promise<void> {
    const parsed = parseRepoUrl(repoUrl);
    if (!parsed) {
      console.error(`❌ Error: Invalid GitHub Repo URL: ${repoUrl}`);
      return;
    }

    const { owner, repo } = parsed;
    if (this.specificPrNumbers && this.specificPrNumbers.length > 0) {
      console.log(
        `🚀 Starting to monitor specific PRs in repository: ${owner}/${repo} - PR numbers: ${this.specificPrNumbers.join(', ')}`
      );
    } else {
      console.log(
        `🚀 Starting to monitor all PRs in repository: ${owner}/${repo}`
      );
    }
    const monitoredPRs = new Map<number, MonitoredPR>();

    let isFirstRun = true;
    try {
      while (true) {
        try {
          const openPRs = await this.githubClient.getOpenPRs(owner, repo);

          // Handle first run behavior
          if (isFirstRun) {
            if (!this.specificPrNumbers || this.specificPrNumbers.length === 0) {
              // Show summary for all PRs
              await this.showInitialSummary(owner, repo, openPRs);
            }
            
            // Mark all current PRs as already processed to avoid notifications on first run
            for (const pr of openPRs) {
              const prNumber = pr.number;
              const commitSha = pr.head.sha;
              const prTitle = pr.title;

              // Skip this PR if we have specific PR numbers configured and this isn't one of them
              if (this.specificPrNumbers && this.specificPrNumbers.length > 0) {
                if (!this.specificPrNumbers.includes(prNumber)) {
                  continue;
                }
              }

              const result = await this.githubClient.checkCommitStatus(
                owner,
                repo,
                prNumber,
                prTitle,
                commitSha
              );

              monitoredPRs.set(prNumber, {
                sha: commitSha,
                title: prTitle,
                notified: result.isCompleted // Mark as notified if completed to prevent first-run spam
              });
            }
            
            isFirstRun = false;
            console.log('🔍 Starting continuous monitoring...\n');
            await sleep(this.pollInterval);
            continue;
          }

          const currentOpenPRNumbers = new Set<number>();

          for (const pr of openPRs) {
            const prNumber = pr.number;
            const commitSha = pr.head.sha;
            const prTitle = pr.title;

            // Skip this PR if we have specific PR numbers configured and this isn't one of them
            if (this.specificPrNumbers && this.specificPrNumbers.length > 0) {
              if (!this.specificPrNumbers.includes(prNumber)) {
                continue;
              }
            }

            currentOpenPRNumbers.add(prNumber);

            if (!monitoredPRs.has(prNumber)) {
              console.log(
                `👀 New PR detected: #${prNumber} '${prTitle}'. Now monitoring.`
              );
              monitoredPRs.set(prNumber, {
                sha: commitSha,
                title: prTitle,
                notified: false,
              });
            } else {
              const monitored = monitoredPRs.get(prNumber)!;
              if (monitored.sha !== commitSha) {
                console.log(
                  `🔄 New commit on PR #${prNumber} '${prTitle}'. Resetting status.`
                );
                monitoredPRs.set(prNumber, {
                  sha: commitSha,
                  title: prTitle,
                  notified: false,
                });
              } else {
                monitored.title = prTitle;
              }
            }
          }

          // Remove closed PRs
          for (const prNumber of monitoredPRs.keys()) {
            if (!currentOpenPRNumbers.has(prNumber)) {
              console.log(
                `🚮 PR #${prNumber} is closed or merged. Removing from monitoring.`
              );
              monitoredPRs.delete(prNumber);
            }
          }

          if (monitoredPRs.size === 0) {
            console.log('No open PRs to monitor. Waiting...');
          } else {
            const prNumbers = Array.from(monitoredPRs.keys());
            console.log(
              `🔍 Checking status for ${monitoredPRs.size} open PR(s): ${prNumbers}`
            );
          }

          // Check status for each monitored PR
          for (const [prNumber, data] of monitoredPRs) {
            if (data.notified) {
              continue;
            }

            const result = await this.githubClient.checkCommitStatus(
              owner,
              repo,
              prNumber,
              data.title,
              data.sha
            );

            if (result.isCompleted && result.message && result.conclusion) {
              console.log(
                `🎉 PR #${prNumber} '${data.title}' finished with conclusion: ${result.conclusion}`
              );
              const title = `PR #${prNumber} ${data.title} Check: ${result.conclusion}`;
              const tags = result.status === 'success' ? 'tada' : 'x';
              await this.notifier.sendNotification(title, result.message, tags);
              data.notified = true;
            }
          }
        } catch (error) {
          console.error(`❌ An API error occurred: ${error}. Retrying...`);
        }

        await sleep(this.pollInterval);
      }
      
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('\n🛑 Monitoring stopped by user.');
      } else {
        console.error(`❌ Unexpected error: ${error}`);
      }
    }
  }

  private async showInitialSummary(owner: string, repo: string, openPRs: PRData[]): Promise<void> {
    if (openPRs.length === 0) {
      console.log('📊 No open PRs found in this repository.');
      try {
        console.log('📤 Sending no PRs notification...');
        await this.notifier.sendNotification(
          `${owner}/${repo} PR Summary`,
          'No open PRs found in this repository.',
          'information_source'
        );
      } catch (error) {
        console.error('⚠️ Failed to send no PRs notification, but continuing:', error);
      }
      return;
    }

    console.log(`\n📊 Initial PR Status Summary for ${owner}/${repo}:`);
    console.log(`Found ${openPRs.length} open PR(s)\n`);

    const statuses = await Promise.all(
      openPRs.map(pr => 
        this.githubClient.getPRStatusSummary(owner, repo, pr.number, pr.title, pr.head.sha)
      )
    );

    const failingPRs = statuses.filter(s => s.isCompleted && s.status === 'failure');
    const passingPRs = statuses.filter(s => s.isCompleted && s.status === 'success');
    const processingPRs = statuses.filter(s => !s.isCompleted);

    // Show failing PRs first
    if (failingPRs.length > 0) {
      console.log('❌ Failing PRs:');
      failingPRs.forEach(pr => {
        console.log(`   #${pr.prNumber}: ${pr.prTitle}`);
      });
      console.log('');
    }

    // Show summary counts
    console.log('📈 Status Overview:');
    console.log(`   ✅ Passing: ${passingPRs.length}`);
    console.log(`   🔄 Processing: ${processingPRs.length}`);
    console.log(`   ❌ Failing: ${failingPRs.length}`);

    // Send notification with summary
    try {
      const title = `${owner}/${repo} PR Summary`;
      let message = `Found ${openPRs.length} open PRs\n\n`;
      message += `✅ Passing: ${passingPRs.length}\n`;
      message += `🔄 Processing: ${processingPRs.length}\n`;
      message += `❌ Failing: ${failingPRs.length}`;
      
      if (failingPRs.length > 0) {
        message += `\n\nFailing PRs:\n`;
        failingPRs.forEach(pr => {
          message += `#${pr.prNumber}: ${pr.prTitle}\n`;
        });
      }

      const tags = failingPRs.length > 0 ? 'warning' : 'information_source';
      console.log('📤 Sending initial summary notification...');
      await this.notifier.sendNotification(title, message, tags);
    } catch (error) {
      console.error('⚠️ Failed to send initial summary notification, but continuing monitoring:', error);
    }
  }
}
