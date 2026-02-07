/**
 * Agent Personas Pattern - TypeScript Implementation
 *
 * Interface-based persona definitions with registry for lookup/registration.
 * Uses discriminated unions for type-safe persona handling.
 */

export type PersonaType = "assistant" | "investigator" | "coder" | "analyst";

export interface AgentPersona {
  readonly name: string;
  readonly personaType: PersonaType;
  readonly systemPrompt: string;
  readonly maxToolCalls: number;
  readonly responseStyle: "concise" | "thorough" | "technical";
  readonly temperature: number;
  readonly allowedTools: readonly string[];
}

/**
 * Creates a new persona with adjusted tool limit.
 * Immutable pattern - returns new object instead of mutating.
 */
export function withToolLimit(
  persona: AgentPersona,
  limit: number
): AgentPersona {
  return { ...persona, maxToolCalls: limit };
}

/**
 * Registry pattern for persona management.
 * Centralizes persona definitions and enables runtime lookup.
 */
class PersonaRegistryImpl {
  private personas = new Map<string, AgentPersona>();

  register(persona: AgentPersona): void {
    this.personas.set(persona.name, persona);
  }

  get(name: string): AgentPersona | undefined {
    return this.personas.get(name);
  }

  listAll(): string[] {
    return Array.from(this.personas.keys());
  }

  has(name: string): boolean {
    return this.personas.has(name);
  }
}

export const PersonaRegistry = new PersonaRegistryImpl();

// Default persona definitions
const DEFAULT_PERSONAS: AgentPersona[] = [
  {
    name: "default",
    personaType: "assistant",
    systemPrompt: "You are a helpful assistant.",
    maxToolCalls: 5,
    responseStyle: "concise",
    temperature: 0.7,
    allowedTools: [],
  },
  {
    name: "investigator",
    personaType: "investigator",
    systemPrompt:
      "You investigate problems deeply. Ask clarifying questions.",
    maxToolCalls: 15,
    responseStyle: "thorough",
    temperature: 0.7,
    allowedTools: ["search", "read_file", "web_fetch"],
  },
  {
    name: "coder",
    personaType: "coder",
    systemPrompt: "You write clean, tested code. Explain your changes.",
    maxToolCalls: 20,
    responseStyle: "technical",
    temperature: 0.3,
    allowedTools: ["read_file", "write_file", "run_tests", "search"],
  },
];

// Register defaults on module load
for (const persona of DEFAULT_PERSONAS) {
  PersonaRegistry.register(persona);
}
