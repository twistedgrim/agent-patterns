/**
 * Memory Integration Pattern - TypeScript Implementation
 *
 * Integrates vector memory into context building.
 */

import { ContextBuilder, ContextPriority } from "./contextBuilder";

export interface MemoryEntry {
  id: string;
  content: string;
  metadata: Record<string, unknown>;
  similarity: number;
}

export interface VectorStore {
  search(query: string, limit?: number): Promise<MemoryEntry[]>;
  add(content: string, metadata?: Record<string, unknown>): Promise<string>;
}

/**
 * Mock vector store for demonstration.
 */
export class MockVectorStore implements VectorStore {
  private memories: MemoryEntry[] = [];
  private counter = 0;

  async add(
    content: string,
    metadata: Record<string, unknown> = {}
  ): Promise<string> {
    this.counter++;
    const id = `mem_${this.counter}`;
    this.memories.push({ id, content, metadata, similarity: 0 });
    return id;
  }

  async search(query: string, limit = 5): Promise<MemoryEntry[]> {
    const queryWords = new Set(query.toLowerCase().split(/\s+/));

    const results = this.memories
      .map((mem) => {
        const contentWords = new Set(mem.content.toLowerCase().split(/\s+/));
        const overlap = [...queryWords].filter((w) => contentWords.has(w))
          .length;
        return { ...mem, similarity: overlap / queryWords.size };
      })
      .filter((m) => m.similarity > 0)
      .sort((a, b) => b.similarity - a.similarity);

    return results.slice(0, limit);
  }
}

interface MemoryAugmentedContextOptions {
  maxMemories?: number;
  similarityThreshold?: number;
}

/**
 * Augments context building with semantic memory retrieval.
 */
export class MemoryAugmentedContext {
  private maxMemories: number;
  private similarityThreshold: number;

  constructor(
    private store: VectorStore,
    options: MemoryAugmentedContextOptions = {}
  ) {
    this.maxMemories = options.maxMemories ?? 3;
    this.similarityThreshold = options.similarityThreshold ?? 0.1;
  }

  async augmentContext(
    builder: ContextBuilder,
    query: string
  ): Promise<ContextBuilder> {
    const memories = await this.store.search(query, this.maxMemories);

    const relevant = memories.filter(
      (m) => m.similarity >= this.similarityThreshold
    );

    if (relevant.length === 0) {
      return builder;
    }

    if (!builder.hasLayer("memory")) {
      builder.addLayer("memory", ContextPriority.MEMORY);
    }

    const memoryText =
      "Relevant context from memory:\n" +
      relevant.map((m) => `- ${m.content}`).join("\n");

    builder.addMessage("memory", "system", memoryText);
    return builder;
  }

  async storeInteraction(
    userQuery: string,
    assistantResponse: string,
    metadata: Record<string, unknown> = {}
  ): Promise<void> {
    const content = `Q: ${userQuery}\nA: ${assistantResponse}`;
    await this.store.add(content, metadata);
  }
}
