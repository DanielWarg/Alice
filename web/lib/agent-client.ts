/**
 * Agent Client - Interface to /api/agent with toolcalling support
 * Handles conversation flow: ASR.final → agent → tools → TTS.speak
 */

export interface Message {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string | null;
  tool_calls?: ToolCall[];
  name?: string;
  tool_call_id?: string;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

export interface AgentRequest {
  session_id: string;
  request_id?: string;
  user_id?: string;
  locale?: string;
  mode?: 'single' | 'stream';
  allow_tool_calls?: boolean;
  messages: Message[];
  limits?: {
    max_tokens?: number;
    temperature?: number;
    tool_max_depth?: number;
  };
  timeout_ms?: number;
}

export interface AgentResponse {
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

export interface AgentError {
  error: {
    code: string;
    message: string;
    retry_after_ms?: number;
    fallback_action: 'text_only' | 'retry' | 'abort';
  };
}

export interface ToolResult {
  ok: boolean;
  [key: string]: any;
  error?: {
    code: string;
    message: string;
  };
}

export interface AgentMetrics {
  llm_latency_ms: number;
  tool_duration_ms?: number;
  tool_call_count: number;
  tool_error_count: number;
  phase_timestamps: {
    asr_final_ts: number;
    agent_req_ts: number;
    agent_resp_ts: number;
    tts_start_ts?: number;
    tts_end_ts?: number;
  };
}

export class AgentClient {
  private sessionId: string;
  private messages: Message[] = [];
  private toolCallDepth = 0;
  private maxToolDepth = 3;

  constructor(sessionId?: string) {
    this.sessionId = sessionId || `session_${Date.now()}_${Math.random().toString(36).substring(2)}`;
  }

  async processUserMessage(
    userText: string, 
    onThinking?: () => void,
    onToolExecution?: (toolName: string, toolArgs: any) => void,
    onProgress?: (metrics: Partial<AgentMetrics>) => void
  ): Promise<{ text: string; metrics: AgentMetrics }> {
    
    const startTime = Date.now();
    const phaseTimestamps = {
      asr_final_ts: startTime,
      agent_req_ts: 0,
      agent_resp_ts: 0
    };

    // Add user message to conversation
    this.messages.push({
      role: 'user',
      content: userText
    });

    let toolCallCount = 0;
    let toolErrorCount = 0;
    let totalToolDuration = 0;
    this.toolCallDepth = 0;

    try {
      // Initial thinking state
      onThinking?.();

      // Process with agent (potentially multiple rounds for tool calling)
      while (this.toolCallDepth < this.maxToolDepth) {
        phaseTimestamps.agent_req_ts = Date.now();

        const agentRequest: AgentRequest = {
          session_id: this.sessionId,
          request_id: `req_${Date.now()}_${Math.random().toString(36).substring(2)}`,
          locale: 'sv-SE',
          allow_tool_calls: true,
          messages: [...this.messages],
          limits: {
            max_tokens: 300,
            temperature: 0.3,
            tool_max_depth: this.maxToolDepth
          },
          timeout_ms: 20000
        };

        console.log(`🤖 Sending request to agent (attempt ${this.toolCallDepth + 1})`);
        
        const response = await fetch('/api/agent', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(agentRequest)
        });

        phaseTimestamps.agent_resp_ts = Date.now();

        if (!response.ok) {
          // Handle HTTP errors
          const errorData: AgentError = await response.json();
          throw new Error(`Agent error (${response.status}): ${errorData.error.message}`);
        }

        const agentResponse: AgentResponse = await response.json();
        
        // Update metrics
        onProgress?.({
          llm_latency_ms: agentResponse.metrics.llm_latency_ms,
          tool_call_count: toolCallCount,
          tool_error_count: toolErrorCount,
          phase_timestamps: phaseTimestamps
        });

        if (agentResponse.next_action === 'final') {
          // Final response - we're done
          console.log(`💬 Agent final response: "${agentResponse.assistant.content?.substring(0, 50)}..."`);
          
          // Add assistant message to conversation
          this.messages.push({
            role: 'assistant',
            content: agentResponse.assistant.content
          });

          const metrics: AgentMetrics = {
            llm_latency_ms: agentResponse.metrics.llm_latency_ms,
            tool_duration_ms: totalToolDuration > 0 ? totalToolDuration : undefined,
            tool_call_count: toolCallCount,
            tool_error_count: toolErrorCount,
            phase_timestamps: phaseTimestamps
          };

          return {
            text: agentResponse.assistant.content || 'Inga svar från agenten.',
            metrics
          };
        }

        if (agentResponse.next_action === 'tool_call' && agentResponse.assistant.tool_calls) {
          // Execute tool calls
          console.log(`🔧 Executing ${agentResponse.assistant.tool_calls.length} tool calls...`);
          
          // Update UI to show tool execution
          if (agentResponse.assistant.tool_calls.length > 0) {
            const firstTool = agentResponse.assistant.tool_calls[0];
            onToolExecution?.(firstTool.name, firstTool.arguments);
          }

          // Add assistant message with tool calls
          this.messages.push({
            role: 'assistant',
            content: null,
            tool_calls: agentResponse.assistant.tool_calls
          });

          // Execute each tool call
          for (const toolCall of agentResponse.assistant.tool_calls) {
            const toolStart = Date.now();
            toolCallCount++;

            try {
              console.log(`🔧 Executing tool: ${toolCall.name} with args:`, toolCall.arguments);
              
              const toolResult = await this.executeToolCall(toolCall);
              const toolDuration = Date.now() - toolStart;
              totalToolDuration += toolDuration;

              console.log(`✅ Tool ${toolCall.name} completed in ${toolDuration}ms`);
              
              // Add tool result to conversation
              this.messages.push({
                role: 'tool',
                name: toolCall.name,
                tool_call_id: toolCall.id,
                content: JSON.stringify(toolResult)
              });

              onProgress?.({
                tool_duration_ms: totalToolDuration,
                tool_call_count: toolCallCount,
                tool_error_count: toolErrorCount
              });

            } catch (error) {
              const toolDuration = Date.now() - toolStart;
              totalToolDuration += toolDuration;
              toolErrorCount++;

              console.error(`❌ Tool ${toolCall.name} failed in ${toolDuration}ms:`, error);
              
              // Add error result to conversation
              this.messages.push({
                role: 'tool',
                name: toolCall.name,
                tool_call_id: toolCall.id,
                content: JSON.stringify({
                  ok: false,
                  error: {
                    code: 'INTERNAL',
                    message: error instanceof Error ? error.message : 'Unknown tool error'
                  }
                })
              });
            }
          }

          this.toolCallDepth++;
          // Continue loop to get final response
        }
      }

      // If we exit the loop, we hit max tool depth
      throw new Error('Maximalt antal verktygsanrop nåddes');

    } catch (error) {
      console.error('Agent processing error:', error);
      
      const metrics: AgentMetrics = {
        llm_latency_ms: 0,
        tool_duration_ms: totalToolDuration > 0 ? totalToolDuration : undefined,
        tool_call_count: toolCallCount,
        tool_error_count: toolErrorCount + 1, // Count this as tool error
        phase_timestamps: phaseTimestamps
      };

      // Return error as text response
      return {
        text: `Ett fel uppstod: ${error instanceof Error ? error.message : 'Okänt fel'}`,
        metrics
      };
    }
  }

  private async executeToolCall(toolCall: ToolCall): Promise<ToolResult> {
    const endpoint = `/api/tools/${toolCall.name}`;
    
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': `${toolCall.id}_${Date.now()}`
      },
      body: JSON.stringify(toolCall.arguments)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Tool ${toolCall.name} failed: ${response.status} ${errorText}`);
    }

    const result: ToolResult = await response.json();
    
    if (!result.ok && result.error) {
      throw new Error(`Tool ${toolCall.name} error: ${result.error.message}`);
    }

    return result;
  }

  getSessionId(): string {
    return this.sessionId;
  }

  getConversationLength(): number {
    return this.messages.length;
  }

  clearConversation(): void {
    this.messages = [];
    this.toolCallDepth = 0;
  }

  // Get conversation for debugging
  getMessages(): Message[] {
    return [...this.messages];
  }
}