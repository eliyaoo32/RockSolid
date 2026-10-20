import { waitFor } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { renderApp } from "../tests/framework/app-driver"

describe("app", () => {
  it("shows a skeleton until the sign-in state is known, then asks a signed-out user to sign in", () => {
    const driver = renderApp({ path: "/" })
    expect(driver.get.isLoading()).toBe(true)
    expect(driver.get.showsSignInScreen()).toBe(false)

    driver.when.signInStateArrives(null)

    expect(driver.get.showsSignInScreen()).toBe(true)
    expect(driver.get.isLoading()).toBe(false)
    expect(driver.get.path()).toBe("/")
  })

  it("sends a signed-in user at an unknown address to the home screen", async () => {
    const driver = renderApp({ path: "/nowhere", signedInAs: "dana" })

    await waitFor(() => {
      expect(driver.get.path()).toBe("/")
    })
  })
})
