/**
 * POC: Simple SDK approach
 *
 * Uses OpenCode SDK with event streaming to get responses.
 * This is a minimal working example to verify SDK integration.
 */

import { createOpencode } from "@opencode-ai/sdk";

// Configuration - z.ai provider with GLM model
const PROVIDER = process.env["OPENCODE_PROVIDER"] ?? "zai-coding-plan";
const MODEL = process.env["OPENCODE_MODEL"] ?? "glm-4.7";

interface SessionEvent {
  type: string;
  properties?: {
    sessionID?: string;
    messageID?: string;
    [key: string]: unknown;
  };
}

export async function runSdkSimple(prompt: string): Promise<string> {
  console.log("Starting OpenCode SDK...");
  console.log(`Provider: ${PROVIDER}, Model: ${MODEL}`);

  // Start embedded OpenCode server
  const { client, server } = await createOpencode();
  console.log(`Server started at ${server.url}`);

  try {
    // Create a session
    const session = await client.session.create({
      body: { title: "SDK POC Test" },
    });

    if (!session.data?.id) {
      throw new Error("Failed to create session - no ID returned");
    }

    const sessionId = session.data.id;
    console.log(`Session created: ${sessionId}`);

    // Set up event listener before sending prompt
    const eventPromise = waitForAssistantResponse(client, sessionId);

    // Send the prompt
    console.log("Sending prompt...");
    await client.session.prompt({
      path: { id: sessionId },
      body: {
        parts: [{ type: "text", text: prompt }],
        model: {
          providerID: PROVIDER,
          modelID: MODEL,
        },
      },
    });
    console.log("Prompt sent, waiting for response...");

    // Wait for assistant response
    const response = await eventPromise;
    return response;
  } finally {
    // Clean up
    console.log("Shutting down server...");
    server.close();
  }
}

/**
 * Wait for assistant response by polling session messages.
 *
 * The SDK doesn't have great streaming support, so we poll.
 */
async function waitForAssistantResponse(
  client: Awaited<ReturnType<typeof createOpencode>>["client"],
  sessionId: string,
  timeoutMs = 120000,
  pollIntervalMs = 2000
): Promise<string> {
  const startTime = Date.now();
  let lastMessageCount = 0;

  while (Date.now() - startTime < timeoutMs) {
    await sleep(pollIntervalMs);

    try {
      const messages = await client.session.messages({
        path: { id: sessionId },
      });

      const messageList = messages.data ?? [];

      // Check if we have new messages
      if (messageList.length > lastMessageCount) {
        console.log(`Messages: ${messageList.length}`);
        lastMessageCount = messageList.length;
      }

      // Look for assistant response
      for (const msg of messageList) {
        const info = msg.info as { role?: string } | undefined;
        if (info?.role === "assistant") {
          const parts = msg.parts as Array<{ type: string; text?: string }>;
          const textContent = parts
            .filter((p) => p.type === "text" && p.text)
            .map((p) => p.text)
            .join("\n");

          if (textContent && textContent.length > 0) {
            return textContent;
          }
        }
      }
    } catch (error) {
      console.error("Error polling messages:", error);
    }

    const elapsed = Math.round((Date.now() - startTime) / 1000);
    console.log(`Polling... ${elapsed}s elapsed`);
  }

  throw new Error(`Timeout waiting for response after ${timeoutMs}ms`);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// CLI runner
if (
  process.argv[1]?.endsWith("sdk-simple.ts") ||
  process.argv[1]?.endsWith("sdk-simple.js")
) {
  const prompt = process.argv[2] ?? "Say hello and tell me what model you are. Keep it brief.";

  console.log("=".repeat(50));
  console.log("SDK Simple POC");
  console.log("=".repeat(50));
  console.log(`Prompt: ${prompt}`);
  console.log("");

  runSdkSimple(prompt)
    .then((response) => {
      console.log("");
      console.log("=".repeat(50));
      console.log("RESPONSE:");
      console.log("=".repeat(50));
      console.log(response);
      process.exit(0);
    })
    .catch((err) => {
      console.error("");
      console.error("ERROR:", err.message);
      if (err.cause) {
        console.error("CAUSE:", err.cause);
      }
      process.exit(1);
    });
}
