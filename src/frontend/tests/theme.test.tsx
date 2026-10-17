import { describe, expect, it } from "vitest"

import { renderApp } from "./framework/app-driver"
import { setSystemTheme } from "./framework/system-theme"

describe("theme", () => {
  it("follows a light system theme, then switches to dark and back", async () => {
    const driver = renderApp({ signedInAs: "dana" })
    expect(driver.get.theme()).toBe("light")

    await driver.when.toggleTheme()
    expect(driver.get.theme()).toBe("dark")

    await driver.when.toggleTheme()
    expect(driver.get.theme()).toBe("light")
  })

  it("follows a dark system theme, then switches to light", async () => {
    setSystemTheme("dark")
    const driver = renderApp({ signedInAs: "dana" })
    expect(driver.get.theme()).toBe("dark")

    await driver.when.toggleTheme()
    expect(driver.get.theme()).toBe("light")
  })
})
