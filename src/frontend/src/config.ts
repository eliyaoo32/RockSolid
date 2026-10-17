import type { FirebaseOptions } from "firebase/app"

/** The only place the frontend reads its environment: the root `.env`, through Vite. */
export function readFirebaseOptions(env: ImportMetaEnv): FirebaseOptions {
  const missing = (
    [
      "FIREBASE_API_KEY",
      "FIREBASE_AUTH_DOMAIN",
      "FIREBASE_PROJECT_ID",
      "FIREBASE_APP_ID",
    ] as const
  ).filter((name) => !env[name])
  if (missing.length > 0) {
    throw new Error(`The root .env is missing ${missing.join(", ")}`)
  }
  return {
    apiKey: env.FIREBASE_API_KEY,
    authDomain: env.FIREBASE_AUTH_DOMAIN,
    projectId: env.FIREBASE_PROJECT_ID,
    appId: env.FIREBASE_APP_ID,
  }
}
