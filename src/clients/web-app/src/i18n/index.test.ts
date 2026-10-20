import { describe, expect, it } from "vitest"

import i18n from "@/i18n"
import { resources } from "@/i18n/resources"

describe("i18n", () => {
  it("renders every text from the resources of the app's language", () => {
    expect(i18n.language).toBe("en")
    expect(i18n.t("signIn.google")).toBe(resources.en.translation.signIn.google)
  })
})
