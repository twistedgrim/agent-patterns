/**
 * Skill/tool provenance verification.
 *
 * Verifies that skills and tools come from trusted publishers
 * before allowing them to be loaded or executed.
 */

import { createHash, createHmac, timingSafeEqual } from "crypto";

export type VerificationStatus =
  | "verified"
  | "unsigned"
  | "invalid_signature"
  | "untrusted_publisher"
  | "expired"
  | "blocked";

export interface Publisher {
  readonly publisherId: string;
  readonly name: string;
  readonly publicKey: Buffer;
  readonly verifiedAt: Date;
  readonly trustLevel: "standard" | "elevated" | "system";
}

export interface SkillManifest {
  readonly skillId: string;
  readonly name: string;
  readonly version: string;
  readonly publisherId: string;
  readonly contentHash: Buffer;
  readonly signature?: Buffer;
  readonly signedAt?: Date;
  readonly dependencies: readonly string[];
}

export interface VerificationResult {
  readonly status: VerificationStatus;
  readonly skillId: string;
  readonly publisher?: Publisher;
  readonly reason?: string;
}

function isVerified(result: VerificationResult): boolean {
  return result.status === "verified";
}

export class ProvenanceVerifier {
  private publishers = new Map<string, Publisher>();
  private blockedPublishers = new Set<string>();
  private requireSignature: boolean;

  constructor(requireSignature = true) {
    this.requireSignature = requireSignature;
  }

  registerPublisher(publisher: Publisher): void {
    this.publishers.set(publisher.publisherId, publisher);
  }

  blockPublisher(publisherId: string): void {
    this.blockedPublishers.add(publisherId);
  }

  unblockPublisher(publisherId: string): void {
    this.blockedPublishers.delete(publisherId);
  }

  verify(manifest: SkillManifest, content: Buffer): VerificationResult {
    // Check if publisher is blocked
    if (this.blockedPublishers.has(manifest.publisherId)) {
      return {
        status: "blocked",
        skillId: manifest.skillId,
        reason: `Publisher ${manifest.publisherId} is blocked`,
      };
    }

    // Check if signature is required but missing
    if (this.requireSignature && !manifest.signature) {
      return {
        status: "unsigned",
        skillId: manifest.skillId,
        reason: "Signature required but not provided",
      };
    }

    // Get publisher
    const publisher = this.publishers.get(manifest.publisherId);
    if (!publisher) {
      return {
        status: "untrusted_publisher",
        skillId: manifest.skillId,
        reason: `Publisher ${manifest.publisherId} not in trust store`,
      };
    }

    // Verify content hash
    const actualHash = createHash("sha256").update(content).digest();
    if (!timingSafeEqual(actualHash, manifest.contentHash)) {
      return {
        status: "invalid_signature",
        skillId: manifest.skillId,
        publisher,
        reason: "Content hash mismatch",
      };
    }

    // Verify signature if present
    if (manifest.signature) {
      if (!this.verifySignature(publisher.publicKey, manifest.contentHash, manifest.signature)) {
        return {
          status: "invalid_signature",
          skillId: manifest.skillId,
          publisher,
          reason: "Signature verification failed",
        };
      }
    }

    return {
      status: "verified",
      skillId: manifest.skillId,
      publisher,
    };
  }

  private verifySignature(publicKey: Buffer, contentHash: Buffer, signature: Buffer): boolean {
    // Simplified HMAC verification - use proper asymmetric crypto in production
    const expected = createHmac("sha256", publicKey).update(contentHash).digest();
    return timingSafeEqual(expected, signature);
  }
}

export function computeContentHash(content: Buffer): Buffer {
  return createHash("sha256").update(content).digest();
}

export function signContent(privateKey: Buffer, contentHash: Buffer): Buffer {
  return createHmac("sha256", privateKey).update(contentHash).digest();
}

// Example usage
if (require.main === module) {
  const verifier = new ProvenanceVerifier(true);

  // Register trusted publisher
  const publisherPrivateKey = Buffer.from("publisher-secret-key-12345678901");
  const publisherPublicKey = createHash("sha256").update(publisherPrivateKey).digest();

  const publisher: Publisher = {
    publisherId: "official-tools",
    name: "Official Tools Publisher",
    publicKey: publisherPublicKey,
    verifiedAt: new Date(),
    trustLevel: "elevated",
  };
  verifier.registerPublisher(publisher);

  // Create a signed skill
  const skillContent = Buffer.from(`
    name: code-formatter
    description: Formats code according to style guidelines
    commands:
      - format_file
      - check_style
  `);

  const contentHash = computeContentHash(skillContent);
  const signature = signContent(publisherPrivateKey, contentHash);

  const manifest: SkillManifest = {
    skillId: "code-formatter-v1",
    name: "Code Formatter",
    version: "1.0.0",
    publisherId: "official-tools",
    contentHash,
    signature,
    signedAt: new Date(),
    dependencies: [],
  };

  // Verify the skill
  const result = verifier.verify(manifest, skillContent);
  console.log(`Verification status: ${result.status}`);
  console.log(`Valid: ${isVerified(result)}`);
  if (result.publisher) {
    console.log(`Publisher: ${result.publisher.name}`);
  }

  // Try with tampered content
  const tamperedContent = Buffer.concat([skillContent, Buffer.from("\n  - malicious_command")]);
  const tamperedResult = verifier.verify(manifest, tamperedContent);
  console.log(`\nTampered content status: ${tamperedResult.status}`);
  console.log(`Reason: ${tamperedResult.reason}`);

  // Try with untrusted publisher
  const untrustedManifest: SkillManifest = {
    skillId: "sketchy-tool",
    name: "Sketchy Tool",
    version: "1.0.0",
    publisherId: "unknown-publisher",
    contentHash,
    signature,
    dependencies: [],
  };
  const untrustedResult = verifier.verify(untrustedManifest, skillContent);
  console.log(`\nUntrusted publisher status: ${untrustedResult.status}`);
  console.log(`Reason: ${untrustedResult.reason}`);
}
