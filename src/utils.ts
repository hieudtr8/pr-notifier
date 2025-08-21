import { URL } from 'url';

export function getApiBaseUrl(
  repoUrlStr: string,
  githubEnterpriseUrl?: string
): string {
  if (githubEnterpriseUrl) {
    return `${githubEnterpriseUrl}/api/v3`;
  }

  try {
    const parsedUrl = new URL(repoUrlStr);
    if (parsedUrl.hostname && parsedUrl.hostname !== 'github.com') {
      return `${parsedUrl.protocol}//${parsedUrl.hostname}/api/v3`;
    }
  } catch (error) {
    // If URL parsing fails, fall back to default
  }

  return 'https://api.github.com';
}

export function parseRepoUrl(
  url: string
): { owner: string; repo: string } | null {
  try {
    const parsedUrl = new URL(url);
    const pathParts = parsedUrl.pathname.replace(/^\//, '').split('/');

    if (pathParts.length >= 2) {
      const owner = pathParts[0];
      const repo = pathParts[1].replace('.git', '');
      return { owner, repo };
    }
  } catch (error) {
    // URL parsing failed
  }

  return null;
}

export function parsePrUrl(
  url: string
): { owner: string; repo: string; prNumber: number } | null {
  try {
    const parsedUrl = new URL(url);
    const pathParts = parsedUrl.pathname.replace(/^\//, '').split('/');

    if (pathParts.length >= 4 && pathParts[2] === 'pull') {
      const owner = pathParts[0];
      const repo = pathParts[1];
      const prNumber = parseInt(pathParts[3], 10);

      if (!isNaN(prNumber)) {
        return { owner, repo, prNumber };
      }
    }
  } catch (error) {
    // URL parsing failed
  }

  return null;
}

export function isPrUrl(url: string): boolean {
  try {
    const parsedUrl = new URL(url);
    return parsedUrl.pathname.includes('/pull/');
  } catch (error) {
    return false;
  }
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
