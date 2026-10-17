import { Code, ConnectError, createClient } from "@connectrpc/connect"
import { UsersService } from "@rocksolid/api/users/v1/users_pb"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook } from "@testing-library/react"
import type { ReactNode } from "react"
import { describe, expect, it } from "vitest"

import { useApiTransport } from "@/api/transport"
import { AuthProvider } from "@/auth/auth-context"

import { fakeBackend, type Account } from "./framework/fake-backend"
import { FakeSignIn } from "./framework/fake-sign-in"

function usersService(signedInAs: Account | null) {
  const signIn = new FakeSignIn(signedInAs)
  const { result } = renderHook(() => useApiTransport(), {
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={new QueryClient()}>
        <AuthProvider signIn={signIn}>{children}</AuthProvider>
      </QueryClientProvider>
    ),
  })
  return createClient(UsersService, result.current)
}

describe("backend calls", () => {
  it("call the generated service on the page's origin, signed with the user's ID token", async () => {
    const calls = fakeBackend()

    const { user } = await usersService("dana").getCurrentUser({})

    expect(user?.displayName).toBe("Dana Levi")
    expect(calls).toEqual([
      {
        url: `${window.location.origin}/users.v1.UsersService/GetCurrentUser`,
        authorization: "Bearer token-dana",
      },
    ])
  })

  it("go unsigned when nobody is signed in, and the backend refuses them", async () => {
    const calls = fakeBackend()

    const call = usersService(null).getCurrentUser({})

    await expect(call).rejects.toThrow(ConnectError)
    await expect(call).rejects.toHaveProperty("code", Code.Unauthenticated)
    expect(calls[0]?.authorization).toBeNull()
  })
})
