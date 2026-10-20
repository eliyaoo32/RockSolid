import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useState } from "react"
import { Navigate, Route, Routes } from "react-router"

import { AuthProvider, useAuth } from "@/auth/auth-context"
import type { SignIn } from "@/auth/sign-in"
import { AppHeader } from "@/components/app-header"
import { PageSkeleton } from "@/components/page-skeleton"
import { TooltipProvider } from "@/components/ui/tooltip"
import { HomeView } from "@/views/home-view"
import { SignInView } from "@/views/sign-in-view"

export function App({ signIn }: { signIn: SignIn }) {
  const [queryClient] = useState(() => new QueryClient())
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider signIn={signIn}>
        <TooltipProvider>
          <AppContent />
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>
  )
}

function AppContent() {
  const { signedIn } = useAuth()
  if (signedIn === undefined) {
    return <PageSkeleton />
  }
  if (!signedIn) {
    return <SignInView />
  }
  return (
    <div className="flex min-h-svh flex-col">
      <AppHeader />
      <main className="flex-1 p-4">
        <Routes>
          <Route path="/" element={<HomeView />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
