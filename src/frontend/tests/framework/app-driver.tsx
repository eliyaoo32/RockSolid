import { act, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, useLocation } from "react-router"

import { App } from "@/App"
import { ThemeProvider } from "@/components/theme-provider"
import i18n from "@/i18n"

import { fakeBackend, USERS, type Account } from "./fake-backend"
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
      signOut: () => click(t("signIn.signOut")),
      toggleTheme: () => click(t("theme.toggle")),
    },
    get: {
      path: () => pathname,
      isLoading: () =>
        screen.queryAllByRole("status", { name: t("loading") }).length > 0,
      showsSignInScreen: () =>
        screen.queryByRole("button", { name: t("signIn.google") }) !== null,
      showsSignInError: () => screen.queryByText(t("signIn.failed")) !== null,
      /** Waits for the header to show the user's name, as the backend knows them. */
      userName: async (account: Account) =>
        (await screen.findByText(USERS[account])).textContent,
      theme: () =>
        document.documentElement.classList.contains("dark") ? "dark" : "light",
    },
  }
}
