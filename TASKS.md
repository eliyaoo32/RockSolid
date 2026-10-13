# Tasks

- [ ] Add a docs checker, ported from EasyTivuch's `scripts/check-docs.mjs`, to the single verification command. It checks that every file in `docs/` is named `<NNN>_FEATURES_<FEATURE_NAME_UPPER_CASE>.md`, that no two blueprints share a number, that each blueprint has exactly the `##` sections of `docs/FEATURE_TEMPLATE.md` in order, that it has a `**Submitted:** YYYY-MM-DD` date, and that it stays under 1,500 lines.
