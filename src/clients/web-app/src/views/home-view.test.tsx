import { render } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { HomeView } from "@/views/home-view"

describe("home view", () => {
  it("stays empty until the product adds its content", () => {
    const { container } = render(<HomeView />)

    expect(container).toBeEmptyDOMElement()
  })
})
