/**
 * POC: SDK with Event Subscription
 *
 * Uses OpenCode SDK with proper event streaming as documented.
 * This approach uses client.event.subscribe() for real-time updates.
 */

import { createOpencode } from "@opencode-ai/sdk";

// Configuration - z.ai provider with GLM model
const PROVIDER = process.env["OPENCODE_PROVIDER"] ?? "zai-coding-plan";
const MODEL = process.env["OPENCODE_MODEL"] ?? "glm-4.7";

interface EventData {
  type: string;
  properties?: {
    sessionID?: string;
    content?: string;
    text?: string;
    role?: string;
    [key: string]: unknown;
  };
}

export async function runSdkWithEvents(prompt: string): Promise<string> {
  console.log("Starting OpenCode SDK with event subscription...");
  console.log(`Provider: ${PROVIDER}, Model: ${MODEL}`);

  // Start embedded OpenCode server
  const { client, server } = await createOpencode();
  console.log(`Server started at ${server.url}`);

  try {
    // Create a session
    const session = await client.session.create({
      body: { title: "SDK Events POC" },
    });

    if (!session.data?.id) {
      throw new Error("Failed to create session - no ID returned");
    }

    const sessionId = session.data.id;
    console.log(`Session created: ${sessionId}`);

    // Set up event listener
    console.log("Subscribing to events...");
    const eventStream = await client.event.subscribe();

    // Collect response parts
    let responseText = "";
    let isComplete = false;

    // Start processing events in background
    const eventPromise = (async () => {
      try {
        for await (const event of eventStream.stream as AsyncIterable<EventData>) {
          console.log(`Event: ${event.type}`);

          // Look for text content events
          if (event.properties?.sessionID === sessionId) {
            if (event.properties?.text) {
              responseText += event.properties.text;
            }
            if (event.properties?.content) {
              responseText += event.properties.content;
            }
          }

          // Check for completion - session.idle indicates the model finished
          if (
            event.type === "session.idle" ||
            event.type === "message.complete" ||
            event.type === "session.complete"
          ) {
            isComplete = true;
            break;
          }

          // Also check for errors
          if (event.type === "error") {
            throw new Error(`Event error: ${JSON.stringify(event.properties)}`);
          }
        }
      } catch (err) {
        if (!isComplete) throw err;
      }
    })();

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
    console.log("Prompt sent, waiting for events...");

    // Wait for events with timeout
    const timeoutPromise = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error("Timeout waiting for response")), 120000)
    );

    await Promise.race([eventPromise, timeoutPromise]);

    // If no text from events, try polling messages
    if (!responseText) {
      console.log("No text from events, checking messages...");
      const messages = await client.session.messages({
        path: { id: sessionId },
      });

      for (const msg of messages.data ?? []) {
        const info = msg.info as { role?: string } | undefined;
        if (info?.role === "assistant") {
          const parts = msg.parts as Array<{ type: string; text?: string }>;
          responseText = parts
            .filter((p) => p.type === "text" && p.text)
            .map((p) => p.text)
            .join("\n");
          if (responseText) break;
        }
      }
    }

    return responseText || "No response received";
  } finally {
    console.log("Shutting down server...");
    server.close();
  }
}

// CLI runner
if (
  process.argv[1]?.endsWith("sdk-events.ts") ||
  process.argv[1]?.endsWith("sdk-events.js")
) {
  const prompt = process.argv[2] ?? "Say hello and tell me what model you are. Keep it brief.";

  console.log("=".repeat(50));
  console.log("SDK Events POC");
  console.log("=".repeat(50));
  console.log(`Prompt: ${prompt}`);
  console.log("");

  runSdkWithEvents(prompt)
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
      process.exit(1);
    });
}
