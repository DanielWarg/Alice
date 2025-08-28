export type ProbeStatus = "UP" | "DOWN";

export class HealthMonitor {
  private url: string;
  private interval: number;
  private timeout: number;
  private lastOk = 0;
  private timer?: any;
  private subs = new Set<(s:ProbeStatus)=>void>();
  constructor(url: string, intervalMs=4000, timeoutMs=7500) {
    this.url = url; this.interval = intervalMs; this.timeout = timeoutMs;
  }
  on(cb:(s:ProbeStatus)=>void){ this.subs.add(cb); return ()=>this.subs.delete(cb); }
  start(){
    const tick = async ()=>{
      try {
        const r = await fetch(this.url, { cache: 'no-store' });
        const j = await r.json();
        if (j.ok) { this.lastOk = Date.now(); this.emit("UP"); }
        else this.check();
      } catch { this.check(); }
    };
    this.timer = setInterval(tick, this.interval); tick();
  }
  stop(){ clearInterval(this.timer); }
  private check(){ const s = (Date.now()-this.lastOk > this.timeout) ? "DOWN":"UP"; this.emit(s); }
  private emit(s:ProbeStatus){ this.subs.forEach(fn=>fn(s)); }
}