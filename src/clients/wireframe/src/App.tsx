import { useTranslation } from "react-i18next"

import { ThemeToggle } from "@/components/theme-toggle"
import { TooltipProvider } from "@/components/ui/tooltip"

export function App() {
  const { t } = useTranslation()
  return (
    <TooltipProvider>
      <div className="flex min-h-svh flex-col">
        <header className="flex items-center gap-2 border-b px-4 py-2">
          <span className="font-medium">{t("app.name")}</span>
          <div className="ms-auto flex items-center gap-2">
            <ThemeToggle />
          </div>
        </header>
        <main className="flex-1 p-4" />
      </div>
    </TooltipProvider>
  )
}
