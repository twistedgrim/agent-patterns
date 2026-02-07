/**
 * Tool Permissions Pattern - TypeScript Implementation
 *
 * Risk-based permission system with glob patterns and hot-reload.
 */

import { readFileSync, statSync } from "fs";
import { parse } from "yaml";

export enum RiskLevel {
  LOW = 1,
  MEDIUM = 2,
  HIGH = 3,
  CRITICAL = 4,
}

interface PermissionRule {
  pattern: string;
  riskLevel: RiskLevel;
  allowed: boolean;
  requiresConfirmation: boolean;
  condition?: string;
}

interface ToolPermissions {
  toolName: string;
  defaultRisk: RiskLevel;
  rules: PermissionRule[];
}

interface YamlConfig {
  tools: Record<
    string,
    {
      default_risk?: string;
      rules?: Array<{
        pattern: string;
        risk?: string;
        allowed?: boolean;
        confirm?: boolean;
        condition?: string;
      }>;
    }
  >;
}

function parseRiskLevel(value: string | undefined): RiskLevel {
  switch (value?.toUpperCase()) {
    case "LOW":
      return RiskLevel.LOW;
    case "MEDIUM":
      return RiskLevel.MEDIUM;
    case "HIGH":
      return RiskLevel.HIGH;
    case "CRITICAL":
      return RiskLevel.CRITICAL;
    default:
      return RiskLevel.MEDIUM;
  }
}

function globMatch(pattern: string, value: string): boolean {
  // Convert glob pattern to regex
  const regexPattern = pattern
    .replace(/\*\*/g, "<<<GLOBSTAR>>>")
    .replace(/\*/g, "[^/]*")
    .replace(/<<<GLOBSTAR>>>/g, ".*")
    .replace(/\?/g, ".");

  const regex = new RegExp(`^${regexPattern}$`);
  return regex.test(value);
}

export interface PermissionResult {
  allowed: boolean;
  riskLevel: RiskLevel;
  requiresConfirmation: boolean;
  reason?: string;
}

/**
 * Evaluates permissions based on risk levels and rules.
 */
export class PermissionEvaluator {
  private tools = new Map<string, ToolPermissions>();
  private configPath?: string;
  private configMtime = 0;

  constructor(private maxAllowedRisk: RiskLevel = RiskLevel.MEDIUM) {}

  loadFromYaml(path: string): void {
    this.configPath = path;
    this.reloadConfig();
  }

  private reloadConfig(): void {
    if (!this.configPath) return;

    try {
      const stat = statSync(this.configPath);
      if (stat.mtimeMs <= this.configMtime) return;

      this.configMtime = stat.mtimeMs;

      const content = readFileSync(this.configPath, "utf-8");
      const data = parse(content) as YamlConfig;

      this.tools.clear();

      for (const [toolName, config] of Object.entries(data.tools ?? {})) {
        const rules: PermissionRule[] = (config.rules ?? []).map((rule) => ({
          pattern: rule.pattern,
          riskLevel: parseRiskLevel(rule.risk),
          allowed: rule.allowed ?? true,
          requiresConfirmation: rule.confirm ?? false,
          condition: rule.condition,
        }));

        this.tools.set(toolName, {
          toolName,
          defaultRisk: parseRiskLevel(config.default_risk),
          rules,
        });
      }
    } catch {
      // Config file doesn't exist or is invalid
    }
  }

  checkHotReload(): void {
    this.reloadConfig();
  }

  evaluate(
    toolName: string,
    argument: string,
    context: Record<string, unknown> = {}
  ): PermissionResult {
    this.checkHotReload();

    const toolConfig = this.tools.get(toolName);
    if (!toolConfig) {
      return {
        allowed: true,
        riskLevel: RiskLevel.MEDIUM,
        requiresConfirmation: false,
      };
    }

    // Find matching rule
    for (const rule of toolConfig.rules) {
      if (globMatch(rule.pattern, argument)) {
        // Check condition if present
        if (rule.condition && !this.evalCondition(rule.condition, context)) {
          continue;
        }

        const allowed = rule.allowed && rule.riskLevel <= this.maxAllowedRisk;
        return {
          allowed,
          riskLevel: rule.riskLevel,
          requiresConfirmation: rule.requiresConfirmation,
          reason: allowed
            ? undefined
            : `Risk level ${RiskLevel[rule.riskLevel]} exceeds maximum`,
        };
      }
    }

    // No matching rule, use default
    const defaultRisk = toolConfig.defaultRisk;
    const allowed = defaultRisk <= this.maxAllowedRisk;
    return {
      allowed,
      riskLevel: defaultRisk,
      requiresConfirmation: defaultRisk >= RiskLevel.HIGH,
      reason: allowed
        ? undefined
        : `Default risk ${RiskLevel[defaultRisk]} exceeds maximum`,
    };
  }

  private evalCondition(
    condition: string,
    context: Record<string, unknown>
  ): boolean {
    // Simple condition evaluation
    try {
      if (condition.includes("==")) {
        const [left, right] = condition.split("==").map((s) => s.trim());
        const rightValue = right.replace(/['"]/g, "");

        const parts = left.split(".");
        let value: unknown = context;
        for (const part of parts) {
          if (part === "context") continue;
          value = (value as Record<string, unknown>)?.[part];
        }

        return String(value) === rightValue;
      }
    } catch {
      // Condition evaluation failed
    }
    return false;
  }
}
