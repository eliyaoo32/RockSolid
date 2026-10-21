import type { Transport } from "@connectrpc/connect"
import { createConnectTransport } from "@connectrpc/connect-web"
import { useMemo } from "react"

import { useAuth } from "@/auth/auth-context"

/**
 * The transport for clients of the generated services (`createClient(Service, transport)`).
 * It calls the backend on the page's own origin and signs every call with the user's ID token.
 */
export function useApiTransport(): Transport {
  const { signIn } = useAuth()
  return useMemo(
    () =>
      createConnectTransport({
        baseUrl: window.location.origin,
        interceptors: [
          (next) => async (request) => {
            const token = await signIn.idToken()
            if (token) {
              request.header.set("Authorization", `Bearer ${token}`)
            }
            return next(request)
          },
        ],
      }),
    [signIn]
  )
}
