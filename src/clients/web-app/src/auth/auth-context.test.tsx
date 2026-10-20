import { act, renderHook } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { useAuth } from "@/auth/auth-context"

import { inApp } from "../../tests/framework/render"

function renderAuth() {
  const app = inApp()
  app.queryClient.setQueryData(["cached"], "from the previous user")
  const { result } = renderHook(() => useAuth(), { wrapper: app.wrapper })
  return { ...app, result }
}

describe("auth context", () => {
  it("is unknown until the sign-in state arrives, then follows it", () => {
    const { signIn, result } = renderAuth()
    expect(result.current.signedIn).toBeUndefined()

    act(() => {
      signIn.report("dana")
    })
    expect(result.current.signedIn).toBe(true)

    act(() => {
      signIn.report(null)
    })
    expect(result.current.signedIn).toBe(false)
  })

  it("forgets every cached answer when the user signs out", () => {
    const { signIn, queryClient } = renderAuth()

    act(() => {
      signIn.report("dana")
    })
    expect(queryClient.getQueryData(["cached"])).toBe("from the previous user")

    act(() => {
      signIn.report(null)
    })
    expect(queryClient.getQueryData(["cached"])).toBeUndefined()
  })

  it("refuses to tell whether someone is signed in outside the app", () => {
    expect(() => renderHook(() => useAuth())).toThrow(
      "useAuth must be used inside AuthProvider"
    )
  })
})
