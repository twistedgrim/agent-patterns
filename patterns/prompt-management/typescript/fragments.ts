/**
 * Prompt Fragment System - TypeScript Implementation
 *
 * Type-safe prompt fragments with taxonomy and ordered assembly.
 */

export type FragmentKind =
  | "capability"
  | "context"
  | "parameters"
  | "safety"
  | "example";

export interface PromptFragment {
  readonly id: string;
  readonly kind: FragmentKind;
  readonly content: string;
  readonly orderIndex: number;
  readonly tags: readonly string[];
  readonly version: number;
}

export function isProduction(fragment: PromptFragment): boolean {
  return fragment.tags.includes("prod");
}

/**
 * In-memory fragment store (replace with database in production).
 */
export class FragmentStore {
  private fragments = new Map<string, PromptFragment>();

  add(fragment: PromptFragment): void {
    this.fragments.set(fragment.id, fragment);
  }

  get(id: string): PromptFragment | undefined {
    return this.fragments.get(id);
  }

  getByKind(kind: FragmentKind): PromptFragment[] {
    const matches = Array.from(this.fragments.values()).filter(
      (f) => f.kind === kind
    );
    return matches.sort((a, b) => a.orderIndex - b.orderIndex);
  }

  getProduction(): PromptFragment[] {
    const matches = Array.from(this.fragments.values()).filter(isProduction);
    return matches.sort((a, b) => a.orderIndex - b.orderIndex);
  }

  list(): PromptFragment[] {
    return Array.from(this.fragments.values()).sort(
      (a, b) => a.orderIndex - b.orderIndex
    );
  }
}

/**
 * Assembles fragments into complete prompts.
 */
export class PromptAssembler {
  constructor(private store: FragmentStore) {}

  assemble(fragmentIds: string[]): string {
    const parts: string[] = [];
    for (const id of fragmentIds) {
      const fragment = this.store.get(id);
      if (fragment) {
        parts.push(fragment.content);
      }
    }
    return parts.join("\n\n");
  }

  assembleByKind(kinds: FragmentKind[]): string {
    const parts: string[] = [];
    for (const kind of kinds) {
      for (const fragment of this.store.getByKind(kind)) {
        parts.push(fragment.content);
      }
    }
    return parts.join("\n\n");
  }

  assembleProduction(): string {
    const fragments = this.store.getProduction();
    return fragments.map((f) => f.content).join("\n\n");
  }
}

// Helper to create fragments with defaults
export function createFragment(
  partial: Omit<PromptFragment, "tags" | "version"> & {
    tags?: string[];
    version?: number;
  }
): PromptFragment {
  return {
    ...partial,
    tags: partial.tags ?? [],
    version: partial.version ?? 1,
  };
}
