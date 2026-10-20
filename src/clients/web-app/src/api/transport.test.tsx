import { Code, ConnectError, createClient } from "@connectrpc/connect"
import { UsersService } from "@rocksolid/api/users/v1/users_pb"
import { renderHook } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { useApiTransport } from "@/api/transport"

import type { Account } from "../../tests/framework/fake-backend"
import { inApp } from "../../tests/framework/render"

function usersService(signedInAs: Account | null) {
  const app = inApp({ signedInAs })
  const { result } = renderHook(() => useApiTransport(), {
    wrapper: app.wrapper,
  })
  return { ...app, users: createClient(UsersService, result.current) }
}

describe("API transport", () => {
  it("calls the generated service on the page's origin, signed with the user's ID token", async () => {
    const { users, backendCalls } = usersService("dana")

    const { user } = await users.getCurrentUser({})

    expect(user?.displayName).toBe("Dana Levi")
    expect(backendCalls).toEqual([
      {
        url: `${window.location.origin}/users.v1.UsersService/GetCurrentUser`,
        authorization: "Bearer token-dana",
      },
    ])
  })

  it("calls unsigned when nobody is signed in, and the backend refuses", async () => {
    const { users, backendCalls } = usersService(null)

    const call = users.getCurrentUser({})

    await expect(call).rejects.toThrow(ConnectError)
    await expect(call).rejects.toHaveProperty("code", Code.Unauthenticated)
    expect(backendCalls[0]?.authorization).toBeNull()
  })
})
