import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render } from "@testing-library/react"
import type { ReactNode } from "react"
import { MemoryRouter } from "react-router"

import { AuthProvider } from "@/auth/auth-context"
import { ThemeProvider } from "@/components/theme-provider"
import { TooltipProvider } from "@/components/ui/tooltip"

import { fakeBackend, type Account } from "./fake-backend"
import { FakeSignIn } from "./fake-sign-in"

/**
 * Everything the app gives one of its pieces, against the fake backend, as a `wrapper` for
 * `render` and `renderHook`. `signedInAs` is undefined while it is still unknown whether
 * someone is signed in.
 */
export function inApp({ signedInAs }: { signedInAs?: Account | null } = {}) {
  const signIn = new FakeSignIn(signedInAs)
  const queryClient = new QueryClient()
  const backendCalls = fakeBackend()
  function wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter>
        <ThemeProvider>
          <QueryClientProvider client={queryClient}>
            <AuthProvider signIn={signIn}>
              <TooltipProvider>{children}</TooltipProvider>
            </AuthProvider>
          </QueryClientProvider>
        </ThemeProvider>
      </MemoryRouter>
    )
  }
  return { signIn, queryClient, backendCalls, wrapper }
}

/** Renders one piece of the app inside everything the app gives it. */
export function renderInApp(
  ui: ReactNode,
  options: { signedInAs?: Account | null } = {}
) {
  const app = inApp(options)
  render(ui, { wrapper: app.wrapper })
  return app
}
