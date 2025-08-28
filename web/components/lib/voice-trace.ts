// Minimal voice-trace stub to avoid import errors
// Real implementation will be added when voice pipeline is integrated

export const trace = {
  start: (name: string) => `${name}_${Date.now()}`,
  ev: (sid: string, event: string, data?: any, level?: string) => {
    console.log(`[${sid}] ${event}:`, data);
  },
  error: (sid: string, event: string, error?: any) => {
    console.error(`[${sid}] ${event}:`, error);
  },
  timeStart: (sid: string, event: string, data?: any) => {
    console.time(`[${sid}] ${event}`);
  },
  timeEnd: (sid: string, event: string, data?: any) => {
    console.timeEnd(`[${sid}] ${event}`);
  }
};