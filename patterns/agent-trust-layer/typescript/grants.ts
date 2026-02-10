/**
 * Time-bound grant management for agent permissions.
 *
 * Grants are scoped, time-limited permissions that can be revoked.
 * This implements least-privilege with automatic expiration.
 */

import { randomUUID } from "crypto";

export type GrantStatus = "active" | "expired" | "revoked";

export interface Grant {
  readonly grantId: string;
  readonly agentId: string;
  readonly scope: string; // e.g., "file:read:/workspace/*"
  readonly issuedAt: Date;
  readonly expiresAt: Date;
  readonly issuer: string;
  readonly revoked: boolean;
  readonly metadata: ReadonlyMap<string, string>;
}

export interface GrantPolicy {
  maxTtlSeconds: number;
  requireConfirmation: boolean;
  auditLevel: "MINIMAL" | "NORMAL" | "VERBOSE";
}

const DEFAULT_POLICY: GrantPolicy = {
  maxTtlSeconds: 3600,
  requireConfirmation: false,
  auditLevel: "NORMAL",
};

function getGrantStatus(grant: Grant): GrantStatus {
  if (grant.revoked) return "revoked";
  if (new Date() > grant.expiresAt) return "expired";
  return "active";
}

function isGrantValid(grant: Grant): boolean {
  return getGrantStatus(grant) === "active";
}

function matchesScope(grantScope: string, requestedScope: string): boolean {
  const grantParts = grantScope.split(":");
  const requestParts = requestedScope.split(":");

  if (grantParts.length < 2 || requestParts.length < 2) {
    return false;
  }

  // Check action matches
  if (grantParts[0] !== requestParts[0] && grantParts[0] !== "*") {
    return false;
  }

  // Check sub-action matches
  if (grantParts[1] !== requestParts[1] && grantParts[1] !== "*") {
    return false;
  }

  // Check resource pattern (simple glob matching)
  if (grantParts.length > 2 && requestParts.length > 2) {
    const pattern = grantParts.slice(2).join(":");
    const resource = requestParts.slice(2).join(":");
    return globMatch(pattern, resource);
  }

  return true;
}

function globMatch(pattern: string, str: string): boolean {
  const regexPattern = pattern
    .replace(/[.+^${}()|[\]\\]/g, "\\$&")
    .replace(/\*/g, ".*")
    .replace(/\?/g, ".");
  return new RegExp(`^${regexPattern}$`).test(str);
}

export class GrantStore {
  private grants = new Map<string, Grant>();
  private byAgent = new Map<string, string[]>();
  private policies = new Map<string, GrantPolicy>();

  setPolicy(scopePrefix: string, policy: GrantPolicy): void {
    this.policies.set(scopePrefix, policy);
  }

  getPolicy(scope: string): GrantPolicy {
    let bestMatch = "";
    for (const prefix of this.policies.keys()) {
      if (scope.startsWith(prefix) && prefix.length > bestMatch.length) {
        bestMatch = prefix;
      }
    }
    return this.policies.get(bestMatch) ?? DEFAULT_POLICY;
  }

  issue(
    agentId: string,
    scope: string,
    ttlSeconds: number,
    issuer: string,
    metadata?: Record<string, string>
  ): Grant {
    const policy = this.getPolicy(scope);

    // Enforce max TTL
    const effectiveTtl = Math.min(ttlSeconds, policy.maxTtlSeconds);

    const now = new Date();
    const grant: Grant = {
      grantId: randomUUID(),
      agentId,
      scope,
      issuedAt: now,
      expiresAt: new Date(now.getTime() + effectiveTtl * 1000),
      issuer,
      revoked: false,
      metadata: new Map(Object.entries(metadata ?? {})),
    };

    this.grants.set(grant.grantId, grant);

    const agentGrants = this.byAgent.get(agentId) ?? [];
    agentGrants.push(grant.grantId);
    this.byAgent.set(agentId, agentGrants);

    return grant;
  }

  check(agentId: string, requestedScope: string): Grant | undefined {
    const grantIds = this.byAgent.get(agentId) ?? [];

    for (const grantId of grantIds) {
      const grant = this.grants.get(grantId);
      if (grant && isGrantValid(grant) && matchesScope(grant.scope, requestedScope)) {
        return grant;
      }
    }

    return undefined;
  }

  revoke(grantId: string): boolean {
    const grant = this.grants.get(grantId);
    if (!grant) return false;

    // Create revoked version (grants are immutable conceptually)
    const revokedGrant: Grant = {
      ...grant,
      revoked: true,
    };
    this.grants.set(grantId, revokedGrant);
    return true;
  }

  revokeAllForAgent(agentId: string): number {
    const grantIds = this.byAgent.get(agentId) ?? [];
    let count = 0;
    for (const grantId of grantIds) {
      if (this.revoke(grantId)) count++;
    }
    return count;
  }

  listGrants(agentId?: string, includeExpired = false): Grant[] {
    let grants: Grant[];

    if (agentId) {
      const grantIds = this.byAgent.get(agentId) ?? [];
      grants = grantIds
        .map((id) => this.grants.get(id))
        .filter((g): g is Grant => g !== undefined);
    } else {
      grants = Array.from(this.grants.values());
    }

    if (!includeExpired) {
      grants = grants.filter(isGrantValid);
    }

    return grants;
  }

  cleanupExpired(): number {
    const expired: string[] = [];

    for (const [grantId, grant] of this.grants) {
      if (!isGrantValid(grant)) {
        expired.push(grantId);
      }
    }

    for (const grantId of expired) {
      const grant = this.grants.get(grantId);
      this.grants.delete(grantId);

      if (grant) {
        const agentGrants = this.byAgent.get(grant.agentId);
        if (agentGrants) {
          this.byAgent.set(
            grant.agentId,
            agentGrants.filter((id) => id !== grantId)
          );
        }
      }
    }

    return expired.length;
  }
}

// Example usage
if (require.main === module) {
  const store = new GrantStore();

  // Set policies
  store.setPolicy("file:read", { maxTtlSeconds: 86400, requireConfirmation: false, auditLevel: "NORMAL" });
  store.setPolicy("file:write", { maxTtlSeconds: 3600, requireConfirmation: false, auditLevel: "NORMAL" });
  store.setPolicy("shell:execute", { maxTtlSeconds: 300, requireConfirmation: true, auditLevel: "VERBOSE" });

  // Issue grants
  const readGrant = store.issue(
    "code-assistant-01",
    "file:read:/workspace/*",
    7200,
    "admin"
  );
  console.log(`Issued read grant: ${readGrant.grantId.slice(0, 8)}...`);
  console.log(`  Scope: ${readGrant.scope}`);
  console.log(`  Expires: ${readGrant.expiresAt.toISOString()}`);

  const writeGrant = store.issue(
    "code-assistant-01",
    "file:write:/workspace/src/*",
    1800,
    "admin"
  );
  console.log(`Issued write grant: ${writeGrant.grantId.slice(0, 8)}...`);

  // Check permissions
  const canRead = store.check("code-assistant-01", "file:read:/workspace/main.py");
  console.log(`\nCan read /workspace/main.py: ${canRead !== undefined}`);

  const canWrite = store.check("code-assistant-01", "file:write:/workspace/src/app.ts");
  console.log(`Can write /workspace/src/app.ts: ${canWrite !== undefined}`);

  const canDelete = store.check("code-assistant-01", "file:delete:/workspace/main.py");
  console.log(`Can delete /workspace/main.py: ${canDelete !== undefined}`);

  // Revoke a grant
  store.revoke(writeGrant.grantId);
  const canWriteAfter = store.check("code-assistant-01", "file:write:/workspace/src/app.ts");
  console.log(`\nAfter revocation, can write: ${canWriteAfter !== undefined}`);
}
