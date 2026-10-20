import { describe, expect, it } from "vitest"

import { readFirebaseOptions } from "@/config"

describe("configuration", () => {
  it("reads the Firebase web settings from the root .env", () => {
    const options = readFirebaseOptions({
      FIREBASE_API_KEY: "key",
      FIREBASE_AUTH_DOMAIN: "project.firebaseapp.com",
      FIREBASE_PROJECT_ID: "project",
      FIREBASE_APP_ID: "app",
    } as ImportMetaEnv)

    expect(options).toEqual({
      apiKey: "key",
      authDomain: "project.firebaseapp.com",
      projectId: "project",
      appId: "app",
    })
  })

  it("names every missing setting", () => {
    expect(() =>
      readFirebaseOptions({
        FIREBASE_API_KEY: "key",
        FIREBASE_APP_ID: "",
      } as ImportMetaEnv)
    ).toThrow(
      "The root .env is missing FIREBASE_AUTH_DOMAIN, FIREBASE_PROJECT_ID, FIREBASE_APP_ID"
    )
  })
})
