import { NextResponse } from "next/server";
import { INTAKE_BLOCKED } from "../stop-intake/route";

export async function GET() {
  // Hämta Guardian daemon status
  let guardianStatus = null;
  try {
    const guardianResponse = await fetch("http://127.0.0.1:8787/health", {
      method: "GET",
      signal: AbortSignal.timeout(2000) // 2s timeout
    });
    
    if (guardianResponse.ok) {
      guardianStatus = await guardianResponse.json();
    }
  } catch (error) {
    guardianStatus = { error: "Guardian daemon unreachable" };
  }
  
  // Hämta Ollama status
  let ollamaStatus = null;
  try {
    const ollamaResponse = await fetch("http://localhost:11434/api/tags", {
      method: "GET", 
      signal: AbortSignal.timeout(2000)
    });
    
    if (ollamaResponse.ok) {
      const tags = await ollamaResponse.json();
      ollamaStatus = {
        available: true,
        models: tags.models?.length || 0
      };
    }
  } catch (error) {
    ollamaStatus = { 
      available: false,
      error: "Ollama unreachable" 
    };
  }
  
  // Sammanställ status
  const status = {
    timestamp: new Date().toISOString(),
    alice: {
      intakeBlocked: INTAKE_BLOCKED,
      status: INTAKE_BLOCKED ? "blocked" : "active"
    },
    guardian: guardianStatus,
    ollama: ollamaStatus,
    system: {
      uptime: process.uptime(),
      nodeVersion: process.version,
      platform: process.platform
    }
  };
  
  return NextResponse.json(status);
}