"""
Memory Integration Pattern - Python Implementation

Integrates vector memory (semantic search) into context building.
Uses pgvector-style interface for similarity search.
"""

from dataclasses import dataclass
from typing import Protocol

from context_builder import ContextBuilder, ContextPriority


@dataclass
class MemoryEntry:
    """A stored memory with embedding metadata."""
    id: str
    content: str
    metadata: dict
    similarity: float = 0.0


class VectorStore(Protocol):
    """Protocol for vector store implementations."""

    def search(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Search for similar memories."""
        ...

    def add(self, content: str, metadata: dict | None = None) -> str:
        """Add a memory, returns ID."""
        ...


class MockVectorStore:
    """
    Mock vector store for demonstration.
    Replace with pgvector, Pinecone, Chroma, etc. in production.
    """

    def __init__(self):
        self._memories: list[MemoryEntry] = []
        self._counter = 0

    def add(self, content: str, metadata: dict | None = None) -> str:
        self._counter += 1
        entry = MemoryEntry(
            id=f"mem_{self._counter}",
            content=content,
            metadata=metadata or {},
        )
        self._memories.append(entry)
        return entry.id

    def search(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Mock search: returns memories containing query words."""
        query_words = set(query.lower().split())
        results = []

        for mem in self._memories:
            content_words = set(mem.content.lower().split())
            overlap = len(query_words & content_words)
            if overlap > 0:
                mem.similarity = overlap / len(query_words)
                results.append(mem)

        results.sort(key=lambda m: m.similarity, reverse=True)
        return results[:limit]


class MemoryAugmentedContext:
    """
    Augments context building with semantic memory retrieval.

    Retrieves relevant memories based on the user query and injects
    them into the context as a dedicated layer.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        max_memories: int = 3,
        similarity_threshold: float = 0.1,
    ):
        self.store = vector_store
        self.max_memories = max_memories
        self.similarity_threshold = similarity_threshold

    def augment_context(
        self,
        builder: ContextBuilder,
        query: str,
    ) -> ContextBuilder:
        """
        Add relevant memories to context based on query.

        Memories are added as system messages in a 'memory' layer
        so the LLM can use them as context.
        """
        memories = self.store.search(query, limit=self.max_memories)

        # Filter by similarity threshold
        relevant = [m for m in memories if m.similarity >= self.similarity_threshold]

        if not relevant:
            return builder

        # Add memory layer if not exists
        if "memory" not in builder.layers:
            builder.add_layer("memory", ContextPriority.MEMORY)

        # Format memories as context
        memory_text = "Relevant context from memory:\n"
        for mem in relevant:
            memory_text += f"- {mem.content}\n"

        builder.add_message("memory", "system", memory_text)
        return builder

    def store_interaction(
        self,
        user_query: str,
        assistant_response: str,
        metadata: dict | None = None,
    ) -> None:
        """Store an interaction for future retrieval."""
        content = f"Q: {user_query}\nA: {assistant_response}"
        self.store.add(content, metadata)


# Example usage
if __name__ == "__main__":
    # Set up vector store with some memories
    vector_store = MockVectorStore()
    vector_store.add("User prefers Python over JavaScript.")
    vector_store.add("User is working on a Discord bot project.")
    vector_store.add("User likes detailed code explanations.")

    # Create memory-augmented context
    memory = MemoryAugmentedContext(vector_store)
    builder = ContextBuilder(max_tokens=4000)

    builder.add_system("You are a coding assistant.")

    # Augment with relevant memories
    query = "Help me write a Python function"
    memory.augment_context(builder, query)

    builder.add_history("user", query)

    # Build final context
    messages = builder.to_api_format()
    for msg in messages:
        print(f"[{msg['role']}] {msg['content'][:80]}...")
