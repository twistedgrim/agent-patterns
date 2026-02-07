/**
 * Context Layering Pattern - TypeScript Implementation
 *
 * Builds layered context with token budget management.
 */

export type MessageRole = "system" | "user" | "assistant";

export enum ContextPriority {
  SYSTEM = 100,
  MEMORY = 80,
  HISTORY = 60,
  SUPPLEMENTAL = 40,
}

export interface Message {
  role: MessageRole;
  content: string;
  priority: ContextPriority;
  tokenCount: number;
}

interface ContextLayer {
  name: string;
  messages: Message[];
  priority: ContextPriority;
}

function estimateTokens(content: string): number {
  // Rough estimate: 4 chars per token
  return Math.ceil(content.length / 4);
}

function createMessage(
  role: MessageRole,
  content: string,
  priority: ContextPriority
): Message {
  return {
    role,
    content,
    priority,
    tokenCount: estimateTokens(content),
  };
}

/**
 * Builds context by assembling layers within token budget.
 */
export class ContextBuilder {
  private layers = new Map<string, ContextLayer>();

  constructor(private maxTokens: number = 8000) {}

  addLayer(name: string, priority: ContextPriority): this {
    this.layers.set(name, { name, messages: [], priority });
    return this;
  }

  addMessage(layer: string, role: MessageRole, content: string): this {
    const contextLayer = this.layers.get(layer);
    if (!contextLayer) {
      throw new Error(`Unknown layer: ${layer}`);
    }

    const msg = createMessage(role, content, contextLayer.priority);
    contextLayer.messages.push(msg);
    return this;
  }

  addSystem(content: string): this {
    if (!this.layers.has("system")) {
      this.addLayer("system", ContextPriority.SYSTEM);
    }
    return this.addMessage("system", "system", content);
  }

  addHistory(role: MessageRole, content: string): this {
    if (!this.layers.has("history")) {
      this.addLayer("history", ContextPriority.HISTORY);
    }
    return this.addMessage("history", role, content);
  }

  build(): Message[] {
    // Sort layers by priority (highest first)
    const sortedLayers = Array.from(this.layers.values()).sort(
      (a, b) => b.priority - a.priority
    );

    const result: Message[] = [];
    let remainingTokens = this.maxTokens;

    for (const layer of sortedLayers) {
      for (const msg of layer.messages) {
        if (msg.tokenCount <= remainingTokens) {
          result.push(msg);
          remainingTokens -= msg.tokenCount;
        } else {
          break;
        }
      }
    }

    // Sort: system first, then preserve order
    const systemMsgs = result.filter((m) => m.role === "system");
    const otherMsgs = result.filter((m) => m.role !== "system");
    return [...systemMsgs, ...otherMsgs];
  }

  toApiFormat(): Array<{ role: MessageRole; content: string }> {
    return this.build().map((m) => ({ role: m.role, content: m.content }));
  }

  getTotalTokens(): number {
    return Array.from(this.layers.values())
      .flatMap((l) => l.messages)
      .reduce((sum, m) => sum + m.tokenCount, 0);
  }

  hasLayer(name: string): boolean {
    return this.layers.has(name);
  }
}
