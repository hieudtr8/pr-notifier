import axios, { AxiosResponse } from 'axios';
import { CheckRunsResponse, PRData, CheckStatus } from './types.js';

export class GitHubClient {
  private headers: Record<string, string>;

  constructor(private apiBaseUrl: string, githubToken: string) {
    this.headers = {
      Authorization: `token ${githubToken}`,
      Accept: 'application/vnd.github.v3+json',
    };
  }

  async getPR(owner: string, repo: string, prNumber: number): Promise<PRData> {
    const url = `${this.apiBaseUrl}/repos/${owner}/${repo}/pulls/${prNumber}`;
    const response: AxiosResponse<PRData> = await axios.get(url, {
      headers: this.headers,
      timeout: 8000,
    });
    return response.data;
  }

  async getOpenPRs(owner: string, repo: string): Promise<PRData[]> {
    const url = `${this.apiBaseUrl}/repos/${owner}/${repo}/pulls`;
    const response: AxiosResponse<PRData[]> = await axios.get(url, {
      headers: this.headers,
      timeout: 8000,
    });
    return response.data;
  }

  async getCheckRuns(
    owner: string,
    repo: string,
    commitSha: string
  ): Promise<CheckRunsResponse> {
    const url = `${this.apiBaseUrl}/repos/${owner}/${repo}/commits/${commitSha}/check-runs`;
    const response: AxiosResponse<CheckRunsResponse> = await axios.get(url, {
      headers: this.headers,
      timeout: 8000,
    });
    return response.data;
  }

  async getPRStatusSummary(
    owner: string,
    repo: string,
    prNumber: number,
    prTitle: string,
    commitSha: string
  ): Promise<{
    prNumber: number;
    prTitle: string;
    status: CheckStatus;
    isCompleted: boolean;
    message?: string;
    conclusion?: string;
  }> {
    const result = await this.checkCommitStatus(owner, repo, prNumber, prTitle, commitSha);
    return {
      prNumber,
      prTitle,
      ...result
    };
  }

  async checkCommitStatus(
    owner: string,
    repo: string,
    prNumber: number,
    prTitle: string,
    commitSha: string
  ): Promise<{
    status: CheckStatus;
    isCompleted: boolean;
    message?: string;
    conclusion?: string;
  }> {
    const checkData = await this.getCheckRuns(owner, repo, commitSha);

    const totalChecks = checkData.total_count;
    if (totalChecks === 0) {
      return { status: 'pending', isCompleted: false };
    }

    const checkRuns = checkData.check_runs;
    const completedChecks = checkRuns.filter(
      (run) => run.status === 'completed'
    );

    if (completedChecks.length === totalChecks) {
      const failures = completedChecks.filter(
        (run) => !['success', 'skipped', 'neutral'].includes(run.conclusion)
      );

      if (failures.length > 0) {
        const failedNames = failures.map((f) => `"${f.name}"`).join(', ');
        const message = `Checks failed: ${failedNames}`;
        return {
          status: 'failure',
          isCompleted: true,
          message,
          conclusion: 'Failure',
        };
      } else {
        const message = `All ${totalChecks} checks passed!`;
        return {
          status: 'success',
          isCompleted: true,
          message,
          conclusion: 'Success',
        };
      }
    }

    return { status: 'in_progress', isCompleted: false };
  }
}
