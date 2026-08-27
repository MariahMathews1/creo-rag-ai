export const APP_STORAGE_VERSION = "v1-pre-azure-1";
export const APP_STORAGE_VERSION_KEY = "creo-rag-ai:storage-version";

const APP_PREFIXES = ["creo-rag-ai:", "profile-review:"];
const RETIRED_KEYS = new Set(["translation-filters", "toolpath-view", "gcode-review-draft", "analysis-filters", "research-tools-state"]);

function owned(key: string) {
  return APP_PREFIXES.some((prefix) => key.startsWith(prefix)) || RETIRED_KEYS.has(key);
}

function removeOwned(storage: Storage) {
  const keys = Array.from({ length: storage.length }, (_, index) => storage.key(index)).filter((key): key is string => Boolean(key));
  keys.filter(owned).forEach((key) => storage.removeItem(key));
}

export function migrateAppStorage(local: Storage = window.localStorage, session: Storage = window.sessionStorage) {
  try {
    if (local.getItem(APP_STORAGE_VERSION_KEY) === APP_STORAGE_VERSION) return false;
    removeOwned(local); removeOwned(session); local.setItem(APP_STORAGE_VERSION_KEY, APP_STORAGE_VERSION); return true;
  } catch {
    return false;
  }
}
