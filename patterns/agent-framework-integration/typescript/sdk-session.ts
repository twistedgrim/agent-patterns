/**
 * POC 2: SDK Session approach
 * Uses the OpenCode SDK to create sessions and send prompts
 */

import { createOpencode, createOpencodeClient } from "@opencode-ai/sdk";

const PROVIDER = process.env["OPENCODE_PROVIDER"] ?? "zai-coding-plan";
const MODEL = process.env["OPENCODE_MODEL"] ?? "glm-4.7";

export async function runSdkSession(prompt: string): Promise<string> {
  console.log("Initializing OpenCode SDK...");

  // Start embedded server
  const { client } = await createOpencode();
  console.log("SDK initialized");

  // Create session
  const session = await client.session.create({
    body: { title: "POC Test" },
  });

  if (!session.data?.id) {
    throw new Error("Failed to create session");
  }

  const sessionId = session.data.id;
  console.log("Session created:", sessionId);

  // Send prompt
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

  // Poll for completion (simple approach)
  let attempts = 0;
  const maxAttempts = 60; // 5 minutes with 5s intervals

  while (attempts < maxAttempts) {
    await new Promise(r => setTimeout(r, 5000));
    attempts++;

    const messages = await client.session.messages({
      path: { id: sessionId },
    });

    if (messages.data && messages.data.length > 1) {
      // Find assistant response
      for (const msg of messages.data) {
        const info = msg.info as { role?: string } | undefined;
        if (info?.role === "assistant") {
          const parts = msg.parts as Array<{ type: string; text?: string }>;
          const textContent = parts
            .filter(p => p.type === "text" && p.text)
            .map(p => p.text)
            .join("\n");

          if (textContent) {
            return textContent;
          }
        }
      }
    }

    console.log(`Polling... attempt ${attempts}/${maxAttempts}`);
  }

  throw new Error("Timeout waiting for response");
}

// Test if run directly
if (process.argv[1]?.endsWith("sdk-session.ts") || process.argv[1]?.endsWith("sdk-session.js")) {
  const prompt = process.argv[2] ?? "Say hello and tell me what model you are";
  console.log("Running SDK Session POC...");
  console.log("Provider:", PROVIDER);
  console.log("Model:", MODEL);
  console.log("Prompt:", prompt.slice(0, 100) + "...");

  runSdkSession(prompt)
    .then(response => {
      console.log("\n=== RESPONSE ===");
      console.log(response);
    })
    .catch(err => {
      console.error("Error:", err.message);
      process.exit(1);
    });
}
