import { describe, expect, it } from "vitest"

import { renderApp } from "./framework/app-driver"
import { USERS } from "./framework/fake-backend"

describe("sign-in", () => {
  it("shows the name the backend knows, with a skeleton until the backend answers", async () => {
    const driver = renderApp({ path: "/" })

    driver.when.signInStateArrives("dana")

    expect(driver.get.isLoading()).toBe(true)
    expect(await driver.get.userName("dana")).toBe(USERS.dana)
    expect(driver.get.isLoading()).toBe(false)
  })

  it("signs in with Google, signs out, and lets another person sign in and see only their own name", async () => {
    const driver = renderApp({ path: "/", signedInAs: null })

    await driver.when.signInWithGoogleAs("dana")
    expect(await driver.get.userName("dana")).toBe(USERS.dana)
    expect(driver.get.showsSignInScreen()).toBe(false)

    await driver.when.signOut()
    expect(driver.get.showsSignInScreen()).toBe(true)

    await driver.when.signInWithGoogleAs("noa")
    expect(await driver.get.userName("noa")).toBe(USERS.noa)
    expect(driver.get.showsSignInScreen()).toBe(false)
  })

  it("keeps the user on the sign-in screen with an error when Google refuses, then signs in on retry", async () => {
    const driver = renderApp({ path: "/", signedInAs: null })
    driver.when.googleRefusesNextSignIn()

    await driver.when.signInWithGoogleAs("dana")

    expect(driver.get.showsSignInError()).toBe(true)
    expect(driver.get.showsSignInScreen()).toBe(true)

    await driver.when.signInWithGoogleAs("dana")
    expect(await driver.get.userName("dana")).toBe(USERS.dana)
    expect(driver.get.showsSignInError()).toBe(false)
  })
})
