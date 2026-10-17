import "@testing-library/jest-dom/vitest"
import "@/i18n"
import { cleanup } from "@testing-library/react"
import { afterEach, beforeEach, vi } from "vitest"

import { setSystemTheme } from "./system-theme"

beforeEach(() => {
  setSystemTheme("light")
})

afterEach(() => {
  cleanup()
  localStorage.clear()
  document.documentElement.className = ""
  vi.unstubAllGlobals()
})
