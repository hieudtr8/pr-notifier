export interface Config {
  githubToken: string;
  ntfyTopic: string;
  pollInterval: number;
  githubEnterpriseUrl?: string;
  repoUrl?: string;
}

export interface PRData {
  number: number;
  title: string;
  head: {
    sha: string;
  };
  state: string;
}

export interface CheckRun {
  name: string;
  status: string;
  conclusion: string;
}

export interface CheckRunsResponse {
  total_count: number;
  check_runs: CheckRun[];
}

export interface MonitoredPR {
  sha: string;
  title: string;
  notified: boolean;
}

export type CheckStatus = 'pending' | 'in_progress' | 'success' | 'failure';
