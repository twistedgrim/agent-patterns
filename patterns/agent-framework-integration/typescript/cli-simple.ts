/**
 * POC: Simple CLI approach
 *
 * Uses `opencode run` command for non-interactive automation.
 * This is the simplest approach - shells out to CLI.
 */

import { exec, spawn } from "child_process";
import { promisify } from "util";
import { writeFile, unlink } from "fs/promises";

const execAsync = promisify(exec);

const MODEL = process.env["OPENCODE_MODEL"] ?? "zai-coding-plan/glm-4.7";

export async function runSimpleCli(prompt: string): Promise<{ stdout: string; stderr: string }> {
  // Write prompt to temp file to avoid shell escaping issues
  const promptFile = `/tmp/prompt_${Date.now()}.txt`;
  await writeFile(promptFile, prompt);

  try {
    // Use `opencode run` which is the correct command for automation
    // The prompt is piped via stdin from the file
    const { stdout, stderr } = await execAsync(
      `cat "${promptFile}" | opencode run --model ${MODEL}`,
      {
        timeout: 300000, // 5 min
        shell: "/bin/bash",
        maxBuffer: 10 * 1024 * 1024, // 10MB
      }
    );
    return { stdout, stderr };
  } finally {
    await unlink(promptFile).catch(() => {});
  }
}

/**
 * Alternative: Use spawn for streaming output
 */
export async function runCliWithStreaming(
  prompt: string,
  onChunk?: (chunk: string) => void
): Promise<string> {
  const promptFile = `/tmp/prompt_${Date.now()}.txt`;
  await writeFile(promptFile, prompt);

  return new Promise((resolve, reject) => {
    const child = spawn(
      "sh",
      ["-c", `cat "${promptFile}" | opencode run --model ${MODEL}`],
      {
        stdio: ["inherit", "pipe", "pipe"],
      }
    );

    let stdout = "";
    let stderr = "";

    child.stdout?.on("data", (data: Buffer) => {
      const chunk = data.toString();
      stdout += chunk;
      onChunk?.(chunk);
    });

    child.stderr?.on("data", (data: Buffer) => {
      stderr += data.toString();
    });

    child.on("close", (code) => {
      unlink(promptFile).catch(() => {});
      if (code === 0) {
        resolve(stdout);
      } else {
        reject(new Error(`Process exited with code ${code}: ${stderr}`));
      }
    });

    child.on("error", (err) => {
      unlink(promptFile).catch(() => {});
      reject(err);
    });

    // Timeout after 5 minutes
    setTimeout(() => {
      child.kill();
      unlink(promptFile).catch(() => {});
      reject(new Error("Timeout waiting for response"));
    }, 300000);
  });
}

// Test if run directly
if (process.argv[1]?.endsWith("cli-simple.ts") || process.argv[1]?.endsWith("cli-simple.js")) {
  const prompt = process.argv[2] ?? "Say hello and tell me what model you are";
  console.log("Running simple CLI POC...");
  console.log("Model:", MODEL);
  console.log("Prompt:", prompt.slice(0, 100) + "...");

  runSimpleCli(prompt)
    .then(({ stdout, stderr }) => {
      console.log("\n=== STDOUT ===");
      console.log(stdout);
      if (stderr) {
        console.log("\n=== STDERR ===");
        console.log(stderr);
      }
    })
    .catch(err => {
      console.error("Error:", err.message);
      process.exit(1);
    });
}
