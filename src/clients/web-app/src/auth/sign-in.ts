/** Why a sign-in request failed, as the user can act on it. */
export type SignInFailure =
  | "wrong-email-or-password"
  | "email-in-use"
  | "weak-password"
  | "too-many-attempts"
  | "other"

/** Thrown by the email requests of `SignIn`, with the reason the user sees. */
export class SignInFailed extends Error {
  readonly failure: SignInFailure

  constructor(failure: SignInFailure, options?: ErrorOptions) {
    super(failure, options)
    this.failure = failure
  }
}

/**
 * Signs the user in with Google, or with an email and password. It knows only whether someone is
 * signed in and their ID token; everything about the user comes from the backend's UsersService.
 */
export interface SignIn {
  /**
   * Calls `onChange` with whether someone is signed in, once that is known and again on every
   * change. Returns a function that stops the calls.
   */
  watchSignedIn(onChange: (signedIn: boolean) => void): () => void
  /** Signs in with Google. Resolves without signing in when the user closes the Google window. */
  signInWithGoogle(): Promise<void>
  /** Signs in with an email and password. Rejects with `SignInFailed`. */
  signInWithEmail(email: string, password: string): Promise<void>
  /** Creates an account with an email and password, and signs in. Rejects with `SignInFailed`. */
  createAccountWithEmail(email: string, password: string): Promise<void>
  /** Emails a link to choose a new password. Rejects with `SignInFailed`. */
  sendPasswordReset(email: string): Promise<void>
  signOut(): Promise<void>
  /** The signed-in user's ID token for the backend, or null when nobody is signed in. */
  idToken(): Promise<string | null>
}
