import { vi } from "vitest"

/** Sets the operating system's theme, which jsdom does not have. */
export function setSystemTheme(theme: "light" | "dark") {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: theme === "dark" && query === "(prefers-color-scheme: dark)",
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  }))
}
