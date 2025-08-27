/**
 * Agent API - Main conversation endpoint with toolcalling support
 * Maps ASR.final → agent processing → TTS.speak(reply)
 */
import { NextRequest, NextResponse } from 'next/server';
import OpenAI from 'openai';
import { withRateLimit } from '@/lib/rate-limiter';
import { validateAgentRequest, ValidationError } from '@/lib/input-validation';
import { agentResponseCache, generateAgentCacheKey } from '@/lib/response-cache';

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

interface Message {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string | null;
  tool_calls?: ToolCall[];
  name?: string;
  tool_call_id?: string;
}

interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

interface AgentRequest {
  session_id: string;
  request_id?: string;
  user_id?: string;
  locale?: string;
  mode?: 'single' | 'stream';
  allow_tool_calls?: boolean;
  tools_capabilities?: any[];
  messages: Message[];
  limits?: {
    max_tokens?: number;
    temperature?: number;
    tool_max_depth?: number;
  };
  timeout_ms?: number;
}

interface AgentResponse {
  session_id: string;
  request_id?: string;
  next_action: 'final' | 'tool_call';
  assistant: {
    content: string | null;
    tool_calls?: ToolCall[];
    speech_hint?: {
      ssml?: string;
      voice_id?: string;
      rate?: number;
      pitch?: number;
    };
  };
  metrics: {
    llm_latency_ms: number;
  };
}

// Available tools configuration
const AVAILABLE_TOOLS = [
  {
    type: "function" as const,
    function: {
      name: "timer_set",
      description: "Starta en timer med specificerad tid",
      parameters: {
        type: "object",
        properties: {
          minutes: {
            type: "integer",
            minimum: 0,
            maximum: 24 * 60,
            description: "Antal minuter"
          },
          seconds: {
            type: "integer",
            minimum: 0,
            maximum: 59,
            default: 0,
            description: "Antal sekunder"
          },
          label: {
            type: "string",
            maxLength: 64,
            description: "Valfri etikett för timern"
          }
        },
        required: ["minutes"]
      }
    }
  },
  {
    type: "function" as const,
    function: {
      name: "weather_get",
      description: "Hämta aktuellt väder och prognos för en plats",
      parameters: {
        type: "object",
        properties: {
          location: {
            type: "string",
            minLength: 2,
            description: "Platsnamn, t.ex. 'Göteborg, SE'"
          },
          units: {
            type: "string",
            enum: ["metric", "imperial"],
            default: "metric",
            description: "Temperaturenheter"
          },
          include_forecast: {
            type: "boolean",
            default: true,
            description: "Inkludera väderprognos"
          },
          days: {
            type: "integer",
            minimum: 1,
            maximum: 7,
            default: 1,
            description: "Antal dagar för prognos"
          }
        },
        required: ["location"]
      }
    }
  }
];

// Map OpenAI function names to actual API endpoints
const TOOL_NAME_MAPPING: Record<string, string> = {
  'timer_set': 'timer.set',
  'weather_get': 'weather.get'
};

export async function POST(request: NextRequest) {
  // Apply rate limiting
  return withRateLimit(request, '/api/agent', async () => {
    return handleAgentRequest(request);
  });
}

async function handleAgentRequest(request: NextRequest) {
  const startTime = Date.now();
  const requestId = `req_${Date.now()}_${Math.random().toString(36).substring(2)}`;
  
  try {
    const rawBody = await request.json();
    
    // Validate and sanitize all input
    let body: AgentRequest;
    try {
      body = validateAgentRequest(rawBody);
    } catch (validationError) {
      if (validationError instanceof ValidationError) {
        return NextResponse.json({
          error: {
            code: 'INVALID_INPUT',
            message: `Validering misslyckades: ${validationError.message}`,
            fallback_action: 'abort'
          }
        }, { status: 400 });
      }
      throw validationError;
    }
    
    // Contract logging (redacted for security)
    console.log(`📋 Agent Request [${requestId}]:`, {
      session_id: body.session_id,
      request_id: requestId,
      message_count: body.messages?.length || 0,
      allow_tools: body.allow_tool_calls !== false,
      last_message_preview: body.messages?.[body.messages.length - 1]?.content?.substring(0, 50) + '...' || 'none'
    });

    // Prepare system message
    const systemMessage = {
      role: 'system' as const,
      content: `Du är Alice, en hjälpsam AI-assistent som talar svenska. Du kan hjälpa till med:
- Väderinformation (weather_get)
- Timers och påminnelser (timer_set)
- Allmänna frågor och konversation

Svara kort och naturligt på svenska. När du använder verktyg, förklara vad du gör.
Dagens datum: ${new Date().toLocaleDateString('sv-SE')}`
    };

    // Prepare messages for OpenAI API
    const messages = [systemMessage, ...body.messages.filter(m => m.role !== 'system')];

    // Check if we should use tools
    const shouldUseTools = body.allow_tool_calls !== false;
    
    // Check cache for simple queries
    const cacheKey = generateAgentCacheKey(body.messages, shouldUseTools);
    if (cacheKey) {
      const cached = agentResponseCache.get(cacheKey);
      if (cached) {
        console.log(`💾 Cache hit for key: ${cacheKey.substring(0, 20)}...`);
        return NextResponse.json({
          ...cached,
          session_id: body.session_id,
          request_id: body.request_id,
          metrics: {
            llm_latency_ms: 5 // Cached response
          }
        });
      }
    }
    
    const openaiRequest: any = {
      model: 'gpt-4o',
      messages: messages,
      max_tokens: body.limits?.max_tokens || 300,
      temperature: body.limits?.temperature || 0.3
    };

    if (shouldUseTools) {
      openaiRequest.tools = AVAILABLE_TOOLS;
      openaiRequest.tool_choice = 'auto';
    }

    // Call OpenAI API
    console.log('🤖 Sending request to OpenAI...');
    const completion = await openai.chat.completions.create(openaiRequest);

    const llmLatency = Date.now() - startTime;
    const choice = completion.choices[0];
    
    if (!choice) {
      throw new Error('No response from OpenAI');
    }

    // Check if response contains tool calls
    if (choice.message.tool_calls && choice.message.tool_calls.length > 0) {
      // Return tool calls for client to execute
      const response: AgentResponse = {
        session_id: body.session_id,
        request_id: body.request_id,
        next_action: 'tool_call',
        assistant: {
          content: null,
          tool_calls: choice.message.tool_calls.map(tc => ({
            id: tc.id,
            name: tc.function.name,
            arguments: JSON.parse(tc.function.arguments)
          }))
        },
        metrics: {
          llm_latency_ms: llmLatency
        }
      };

      // Contract logging for tool_call response
      console.log(`🔧 Agent Response [${requestId}]:`, {
        session_id: body.session_id,
        request_id: requestId,
        next_action: 'tool_call',
        tool_count: choice.message.tool_calls.length,
        tool_names: choice.message.tool_calls.map(tc => tc.function.name),
        llm_latency_ms: llmLatency
      });
      
      return NextResponse.json(response);
    }

    // Return final response
    const response: AgentResponse = {
      session_id: body.session_id,
      request_id: body.request_id,
      next_action: 'final',
      assistant: {
        content: choice.message.content || 'Jag förstod inte riktigt vad du menade.',
        speech_hint: {
          voice_id: 'sv_female_1',
          rate: 1.0,
          pitch: 0
        }
      },
      metrics: {
        llm_latency_ms: llmLatency
      }
    };

    // Cache simple responses for performance
    if (cacheKey && response.next_action === 'final') {
      agentResponseCache.set(cacheKey, {
        next_action: response.next_action,
        assistant: response.assistant
      });
      console.log(`💾 Cached response for key: ${cacheKey.substring(0, 20)}...`);
    }

    // Contract logging for final response
    console.log(`💬 Agent Response [${requestId}]:`, {
      session_id: body.session_id,
      request_id: requestId,
      next_action: 'final',
      content_preview: response.assistant.content?.substring(0, 50) + '...' || 'no content',
      llm_latency_ms: llmLatency
    });
    
    return NextResponse.json(response);

  } catch (error: any) {
    const llmLatency = Date.now() - startTime;
    console.error('❌ Agent error:', error);

    // Handle specific error types
    if (error.code === 'insufficient_quota' || error.status === 429) {
      return NextResponse.json({
        error: {
          code: 'TOO_MANY_REQUESTS',
          message: 'För många förfrågningar. Försök igen senare.',
          retry_after_ms: 5000,
          fallback_action: 'text_only'
        }
      }, { status: 429 });
    }

    if (error.code === 'context_length_exceeded') {
      return NextResponse.json({
        error: {
          code: 'INVALID_INPUT',
          message: 'Konversationen är för lång. Starta om för att fortsätta.',
          fallback_action: 'abort'
        }
      }, { status: 400 });
    }

    // Generic error
    return NextResponse.json({
      error: {
        code: 'INTERNAL',
        message: 'Ett tekniskt fel uppstod. Försök igen.',
        fallback_action: 'retry'
      }
    }, { status: 500 });
  }
}

// Health check endpoint
export async function GET() {
  try {
    // Quick health check - just verify OpenAI client is configured
    if (!process.env.OPENAI_API_KEY) {
      return NextResponse.json({
        status: 'error',
        message: 'OpenAI API key not configured'
      }, { status: 503 });
    }

    return NextResponse.json({
      status: 'ok',
      timestamp: new Date().toISOString(),
      version: '1.0'
    });
  } catch (error) {
    return NextResponse.json({
      status: 'error',
      message: 'Agent service unavailable'
    }, { status: 503 });
  }
}