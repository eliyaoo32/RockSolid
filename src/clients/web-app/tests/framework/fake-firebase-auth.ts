import { FirebaseError } from "firebase/app"

interface FakeFirebaseUser {
  getIdToken: () => Promise<string>
}

/** Stands in for the `firebase/auth` module: `vi.mock("firebase/auth", () => import(...))`. */
export const fakeAuth = {
  currentUser: null as FakeFirebaseUser | null,
  googleUser: null as FakeFirebaseUser | null,
  popup: "signs-in" as "signs-in" | "closed" | "fails",
  listener: undefined as ((user: FakeFirebaseUser | null) => void) | undefined,
}

function setUser(user: FakeFirebaseUser | null) {
  fakeAuth.currentUser = user
  fakeAuth.listener?.(user)
}

export function firebaseUser(email: string): FakeFirebaseUser {
  return { getIdToken: () => Promise.resolve(`token-of-${email}`) }
}

export function getAuth() {
  return fakeAuth
}

export class GoogleAuthProvider {
  readonly providerId = "google.com"
}

export function onAuthStateChanged(
  _auth: unknown,
  listener: (user: FakeFirebaseUser | null) => void
) {
  fakeAuth.listener = listener
  listener(fakeAuth.currentUser)
  return () => {
    fakeAuth.listener = undefined
  }
}

export function signInWithPopup(_auth: unknown, provider: unknown) {
  if (!(provider instanceof GoogleAuthProvider)) {
    return Promise.reject(new Error("Only Google sign-in is faked"))
  }
  if (fakeAuth.popup === "closed") {
    return Promise.reject(
      new FirebaseError("auth/popup-closed-by-user", "Popup closed")
    )
  }
  if (fakeAuth.popup === "fails") {
    return Promise.reject(
      new FirebaseError("auth/network-request-failed", "Network failed")
    )
  }
  setUser(fakeAuth.googleUser)
  return Promise.resolve()
}

export function signOut() {
  setUser(null)
  return Promise.resolve()
}
