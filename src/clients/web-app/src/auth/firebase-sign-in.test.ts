import { beforeEach, describe, expect, it, vi } from "vitest"

import { createFirebaseSignIn } from "@/auth/firebase-sign-in"

import {
  fakeAuth,
  firebaseUser,
} from "../../tests/framework/fake-firebase-auth"

vi.mock(
  "firebase/auth",
  () => import("../../tests/framework/fake-firebase-auth")
)

function signInWatched() {
  const reported: boolean[] = []
  const signIn = createFirebaseSignIn({ apiKey: "key", projectId: "project" })
  const stop = signIn.watchSignedIn((signedIn) => reported.push(signedIn))
  return { signIn, reported, stop }
}

describe("Firebase sign-in", () => {
  beforeEach(() => {
    fakeAuth.currentUser = null
    fakeAuth.popup = "signs-in"
    fakeAuth.googleUser = firebaseUser("dana@example.com")
  })

  it("signs in with Google, gives the ID token, signs out, and stops reporting", async () => {
    const { signIn, reported, stop } = signInWatched()
    expect(await signIn.idToken()).toBeNull()

    await signIn.signInWithGoogle()
    expect(await signIn.idToken()).toBe("token-of-dana@example.com")

    await signIn.signOut()
    expect(await signIn.idToken()).toBeNull()
    expect(reported).toEqual([false, true, false])

    stop()
    expect(fakeAuth.listener).toBeUndefined()
  })

  it("stays signed out without an error when the user closes the Google window", async () => {
    const { signIn, reported } = signInWatched()
    fakeAuth.popup = "closed"

    await signIn.signInWithGoogle()

    expect(reported).toEqual([false])
  })

  it("fails when Google fails, then signs in on retry", async () => {
    const { signIn, reported } = signInWatched()
    fakeAuth.popup = "fails"

    await expect(signIn.signInWithGoogle()).rejects.toThrow("Network failed")

    fakeAuth.popup = "signs-in"
    await signIn.signInWithGoogle()
    expect(reported).toEqual([false, true])
  })
})
