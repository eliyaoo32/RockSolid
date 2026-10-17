import {
  FirebaseError,
  initializeApp,
  type FirebaseOptions,
} from "firebase/app"
import {
  GoogleAuthProvider,
  getAuth,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
} from "firebase/auth"

import type { SignIn } from "./sign-in"

// The user closed the Google window, or opened a second one: a choice, not a failure.
const CANCELLED = new Set([
  "auth/popup-closed-by-user",
  "auth/cancelled-popup-request",
])

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
    signOut: () => signOut(auth),
    idToken: async () => (await auth.currentUser?.getIdToken()) ?? null,
  }
}
