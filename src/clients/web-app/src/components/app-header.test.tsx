import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { AppHeader } from "@/components/app-header"
import i18n from "@/i18n"

import { renderInApp } from "../../tests/framework/render"

describe("app header", () => {
  it("shows a skeleton until the backend says who the user is, then their name", async () => {
    renderInApp(<AppHeader />, { signedInAs: "dana" })

    expect(
      screen.getByRole("status", { name: i18n.t("loading") })
    ).toBeInTheDocument()
    expect(await screen.findByText("Dana Levi")).toBeInTheDocument()
    expect(screen.queryByRole("status")).not.toBeInTheDocument()
  })

  it("signs the user out", async () => {
    const { signIn } = renderInApp(<AppHeader />, { signedInAs: "dana" })
    const signOut = vi.spyOn(signIn, "signOut")

    await userEvent.click(
      screen.getByRole("button", { name: i18n.t("signIn.signOut") })
    )

    expect(signOut).toHaveBeenCalledOnce()
  })
})
