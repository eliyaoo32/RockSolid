import { describe, expect, it } from "vitest"

import { DEBUG_USER_JWT_KEY, createDebugSignIn } from "@/auth/debug-sign-in"

function signInWatched() {
  localStorage.setItem(DEBUG_USER_JWT_KEY, "debug-token")
  const reported: boolean[] = []
  const signIn = createDebugSignIn("debug-token")
  const stop = signIn.watchSignedIn((signedIn) => reported.push(signedIn))
  return { signIn, reported, stop }
}

describe("debug sign-in", () => {
  it("starts signed in as the debug user, with the debug token for the backend", async () => {
    const { signIn, reported } = signInWatched()

    expect(reported).toEqual([true])
    expect(await signIn.idToken()).toBe("debug-token")
  })

  it("signs out and forgets the token, then signs in again and keeps it", async () => {
    const { signIn, reported } = signInWatched()

    await signIn.signOut()
    expect(await signIn.idToken()).toBeNull()
    expect(localStorage.getItem(DEBUG_USER_JWT_KEY)).toBeNull()

    await signIn.signInWithGoogle()
    expect(await signIn.idToken()).toBe("debug-token")
    expect(localStorage.getItem(DEBUG_USER_JWT_KEY)).toBe("debug-token")
    expect(reported).toEqual([true, false, true])
  })

  it("stops reporting once the watcher stops", async () => {
    const { signIn, reported, stop } = signInWatched()

    stop()
    await signIn.signOut()

    expect(reported).toEqual([true])
  })
})
