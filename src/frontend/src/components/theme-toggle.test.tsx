import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"

import { ThemeToggle } from "@/components/theme-toggle"
import i18n from "@/i18n"

import { renderInApp } from "../../tests/framework/render"
import { setSystemTheme } from "../../tests/framework/system-theme"

const LABEL = i18n.t("theme.toggle")

function theme() {
  return document.documentElement.classList.contains("dark") ? "dark" : "light"
}

describe("theme toggle", () => {
  it("follows a light system theme, then switches to dark and back", async () => {
    renderInApp(<ThemeToggle />)
    expect(theme()).toBe("light")

    await userEvent.click(screen.getByRole("button", { name: LABEL }))
    expect(theme()).toBe("dark")

    await userEvent.click(screen.getByRole("button", { name: LABEL }))
    expect(theme()).toBe("light")
  })

  it("follows a dark system theme, then switches to light", async () => {
    setSystemTheme("dark")
    renderInApp(<ThemeToggle />)
    expect(theme()).toBe("dark")

    await userEvent.click(screen.getByRole("button", { name: LABEL }))
    expect(theme()).toBe("light")
  })

  it("names the icon-only button with a label, a title, and a tooltip", async () => {
    renderInApp(<ThemeToggle />)
    const button = screen.getByRole("button", { name: LABEL })

    await userEvent.hover(button)

    expect(button).toHaveAttribute("title", LABEL)
    // Base UI's tooltip has no ARIA role; the button's label already names it.
    await waitFor(() => {
      expect(
        document.querySelector('[data-slot="tooltip-content"]')
      ).toHaveTextContent(LABEL)
    })
  })
})
