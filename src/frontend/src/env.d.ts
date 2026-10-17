// Vite exposes only the root .env variables whose names start with FIREBASE_ (see `envPrefix`).
interface ImportMetaEnv {
  readonly FIREBASE_API_KEY?: string
  readonly FIREBASE_AUTH_DOMAIN?: string
  readonly FIREBASE_PROJECT_ID?: string
  readonly FIREBASE_APP_ID?: string
}
