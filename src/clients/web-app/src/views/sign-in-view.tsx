import { useState } from "react"
import { useTranslation } from "react-i18next"

import { useAuth } from "@/auth/auth-context"
import { Alert, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export function SignInView() {
  const { t } = useTranslation()
  const { signIn } = useAuth()
  const [attempt, setAttempt] = useState<"idle" | "pending" | "failed">("idle")
  async function signInWithGoogle() {
    setAttempt("pending")
    try {
      await signIn.signInWithGoogle()
      setAttempt("idle")
    } catch {
      setAttempt("failed")
    }
  }

  return (
    <main className="flex min-h-svh items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>{t("signIn.title")}</CardTitle>
          <CardDescription>{t("signIn.description")}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {attempt === "failed" && (
            <Alert variant="destructive">
              <AlertTitle>{t("signIn.failed")}</AlertTitle>
            </Alert>
          )}
          <Button
            disabled={attempt === "pending"}
            onClick={() => void signInWithGoogle()}
          >
            {t("signIn.google")}
          </Button>
        </CardContent>
      </Card>
    </main>
  )
}
