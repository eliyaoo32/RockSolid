import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router"

import "./index.css"
import "@/i18n"
import { App } from "@/App"
import { createFirebaseSignIn } from "@/auth/firebase-sign-in"
import { ThemeProvider } from "@/components/theme-provider"
import { readFirebaseOptions } from "@/config"

const root = document.getElementById("root")
if (!root) {
  throw new Error("index.html has no #root element")
}

createRoot(root).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <App
          signIn={createFirebaseSignIn(readFirebaseOptions(import.meta.env))}
        />
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>
)
