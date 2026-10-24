import { useTranslation } from "react-i18next"

import { useCurrentUser } from "@/api/current-user"
import { useAuth } from "@/auth/auth-context"
import { ThemeToggle } from "@/components/theme-toggle"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"

export function AppHeader() {
  const { t } = useTranslation()
  const { signIn } = useAuth()
  const user = useCurrentUser()
  return (
    <header className="flex items-center gap-2 border-b px-4 py-2">
      <span className="font-medium">{t("app.name")}</span>
      <div className="ms-auto flex items-center gap-2">
        {user.isPending ? (
          <Skeleton
            role="status"
            aria-label={t("loading")}
            className="h-4 w-24"
          />
        ) : (
          <span data-testid="account" className="text-sm text-muted-foreground">
            {user.data?.displayName}
          </span>
        )}
        <ThemeToggle />
        <Button
          variant="outline"
          size="sm"
          data-testid="sign-out"
          onClick={() => void signIn.signOut()}
        >
          {t("signIn.signOut")}
        </Button>
      </div>
    </header>
  )
}
