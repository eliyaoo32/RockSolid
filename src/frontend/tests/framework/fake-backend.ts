import { vi } from "vitest"

/** The backend's users, by the account each one signs in with. */
export const USERS = { dana: "Dana Levi", noa: "Noa Bar" }
export type Account = keyof typeof USERS

function isAccount(value: string | undefined): value is Account {
  return value !== undefined && value in USERS
}

/** Serves the backend's calls the way the backend would, and records each call. */
export function fakeBackend() {
  const calls: { url: string; authorization: string | null }[] = []
  vi.stubGlobal("fetch", (url: string, init: RequestInit) => {
    const authorization = new Headers(init.headers).get("authorization")
    calls.push({ url, authorization })
    const account = authorization?.replace("Bearer token-", "")
    if (!url.endsWith("/users.v1.UsersService/GetCurrentUser")) {
      return Promise.resolve(
        Response.json({ code: "unimplemented", message: url }, { status: 501 })
      )
    }
    if (!isAccount(account)) {
      return Promise.resolve(
        Response.json(
          { code: "unauthenticated", message: "Sign in to call this method." },
          { status: 401 }
        )
      )
    }
    return Promise.resolve(
      Response.json({
        user: {
          name: `users/${account}`,
          displayName: USERS[account],
          email: `${account}@example.com`,
        },
      })
    )
  })
  return calls
}
