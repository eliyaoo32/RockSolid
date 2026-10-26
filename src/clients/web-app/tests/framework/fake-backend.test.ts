import { Code, ConnectError, createClient } from "@connectrpc/connect"
import { UserSchema, UsersService } from "@rocksolid/api/users/v1/users_pb"
import { renderHook } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { useApiTransport } from "@/api/transport"

import { FakeUsers } from "./fake-backend"
import { inApp } from "./render"

function usersAs(signedInAs: "dana" | null) {
  const app = inApp({ signedInAs })
  const { result } = renderHook(() => useApiTransport(), {
    wrapper: app.wrapper,
  })
  return { ...app, users: createClient(UsersService, result.current) }
}

async function failureOf(call: Promise<unknown>): Promise<ConnectError> {
  try {
    await call
  } catch (error) {
    return ConnectError.from(error)
  }
  throw new Error("The call succeeded")
}

describe("fake backend", () => {
  it("answers through the running fake, whose state a test changes", async () => {
    const { users, backend } = usersAs("dana")
    backend.fake(FakeUsers).methods.GetCurrentUser = () => ({
      user: {
        name: "users/dana",
        displayName: "Dana Cohen",
        email: "dana@example.com",
      },
    })

    const { user } = await users.getCurrentUser({})

    expect(user?.displayName).toBe("Dana Cohen")
  })

  it("fails a call with the fake's error code, message, and details", async () => {
    const { users, backend } = usersAs("dana")
    backend.fake(FakeUsers).methods.GetCurrentUser = () => {
      throw new ConnectError(
        "Already taken.",
        Code.FailedPrecondition,
        undefined,
        [{ desc: UserSchema, value: { displayName: "Noa Bar" } }]
      )
    }

    const failure = await failureOf(users.getCurrentUser({}))

    expect(failure.code).toBe(Code.FailedPrecondition)
    expect(failure.rawMessage).toBe("Already taken.")
    expect(failure.findDetails(UserSchema)[0]?.displayName).toBe("Noa Bar")
  })

  it("refuses a caller who is not signed in", async () => {
    const { users } = usersAs(null)

    const failure = await failureOf(users.getCurrentUser({}))

    expect(failure.code).toBe(Code.Unauthenticated)
  })
})
