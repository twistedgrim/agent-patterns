/**
 * Provider Abstraction Pattern - TypeScript Implementation
 *
 * Type-safe model registry with YAML config and cost tracking.
 */

import { readFileSync } from "fs";
import { parse } from "yaml";

export interface ModelConfig {
  readonly provider: string;
  readonly modelId: string;
  readonly displayName: string;
  readonly contextWindow: number;
  readonly costPer1kInput: number;
  readonly costPer1kOutput: number;
  readonly supportsTools: boolean;
  readonly supportsVision: boolean;
}

export interface ProviderConfig {
  readonly name: string;
  readonly apiBase?: string;
  readonly envVar?: string;
}

interface YamlConfig {
  providers: Record<
    string,
    { api_base?: string; env_var?: string }
  >;
  models: Record<
    string,
    {
      provider: string;
      model_id: string;
      display_name?: string;
      context_window?: number;
      cost_per_1k_input?: number;
      cost_per_1k_output?: number;
      supports_tools?: boolean;
      supports_vision?: boolean;
    }
  >;
  aliases: Record<string, string>;
}

/**
 * Registry for model configurations with alias support.
 */
export class ModelRegistry {
  private models = new Map<string, ModelConfig>();
  private aliases = new Map<string, string>();
  private providers = new Map<string, ProviderConfig>();

  loadFromYaml(path: string): void {
    const content = readFileSync(path, "utf-8");
    const data = parse(content) as YamlConfig;

    // Load providers
    for (const [name, config] of Object.entries(data.providers ?? {})) {
      this.providers.set(name, {
        name,
        apiBase: config.api_base,
        envVar: config.env_var,
      });
    }

    // Load models
    for (const [key, config] of Object.entries(data.models ?? {})) {
      this.models.set(key, {
        provider: config.provider,
        modelId: config.model_id,
        displayName: config.display_name ?? key,
        contextWindow: config.context_window ?? 8192,
        costPer1kInput: config.cost_per_1k_input ?? 0,
        costPer1kOutput: config.cost_per_1k_output ?? 0,
        supportsTools: config.supports_tools ?? true,
        supportsVision: config.supports_vision ?? false,
      });
    }

    // Load aliases
    for (const [alias, model] of Object.entries(data.aliases ?? {})) {
      this.aliases.set(alias, model);
    }
  }

  resolve(nameOrAlias: string): ModelConfig {
    const modelKey = this.aliases.get(nameOrAlias) ?? nameOrAlias;
    const config = this.models.get(modelKey);

    if (!config) {
      throw new Error(`Unknown model: ${nameOrAlias}`);
    }

    return config;
  }

  getProvider(name: string): ProviderConfig {
    const config = this.providers.get(name);
    if (!config) {
      throw new Error(`Unknown provider: ${name}`);
    }
    return config;
  }

  listModels(): string[] {
    return Array.from(this.models.keys());
  }

  listAliases(): Map<string, string> {
    return new Map(this.aliases);
  }
}

interface UsageRecord {
  inputTokens: number;
  outputTokens: number;
}

/**
 * Tracks API costs per model.
 */
export class CostTracker {
  private usage = new Map<string, UsageRecord>();

  constructor(private registry: ModelRegistry) {}

  recordUsage(
    modelName: string,
    inputTokens: number,
    outputTokens: number
  ): number {
    const config = this.registry.resolve(modelName);

    const existing = this.usage.get(modelName) ?? {
      inputTokens: 0,
      outputTokens: 0,
    };

    this.usage.set(modelName, {
      inputTokens: existing.inputTokens + inputTokens,
      outputTokens: existing.outputTokens + outputTokens,
    });

    return (
      (inputTokens / 1000) * config.costPer1kInput +
      (outputTokens / 1000) * config.costPer1kOutput
    );
  }

  getTotalCost(): number {
    let total = 0;
    for (const [modelName, tokens] of this.usage) {
      const config = this.registry.resolve(modelName);
      total +=
        (tokens.inputTokens / 1000) * config.costPer1kInput +
        (tokens.outputTokens / 1000) * config.costPer1kOutput;
    }
    return total;
  }

  getSummary(): Record<
    string,
    { inputTokens: number; outputTokens: number; cost: number }
  > {
    const summary: Record<
      string,
      { inputTokens: number; outputTokens: number; cost: number }
    > = {};

    for (const [modelName, tokens] of this.usage) {
      const config = this.registry.resolve(modelName);
      const cost =
        (tokens.inputTokens / 1000) * config.costPer1kInput +
        (tokens.outputTokens / 1000) * config.costPer1kOutput;

      summary[modelName] = {
        inputTokens: tokens.inputTokens,
        outputTokens: tokens.outputTokens,
        cost,
      };
    }

    return summary;
  }
}
