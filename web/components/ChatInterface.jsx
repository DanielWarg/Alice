"use client";
import React, { useState, useRef, useEffect } from "react";
import { ErrorBoundary } from "./ErrorBoundary";
import { useSafeBootMode } from "./SafeBootMode";
import { useUIStore } from "../store/uiStore";

/**
 * ChatInterface - Chat conversation component for Alice HUD
 * 
 * Provides conversational interface with:
 * - Message history management
 * - Real-time streaming support
 * - Error handling and recovery
 * - Safe boot compatibility
 */

// Generate safe UUID fallback
const generateId = () => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `msg-${Math.random().toString(36).slice(2)}-${Date.now()}`;
};

export function ChatInterface({
  className = "",
  onSpeakLevel,
  onMessageSent,
  apiEndpoint = "http://localhost:8000/api/chat/stream",
  maxMessages = 50,
  disabled = false
}) {
  const { safeBootEnabled, isExternalAPIsDisabled } = useSafeBootMode();
  const [messages, setMessages] = useState([
    { 
      id: generateId(), 
      role: 'assistant', 
      text: 'Hej! Jag är Alice. Vad kan jag hjälpa dig med?',
      timestamp: Date.now()
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  const [currentStreamId, setCurrentStreamId] = useState(null);
  
  const messagesEndRef = useRef(null);
  const controllerRef = useRef(null);
  const inputRef = useRef(null);
  const retryTimeoutRef = useRef(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  // Focus input on mount
  useEffect(() => {
    if (!disabled && inputRef.current) {
      inputRef.current.focus();
    }
  }, [disabled]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (controllerRef.current) {
        controllerRef.current.abort();
      }
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, []);

  // Simulate speaking animation
  const simulateSpeaking = (duration = 1600) => {
    if (!onSpeakLevel || safeBootEnabled) return;
    
    let elapsedTime = 0;
    const interval = 80;
    
    const animate = () => {
      elapsedTime += interval;
      const progress = elapsedTime / duration;
      const phase = (progress * 4) % Math.PI;
      const level = 0.25 + Math.abs(Math.sin(phase)) * 0.7;
      
      onSpeakLevel(level);
      
      if (elapsedTime < duration) {
        setTimeout(animate, interval);
      } else {
        onSpeakLevel(0);
      }
    };
    
    animate();
  };

  // Add message to chat
  const addMessage = (message) => {
    setMessages(prev => {
      const newMessages = [...prev, message];
      return newMessages.slice(-maxMessages); // Keep only last N messages
    });
  };

  // Update streaming message
  const updateStreamingMessage = (id, text) => {
    setMessages(prev => 
      prev.map(msg => 
        msg.id === id ? { ...msg, text, isStreaming: true } : msg
      )
    );
  };

  // Finalize streaming message
  const finalizeStreamingMessage = (id) => {
    setMessages(prev => 
      prev.map(msg => 
        msg.id === id ? { ...msg, isStreaming: false } : msg
      )
    );
  };

  // Handle message sending
  const sendMessage = async () => {
    const messageText = input.trim();
    if (!messageText || isLoading || disabled) return;

    // Clear previous error
    setError(null);
    
    // Add user message
    const userMessage = {
      id: generateId(),
      role: 'user',
      text: messageText,
      timestamp: Date.now()
    };
    
    addMessage(userMessage);
    setInput("");
    setIsLoading(true);

    // Callback for message sent
    if (onMessageSent) {
      onMessageSent(userMessage);
    }

    // Handle safe boot or offline mode
    if (safeBootEnabled || isExternalAPIsDisabled) {
      handleOfflineResponse(messageText);
      return;
    }

    try {
      await streamResponse(messageText);
    } catch (err) {
      handleError(err);
    }
  };

  // Handle offline/safe boot response
  const handleOfflineResponse = (userText) => {
    simulateSpeaking(1800);
    
    const responses = [
      "Jag körs i säkert läge just nu. Funktionaliteten är begränsad.",
      "Safe Boot-läge är aktivt. Många funktioner är inaktiverade för säkerhets skull.",
      "I säkert läge kan jag bara ge grundläggande svar.",
      "Extern API-åtkomst är inaktiverad i privacy-läge."
    ];
    
    const randomResponse = responses[Math.floor(Math.random() * responses.length)];
    
    setTimeout(() => {
      const assistantMessage = {
        id: generateId(),
        role: 'assistant',
        text: randomResponse,
        timestamp: Date.now(),
        isSafeMode: true
      };
      
      addMessage(assistantMessage);
      setIsLoading(false);
    }, 1200);
  };

  // Stream response from API
  const streamResponse = async (messageText) => {
    // Abort previous request
    if (controllerRef.current) {
      controllerRef.current.abort();
    }
    
    controllerRef.current = new AbortController();
    
    const streamId = generateId();
    setCurrentStreamId(streamId);
    setIsStreaming(true);

    // Add placeholder assistant message
    const assistantMessage = {
      id: streamId,
      role: 'assistant',
      text: '',
      timestamp: Date.now(),
      isStreaming: true
    };
    
    addMessage(assistantMessage);
    simulateSpeaking(2000);

    try {
      const response = await fetch(apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          prompt: messageText, 
          stream: true 
        }),
        signal: controllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is not readable');
      }

      const decoder = new TextDecoder();
      let buffer = '';
      let fullText = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        
        // Process complete lines, keep incomplete line in buffer
        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim();
          if (line.startsWith('data:')) {
            try {
              const jsonData = line.slice(5).trim();
              const event = JSON.parse(jsonData);
              
              if (event.type === 'chunk' && event.text) {
                fullText += event.text;
                updateStreamingMessage(streamId, fullText);
              } else if (event.type === 'final' && event.text) {
                fullText = event.text;
                updateStreamingMessage(streamId, fullText);
              } else if (event.type === 'done') {
                finalizeStreamingMessage(streamId);
                break;
              }
            } catch (parseError) {
              console.warn('Failed to parse SSE data:', parseError);
            }
          }
        }
        
        buffer = lines[lines.length - 1];
      }

    } catch (err) {
      if (err.name !== 'AbortError') {
        throw err;
      }
    } finally {
      setIsStreaming(false);
      setIsLoading(false);
      setCurrentStreamId(null);
    }
  };

  // Handle errors
  const handleError = (err) => {
    console.error('Chat error:', err);
    
    const errorMessage = {
      id: generateId(),
      role: 'assistant',
      text: `Ursäkta, det uppstod ett fel: ${err.message}. Försök igen.`,
      timestamp: Date.now(),
      isError: true
    };
    
    addMessage(errorMessage);
    setError(err.message);
    setIsLoading(false);
    setIsStreaming(false);
  };

  // Retry last message
  const retryLastMessage = () => {
    const lastUserMessage = [...messages].reverse().find(msg => msg.role === 'user');
    if (lastUserMessage) {
      setInput(lastUserMessage.text);
      // Remove error messages
      setMessages(prev => prev.filter(msg => !msg.isError));
      setError(null);
    }
  };

  // Clear chat
  const clearChat = () => {
    if (confirm('Rensa hela chatten?')) {
      setMessages([{
        id: generateId(),
        role: 'assistant',
        text: 'Chat rensad. Vad kan jag hjälpa dig med?',
        timestamp: Date.now()
      }]);
      setError(null);
    }
  };

  // Stop current streaming
  const stopStreaming = () => {
    if (controllerRef.current) {
      controllerRef.current.abort();
    }
    setIsStreaming(false);
    setIsLoading(false);
  };

  // Handle key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Message component
  const Message = ({ message }) => (
    <div className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} mb-3`}>
      <div className={`max-w-[85%] rounded-lg px-4 py-3 text-sm ${
        message.role === 'user'
          ? 'bg-cyan-500/20 text-cyan-100'
          : message.isError
          ? 'bg-red-950/40 text-red-200 border border-red-500/30'
          : message.isSafeMode
          ? 'bg-orange-950/40 text-orange-200 border border-orange-500/30'
          : 'bg-cyan-950/40 text-cyan-100 border border-cyan-500/10'
      }`}>
        {message.text}
        {message.isStreaming && (
          <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
        )}
        {message.isSafeMode && (
          <div className="mt-2 text-xs opacity-70">
            Säkert läge aktivt
          </div>
        )}
      </div>
    </div>
  );

  return (
    <ErrorBoundary componentName="ChatInterface">
      <div className={`flex flex-col min-h-[300px] rounded-xl border border-cyan-500/20 bg-cyan-900/20 backdrop-blur ${className}`}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-cyan-500/20">
          <h3 className="text-sm font-semibold text-cyan-200">Chat med Alice</h3>
          <div className="flex gap-2">
            {isStreaming && (
              <button
                onClick={stopStreaming}
                className="px-3 py-1 text-xs border border-red-400/30 text-red-200 hover:bg-red-400/10 rounded-md"
              >
                Stoppa
              </button>
            )}
            {error && (
              <button
                onClick={retryLastMessage}
                className="px-3 py-1 text-xs border border-yellow-400/30 text-yellow-200 hover:bg-yellow-400/10 rounded-md"
              >
                Försök igen
              </button>
            )}
            <button
              onClick={clearChat}
              className="px-3 py-1 text-xs border border-cyan-400/30 text-cyan-300 hover:bg-cyan-400/10 rounded-md"
            >
              Rensa
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-2">
          {messages.map(message => (
            <Message key={message.id} message={message} />
          ))}
          {isLoading && !isStreaming && (
            <div className="flex justify-start">
              <div className="bg-cyan-950/40 border border-cyan-500/10 rounded-lg px-4 py-3 text-sm text-cyan-300">
                <div className="flex items-center gap-2">
                  <div className="animate-spin h-4 w-4 border-2 border-cyan-400 border-t-transparent rounded-full"></div>
                  Alice tänker...
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-cyan-500/20">
          <div className="flex items-center gap-3">
            <div className="flex-1 relative">
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={disabled ? "Inaktiverad" : safeBootEnabled ? "Säkert läge aktivt..." : "Fråga Alice..."}
                disabled={disabled || isLoading}
                className="w-full bg-transparent text-cyan-100 placeholder:text-cyan-300/40 focus:outline-none disabled:opacity-50"
              />
            </div>
            <button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading || disabled}
              className="rounded-xl border border-cyan-400/30 px-4 py-2 text-sm text-cyan-200 hover:bg-cyan-400/10 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? "Skickar..." : "Skicka"}
            </button>
          </div>
          
          {safeBootEnabled && (
            <div className="mt-2 text-xs text-orange-300/70">
              Chatfunktionaliteten är begränsad i säkert läge
            </div>
          )}
          
          {error && (
            <div className="mt-2 text-xs text-red-300/70">
              Fel: {error}
            </div>
          )}
        </div>
      </div>
    </ErrorBoundary>
  );
}

export default ChatInterface;