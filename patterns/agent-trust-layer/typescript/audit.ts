/**
 * Append-only audit log for agent actions.
 *
 * Records all agent actions with cryptographic attribution
 * for forensics and compliance.
 */

import { createHash } from "crypto";

export type ActionType =
  | "file:read"
  | "file:write"
  | "file:delete"
  | "shell:execute"
  | "api:call"
  | "grant:issued"
  | "grant:revoked"
  | "identity:created"
  | "identity:revoked";

export type AuditLevel = "minimal" | "normal" | "verbose";
export type ActionResult = "success" | "denied" | "error";

export interface AuditEntry {
  readonly entryId: string;
  readonly timestamp: Date;
  readonly agentId: string;
  readonly actionType: ActionType;
  readonly resource: string;
  readonly result: ActionResult;
  readonly signature: Buffer;
  readonly previousHash: Buffer;
  readonly grantId?: string;
  readonly context: ReadonlyMap<string, string>;
}

function computeEntryHash(entry: AuditEntry): Buffer {
  const data = [
    entry.entryId,
    entry.timestamp.toISOString(),
    entry.agentId,
    entry.actionType,
    entry.resource,
    entry.result,
    entry.previousHash.toString("hex"),
  ].join(":");

  return createHash("sha256").update(data).digest();
}

export class AuditLog {
  private entries: AuditEntry[] = [];
  private auditLevel: AuditLevel;
  private entryCounter = 0;
  private lastHash: Buffer;

  constructor(auditLevel: AuditLevel = "normal") {
    this.auditLevel = auditLevel;
    this.lastHash = createHash("sha256").update("genesis").digest();
  }

  record(
    agentId: string,
    actionType: ActionType,
    resource: string,
    result: ActionResult,
    signature: Buffer,
    grantId?: string,
    context?: Record<string, string>
  ): AuditEntry {
    this.entryCounter++;

    // Filter context based on audit level
    let filteredContext = new Map<string, string>();
    if (context) {
      if (this.auditLevel === "verbose") {
        filteredContext = new Map(Object.entries(context));
      } else if (this.auditLevel === "normal") {
        const safeKeys = new Set(["user", "session", "request_id"]);
        for (const [k, v] of Object.entries(context)) {
          if (safeKeys.has(k)) {
            filteredContext.set(k, v);
          }
        }
      }
    }

    const entry: AuditEntry = {
      entryId: `audit-${String(this.entryCounter).padStart(8, "0")}`,
      timestamp: new Date(),
      agentId,
      actionType,
      resource,
      result,
      signature,
      previousHash: this.lastHash,
      grantId,
      context: filteredContext,
    };

    this.entries.push(entry);
    this.lastHash = computeEntryHash(entry);

    return entry;
  }

  verifyChain(): { valid: boolean; error?: string } {
    if (this.entries.length === 0) {
      return { valid: true };
    }

    let expectedHash = createHash("sha256").update("genesis").digest();

    for (let i = 0; i < this.entries.length; i++) {
      const entry = this.entries[i];

      if (!entry.previousHash.equals(expectedHash)) {
        return {
          valid: false,
          error: `Chain broken at entry ${i}: ${entry.entryId}`,
        };
      }

      expectedHash = computeEntryHash(entry);
    }

    return { valid: true };
  }

  query(options: {
    agentId?: string;
    actionType?: ActionType;
    resourcePrefix?: string;
    since?: Date;
    until?: Date;
    limit?: number;
  }): AuditEntry[] {
    const { agentId, actionType, resourcePrefix, since, until, limit = 100 } = options;
    const results: AuditEntry[] = [];

    for (let i = this.entries.length - 1; i >= 0 && results.length < limit; i--) {
      const entry = this.entries[i];

      if (agentId && entry.agentId !== agentId) continue;
      if (actionType && entry.actionType !== actionType) continue;
      if (resourcePrefix && !entry.resource.startsWith(resourcePrefix)) continue;
      if (since && entry.timestamp < since) continue;
      if (until && entry.timestamp > until) continue;

      results.push(entry);
    }

    return results.reverse();
  }

  getAgentActivity(agentId: string): Map<string, number> {
    const activity = new Map<string, number>();

    for (const entry of this.entries) {
      if (entry.agentId === agentId) {
        const key = `${entry.actionType}:${entry.result}`;
        activity.set(key, (activity.get(key) ?? 0) + 1);
      }
    }

    return activity;
  }

  exportJson(entries?: AuditEntry[]): string {
    const target = entries ?? this.entries;

    const data = target.map((e) => ({
      entry_id: e.entryId,
      timestamp: e.timestamp.toISOString(),
      agent_id: e.agentId,
      action_type: e.actionType,
      resource: e.resource,
      result: e.result,
      grant_id: e.grantId,
      context: Object.fromEntries(e.context),
    }));

    return JSON.stringify(data, null, 2);
  }

  get length(): number {
    return this.entries.length;
  }

  [Symbol.iterator](): Iterator<AuditEntry> {
    return this.entries[Symbol.iterator]();
  }
}

// Example usage
if (require.main === module) {
  const log = new AuditLog("verbose");

  const dummySignature = Buffer.from("agent-signature-placeholder");

  // Record file read
  log.record(
    "code-assistant-01",
    "file:read",
    "/workspace/main.py",
    "success",
    dummySignature,
    "grant-001",
    { user: "developer", session: "sess-123" }
  );

  // Record file write
  log.record(
    "code-assistant-01",
    "file:write",
    "/workspace/output.txt",
    "success",
    dummySignature,
    "grant-002"
  );

  // Record denied action
  log.record(
    "code-assistant-01",
    "shell:execute",
    "rm -rf /",
    "denied",
    dummySignature,
    undefined,
    { reason: "blocked by policy" }
  );

  // Different agent
  log.record(
    "data-processor-02",
    "api:call",
    "https://api.example.com/data",
    "success",
    dummySignature
  );

  // Verify chain integrity
  const { valid, error } = log.verifyChain();
  console.log(`Chain integrity: ${valid ? "valid" : `INVALID - ${error}`}`);

  // Query by agent
  console.log(`\nTotal entries: ${log.length}`);

  const agentEntries = log.query({ agentId: "code-assistant-01" });
  console.log(`Entries for code-assistant-01: ${agentEntries.length}`);

  // Get activity summary
  const activity = log.getAgentActivity("code-assistant-01");
  console.log(`\nActivity summary:`);
  for (const [action, count] of activity) {
    console.log(`  ${action}: ${count}`);
  }

  // Export for analysis
  console.log(`\nJSON export:`);
  console.log(log.exportJson(agentEntries.slice(0, 2)));
}
