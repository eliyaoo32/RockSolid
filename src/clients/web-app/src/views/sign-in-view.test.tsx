import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"

import type { SignInFailure } from "@/auth/sign-in"
import i18n from "@/i18n"
import { SignInView } from "@/views/sign-in-view"

import { renderInApp } from "../../tests/framework/render"

const t = i18n.t.bind(i18n)

const button = (name: string) => screen.getByRole("button", { name })
const emailInput = () => screen.getByLabelText(t("signIn.email"))
const passwordInput = () => screen.getByLabelText(t("signIn.password"))
const title = () =>
  screen.getByText(
    (_, element) => element?.getAttribute("data-slot") === "card-title"
  )

function renderSignIn() {
  const app = renderInApp(<SignInView />, { signedInAs: null })
  const events = userEvent.setup()
  async function fill(email: string, password?: string) {
    await events.clear(emailInput())
    await events.type(emailInput(), email)
    if (password !== undefined) {
      await events.clear(passwordInput())
      await events.type(passwordInput(), password)
    }
  }
  return { ...app, events, fill }
}

describe("sign-in view", () => {
  it("asks the user to sign in with Google or with an email and password", () => {
    renderInApp(<SignInView />, { signedInAs: null })

    expect(title()).toHaveTextContent(t("signIn.title.sign-in"))
    expect(
      screen.getByText(t("signIn.description.sign-in"))
    ).toBeInTheDocument()
    expect(button(t("signIn.google"))).toBeEnabled()
    expect(emailInput()).toHaveAttribute("type", "email")
    expect(emailInput()).toBeRequired()
    expect(passwordInput()).toHaveAttribute("type", "password")
    expect(passwordInput()).toHaveAttribute("autocomplete", "current-password")
    expect(button(t("signIn.submit.sign-in"))).toBeEnabled()
  })

  it("disables every control and shows a spinner while a request runs", async () => {
    const { signIn, events, fill } = renderSignIn()
    const finishSignIn = signIn.holdNextRequest()
    await fill("dana@example.com", "secret-password")

    await events.click(button(t("signIn.google")))
    expect(button(t("signIn.google"))).toBeDisabled()
    expect(button(t("signIn.submit.sign-in"))).toBeDisabled()
    expect(emailInput()).toBeDisabled()
    expect(passwordInput()).toBeDisabled()
    expect(button(t("signIn.showCreateAccount"))).toBeDisabled()
    expect(screen.getByRole("status")).toHaveTextContent(t("loading"))
    expect(button(t("signIn.google")).querySelector("svg")).not.toBeNull()
    expect(button(t("signIn.submit.sign-in")).querySelector("svg")).toBeNull()

    finishSignIn()
    await waitFor(() => {
      expect(button(t("signIn.google"))).toBeEnabled()
    })
    expect(emailInput()).toBeEnabled()
    expect(screen.queryByRole("status")).not.toBeInTheDocument()
  })

  it("shows an error when Google refuses, and clears it when the retry succeeds", async () => {
    const { signIn, events } = renderSignIn()
    signIn.googleRefusesNextSignIn()

    await events.click(button(t("signIn.google")))
    expect(screen.getByRole("alert")).toHaveTextContent(
      t("signIn.failure.other")
    )
    expect(button(t("signIn.google"))).toBeEnabled()

    await events.click(button(t("signIn.google")))
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
    expect(await signIn.idToken()).toBe("token-dana")
  })

  it("signs in with an email and password when the user presses Enter", async () => {
    const { signIn, events, fill } = renderSignIn()
    signIn.hasEmailAccount("noa", "secret-password")

    await fill("noa@example.com", "secret-password")
    await events.keyboard("{Enter}")

    expect(await signIn.idToken()).toBe("token-noa")
  })

  it("keeps what the user typed when the password is wrong, and signs in once it is right", async () => {
    const { signIn, events, fill } = renderSignIn()
    signIn.hasEmailAccount("noa", "secret-password")

    await fill("noa@example.com", "wrong-password")
    await events.click(button(t("signIn.submit.sign-in")))
    expect(screen.getByRole("alert")).toHaveTextContent(
      t("signIn.failure.wrong-email-or-password")
    )
    expect(emailInput()).toHaveValue("noa@example.com")
    expect(passwordInput()).toHaveValue("wrong-password")
    expect(await signIn.idToken()).toBeNull()

    await fill("noa@example.com", "secret-password")
    await events.click(button(t("signIn.submit.sign-in")))
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
    expect(await signIn.idToken()).toBe("token-noa")
  })

  it("creates an account with an email and password", async () => {
    const { signIn, events, fill } = renderSignIn()

    await events.click(button(t("signIn.showCreateAccount")))
    expect(title()).toHaveTextContent(t("signIn.title.create-account"))
    expect(
      screen.getByText(t("signIn.description.create-account"))
    ).toBeInTheDocument()
    expect(passwordInput()).toHaveAttribute("autocomplete", "new-password")
    expect(
      screen.queryByRole("button", { name: t("signIn.forgotPassword") })
    ).not.toBeInTheDocument()

    await fill("noa@example.com", "secret-password")
    await events.click(button(t("signIn.submit.create-account")))

    expect(await signIn.idToken()).toBe("token-noa")
  })

  it("tells the user the email already has an account, and lets them sign in instead", async () => {
    const { signIn, events, fill } = renderSignIn()
    signIn.hasEmailAccount("noa", "secret-password")

    await events.click(button(t("signIn.showCreateAccount")))
    await fill("noa@example.com", "secret-password")
    await events.click(button(t("signIn.submit.create-account")))
    expect(screen.getByRole("alert")).toHaveTextContent(
      t("signIn.failure.email-in-use")
    )

    await events.click(button(t("signIn.showSignIn")))
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
    expect(emailInput()).toHaveValue("noa@example.com")
    await events.click(button(t("signIn.submit.sign-in")))
    expect(await signIn.idToken()).toBe("token-noa")
  })

  it.each<SignInFailure>(["weak-password", "too-many-attempts", "other"])(
    "shows why creating the account failed: %s",
    async (failure) => {
      const { signIn, events, fill } = renderSignIn()
      signIn.failNextRequest(failure)

      await events.click(button(t("signIn.showCreateAccount")))
      await fill("noa@example.com", "short")
      await events.click(button(t("signIn.submit.create-account")))

      expect(screen.getByRole("alert")).toHaveTextContent(
        t(`signIn.failure.${failure}`)
      )
      expect(emailInput()).toHaveValue("noa@example.com")
      expect(button(t("signIn.submit.create-account"))).toBeEnabled()
    }
  )

  it("sends the password-reset email and confirms it, back on the sign-in form", async () => {
    const { signIn, events, fill } = renderSignIn()
    await fill("noa@example.com")

    await events.click(button(t("signIn.forgotPassword")))
    expect(title()).toHaveTextContent(t("signIn.title.reset-password"))
    expect(
      screen.getByText(t("signIn.description.reset-password"))
    ).toBeInTheDocument()
    expect(
      screen.queryByLabelText(t("signIn.password"))
    ).not.toBeInTheDocument()
    expect(emailInput()).toHaveValue("noa@example.com")

    await events.type(emailInput(), "{Enter}")

    expect(signIn.resetEmailsSentTo).toEqual(["noa@example.com"])
    expect(screen.getByRole("status")).toHaveTextContent(
      t("signIn.resetEmailSent", { email: "noa@example.com" })
    )
    expect(title()).toHaveTextContent(t("signIn.title.sign-in"))
    expect(emailInput()).toHaveValue("noa@example.com")

    await events.type(passwordInput(), "x")
    await events.click(button(t("signIn.submit.sign-in")))
    expect(screen.queryByRole("status")).not.toBeInTheDocument()
  })

  it("shows why the reset email was not sent, and goes back to sign in", async () => {
    const { signIn, events, fill } = renderSignIn()
    signIn.failNextRequest("too-many-attempts")

    await events.click(button(t("signIn.forgotPassword")))
    await fill("noa@example.com")
    await events.click(button(t("signIn.submit.reset-password")))
    expect(screen.getByRole("alert")).toHaveTextContent(
      t("signIn.failure.too-many-attempts")
    )
    expect(signIn.resetEmailsSentTo).toEqual([])

    await events.click(button(t("signIn.showSignIn")))
    expect(title()).toHaveTextContent(t("signIn.title.sign-in"))
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
  })
})
