/**
 * Agent identity with cryptographic key generation.
 *
 * Each agent has a unique identity with a keypair for signing actions.
 * This enables attribution and non-repudiation of agent behavior.
 */

import { createHmac, randomBytes, createHash, timingSafeEqual } from "crypto";

export interface AgentIdentity {
  readonly agentId: string;
  readonly publicKey: Buffer;
  readonly issuer: string;
  readonly createdAt: Date;
  readonly metadata: ReadonlyMap<string, string>;
}

export interface AgentKeyPair {
  readonly identity: AgentIdentity;
  readonly privateKey: Buffer;
}

function computeFingerprint(publicKey: Buffer): string {
  return createHash("sha256").update(publicKey).digest("hex").slice(0, 16);
}

function sign(privateKey: Buffer, data: Buffer): Buffer {
  return createHmac("sha256", privateKey).update(data).digest();
}

function verify(privateKey: Buffer, data: Buffer, signature: Buffer): boolean {
  const expected = sign(privateKey, data);
  return timingSafeEqual(expected, signature);
}

export class IdentityRegistry {
  private identities = new Map<string, AgentIdentity>();
  private keypairs = new Map<string, AgentKeyPair>();

  createIdentity(
    agentId: string,
    issuer: string,
    metadata?: Record<string, string>
  ): AgentKeyPair {
    if (this.identities.has(agentId)) {
      throw new Error(`Agent ${agentId} already exists`);
    }

    // Generate keypair (simplified - use proper crypto in production)
    const privateKey = randomBytes(32);
    const publicKey = createHash("sha256").update(privateKey).digest();

    const identity: AgentIdentity = {
      agentId,
      publicKey,
      issuer,
      createdAt: new Date(),
      metadata: new Map(Object.entries(metadata ?? {})),
    };

    const keypair: AgentKeyPair = { identity, privateKey };

    this.identities.set(agentId, identity);
    this.keypairs.set(agentId, keypair);

    return keypair;
  }

  getIdentity(agentId: string): AgentIdentity | undefined {
    return this.identities.get(agentId);
  }

  getKeypair(agentId: string): AgentKeyPair | undefined {
    return this.keypairs.get(agentId);
  }

  revokeIdentity(agentId: string): boolean {
    if (this.identities.has(agentId)) {
      this.identities.delete(agentId);
      this.keypairs.delete(agentId);
      return true;
    }
    return false;
  }

  listIdentities(): AgentIdentity[] {
    return Array.from(this.identities.values());
  }
}

export function signAction(keypair: AgentKeyPair, data: Buffer): Buffer {
  return sign(keypair.privateKey, data);
}

export function verifyAction(
  keypair: AgentKeyPair,
  data: Buffer,
  signature: Buffer
): boolean {
  return verify(keypair.privateKey, data, signature);
}

// Example usage
if (require.main === module) {
  const registry = new IdentityRegistry();

  // Create agent identity
  const keypair = registry.createIdentity("code-assistant-01", "my-organization", {
    purpose: "code-review",
    environment: "production",
  });

  console.log(`Agent ID: ${keypair.identity.agentId}`);
  console.log(`Fingerprint: ${computeFingerprint(keypair.identity.publicKey)}`);
  console.log(`Issuer: ${keypair.identity.issuer}`);

  // Sign an action
  const actionData = Buffer.from("file:write:/workspace/main.py");
  const signature = signAction(keypair, actionData);
  console.log(`Signature: ${signature.toString("hex").slice(0, 32)}...`);

  // Verify signature
  const isValid = verifyAction(keypair, actionData, signature);
  console.log(`Signature valid: ${isValid}`);
}
