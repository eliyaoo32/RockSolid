import { useTranslation } from "react-i18next"

import { Skeleton } from "@/components/ui/skeleton"

/** Shaped like the app with its header, shown until it is known whether someone is signed in. */
export function PageSkeleton() {
  const { t } = useTranslation()
  return (
    <div
      role="status"
      aria-label={t("loading")}
      className="flex min-h-svh flex-col"
    >
      <div className="flex items-center gap-2 border-b px-4 py-2">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="ms-auto size-8" />
      </div>
      <div className="flex-1 p-4">
        <Skeleton className="h-32 w-full" />
      </div>
    </div>
  )
}
