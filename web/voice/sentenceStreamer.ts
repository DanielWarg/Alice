/**
 * FAS 7 - Sentence Streaming (Stub for future implementation)
 * Streams first sentence immediately for faster TTS
 */

export function streamToSentences(
  textStream: AsyncIterable<string>, 
  onSentence: (s: string) => void
) {
  let buf = "";
  
  (async () => {
    for await (const chunk of textStream) {
      buf += chunk;
      
      // Split on sentence endings
      const parts = buf.split(/([.!?]+)\s+/);
      
      for (let i = 0; i < parts.length - 1; i += 2) {
        const sentence = (parts[i] + (parts[i + 1] || "")).trim();
        if (sentence) {
          onSentence(sentence);
        }
      }
      
      // Keep remaining text in buffer
      buf = parts[parts.length - 1] || "";
    }
    
    // Send remaining text as final sentence
    if (buf.trim()) {
      onSentence(buf.trim());
    }
  })().catch(console.error);
}