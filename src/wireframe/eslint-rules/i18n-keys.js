// Fails a t("key") call whose key is missing from any language in src/i18n/resources.ts.
import { resources } from "../src/i18n/resources.ts"

function collect(tree, prefix, leaves, groups) {
  for (const [name, value] of Object.entries(tree)) {
    const key = prefix + name
    if (typeof value === "string") {
      leaves.add(key)
    } else {
      groups.add(key)
      collect(value, `${key}.`, leaves, groups)
    }
  }
}

const languages = Object.entries(resources).map(
  ([language, { translation }]) => {
    const keys = { language, leaves: new Set(), groups: new Set() }
    collect(translation, "", keys.leaves, keys.groups)
    return keys
  }
)

const noMissingKeys = {
  meta: {
    type: "problem",
    schema: [],
    messages: {
      missing:
        'Translation key "{{key}}" is missing in "{{language}}" (src/i18n/resources.ts).',
    },
  },
  create(context) {
    function report(node, key, kind) {
      for (const keys of languages) {
        if (!keys[kind].has(key)) {
          context.report({
            node,
            messageId: "missing",
            data: { key, language: keys.language },
          })
        }
      }
    }

    function check(node) {
      if (node.type === "Literal" && typeof node.value === "string") {
        report(node, node.value, "leaves")
      } else if (node.type === "TemplateLiteral") {
        const start = node.quasis[0].value.cooked
        if (node.expressions.length === 0) {
          report(node, start, "leaves")
        } else {
          // A key built at runtime must start with a group that exists, such as `status.${value}`.
          report(node, start.replace(/\.$/, ""), "groups")
        }
      } else if (node.type === "ConditionalExpression") {
        check(node.consequent)
        check(node.alternate)
      }
    }

    return {
      CallExpression(node) {
        const { callee } = node
        const name =
          callee.type === "Identifier"
            ? callee.name
            : callee.type === "MemberExpression" &&
                callee.property.type === "Identifier"
              ? callee.property.name
              : undefined
        if (name === "t" && node.arguments.length > 0) {
          check(node.arguments[0])
        }
      },
    }
  },
}

export default {
  meta: { name: "i18n-keys" },
  rules: { "no-missing-keys": noMissingKeys },
}
