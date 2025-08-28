// Browser SpeechRecognition client (samma som nuvarande VoiceBox)
export class LaptopClient {
  private recognition: any = null;
  private subs = new Set<(e:any)=>void>();
  
  on(cb:(e:any)=>void){ this.subs.add(cb); return ()=>this.subs.delete(cb); }
  
  async start(){
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      throw new Error('Browser speech recognition not supported');
    }
    
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    this.recognition = new SpeechRecognition();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = 'sv-SE';
    
    this.recognition.onresult = (event: any) => {
      const result = event.results[event.results.length - 1];
      this.emit({type: result.isFinal ? 'transcript.final' : 'transcript.interim', text: result[0].transcript});
    };
    
    this.recognition.onstart = () => this.emit({type:'sr.start'});
    this.recognition.onend = () => this.emit({type:'sr.end'});
    this.recognition.onerror = (e:any) => this.emit({type:'sr.error', error:e});
    
    this.recognition.start();
  }
  
  async stop(){
    if(this.recognition) {
      this.recognition.stop();
      this.recognition = null;
    }
  }
  
  private emit(e:any){ this.subs.forEach(fn=>fn(e)); }
}