import {
  FirebaseError,
  initializeApp,
  type FirebaseOptions,
} from "firebase/app"
import {
  GoogleAuthProvider,
  createUserWithEmailAndPassword,
  getAuth,
  onAuthStateChanged,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
} from "firebase/auth"

import { SignInFailed, type SignInFailure, type SignIn } from "./sign-in"

// The user closed the Google window, or opened a second one: a choice, not a failure.
const CANCELLED = new Set([
  "auth/popup-closed-by-user",
  "auth/cancelled-popup-request",
])

// Firebase's error codes that the user can act on; every other code is "other".
const FAILURES: Partial<Record<string, SignInFailure>> = {
  "auth/invalid-credential": "wrong-email-or-password",
  "auth/wrong-password": "wrong-email-or-password",
  "auth/user-not-found": "wrong-email-or-password",
  "auth/invalid-email": "wrong-email-or-password",
  "auth/email-already-in-use": "email-in-use",
  "auth/weak-password": "weak-password",
  "auth/too-many-requests": "too-many-attempts",
}

async function failingAsSignInFailed(request: Promise<unknown>) {
  try {
    await request
  } catch (error) {
    const failure =
      error instanceof FirebaseError ? FAILURES[error.code] : undefined
    throw new SignInFailed(failure ?? "other", { cause: error })
  }
}

export function createFirebaseSignIn(options: FirebaseOptions): SignIn {
  const auth = getAuth(initializeApp(options))
  return {
    watchSignedIn: (onChange) =>
      onAuthStateChanged(auth, (user) => {
        onChange(user !== null)
      }),
    signInWithGoogle: async () => {
      try {
        await signInWithPopup(auth, new GoogleAuthProvider())
      } catch (error) {
        if (!(error instanceof FirebaseError && CANCELLED.has(error.code))) {
          throw error
        }
      }
    },
    signInWithEmail: (email, password) =>
      failingAsSignInFailed(signInWithEmailAndPassword(auth, email, password)),
    createAccountWithEmail: (email, password) =>
      failingAsSignInFailed(
        createUserWithEmailAndPassword(auth, email, password)
      ),
    sendPasswordReset: (email) =>
      failingAsSignInFailed(sendPasswordResetEmail(auth, email)),
    signOut: () => signOut(auth),
    idToken: async () => (await auth.currentUser?.getIdToken()) ?? null,
  }
}
