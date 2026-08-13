import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const generateMigrationPlan = async (oldSpec, newSpec) => {
  const response = await api.post('/migration-plan', {
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
    provider_id: providerId
  });
  return response.data;
};

export const registerProvider = async (name, specUrl, repositoryPath, changelogUrl = null) => {
  const response = await api.post('/providers', {
    name,
    spec_url: specUrl,
    repository_path: repositoryPath,
    changelog_url: changelogUrl
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
