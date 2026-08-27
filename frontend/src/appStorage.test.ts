import { beforeEach, expect, test, vi } from "vitest";
import { APP_STORAGE_VERSION, APP_STORAGE_VERSION_KEY, migrateAppStorage } from "./appStorage";

function memoryStorage(): Storage {
  const values = new Map<string, string>();
  return { get length() { return values.size; }, clear: () => values.clear(), getItem: (key) => values.get(key) ?? null, key: (index) => [...values.keys()][index] ?? null, removeItem: (key) => { values.delete(key); }, setItem: (key, value) => { values.set(key, value); } };
}
beforeEach(() => { vi.stubGlobal("localStorage", memoryStorage()); vi.stubGlobal("sessionStorage", memoryStorage()); });

test("storage migration removes only app-owned obsolete state", () => {
  localStorage.setItem("translation-filters", "old"); localStorage.setItem("unrelated-app", "keep"); sessionStorage.setItem("profile-review:9:categories", "old");
  expect(migrateAppStorage()).toBe(true); expect(localStorage.getItem(APP_STORAGE_VERSION_KEY)).toBe(APP_STORAGE_VERSION);
  expect(localStorage.getItem("translation-filters")).toBeNull(); expect(sessionStorage.getItem("profile-review:9:categories")).toBeNull(); expect(localStorage.getItem("unrelated-app")).toBe("keep");
  expect(migrateAppStorage()).toBe(false);
});
