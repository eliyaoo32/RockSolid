import { FirebaseError } from "firebase/app"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { createFirebaseSignIn } from "@/auth/firebase-sign-in"
import { SignInFailed, type SignInFailure } from "@/auth/sign-in"

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
    fakeAuth.emailFails = null
    fakeAuth.resetEmailsSentTo = []
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

  it("signs in with an email and password, and gives that user's ID token", async () => {
    const { signIn, reported } = signInWatched()

    await signIn.signInWithEmail("noa@example.com", "secret-password")

    expect(await signIn.idToken()).toBe("token-of-noa@example.com")
    expect(reported).toEqual([false, true])
  })

  it("creates an account with an email and password, and signs it in", async () => {
    const { signIn, reported } = signInWatched()

    await signIn.createAccountWithEmail("noa@example.com", "secret-password")

    expect(await signIn.idToken()).toBe("token-of-noa@example.com")
    expect(reported).toEqual([false, true])
  })

  it("sends the password-reset email to the given address", async () => {
    const { signIn } = signInWatched()

    await signIn.sendPasswordReset("noa@example.com")

    expect(fakeAuth.resetEmailsSentTo).toEqual(["noa@example.com"])
  })

  it.each<[string, SignInFailure]>([
    ["auth/invalid-credential", "wrong-email-or-password"],
    ["auth/wrong-password", "wrong-email-or-password"],
    ["auth/user-not-found", "wrong-email-or-password"],
    ["auth/invalid-email", "wrong-email-or-password"],
    ["auth/email-already-in-use", "email-in-use"],
    ["auth/weak-password", "weak-password"],
    ["auth/too-many-requests", "too-many-attempts"],
    ["auth/network-request-failed", "other"],
  ])("tells the user why when Firebase answers %s", async (code, failure) => {
    const { signIn } = signInWatched()
    const cause = new FirebaseError(code, code)
    fakeAuth.emailFails = cause

    const failed = signIn.signInWithEmail("noa@example.com", "secret-password")

    await expect(failed).rejects.toBeInstanceOf(SignInFailed)
    await expect(failed).rejects.toHaveProperty("failure", failure)
    await expect(failed).rejects.toHaveProperty("cause", cause)
  })

  it("fails every email request the same way, and succeeds on retry", async () => {
    const { signIn, reported } = signInWatched()

    fakeAuth.emailFails = new FirebaseError("auth/email-already-in-use", "")
    await expect(
      signIn.createAccountWithEmail("noa@example.com", "secret-password")
    ).rejects.toHaveProperty("failure", "email-in-use")
    fakeAuth.emailFails = new Error("Offline")
    await expect(
      signIn.sendPasswordReset("noa@example.com")
    ).rejects.toHaveProperty("failure", "other")
    expect(fakeAuth.resetEmailsSentTo).toEqual([])

    await signIn.sendPasswordReset("noa@example.com")
    await signIn.createAccountWithEmail("noa@example.com", "secret-password")
    expect(fakeAuth.resetEmailsSentTo).toEqual(["noa@example.com"])
    expect(reported).toEqual([false, true])
  })
})
