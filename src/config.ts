import dotenv from 'dotenv';
import { Config } from './types.js';

dotenv.config();

export function loadConfig(): Config {
  const githubToken = process.env.GITHUB_TOKEN;
  const ntfyTopic = process.env.NTFY_TOPIC;

  if (!githubToken) {
    console.error(
      '❌ Error: GITHUB_TOKEN not found. Please set it in your environment or a .env file.'
    );
    process.exit(1);
  }

  if (!ntfyTopic) {
    console.error(
      '❌ Error: NTFY_TOPIC not found. Please set it in your environment or a .env file.'
    );
    process.exit(1);
  }

  return {
    githubToken,
    ntfyTopic,
    pollInterval: parseInt(process.env.POLL_INTERVAL || '60', 10),
    githubEnterpriseUrl: process.env.GITHUB_ENTERPRISE_URL,
    repoUrl: process.env.REPO_URL,
  };
}
