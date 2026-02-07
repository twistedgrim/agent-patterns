/**
 * Agent Orchestrator Pattern - TypeScript Implementation
 *
 * Mode-based routing using discriminated unions for type safety.
 * Selects appropriate persona and constraints based on agent mode.
 */

import { AgentPersona, PersonaRegistry, withToolLimit } from "./personas";

export type AgentMode = "conversation" | "investigation" | "autonomous";

interface ModeConfig {
  personaName: string;
  maxToolCalls: number;
  autoInvestigate: boolean;
  requireConfirmation: boolean;
}

const MODE_CONFIGS: Record<AgentMode, ModeConfig> = {
  conversation: {
    personaName: "default",
    maxToolCalls: 3,
    autoInvestigate: false,
    requireConfirmation: true,
  },
  investigation: {
    personaName: "investigator",
    maxToolCalls: 15,
    autoInvestigate: true,
    requireConfirmation: true,
  },
  autonomous: {
    personaName: "coder",
    maxToolCalls: 50,
    autoInvestigate: true,
    requireConfirmation: false,
  },
};

type ModeChangeCallback = (mode: AgentMode) => void;

/**
 * Routes requests to appropriate persona based on mode.
 *
 * The orchestrator acts as the control plane, determining which
 * persona handles a request and with what constraints.
 */
export class Orchestrator {
  private currentMode: AgentMode;
  private modeChangeHooks: ModeChangeCallback[] = [];

  constructor(defaultMode: AgentMode = "conversation") {
    this.currentMode = defaultMode;
  }

  setMode(mode: AgentMode): void {
    this.currentMode = mode;
    for (const hook of this.modeChangeHooks) {
      hook(mode);
    }
  }

  getMode(): AgentMode {
    return this.currentMode;
  }

  onModeChange(callback: ModeChangeCallback): void {
    this.modeChangeHooks.push(callback);
  }

  getActivePersona(): AgentPersona {
    const config = MODE_CONFIGS[this.currentMode];
    let persona = PersonaRegistry.get(config.personaName);

    if (!persona) {
      persona = PersonaRegistry.get("default");
    }

    if (!persona) {
      throw new Error("No default persona registered");
    }

    // Apply mode-specific tool limit
    return withToolLimit(persona, config.maxToolCalls);
  }

  shouldAutoInvestigate(): boolean {
    return MODE_CONFIGS[this.currentMode].autoInvestigate;
  }

  requiresConfirmation(): boolean {
    return MODE_CONFIGS[this.currentMode].requireConfirmation;
  }
}

// Usage example
if (import.meta.url === `file://${process.argv[1]}`) {
  const orchestrator = new Orchestrator();

  // Get persona for default mode
  let persona = orchestrator.getActivePersona();
  console.log(`Mode: ${orchestrator.getMode()}`);
  console.log(`Persona: ${persona.name}, Tools: ${persona.maxToolCalls}`);

  // Switch to autonomous mode
  orchestrator.setMode("autonomous");
  persona = orchestrator.getActivePersona();
  console.log(`Mode: ${orchestrator.getMode()}`);
  console.log(`Persona: ${persona.name}, Tools: ${persona.maxToolCalls}`);
}
