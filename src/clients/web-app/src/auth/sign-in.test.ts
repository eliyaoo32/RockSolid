import { describe, expect, it } from "vitest"

import { SignInFailed } from "@/auth/sign-in"

describe("sign-in failure", () => {
  it("carries the reason the user sees, and the error that caused it", () => {
    const cause = new Error("auth/weak-password")

    const failed = new SignInFailed("weak-password", { cause })

    expect(failed.failure).toBe("weak-password")
    expect(failed.cause).toBe(cause)
  })
})
