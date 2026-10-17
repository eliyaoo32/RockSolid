# Wireframe

The wireframe shows how the product looks and feels on mobile and desktop, without business logic. The owner approved every view and decision below, and the production frontend in `src/frontend/` builds them exactly.

> **How to fill this document.** Describe each view explicitly enough that a developer can build it without asking: its layout, components, states, colors, text, and the reason for each choice the owner made. Name the shadcn components and variants, and quote the exact text. A wireframe change updates this document in the same change, so it always describes the wireframe as it is today. Delete every line that starts with `>`.

Run it with `pnpm --filter @rocksolid/wireframe dev`.

## Global Decisions

### Layout

- A header runs across the top of every screen: the product name at the start, and the actions at the end. The screen's content fills the space below it.

### Theme

- Light and dark themes follow the operating system until the user picks one with the theme button in the header, or with the `d` key. The choice is kept in the browser.
- Colors come only from the theme's tokens (`bg-background`, `text-muted-foreground`), so both themes work.

### Text

- Every text the user sees comes from `src/i18n/resources.ts`.

## Views

> One `###` section per view, in the order the user meets them. Start each with the user flow: who arrives, from where, what they want done, and where they go next.

### Home

- The screen a signed-in user lands on. It is empty until the product adds its first view.
