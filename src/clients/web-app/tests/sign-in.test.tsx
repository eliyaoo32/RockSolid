import { describe, expect, it } from "vitest"

import i18n from "@/i18n"

import { renderApp } from "./framework/app-driver"
import { USERS } from "./framework/fake-backend"

const t = i18n.t.bind(i18n)

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

  it("signs in with an email after a wrong password, keeping the typed email, and Google still works after signing out", async () => {
    const driver = renderApp({ path: "/", signedInAs: null })
    driver.when.hasEmailAccount("noa", "secret-password")

    await driver.when.signInWithEmail("noa", "wrong-password")
    expect(driver.get.signInMessage()).toBe(
      t("signIn.failure.wrong-email-or-password")
    )
    expect(driver.get.typedEmail()).toBe("noa@example.com")
    expect(driver.get.showsSignInScreen()).toBe(true)

    await driver.when.signInWithEmail("noa", "secret-password")
    expect(await driver.get.userName("noa")).toBe(USERS.noa)
    expect(driver.get.showsSignInScreen()).toBe(false)

    await driver.when.signOut()
    await driver.when.signInWithGoogleAs("dana")
    expect(await driver.get.userName("dana")).toBe(USERS.dana)
  })

  it("creates an account, refuses a second account with the same email, and signs in with the first", async () => {
    const driver = renderApp({ path: "/", signedInAs: null })

    await driver.when.createAccountWithEmail("noa", "secret-password")
    expect(await driver.get.userName("noa")).toBe(USERS.noa)

    await driver.when.signOut()
    await driver.when.createAccountWithEmail("noa", "another-password")
    expect(driver.get.signInMessage()).toBe(t("signIn.failure.email-in-use"))
    expect(driver.get.typedEmail()).toBe("noa@example.com")
    expect(driver.get.showsSignInScreen()).toBe(true)

    await driver.when.goBackToSignIn()
    expect(driver.get.signInMessage()).toBeNull()
    await driver.when.signInWithEmail("noa", "secret-password")
    expect(await driver.get.userName("noa")).toBe(USERS.noa)
  })

  it("sends the password-reset email, confirms it, and lets the user sign in", async () => {
    const driver = renderApp({ path: "/", signedInAs: null })
    driver.when.hasEmailAccount("noa", "secret-password")

    await driver.when.sendPasswordReset("noa")

    expect(driver.get.resetEmailsSentTo()).toEqual(["noa@example.com"])
    expect(driver.get.signInMessage()).toBe(
      t("signIn.resetEmailSent", { email: "noa@example.com" })
    )
    await driver.when.signInWithEmail("noa", "secret-password")
    expect(await driver.get.userName("noa")).toBe(USERS.noa)
  })
})
