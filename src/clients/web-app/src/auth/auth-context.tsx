import { useQueryClient } from "@tanstack/react-query"
import { createContext, use, useEffect, useState, type ReactNode } from "react"

import type { SignIn } from "./sign-in"

interface Auth {
  /** Whether someone is signed in, or undefined until that is known. */
  signedIn: boolean | undefined
  signIn: SignIn
}

const AuthContext = createContext<Auth | null>(null)

export function AuthProvider({
  signIn,
  children,
}: {
  signIn: SignIn
  children: ReactNode
}) {
  const queryClient = useQueryClient()
  const [signedIn, setSignedIn] = useState<boolean>()
  useEffect(
    () =>
      signIn.watchSignedIn((now) => {
        // The next user must never see the previous user's cached data.
        if (!now) {
          queryClient.clear()
        }
        setSignedIn(now)
      }),
    [signIn, queryClient]
  )
  return <AuthContext value={{ signedIn, signIn }}>{children}</AuthContext>
}

export function useAuth(): Auth {
  const auth = use(AuthContext)
  if (!auth) {
    throw new Error("useAuth must be used inside AuthProvider")
  }
  return auth
}
