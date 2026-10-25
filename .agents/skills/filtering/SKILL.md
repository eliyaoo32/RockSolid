---
name: filtering
description: The filter syntax List methods accept, and how to make a field filterable. Use when writing a `filter` for a List call, when a List call fails with an invalid filter, or when adding a List method or a filterable field.
---

# Filtering

List methods take a `filter` string in OData `$filter` syntax. An empty filter returns everything.

## Syntax

| Kind | Syntax | Example |
|---|---|---|
| Compare | `eq`, `ne`, `gt`, `ge`, `lt`, `le` | `display_name eq 'Avi Cohen'` |
| One of | `in` | `display_name in ('Avi', 'Noa')`; one value takes a trailing comma: `display_name in ('Avi',)` |
| Combine | `and`, `or`, `not`, parentheses | `email ne null and not (display_name eq 'Avi')` |
| Text | `contains`, `startswith`, `endswith` | `startswith(display_name, 'Avi')` |
| Missing value | `null` | `email eq null` |
| Nested field | `/` between names | `company/name eq 'Acme'` |

Values:

- **Text** in single quotes: `'Avi'`. A quote inside text is doubled: `'O''Brien'`.
- **Numbers** as they are: `35`, `2.5`.
- **Date-times** in UTC, without quotes: `2026-01-01T00:00:00Z`.
- **IDs** without quotes: `0f8fad5b-d9cb-469f-a165-70867728950e`.
- **true** and **false** without quotes.

Nothing else is supported: no arithmetic (`age add 1`), no other functions (`tolower`), no `any` or `all`.

## When a filter is rejected

The call fails with `INVALID_ARGUMENT`. The message says what is wrong and lists the filterable fields, for example:

> filter: unknown field 'owner_id'. Filterable fields: create_time, display_name, email, update_time.

Fix the part the message names: the syntax, an unknown field, or a value of the wrong type (a text field compared with a number).

## Making a field filterable

Each List method's filter schema lives in its module's `repositories/`, next to the table model:

```python
CLIENT_FILTERS = FilterSchema(
    {
        "display_name": col(ClientRow.display_name),            # a column
        "family_name": col(ClientRow.last_name),                # a renamed column
        "full_name": func.concat(ClientRow.first, " ", ClientRow.last),  # a computed expression
        "company/name": col(CompanyRow.name),                   # a joined column; the query joins it
    }
)
```

- Parse and translate a filter only through `FilterSchema` from `src/backend/libs/infra/filtering/`, never through the filtering library directly.
- The schema key is the name the API uses. The value is the SQL behind it.
- A value that exists only in Python cannot be filtered.
- Update the `filter` field's comment in the `.proto` file to list the filterable fields.
