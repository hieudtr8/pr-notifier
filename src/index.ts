#!/usr/bin/env node

import { program } from 'commander';
import { loadConfig } from './config';
import { getApiBaseUrl, isPrUrl } from './utils';
import { GitHubClient } from './github';
import { NotificationService } from './notifier';
import { PRMonitor } from './monitor';

async function main() {
  program
    .name('pr-notifier')
    .description('Monitor GitHub PRs and send notifications')
    .argument(
      '[url]',
      'The full URL of the GitHub Repository or a specific Pull Request. Reads from .env if not provided.'
    )
    .parse();

  const config = loadConfig();
  const args = program.args;

  const targetUrl = args[0] || config.repoUrl;
  if (!targetUrl) {
    console.error(
      '❌ Error: No URL provided via command line or in .env file (REPO_URL).'
    );
    process.exit(1);
  }

  const apiBaseUrl = getApiBaseUrl(targetUrl, config.githubEnterpriseUrl);
  console.log(`✅ API Endpoint set to: ${apiBaseUrl}`);

  const githubClient = new GitHubClient(apiBaseUrl, config.githubToken);
  const notifier = new NotificationService(config.ntfyTopic);
  const monitor = new PRMonitor(githubClient, notifier, config.pollInterval);

  // Handle graceful shutdown
  process.on('SIGINT', () => {
    console.log('\n🛑 Monitoring stopped by user.');
    process.exit(0);
  });

  process.on('SIGTERM', () => {
    console.log('\n🛑 Monitoring stopped.');
    process.exit(0);
  });

  if (isPrUrl(targetUrl)) {
    await monitor.monitorSinglePR(targetUrl);
  } else {
    await monitor.monitorRepository(targetUrl);
  }
}

if (require.main === module) {
  main().catch((error) => {
    console.error('❌ Fatal error:', error);
    process.exit(1);
  });
}
