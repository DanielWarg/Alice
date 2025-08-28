// WebSocket client för Pi probe connection
export class ProbeClient {
  private ws: WebSocket | null = null;
  private subs = new Set<(e:any)=>void>();
  private reconnectTimer?: any;
  private url: string;
  
  constructor(url = 'ws://127.0.0.1:8000/ws/voice-gateway') {
    this.url = url;
  }
  
  on(cb:(e:any)=>void){ this.subs.add(cb); return ()=>this.subs.delete(cb); }
  
  async start(){
    if (this.ws) return;
    
    this.ws = new WebSocket(this.url);
    
    this.ws.onopen = () => {
      this.emit({type:'ws.open'});
      // Send hello message
      this.send({type:'hello', client:'browser'});
    };
    
    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'transcript.final') {
          this.emit({type:'transcript.final', text:data.text});
        }
      } catch (e) {
        console.warn('ProbeClient: Invalid JSON:', event.data);
      }
    };
    
    this.ws.onclose = () => {
      this.emit({type:'ws.close'});
      this.ws = null;
      // Auto-reconnect efter 3s
      this.reconnectTimer = setTimeout(() => this.start(), 3000);
    };
    
    this.ws.onerror = (e) => this.emit({type:'ws.error', error:e});
  }
  
  async stop(){
    clearTimeout(this.reconnectTimer);
    if (this.ws) {
      this.send({type:'segment.stop'});
      this.ws.close();
      this.ws = null;
    }
  }
  
  private send(obj: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(obj));
    }
  }
  
  private emit(e:any){ this.subs.forEach(fn=>fn(e)); }
}