import {
  create,
  fromJson,
  toJson,
  type DescService,
  type JsonValue,
} from "@bufbuild/protobuf"
import { Code, ConnectError } from "@connectrpc/connect"
import {
  codeToHttpStatus,
  errorToJson,
} from "@connectrpc/connect/protocol-connect"
import { UsersService } from "@rocksolid/api/users/v1/users_pb"
import { vi } from "vitest"

import { FAKE_SERVICES } from "./fake-services"

/** The backend's users, by the account each one signs in with. */
export const USERS = { dana: "Dana Levi", noa: "Noa Bar" }
export type Account = keyof typeof USERS

function isAccount(value: string | undefined): value is Account {
  return value !== undefined && value in USERS
}

export function emailOf(account: Account) {
  return `${account}@example.com`
}

/** The account an email belongs to, for the emails of the backend's users only. */
export function accountOf(email: string): Account {
  const account = email.replace(/@example\.com$/, "")
  if (!isAccount(account)) {
    throw new Error(`The backend has no user with the email ${email}`)
  }
  return account
}

/**
 * A fake of one of the backend's services. `fakeBackend` serves its methods through the
 * service's contract, the way the backend does, so a test reads and changes the fake's state.
 */
export interface FakeService {
  readonly service: DescService
  /**
   * Each method the fake answers, by its name in the contract, such as `GetCurrentUser`. It gets
   * the request and the signed-in account, returns the response, and throws ConnectError to fail.
   */
  readonly methods: Record<
    string,
    (request: never, account: Account) => unknown
  >
}

/** The backend's UsersService: each account sees itself. */
export class FakeUsers implements FakeService {
  readonly service = UsersService
  readonly methods = {
    GetCurrentUser: (_request: never, account: Account) => ({
      user: {
        name: `users/${account}`,
        displayName: USERS[account],
        email: emailOf(account),
      },
    }),
  }
}

/**
 * Serves the backend's calls through the fakes of its services, `FakeUsers` and every fake in
 * `FAKE_SERVICES`, and records each call.
 */
export function fakeBackend() {
  const calls: { url: string; authorization: string | null }[] = []
  const fakes: FakeService[] = [
    new FakeUsers(),
    ...FAKE_SERVICES.map((Fake) => new Fake()),
  ]
  vi.stubGlobal("fetch", async (url: string, init: RequestInit) => {
    const authorization = new Headers(init.headers).get("authorization")
    calls.push({ url, authorization })
    try {
      return Response.json(await answer(fakes, url, init, authorization))
    } catch (error) {
      const failure = ConnectError.from(error)
      return Response.json(errorToJson(failure, undefined), {
        status: codeToHttpStatus(failure.code),
      })
    }
  })
  return {
    calls,
    /** The running fake of this kind, such as `backend.fake(FakeUsers)`. */
    fake<T extends FakeService>(kind: new () => T): T {
      const found = fakes.find((fake): fake is T => fake instanceof kind)
      if (found === undefined) {
        throw new Error(`No ${kind.name} is in FAKE_SERVICES`)
      }
      return found
    },
  }
}

async function answer(
  fakes: FakeService[],
  url: string,
  init: RequestInit,
  authorization: string | null
) {
  const [typeName, methodName = ""] = new URL(url).pathname.slice(1).split("/")
  const fake = fakes.find(
    (candidate) => candidate.service.typeName === typeName
  )
  const method = fake?.service.methods.find((m) => m.name === methodName)
  const implementation = fake?.methods[methodName]
  if (method === undefined || implementation === undefined) {
    throw new ConnectError(url, Code.Unimplemented)
  }
  const account = authorization?.replace("Bearer token-", "")
  if (!isAccount(account)) {
    throw new ConnectError("Sign in to call this method.", Code.Unauthenticated)
  }
  // connect-web sends each request as JSON bytes.
  const body = new TextDecoder().decode(init.body as Uint8Array)
  const request = fromJson(method.input, JSON.parse(body) as JsonValue)
  const response = await implementation(request as never, account)
  return toJson(method.output, create(method.output, response as never))
}
