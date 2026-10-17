---
name: api-design
description: How to design and review ConnectRPC APIs in this project. Use when writing or changing a .proto file, adding an RPC service, method, or message, or reviewing an API in a blueprint.
---

# API Design

Google AIPs decide what the API means. The Buf style guide decides how the protos look. Where they disagree, Buf wins, because the verification command enforces it.

## Resources

- **Resource-oriented design ([AIP-121](https://google.aip.dev/121)):** model the API as resources (nouns) with standard methods. Prefer a standard method over a custom one.
- **Resource names ([AIP-122](https://google.aip.dev/122)):** every resource has a `name` field, such as `contacts/{contact}`. A child resource lives under its parent: `contacts/{contact}/notes/{note}`. Collection names are plural.
- **References ([AIP-124](https://google.aip.dev/124)):** a field that points to another resource holds that resource's `name`, and is named after the resource type (`company`, not `company_id`).
- **Enums ([AIP-126](https://google.aip.dev/126)):** the zero value is `<ENUM_NAME>_UNSPECIFIED` and is never a valid choice.
- **Server-set values ([AIP-129](https://google.aip.dev/129)):** fields the server sets, such as `create_time`, are output-only. The server ignores them on input.
- **Singletons ([AIP-156](https://google.aip.dev/156)):** a resource that exists once per parent, such as `users/{user}/settings`, has only Get and Update.
- **Value objects are their own messages:** a value object such as `Address` is one nested message, defined once in a shared proto package. It is never flattened into the resource.

## Methods

Every request and response is its own message named after its method (`GetContactRequest`, `GetContactResponse`), even where an AIP returns the resource directly. This is Buf's rule, and it lets a response grow without breaking clients.

- **Get ([AIP-131](https://google.aip.dev/131)):** takes `name`. The response holds the resource.
- **List ([AIP-132](https://google.aip.dev/132), [AIP-158](https://google.aip.dev/158)):** takes `parent`, `page_size`, `page_token`, `filter`, and `order_by`. The response holds the resources and `next_page_token`. Page tokens are opaque.
- **Create ([AIP-133](https://google.aip.dev/133)):** takes `parent` and the resource.
- **Update ([AIP-134](https://google.aip.dev/134), [AIP-161](https://google.aip.dev/161)):** takes the resource and an `update_mask` (`google.protobuf.FieldMask`). Only the fields in the mask change.
- **Delete ([AIP-135](https://google.aip.dev/135)):** takes `name`.
- **Custom methods ([AIP-136](https://google.aip.dev/136)):** used only when no standard method fits. Named verb + noun, such as `ArchiveContact`.
- **Read-only methods** set `option idempotency_level = NO_SIDE_EFFECTS;`, so Connect serves them over HTTP GET and they can be cached.

## Fields

- **Names ([AIP-140](https://google.aip.dev/140)):** `lower_snake_case`, and plain words that say what the field holds.
- **Time ([AIP-142](https://google.aip.dev/142)):** timestamps are `google.protobuf.Timestamp` with a `_time` suffix (`create_time`). Durations are `google.protobuf.Duration`.
- **Standard codes ([AIP-143](https://google.aip.dev/143)):** `language_code` (BCP-47), `region_code` (CLDR), `currency_code` (ISO 4217), `time_zone` (IANA).
- **Repeated fields ([AIP-144](https://google.aip.dev/144)):** plural names.
- **Ranges ([AIP-145](https://google.aip.dev/145)):** `start_<x>` and `end_<x>`, with the start included and the end excluded.
- **Sensitive fields ([AIP-147](https://google.aip.dev/147)):** secrets are input-only and never returned.
- **Standard fields ([AIP-148](https://google.aip.dev/148)):** use the standard name when one exists: `name`, `display_name`, `create_time`, `update_time`, `delete_time`, `etag`.
- **Unset values ([AIP-149](https://google.aip.dev/149)):** mark a field `optional` when "not set" and "zero" mean different things.
- **States ([AIP-216](https://google.aip.dev/216)):** a resource with a lifecycle has an output-only `state` enum. Only methods change it, never Update. The states match the blueprint's state diagram.
- **Validation:** field constraints are `buf.validate` annotations, such as required fields, lengths, and formats.

## Patterns

- **Optimistic concurrency ([AIP-154](https://google.aip.dev/154)):** a resource that two callers may change at once has an `etag`. Update and Delete send it back, and a stale `etag` fails with `ABORTED`.
- **Idempotent requests ([AIP-155](https://google.aip.dev/155)):** a create or custom method that must not run twice takes an optional `request_id` (a UUID). A repeated `request_id` returns the first result.
- **Soft delete ([AIP-164](https://google.aip.dev/164)):** Delete sets `delete_time` and keeps the resource. List hides deleted resources unless `show_deleted` is true, and Get still returns them. `Undelete` restores a resource, and fails with `ALREADY_EXISTS` when it is not deleted.
- **Authorization before existence ([AIP-211](https://google.aip.dev/211)):** check permission first. A caller without permission gets `PERMISSION_DENIED` whether or not the resource exists, so the error never reveals it.
- **Errors ([AIP-193](https://google.aip.dev/193)):** use the Connect error code that matches the failure, with a message a developer can act on and error details where a client needs to react.
- **Compatibility ([AIP-180](https://google.aip.dev/180)):** never remove or renumber a field, and never change its type or meaning. Add new fields and methods instead.

## Not Used

- Long-running operations ([AIP-151](https://google.aip.dev/151)) and jobs ([AIP-152](https://google.aip.dev/152)). Background work runs as a task in the tasks queue.
- Batch methods (AIP-231 to AIP-235).
- AIP-160 filtering. List filters use OData `$filter` syntax instead.
- Versioning AIPs (181 to 185). Buf's rule that every package ends in a version, such as `contacts.v1`, covers it.
- HTTP transcoding ([AIP-127](https://google.aip.dev/127)). Connect has its own HTTP mapping.

## Form

- **Buf style guide:** follow the [Buf style guide](https://buf.build/docs/best-practices/style-guide). `buf lint` (the `STANDARD` rules), `buf format`, and `buf breaking` run in the verification command.
- **Packages:** one package per module and version, such as `contacts.v1`, in a folder that matches it: `protos/contacts/v1/`.
- **Comments:** every service, method, message, and field has a comment that says what it is for.
