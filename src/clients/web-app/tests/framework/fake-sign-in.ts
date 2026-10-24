import { SignInFailed, type SignIn, type SignInFailure } from "@/auth/sign-in"

import { accountOf, emailOf, type Account } from "./fake-backend"

/** Signs in the way Google and Firebase's email sign-in would, without leaving the test. */
export class FakeSignIn implements SignIn {
  /** The account the Google window signs in with. */
  googleAccount: Account = "dana"
  /** The addresses the password-reset email was sent to, in order. */
  readonly resetEmailsSentTo: string[] = []
  private readonly listeners = new Set<(signedIn: boolean) => void>()
  /** The password of each email that has an account. */
  private readonly passwords = new Map<string, string>()
  private nextFailure: Error | undefined
  private pendingRequest = Promise.resolve()
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

  hasEmailAccount(account: Account, password: string) {
    this.passwords.set(emailOf(account), password)
  }

  googleRefusesNextSignIn() {
    this.nextFailure = new Error("Google refused the sign-in")
  }

  /** Fails the next request with `failure`, the way Firebase's answer maps to it. */
  failNextRequest(failure: SignInFailure) {
    this.nextFailure = new SignInFailed(failure)
  }

  /** Keeps the next request pending until the returned function finishes it. */
  holdNextRequest(): () => void {
    let finish!: () => void
    this.pendingRequest = new Promise<void>((resolve) => {
      finish = resolve
    })
    return finish
  }

  async signInWithGoogle() {
    await this.request()
    this.report(this.googleAccount)
  }

  async signInWithEmail(email: string, password: string) {
    await this.request()
    if (this.passwords.get(email) !== password) {
      throw new SignInFailed("wrong-email-or-password")
    }
    this.report(accountOf(email))
  }

  async createAccountWithEmail(email: string, password: string) {
    await this.request()
    if (this.passwords.has(email)) {
      throw new SignInFailed("email-in-use")
    }
    this.passwords.set(email, password)
    this.report(accountOf(email))
  }

  async sendPasswordReset(email: string) {
    await this.request()
    this.resetEmailsSentTo.push(email)
  }

  signOut() {
    this.report(null)
    return Promise.resolve()
  }

  idToken() {
    return Promise.resolve(this.signedInAs ? `token-${this.signedInAs}` : null)
  }

  private async request() {
    const failure = this.nextFailure
    if (failure) {
      this.nextFailure = undefined
      throw failure
    }
    await this.pendingRequest
  }
}
