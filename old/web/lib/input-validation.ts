/**
 * Input Validation Utilities for Alice APIs
 * Sanitizes and validates all user inputs for security
 */

// Validation error types
export class ValidationError extends Error {
  constructor(public field: string, message: string) {
    super(`Validation error in '${field}': ${message}`);
    this.name = 'ValidationError';
  }
}

// Common validation patterns
const patterns = {
  sessionId: /^[a-zA-Z0-9_-]{8,64}$/,
  requestId: /^[a-zA-Z0-9_-]{8,128}$/,
  locale: /^[a-z]{2}(-[A-Z]{2})?$/,
  toolName: /^[a-zA-Z0-9_.-]{1,50}$/,
  uuid: /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
};

// String sanitization
export function sanitizeString(input: string, maxLength: number = 1000): string {
  if (typeof input !== 'string') {
    throw new ValidationError('input', 'Expected string');
  }
  
  // Remove potentially dangerous characters
  const sanitized = input
    .replace(/[\x00-\x1F\x7F]/g, '') // Control characters
    .replace(/<script[^>]*>.*?<\/script>/gi, '') // Script tags
    .replace(/<[^>]*>/g, '') // HTML tags
    .trim();
    
  if (sanitized.length > maxLength) {
    throw new ValidationError('input', `String too long (max ${maxLength} chars)`);
  }
  
  return sanitized;
}

// Agent request validation
export interface AgentRequestValidation {
  session_id: string;
  request_id?: string;
  user_id?: string;
  locale?: string;
  mode?: 'single' | 'stream';
  allow_tool_calls?: boolean;
  messages: Array<{
    role: 'system' | 'user' | 'assistant' | 'tool';
    content: string | null;
    tool_calls?: any[];
    name?: string;
    tool_call_id?: string;
  }>;
  limits?: {
    max_tokens?: number;
    temperature?: number;
    tool_max_depth?: number;
  };
  timeout_ms?: number;
}

export function validateAgentRequest(data: any): AgentRequestValidation {
  if (!data || typeof data !== 'object') {
    throw new ValidationError('request', 'Request body must be an object');
  }

  // Validate session_id
  if (!data.session_id || typeof data.session_id !== 'string') {
    throw new ValidationError('session_id', 'Required string field');
  }
  if (!patterns.sessionId.test(data.session_id)) {
    throw new ValidationError('session_id', 'Invalid format (8-64 alphanumeric chars)');
  }

  // Validate messages array
  if (!Array.isArray(data.messages) || data.messages.length === 0) {
    throw new ValidationError('messages', 'Required non-empty array');
  }
  if (data.messages.length > 50) {
    throw new ValidationError('messages', 'Too many messages (max 50)');
  }

  // Validate each message
  const validatedMessages = data.messages.map((msg: any, index: number) => {
    if (!msg || typeof msg !== 'object') {
      throw new ValidationError(`messages[${index}]`, 'Must be an object');
    }

    const validRoles = ['system', 'user', 'assistant', 'tool'];
    if (!validRoles.includes(msg.role)) {
      throw new ValidationError(`messages[${index}].role`, `Must be one of: ${validRoles.join(', ')}`);
    }

    if (msg.content !== null && typeof msg.content !== 'string') {
      throw new ValidationError(`messages[${index}].content`, 'Must be string or null');
    }

    if (msg.content && msg.content.length > 4000) {
      throw new ValidationError(`messages[${index}].content`, 'Content too long (max 4000 chars)');
    }

    return {
      role: msg.role,
      content: msg.content ? sanitizeString(msg.content, 4000) : null,
      tool_calls: msg.tool_calls || [],
      name: msg.name ? sanitizeString(msg.name, 100) : undefined,
      tool_call_id: msg.tool_call_id ? sanitizeString(msg.tool_call_id, 100) : undefined
    };
  });

  // Validate optional fields
  const validated: AgentRequestValidation = {
    session_id: data.session_id,
    messages: validatedMessages
  };

  if (data.request_id) {
    if (!patterns.requestId.test(data.request_id)) {
      throw new ValidationError('request_id', 'Invalid format');
    }
    validated.request_id = data.request_id;
  }

  if (data.user_id) {
    validated.user_id = sanitizeString(data.user_id, 100);
  }

  if (data.locale) {
    if (!patterns.locale.test(data.locale)) {
      throw new ValidationError('locale', 'Invalid locale format (e.g., en, sv-SE)');
    }
    validated.locale = data.locale;
  }

  if (data.mode) {
    if (!['single', 'stream'].includes(data.mode)) {
      throw new ValidationError('mode', 'Must be "single" or "stream"');
    }
    validated.mode = data.mode;
  }

  if (typeof data.allow_tool_calls === 'boolean') {
    validated.allow_tool_calls = data.allow_tool_calls;
  }

  if (data.limits && typeof data.limits === 'object') {
    const limits: any = {};
    
    if (data.limits.max_tokens !== undefined) {
      if (typeof data.limits.max_tokens !== 'number' || data.limits.max_tokens < 1 || data.limits.max_tokens > 4000) {
        throw new ValidationError('limits.max_tokens', 'Must be number between 1-4000');
      }
      limits.max_tokens = data.limits.max_tokens;
    }

    if (data.limits.temperature !== undefined) {
      if (typeof data.limits.temperature !== 'number' || data.limits.temperature < 0 || data.limits.temperature > 2) {
        throw new ValidationError('limits.temperature', 'Must be number between 0-2');
      }
      limits.temperature = data.limits.temperature;
    }

    if (data.limits.tool_max_depth !== undefined) {
      if (typeof data.limits.tool_max_depth !== 'number' || data.limits.tool_max_depth < 1 || data.limits.tool_max_depth > 10) {
        throw new ValidationError('limits.tool_max_depth', 'Must be number between 1-10');
      }
      limits.tool_max_depth = data.limits.tool_max_depth;
    }

    validated.limits = limits;
  }

  if (data.timeout_ms !== undefined) {
    if (typeof data.timeout_ms !== 'number' || data.timeout_ms < 1000 || data.timeout_ms > 60000) {
      throw new ValidationError('timeout_ms', 'Must be number between 1000-60000');
    }
    validated.timeout_ms = data.timeout_ms;
  }

  return validated;
}

// Tool parameter validation
export function validateToolParameters(toolName: string, params: any): any {
  if (!patterns.toolName.test(toolName)) {
    throw new ValidationError('toolName', 'Invalid tool name format');
  }

  if (!params || typeof params !== 'object') {
    throw new ValidationError('parameters', 'Tool parameters must be an object');
  }

  // Tool-specific validation
  switch (toolName) {
    case 'timer.set':
    case 'timer_set':
      return validateTimerParams(params);
    
    case 'weather.get':
    case 'weather_get':
      return validateWeatherParams(params);
    
    default:
      // Generic validation for unknown tools
      return sanitizeObject(params);
  }
}

function validateTimerParams(params: any) {
  const validated: any = {};

  if (params.minutes === undefined) {
    throw new ValidationError('minutes', 'Required field');
  }
  if (typeof params.minutes !== 'number' || params.minutes < 0 || params.minutes > 24 * 60) {
    throw new ValidationError('minutes', 'Must be number between 0-1440');
  }
  validated.minutes = params.minutes;

  if (params.seconds !== undefined) {
    if (typeof params.seconds !== 'number' || params.seconds < 0 || params.seconds > 59) {
      throw new ValidationError('seconds', 'Must be number between 0-59');
    }
    validated.seconds = params.seconds;
  }

  if (params.label !== undefined) {
    validated.label = sanitizeString(params.label, 64);
  }

  return validated;
}

function validateWeatherParams(params: any) {
  const validated: any = {};

  if (!params.location) {
    throw new ValidationError('location', 'Required field');
  }
  validated.location = sanitizeString(params.location, 100);

  if (params.units !== undefined) {
    if (!['metric', 'imperial'].includes(params.units)) {
      throw new ValidationError('units', 'Must be "metric" or "imperial"');
    }
    validated.units = params.units;
  }

  if (params.include_forecast !== undefined) {
    if (typeof params.include_forecast !== 'boolean') {
      throw new ValidationError('include_forecast', 'Must be boolean');
    }
    validated.include_forecast = params.include_forecast;
  }

  if (params.days !== undefined) {
    if (typeof params.days !== 'number' || params.days < 1 || params.days > 7) {
      throw new ValidationError('days', 'Must be number between 1-7');
    }
    validated.days = params.days;
  }

  return validated;
}

// Generic object sanitization
function sanitizeObject(obj: any, maxDepth: number = 3): any {
  if (maxDepth <= 0) {
    throw new ValidationError('object', 'Object nesting too deep');
  }

  if (obj === null || typeof obj !== 'object') {
    return obj;
  }

  if (Array.isArray(obj)) {
    if (obj.length > 100) {
      throw new ValidationError('array', 'Array too large (max 100 items)');
    }
    return obj.map(item => sanitizeObject(item, maxDepth - 1));
  }

  const sanitized: any = {};
  let fieldCount = 0;

  for (const [key, value] of Object.entries(obj)) {
    if (fieldCount >= 50) {
      throw new ValidationError('object', 'Too many fields (max 50)');
    }

    const sanitizedKey = sanitizeString(key, 100);
    
    if (typeof value === 'string') {
      sanitized[sanitizedKey] = sanitizeString(value, 1000);
    } else {
      sanitized[sanitizedKey] = sanitizeObject(value, maxDepth - 1);
    }

    fieldCount++;
  }

  return sanitized;
}