import { Loader2Icon } from "lucide-react"
import { useId, useState } from "react"
import { useTranslation } from "react-i18next"

import { useAuth } from "@/auth/auth-context"
import { SignInFailed, type SignInFailure } from "@/auth/sign-in"
import { Alert, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

type Mode = "sign-in" | "create-account" | "reset-password"

export function SignInView() {
  const { t } = useTranslation()
  const { signIn } = useAuth()
  const [mode, setMode] = useState<Mode>("sign-in")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [pending, setPending] = useState<"google" | "email" | null>(null)
  const [failure, setFailure] = useState<SignInFailure | null>(null)
  const [resetEmailSentTo, setResetEmailSentTo] = useState<string | null>(null)
  const emailId = useId()
  const passwordId = useId()

  function switchTo(next: Mode) {
    setMode(next)
    setFailure(null)
    setResetEmailSentTo(null)
  }

  async function run(kind: "google" | "email", request: () => Promise<void>) {
    setPending(kind)
    setFailure(null)
    setResetEmailSentTo(null)
    try {
      await request()
    } catch (error) {
      setFailure(error instanceof SignInFailed ? error.failure : "other")
    }
    setPending(null)
  }

  function submitEmail() {
    void run("email", async () => {
      if (mode === "sign-in") {
        await signIn.signInWithEmail(email, password)
      } else if (mode === "create-account") {
        await signIn.createAccountWithEmail(email, password)
      } else {
        await signIn.sendPasswordReset(email)
        setMode("sign-in")
        setResetEmailSentTo(email)
      }
    })
  }

  const spinner = <Loader2Icon aria-hidden className="animate-spin" />

  return (
    <main className="flex min-h-svh items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>{t(`signIn.title.${mode}`)}</CardTitle>
          <CardDescription>{t(`signIn.description.${mode}`)}</CardDescription>
        </CardHeader>
        <CardContent>
          {/* A disabled fieldset disables every control in it while a request runs. */}
          <fieldset disabled={pending !== null} className="flex flex-col gap-4">
            {pending && (
              <span role="status" className="sr-only">
                {t("loading")}
              </span>
            )}
            {failure && (
              <Alert variant="destructive">
                <AlertTitle>{t(`signIn.failure.${failure}`)}</AlertTitle>
              </Alert>
            )}
            {resetEmailSentTo && (
              <Alert role="status">
                <AlertTitle>
                  {t("signIn.resetEmailSent", { email: resetEmailSentTo })}
                </AlertTitle>
              </Alert>
            )}
            {mode !== "reset-password" && (
              <>
                <Button
                  variant="outline"
                  onClick={() =>
                    void run("google", () => signIn.signInWithGoogle())
                  }
                >
                  {pending === "google" && spinner}
                  {t("signIn.google")}
                </Button>
                <p className="text-center text-sm text-muted-foreground">
                  {t("signIn.or")}
                </p>
              </>
            )}
            <form
              onSubmit={(event) => {
                event.preventDefault()
                submitEmail()
              }}
              className="flex flex-col gap-4"
            >
              <div className="flex flex-col gap-2">
                <Label htmlFor={emailId}>{t("signIn.email")}</Label>
                <Input
                  id={emailId}
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(event) => {
                    setEmail(event.target.value)
                  }}
                />
              </div>
              {mode !== "reset-password" && (
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor={passwordId}>{t("signIn.password")}</Label>
                    {mode === "sign-in" && (
                      <Button
                        type="button"
                        variant="link"
                        size="xs"
                        onClick={() => {
                          switchTo("reset-password")
                        }}
                      >
                        {t("signIn.forgotPassword")}
                      </Button>
                    )}
                  </div>
                  <Input
                    id={passwordId}
                    type="password"
                    autoComplete={
                      mode === "sign-in" ? "current-password" : "new-password"
                    }
                    required
                    value={password}
                    onChange={(event) => {
                      setPassword(event.target.value)
                    }}
                  />
                </div>
              )}
              <Button type="submit">
                {pending === "email" && spinner}
                {t(`signIn.submit.${mode}`)}
              </Button>
            </form>
            <Button
              variant="link"
              onClick={() => {
                switchTo(mode === "sign-in" ? "create-account" : "sign-in")
              }}
            >
              {mode === "sign-in"
                ? t("signIn.showCreateAccount")
                : t("signIn.showSignIn")}
            </Button>
          </fieldset>
        </CardContent>
      </Card>
    </main>
  )
}
