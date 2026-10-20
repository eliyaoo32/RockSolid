import type { SignIn } from "./sign-in"

/** Where the browser keeps the backend's debug user token, such as E2E tests put it. */
export const DEBUG_USER_JWT_KEY = "rocksolid.debugUserJwt"

/**
 * Signs in as the backend's debug user with its token, in place of Google. Only a backend run
 * with `DEBUG=true` and the same `DEBUG_USER_JWT` accepts the token.
 */
export function createDebugSignIn(token: string): SignIn {
  const listeners = new Set<(signedIn: boolean) => void>()
  let signedIn = true
  function report(now: boolean) {
    signedIn = now
    for (const listener of listeners) {
      listener(now)
    }
  }
  return {
    watchSignedIn: (onChange) => {
      listeners.add(onChange)
      onChange(signedIn)
      return () => {
        listeners.delete(onChange)
      }
    },
    signInWithGoogle: () => {
      localStorage.setItem(DEBUG_USER_JWT_KEY, token)
      report(true)
      return Promise.resolve()
    },
    signOut: () => {
      localStorage.removeItem(DEBUG_USER_JWT_KEY)
      report(false)
      return Promise.resolve()
    },
    idToken: () => Promise.resolve(signedIn ? token : null),
  }
}
