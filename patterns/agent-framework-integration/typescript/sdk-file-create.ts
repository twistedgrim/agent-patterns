/**
 * POC Step 2: SDK File Creation
 *
 * Tests OpenCode SDK's ability to create files.
 * Uses the working polling approach from sdk-simple.ts.
 */

import { createOpencode } from "@opencode-ai/sdk";
import { readFile, rm, mkdir } from "fs/promises";
import { existsSync } from "fs";

// Configuration
const PROVIDER = process.env["OPENCODE_PROVIDER"] ?? "zai-coding-plan";
const MODEL = process.env["OPENCODE_MODEL"] ?? "glm-4.7";
// Output to poc/output subdirectory (relative to where script runs)
const SCRIPT_DIR = new URL(".", import.meta.url).pathname;
const OUTPUT_DIR = process.env["POC_OUTPUT_DIR"] ?? `${SCRIPT_DIR}output`;

export async function runSdkFileCreate(): Promise<{
  success: boolean;
  filePath?: string;
  fileContent?: string;
  response?: string;
  error?: string;
}> {
  console.log("=".repeat(50));
  console.log("SDK File Creation POC");
  console.log("=".repeat(50));
  console.log(`Provider: ${PROVIDER}, Model: ${MODEL}`);
  console.log(`Output dir: ${OUTPUT_DIR}`);
  console.log("");

  // Ensure output directory exists and is clean
  if (existsSync(OUTPUT_DIR)) {
    await rm(OUTPUT_DIR, { recursive: true });
  }
  await mkdir(OUTPUT_DIR, { recursive: true });

  // Start embedded OpenCode server
  console.log("Starting OpenCode SDK...");
  const { client, server } = await createOpencode();
  console.log(`Server started at ${server.url}`);

  try {
    // Create a session
    const session = await client.session.create({
      body: { title: "File Creation POC" },
    });

    if (!session.data?.id) {
      throw new Error("Failed to create session - no ID returned");
    }

    const sessionId = session.data.id;
    console.log(`Session created: ${sessionId}`);

    // Prompt to create a simple file
    const targetFile = `${OUTPUT_DIR}/hello.py`;
    const prompt = `Create a simple Python file at ${targetFile} that:
1. Defines a function called greet(name) that returns "Hello, {name}!"
2. Has a main block that calls greet("World") and prints the result

Just create the file, nothing else. Do not explain.`;

    console.log("Sending prompt to create file...");
    console.log(`Target: ${targetFile}`);
    console.log("");

    // Subscribe to events for streaming output
    const eventStream = await client.event.subscribe();

    // Start streaming events to stdout in background
    const streamingPromise = streamEvents(eventStream, sessionId);

    // Send the prompt
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

    // Wait for streaming to complete (session.idle)
    await streamingPromise;

    // Get final response from messages
    const response = await getAssistantResponse(client, sessionId);
    console.log("Response received:");
    console.log(response.slice(0, 500));
    console.log("");

    // Check if file was created
    console.log("Checking if file was created...");
    if (existsSync(targetFile)) {
      const content = await readFile(targetFile, "utf-8");
      console.log("SUCCESS: File created!");
      console.log("");
      console.log("File content:");
      console.log("-".repeat(40));
      console.log(content);
      console.log("-".repeat(40));

      return {
        success: true,
        filePath: targetFile,
        fileContent: content,
        response,
      };
    } else {
      console.log("File was NOT created at expected path.");

      // Check what files exist in output dir
      const { readdir } = await import("fs/promises");
      const files = await readdir(OUTPUT_DIR).catch(() => []);
      console.log(`Files in ${OUTPUT_DIR}:`, files);

      return {
        success: false,
        response,
        error: "File was not created at expected path",
      };
    }
  } finally {
    console.log("\nShutting down server...");
    server.close();
  }
}

interface EventData {
  type: string;
  properties?: {
    sessionID?: string;
    path?: string;
    content?: string;
    text?: string;
    [key: string]: unknown;
  };
}

/**
 * Stream events to stdout for real-time logging.
 * Returns when session.idle is received.
 */
async function streamEvents(
  eventStream: Awaited<ReturnType<Awaited<ReturnType<typeof createOpencode>>["client"]["event"]["subscribe"]>>,
  sessionId: string,
  timeoutMs = 180000
): Promise<void> {
  const startTime = Date.now();

  console.log("[STREAM] Waiting for events...");

  try {
    for await (const event of eventStream.stream as AsyncIterable<EventData>) {
      // Check timeout
      if (Date.now() - startTime > timeoutMs) {
        console.log("[STREAM] Timeout reached");
        break;
      }

      // Log event type
      const timestamp = new Date().toISOString().slice(11, 19);

      // Filter to relevant events and log details
      switch (event.type) {
        case "session.status":
          console.log(`[${timestamp}] ${event.type}`);
          break;

        case "session.diff":
          // File operation
          if (event.properties?.path) {
            console.log(`[${timestamp}] FILE: ${event.properties.path}`);
          }
          break;

        case "message.part.updated":
          // Streaming text - could extract and show partial content
          // For now just show a dot to indicate progress
          process.stdout.write(".");
          break;

        case "message.updated":
          console.log(`\n[${timestamp}] ${event.type}`);
          break;

        case "session.idle":
          console.log(`\n[${timestamp}] Session complete (idle)`);
          return;

        case "error":
          console.error(`[${timestamp}] ERROR:`, event.properties);
          break;

        default:
          // Skip verbose events like server.heartbeat
          if (!event.type.startsWith("server.")) {
            console.log(`[${timestamp}] ${event.type}`);
          }
      }
    }
  } catch (err) {
    console.log("[STREAM] Event stream ended");
  }
}

/**
 * Get assistant response from session messages.
 */
async function getAssistantResponse(
  client: Awaited<ReturnType<typeof createOpencode>>["client"],
  sessionId: string
): Promise<string> {
  const messages = await client.session.messages({
    path: { id: sessionId },
  });

  for (const msg of messages.data ?? []) {
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

  return "(No response text found)";
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// CLI runner
if (
  process.argv[1]?.endsWith("sdk-file-create.ts") ||
  process.argv[1]?.endsWith("sdk-file-create.js")
) {
  runSdkFileCreate()
    .then((result) => {
      console.log("\n" + "=".repeat(50));
      console.log("RESULT:", result.success ? "SUCCESS" : "FAILED");
      if (result.error) {
        console.log("Error:", result.error);
      }
      process.exit(result.success ? 0 : 1);
    })
    .catch((err) => {
      console.error("\nERROR:", err.message);
      process.exit(1);
    });
}
