import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { PageSkeleton } from "@/components/page-skeleton"
import i18n from "@/i18n"

describe("page skeleton", () => {
  it("tells assistive technology that the page is loading", () => {
    render(<PageSkeleton />)

    expect(
      screen.getByRole("status", { name: i18n.t("loading") })
    ).toBeInTheDocument()
  })
})
