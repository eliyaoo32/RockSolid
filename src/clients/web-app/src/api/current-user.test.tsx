import { renderHook, waitFor } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { useCurrentUser } from "@/api/current-user"

import { inApp } from "../../tests/framework/render"

describe("current user", () => {
  it("is the signed-in user, as the backend knows them", async () => {
    const { wrapper } = inApp({ signedInAs: "dana" })

    const { result } = renderHook(() => useCurrentUser(), { wrapper })

    await waitFor(() => {
      expect(result.current.data?.displayName).toBe("Dana Levi")
    })
  })
})
