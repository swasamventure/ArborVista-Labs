(() => {
  'use strict';

  const migrationKey = 'arbor-market-v421-real-snapshot-reset-applied';
  const workspaceKey = 'arbor-market-workspace-v421';
  const propertyKey = 'arbor-market-property-v421';

  try {
    if (window.localStorage.getItem(migrationKey) === '1') return;

    const savedWorkspace = window.localStorage.getItem(workspaceKey);
    if (savedWorkspace) {
      const normalized = savedWorkspace.toLowerCase();
      const containsBundledRealSnapshot =
        normalized.includes('public listing metadata') ||
        normalized.includes('airbnb-24113496');

      if (!containsBundledRealSnapshot) {
        window.localStorage.removeItem(workspaceKey);
        window.localStorage.removeItem(propertyKey);
      }
    }

    window.localStorage.setItem(migrationKey, '1');
  } catch (_) {
    // The page still works when browser storage is unavailable.
  }
})();
