/**
 * Prompt Template Engine - TypeScript Implementation
 *
 * Expands template variables with type-safe handlers.
 */

import { FragmentKind, FragmentStore } from "./fragments";

type VariableHandler = (param: string | undefined) => string;

export interface TemplateContext {
  user_input?: string;
  [key: string]: unknown;
}

const FRAGMENT_KINDS: FragmentKind[] = [
  "capability",
  "context",
  "parameters",
  "safety",
  "example",
];

function isFragmentKind(value: string): value is FragmentKind {
  return FRAGMENT_KINDS.includes(value as FragmentKind);
}

/**
 * Expands template variables in prompt strings.
 *
 * Supported syntax:
 * - {fragment:id} - Insert fragment content by ID
 * - {kind:type} - Insert all fragments of a kind
 * - {user_input} - Insert user's message
 * - {date} - Insert current date
 * - {var_name} - Insert from context dict
 */
export class TemplateEngine {
  private customHandlers = new Map<string, VariableHandler>();

  // Pattern matches {name} or {name:value}
  private static PATTERN = /\{(\w+)(?::(\w+))?\}/g;

  constructor(private store: FragmentStore) {}

  registerHandler(name: string, handler: VariableHandler): void {
    this.customHandlers.set(name, handler);
  }

  expand(template: string, context: TemplateContext = {}): string {
    return template.replace(
      TemplateEngine.PATTERN,
      (match, name: string, param: string | undefined) => {
        // Handle built-in variables
        if (name === "fragment" && param) {
          const fragment = this.store.get(param);
          return fragment?.content ?? `[missing:${param}]`;
        }

        if (name === "kind" && param) {
          if (isFragmentKind(param)) {
            const fragments = this.store.getByKind(param);
            return fragments.map((f) => f.content).join("\n\n");
          }
          return `[unknown kind:${param}]`;
        }

        if (name === "date") {
          return new Date().toISOString().split("T")[0];
        }

        if (name === "user_input") {
          return context.user_input ?? "";
        }

        // Check custom handlers
        const handler = this.customHandlers.get(name);
        if (handler) {
          return handler(param);
        }

        // Fall back to context
        if (name in context) {
          return String(context[name]);
        }

        // Return original if no match
        return match;
      }
    );
  }
}

/**
 * Convenience function for simple template expansion.
 */
export function expandTemplate(
  template: string,
  store: FragmentStore,
  context: TemplateContext = {}
): string {
  const engine = new TemplateEngine(store);
  return engine.expand(template, context);
}
