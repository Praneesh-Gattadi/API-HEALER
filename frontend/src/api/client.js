import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

export const checkBackendHealth = async () => {
  try {
    const response = await api.get('/providers');
    return response.status === 200;
  } catch (err) {
    return false;
  }
};

export const calculateDiff = async (oldSpec, newSpec) => {
  const response = await api.post('/diff/diff', {
    old_spec: oldSpec,
    new_spec: newSpec,
  });
  return response.data;
};

export const generateMigrationPlan = async (oldSpec, newSpec) => {
  const response = await api.post('/migration-plan/migration-plan', {
    old_spec: oldSpec,
    new_spec: newSpec,
  });
  return response.data;
};

export const applyTransformation = async (migrationPlan, repositoryRoot, dryRun = true, providerId = null) => {
  const response = await api.post('/transform', {
    migration_plan: migrationPlan,
    repository_root: repositoryRoot,
    dry_run: dryRun,
    provider_id: providerId,
  });
  return response.data;
};

export const registerProvider = async (name, specUrl, repositoryPath, changelogUrl = null, githubRepo = null) => {
  const response = await api.post('/providers', {
    name,
    spec_url: specUrl,
    repository_path: repositoryPath,
    changelog_url: changelogUrl,
    github_repo: githubRepo,
  });
  return response.data;
};

export const checkProviderUpdates = async (providerId) => {
  const response = await api.post(`/providers/${providerId}/check`);
  return response.data;
};

export const listProviders = async () => {
  const response = await api.get('/providers');
  return response.data;
};

export const getSnapshotSpec = async (providerId, snapshotId) => {
  const response = await api.get(`/providers/${providerId}/snapshots/${snapshotId}`);
  return response.data;
};

export const createPullRequest = async ({ providerId, repositoryPath, githubRepo, baseBranch = 'main', title, body, filesToCommit }) => {
  const response = await api.post('/github/pull-request', {
    provider_id: providerId,
    repository_path: repositoryPath,
    github_repo: githubRepo,
    base_branch: baseBranch,
    title,
    body,
    files_to_commit: filesToCommit,
  });
  return response.data;
};
