import { act, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, useLocation } from "react-router"

import { App } from "@/App"
import { ThemeProvider } from "@/components/theme-provider"
import i18n from "@/i18n"

import { emailOf, fakeBackend, USERS, type Account } from "./fake-backend"
import { FakeSignIn } from "./fake-sign-in"

const t = i18n.t.bind(i18n)

/**
 * Opens the app at `path`, against the fake backend. `signedInAs` is undefined while it is still
 * unknown whether someone is signed in.
 */
export function renderApp({
  path = "/",
  signedInAs,
}: { path?: string; signedInAs?: Account | null } = {}) {
  const signIn = new FakeSignIn(signedInAs)
  fakeBackend()
  let pathname = path
  function TrackPath() {
    pathname = useLocation().pathname
    return null
  }
  render(
    <MemoryRouter initialEntries={[path]}>
      <TrackPath />
      <ThemeProvider>
        <App signIn={signIn} />
      </ThemeProvider>
    </MemoryRouter>
  )
  const events = userEvent.setup()
  const click = (name: string) =>
    events.click(screen.getByRole("button", { name }))
  const field = (label: string) => screen.getByLabelText(label)
  async function fill(label: string, text: string) {
    await events.clear(field(label))
    await events.type(field(label), text)
  }

  return {
    when: {
      signInStateArrives: (signedInAs: Account | null) => {
        act(() => {
          signIn.report(signedInAs)
        })
      },
      googleRefusesNextSignIn: () => {
        signIn.googleRefusesNextSignIn()
      },
      signInWithGoogleAs: (account: Account) => {
        signIn.googleAccount = account
        return click(t("signIn.google"))
      },
      hasEmailAccount: (account: Account, password: string) => {
        signIn.hasEmailAccount(account, password)
      },
      /** Types the email and password and presses Enter. */
      signInWithEmail: async (account: Account, password: string) => {
        await fill(t("signIn.email"), emailOf(account))
        await fill(t("signIn.password"), password)
        await events.keyboard("{Enter}")
      },
      createAccountWithEmail: async (account: Account, password: string) => {
        await click(t("signIn.showCreateAccount"))
        await fill(t("signIn.email"), emailOf(account))
        await fill(t("signIn.password"), password)
        await click(t("signIn.submit.create-account"))
      },
      goBackToSignIn: () => click(t("signIn.showSignIn")),
      sendPasswordReset: async (account: Account) => {
        await click(t("signIn.forgotPassword"))
        await fill(t("signIn.email"), emailOf(account))
        await click(t("signIn.submit.reset-password"))
      },
      signOut: () => click(t("signIn.signOut")),
    },
    get: {
      path: () => pathname,
      isLoading: () =>
        screen.queryAllByRole("status", { name: t("loading") }).length > 0,
      showsSignInScreen: () =>
        screen.queryByRole("button", { name: t("signIn.google") }) !== null,
      showsSignInError: () =>
        screen.queryByText(t("signIn.failure.other")) !== null,
      /** The error or confirmation the sign-in screen shows, or null when it shows none. */
      signInMessage: () =>
        (screen.queryByRole("alert") ?? screen.queryByRole("status"))
          ?.textContent ?? null,
      typedEmail: () => (field(t("signIn.email")) as HTMLInputElement).value,
      resetEmailsSentTo: () => signIn.resetEmailsSentTo,
      /** Waits for the header to show the user's name, as the backend knows them. */
      userName: async (account: Account) =>
        (await screen.findByText(USERS[account])).textContent,
    },
  }
}
