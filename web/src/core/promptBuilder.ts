/**
 * FAS 4 - PromptBuilder System
 * Manages context injection with budget control
 */

import type { Artifact } from "@/src/memory/types";
import memory from "@/src/memory";
import { emit } from "./eventBus";
import fs from "fs";
import path from "path";
import yaml from "js-yaml";

const INJECT_BUDGET_PCT = parseInt(process.env.INJECT_BUDGET_PCT || "25");
const MAX_CONTEXT_TOKENS = 200; // Much smaller budget to stay within 25%

// Load persona and style files
function loadIdentityFile(filename: string): string {
  try {
    const filePath = path.join(process.cwd(), "alice", "identity", filename);
    if (fs.existsSync(filePath)) {
      const content = fs.readFileSync(filePath, "utf8");
      if (filename.endsWith(".yml") || filename.endsWith(".yaml")) {
        const parsed = yaml.load(content) as any;
        return yaml.dump(parsed, { indent: 2 });
      }
      return content;
    }
  } catch (error) {
    console.error(`Failed to load identity file ${filename}:`, error);
  }
  return "";
}

export function compressArtifacts(arts: Artifact[], maxChars = 1500): string {
  if (!arts.length) return "";
  
  // Sort by score (highest first) and take top items that fit budget
  const sorted = arts.sort((a, b) => b.score - a.score);
  let totalChars = 0;
  const selected: Artifact[] = [];
  
  for (const art of sorted) {
    const artText = `• [${art.kind}] ${art.text}`;
    if (totalChars + artText.length <= maxChars) {
      selected.push(art);
      totalChars += artText.length;
    } else {
      break;
    }
  }
  
  return selected.map(a => `• [${a.kind}] ${a.text}`).join("\n");
}

export async function buildContext(userId: string): Promise<string> {
  try {
    // Get relevant artifacts from memory
    const artifacts = await memory.fetch(userId, 12);
    
    // Filter by confidence threshold
    const confThreshold = parseFloat(process.env.ARTIFACT_CONFIDENCE_MIN || "0.7");
    const filtered = artifacts.filter(a => a.score >= confThreshold);
    
    // Compress within budget
    const maxContextChars = Math.floor(MAX_CONTEXT_TOKENS * 4); // ~4 chars per token estimate
    const compressed = compressArtifacts(filtered, maxContextChars);
    
    return compressed;
  } catch (error) {
    console.error("Failed to build context:", error);
    return "";
  }
}

export function buildSystemPrompt(persona: string, style: string, context: string): any[] {
  // Combine all system content into single message to save tokens
  const parts = [];
  
  if (persona.trim()) {
    parts.push(persona.trim());
  }
  
  if (style.trim()) {
    parts.push(`Stil: ${style.trim()}`);
  }
  
  if (context.trim()) {
    parts.push(`Kontext: ${context.trim()}`);
  }
  
  // Single system message instead of multiple
  if (parts.length > 0) {
    return [{
      role: "system",
      content: parts.join('\n\n')
    }];
  }
  
  return [];
}

export async function buildPromptWithContext(
  userId: string, 
  userMessage: string
): Promise<{
  messages: any[],
  stats: { injected_tokens_pct: number, artifacts_used: number }
}> {
  const t0 = Date.now();
  
  // Load identity files
  const persona = loadIdentityFile("persona.yml");
  const style = loadIdentityFile("style.yml");
  
  // Build context from memory
  const context = await buildContext(userId);
  
  // Build system messages
  const systemMessages = buildSystemPrompt(persona, style, context);
  
  // Add user message
  const messages = [
    ...systemMessages,
    { role: "user", content: userMessage }
  ];
  
  // Calculate token injection percentage (rough estimate: 4 chars = 1 token)
  const userTokens = userMessage.length / 4;
  const systemTokens = systemMessages.reduce((sum, msg) => sum + (msg.content?.length || 0), 0) / 4;
  const totalTokens = userTokens + systemTokens;
  const injected_tokens_pct = totalTokens > 0 ? (systemTokens / totalTokens) * 100 : 0;
  
  // If we're over budget, trim system content  
  if (injected_tokens_pct > INJECT_BUDGET_PCT && systemMessages.length > 0) {
    // Calculate max allowed system tokens based on user message
    const maxSystemTokens = (userTokens * INJECT_BUDGET_PCT) / (100 - INJECT_BUDGET_PCT);
    const maxSystemChars = Math.floor(maxSystemTokens * 4);
    
    // Trim system content to fit budget
    let systemContent = systemMessages[0].content;
    if (systemContent.length > maxSystemChars) {
      systemContent = systemContent.substring(0, maxSystemChars - 3) + "...";
      systemMessages[0] = {
        role: "system",
        content: systemContent
      };
      
      // Recalculate messages array
      messages.splice(0, messages.length - 1, ...systemMessages);
    }
    
    // Recalculate percentage after trimming
    const newSystemTokens = systemMessages.reduce((sum, msg) => sum + (msg.content?.length || 0), 0) / 4;
    const newTotalTokens = userTokens + newSystemTokens;
    const finalInjectedPct = newTotalTokens > 0 ? (newSystemTokens / newTotalTokens) * 100 : 0;
    
    return {
      messages: [
        ...systemMessages,
        { role: "user", content: userMessage }
      ],
      stats: {
        injected_tokens_pct: Math.round(finalInjectedPct * 10) / 10,
        artifacts_used: context ? context.split("•").length - 1 : 0
      }
    };
  }
  
  const stats = {
    injected_tokens_pct: Math.round(injected_tokens_pct * 10) / 10,
    artifacts_used: context ? context.split("•").length - 1 : 0
  };
  
  // Log metrics
  emit("brain_compose", {
    stage: "prompt_built",
    user_id: userId,
    t_ms: Date.now() - t0,
    injected_tokens_pct: stats.injected_tokens_pct,
    artifacts_used: stats.artifacts_used,
    budget_ok: stats.injected_tokens_pct <= INJECT_BUDGET_PCT
  });
  
  return { messages, stats };
}