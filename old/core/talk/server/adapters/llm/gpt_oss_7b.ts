/**
 * GPT-OSS 7B LLM Adapter
 * Streaming language model with first token ≤300ms
 */

import { EventEmitter } from 'events';
import { spawn, ChildProcess } from 'child_process';

interface LLMConfig {
  model_path: string;
  max_new_tokens: number;
  temperature: number;
  top_p: number;
  system_prompt: string;
  context_length: number;
}

const DEFAULT_LLM_CONFIG: LLMConfig = {
  model_path: 'models/gpt-oss-7b-q4_k_m.gguf',
  max_new_tokens: 40,
  temperature: 0.2,
  top_p: 0.9,
  system_prompt: "Du är Alice, en svensk AI-assistent. Svara i talspråk, max 2 meningar, koncist. Börja tala utan att vänta på skiljetecken.",
  context_length: 2048
};

interface GenerationOptions {
  max_tokens?: number;
  temperature?: number;
  top_p?: number;
  system_prompt?: string;
}

interface LLMResponse {
  type: 'token' | 'first_token' | 'complete' | 'error';
  text?: string;
  timestamp: number;
  token_count?: number;
  generation_time?: number;
}

export class GPTOss7BLLM extends EventEmitter {
  private config: LLMConfig;
  private llamaProcess: ChildProcess | null = null;
  private isGenerating: boolean = false;
  private generationStartTime: number = 0;
  private firstTokenEmitted: boolean = false;
  private tokenCount: number = 0;

  constructor(config: Partial<LLMConfig> = {}) {
    super();
    
    this.config = { ...DEFAULT_LLM_CONFIG, ...config };
    this.initializeLlamaCpp();
  }

  private async initializeLlamaCpp(): Promise<void> {
    try {
      console.log('🧠 Initializing gpt-oss 7B LLM...');
      
      // Check if model file exists
      const fs = require('fs');
      if (!fs.existsSync(this.config.model_path)) {
        throw new Error(`Model file not found: ${this.config.model_path}`);
      }

      // Spawn llama.cpp server process
      this.llamaProcess = spawn('llama-server', [
        '--model', this.config.model_path,
        '--ctx-size', this.config.context_length.toString(),
        '--threads', '8', // Adjust based on CPU cores
        '--port', '11434',
        '--host', '127.0.0.1',
        '--log-format', 'json',
        '--metrics',
        '--parallel', '1', // Single slot for low latency
        '--cont-batching',
        '--flash-attn',
        '--no-mmap' // Load into RAM for faster access
      ]);

      if (!this.llamaProcess.stdout || !this.llamaProcess.stderr) {
        throw new Error('Failed to create llama.cpp server streams');
      }

      // Handle server logs
      this.llamaProcess.stdout.on('data', (data: Buffer) => {
        const lines = data.toString().trim().split('\\n');
        for (const line of lines) {
          if (line.includes('HTTP server listening')) {
            console.log('✅ llama.cpp server ready');
            this.emit('ready');
          }
        }
      });

      this.llamaProcess.stderr.on('data', (data: Buffer) => {
        console.error('🚨 llama.cpp error:', data.toString());
      });

      this.llamaProcess.on('error', (error) => {
        console.error('❌ llama.cpp process error:', error);
        this.emit('error', error);
      });

      this.llamaProcess.on('exit', (code) => {
        console.log(`🔚 llama.cpp server exited with code ${code}`);
        this.llamaProcess = null;
      });

      // Wait for server to be ready
      await this.waitForReady();
      
    } catch (error) {
      console.error('❌ Failed to initialize gpt-oss 7B:', error);
      this.emit('error', error);
    }
  }

  private async waitForReady(): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('llama.cpp server startup timeout'));
      }, 60000); // 60 second timeout

      const onReady = () => {
        clearTimeout(timeout);
        this.off('error', onError);
        resolve();
      };

      const onError = (error: Error) => {
        clearTimeout(timeout);
        this.off('ready', onReady);
        reject(error);
      };

      this.once('ready', onReady);
      this.once('error', onError);
    });
  }

  public async generateStreaming(
    prompt: string,
    options: GenerationOptions = {}
  ): Promise<void> {
    if (this.isGenerating) {
      console.warn('⚠️ LLM generation already in progress, queuing request');
      return;
    }

    try {
      this.isGenerating = true;
      this.generationStartTime = Date.now();
      this.firstTokenEmitted = false;
      this.tokenCount = 0;

      console.log(`🧠 Generating response for: "${prompt.substring(0, 100)}..."`);

      const requestPayload = {
        prompt: this.buildPrompt(prompt, options.system_prompt),
        temperature: options.temperature ?? this.config.temperature,
        top_p: options.top_p ?? this.config.top_p,
        n_predict: options.max_tokens ?? this.config.max_new_tokens,
        stream: true,
        stop: ['\\n\\n', '</s>', '<|im_end|>', 'Human:', 'User:'],
        cache_prompt: true, // Enable KV cache for faster subsequent requests
        slot_id: 0 // Use dedicated slot
      };

      // Make streaming request to llama.cpp server
      const response = await fetch('http://127.0.0.1:11434/completion', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestPayload)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('No response body from llama.cpp server');
      }

      // Process streaming response
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      try {
        while (true) {
          const { value, done } = await reader.read();
          
          if (done) {
            console.log(`✅ LLM generation completed (${this.tokenCount} tokens)`);
            this.finishGeneration();
            break;
          }

          const chunk = decoder.decode(value, { stream: true });
          this.processStreamChunk(chunk);
        }
      } finally {
        reader.releaseLock();
      }

    } catch (error) {
      console.error('❌ LLM generation error:', error);
      this.emit('error', error);
      this.isGenerating = false;
    }
  }

  private buildPrompt(userInput: string, systemPrompt?: string): string {
    const system = systemPrompt || this.config.system_prompt;
    
    // Use ChatML format for gpt-oss models
    return `<|im_start|>system
${system}<|im_end|>
<|im_start|>user
${userInput}<|im_end|>
<|im_start|>assistant
`;
  }

  private processStreamChunk(chunk: string): void {
    const lines = chunk.split('\\n').filter(line => line.trim());
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const jsonStr = line.substring(6).trim();
          if (jsonStr === '[DONE]') {
            this.finishGeneration();
            return;
          }

          const data = JSON.parse(jsonStr);
          
          if (data.content) {
            this.tokenCount++;
            
            // Emit first token event
            if (!this.firstTokenEmitted) {
              const ttft = Date.now() - this.generationStartTime;
              console.log(`⚡ First token in ${ttft}ms`);
              
              this.emit('first_token', data.content);
              this.firstTokenEmitted = true;
            }

            // Emit token delta
            this.emit('delta', data.content);
          }

          // Check for completion
          if (data.stop === true || data.stopped_eos === true) {
            this.finishGeneration();
            return;
          }

        } catch (error) {
          console.error('❌ Error parsing streaming response:', error);
        }
      }
    }
  }

  private finishGeneration(): void {
    if (!this.isGenerating) {
      return;
    }

    const totalTime = Date.now() - this.generationStartTime;
    const tokensPerSecond = this.tokenCount / (totalTime / 1000);

    console.log(`🏁 Generation finished: ${this.tokenCount} tokens in ${totalTime}ms (${tokensPerSecond.toFixed(1)} tok/s)`);

    this.emit('complete');
    this.isGenerating = false;
  }

  public isReady(): boolean {
    return this.llamaProcess !== null && !this.llamaProcess.killed;
  }

  public isGenerating(): boolean {
    return this.isGenerating;
  }

  public async getModelInfo(): Promise<any> {
    try {
      const response = await fetch('http://127.0.0.1:11434/props');
      return await response.json();
    } catch (error) {
      console.error('❌ Error getting model info:', error);
      return null;
    }
  }

  public async getHealth(): Promise<boolean> {
    try {
      const response = await fetch('http://127.0.0.1:11434/health');
      return response.ok;
    } catch (error) {
      return false;
    }
  }

  public cleanup(): void {
    console.log('🧹 Cleaning up gpt-oss 7B LLM');
    
    this.isGenerating = false;
    
    if (this.llamaProcess) {
      this.llamaProcess.kill('SIGTERM');
      
      // Force kill after 5 seconds if not terminated
      setTimeout(() => {
        if (this.llamaProcess && !this.llamaProcess.killed) {
          console.warn('⚠️ Force killing llama.cpp server');
          this.llamaProcess.kill('SIGKILL');
        }
      }, 5000);
      
      this.llamaProcess = null;
    }
    
    this.removeAllListeners();
  }
}