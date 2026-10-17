import i18n from "i18next"
import { initReactI18next } from "react-i18next"

import { resources } from "./resources"

void i18n.use(initReactI18next).init({
  resources,
  lng: "en",
  // React already escapes rendered text.
  interpolation: { escapeValue: false },
})

export default i18n
