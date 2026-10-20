import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"

import i18n from "@/i18n"
import { SignInView } from "@/views/sign-in-view"

import { renderInApp } from "../../tests/framework/render"

const t = i18n.t.bind(i18n)

function googleButton() {
  return screen.getByRole("button", { name: t("signIn.google") })
}

describe("sign-in view", () => {
  it("asks the user to sign in with Google", () => {
    renderInApp(<SignInView />, { signedInAs: null })

    expect(screen.getByText(t("signIn.title"))).toBeInTheDocument()
    expect(screen.getByText(t("signIn.description"))).toBeInTheDocument()
    expect(googleButton()).toBeEnabled()
  })

  it("disables the button while the Google window is open", async () => {
    const { signIn } = renderInApp(<SignInView />, { signedInAs: null })
    const closeGoogleWindow = signIn.holdGoogleWindow()

    await userEvent.click(googleButton())
    expect(googleButton()).toBeDisabled()

    closeGoogleWindow()
    await expect.poll(() => googleButton().hasAttribute("disabled")).toBe(false)
  })

  it("shows an error when Google refuses, and clears it when the retry succeeds", async () => {
    const { signIn } = renderInApp(<SignInView />, { signedInAs: null })
    signIn.googleRefusesNextSignIn()

    await userEvent.click(googleButton())
    expect(screen.getByText(t("signIn.failed"))).toBeInTheDocument()
    expect(googleButton()).toBeEnabled()

    await userEvent.click(googleButton())
    expect(screen.queryByText(t("signIn.failed"))).not.toBeInTheDocument()
  })
})
