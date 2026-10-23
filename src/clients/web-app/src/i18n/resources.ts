// Every language holds the same keys; the i18n-keys lint rule checks each key in each language.
export const resources = {
  en: {
    translation: {
      app: {
        name: "RockSolid",
      },
      theme: {
        toggle: "Toggle dark mode",
      },
      signIn: {
        title: {
          "sign-in": "Sign in",
          "create-account": "Create an account",
          "reset-password": "Reset your password",
        },
        description: {
          "sign-in": "Use your Google account or your email to continue.",
          "create-account":
            "Use your Google account, or choose an email and password.",
          "reset-password":
            "We will email you a link to choose a new password.",
        },
        submit: {
          "sign-in": "Sign in",
          "create-account": "Create account",
          "reset-password": "Send reset email",
        },
        google: "Sign in with Google",
        or: "or",
        email: "Email",
        password: "Password",
        forgotPassword: "Forgot password?",
        showCreateAccount: "Create an account",
        showSignIn: "Back to sign in",
        resetEmailSent: "We sent a link to choose a new password to {{email}}.",
        failure: {
          "wrong-email-or-password": "The email or password is incorrect.",
          "email-in-use":
            "An account with this email already exists. Sign in instead.",
          "weak-password": "This password is too weak. Choose a longer one.",
          "too-many-attempts":
            "Too many attempts. Wait a few minutes and try again.",
          other: "Sign-in failed. Try again.",
        },
        signOut: "Sign out",
      },
      loading: "Loading",
    },
  },
}
