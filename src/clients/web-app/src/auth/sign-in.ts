/**
 * Signs the user in with Google. It knows only whether someone is signed in and their ID token;
 * everything about the user comes from the backend's UsersService.
 */
export interface SignIn {
  /**
   * Calls `onChange` with whether someone is signed in, once that is known and again on every
   * change. Returns a function that stops the calls.
   */
  watchSignedIn(onChange: (signedIn: boolean) => void): () => void
  /** Signs in with Google. Resolves without signing in when the user closes the Google window. */
  signInWithGoogle(): Promise<void>
  signOut(): Promise<void>
  /** The signed-in user's ID token for the backend, or null when nobody is signed in. */
  idToken(): Promise<string | null>
}
