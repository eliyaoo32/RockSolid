import type { SignIn } from "@/auth/sign-in"

import type { Account } from "./fake-backend"

/** Signs in the way Google would, without leaving the test. */
export class FakeSignIn implements SignIn {
  /** The account the Google window signs in with. */
  googleAccount: Account = "dana"
  private readonly listeners = new Set<(signedIn: boolean) => void>()
  private refuseNextSignIn = false
  /** Undefined until `report` says whether someone is signed in. */
  private signedInAs: Account | null | undefined

  constructor(signedInAs?: Account | null) {
    this.signedInAs = signedInAs
  }

  watchSignedIn(onChange: (signedIn: boolean) => void) {
    this.listeners.add(onChange)
    if (this.signedInAs !== undefined) {
      onChange(this.signedInAs !== null)
    }
    return () => {
      this.listeners.delete(onChange)
    }
  }

  report(signedInAs: Account | null) {
    this.signedInAs = signedInAs
    for (const listener of this.listeners) {
      listener(signedInAs !== null)
    }
  }

  googleRefusesNextSignIn() {
    this.refuseNextSignIn = true
  }

  signInWithGoogle() {
    if (this.refuseNextSignIn) {
      this.refuseNextSignIn = false
      return Promise.reject(new Error("Google refused the sign-in"))
    }
    this.report(this.googleAccount)
    return Promise.resolve()
  }

  signOut() {
    this.report(null)
    return Promise.resolve()
  }

  idToken() {
    return Promise.resolve(this.signedInAs ? `token-${this.signedInAs}` : null)
  }
}
