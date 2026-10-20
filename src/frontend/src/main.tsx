import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router"

import "./index.css"
import "@/i18n"
import { App } from "@/App"
import { DEBUG_USER_JWT_KEY, createDebugSignIn } from "@/auth/debug-sign-in"
import { createFirebaseSignIn } from "@/auth/firebase-sign-in"
import { ThemeProvider } from "@/components/theme-provider"
import { readFirebaseOptions } from "@/config"

const root = document.getElementById("root")
if (!root) {
  throw new Error("index.html has no #root element")
}

const debugUserJwt = localStorage.getItem(DEBUG_USER_JWT_KEY)

createRoot(root).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <App
          signIn={
            debugUserJwt
              ? createDebugSignIn(debugUserJwt)
              : createFirebaseSignIn(readFirebaseOptions(import.meta.env))
          }
        />
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>
)
