type State = "IDLE"|"LISTENING"|"REPLYING";
type Source = "PROBE"|"LAPTOP"|"OFFLINE";

export class Orchestrator {
  state: State = "IDLE";
  source: Source = "LAPTOP";
  private subs = new Set<(e:any)=>void>();
  constructor(private probe: any, private laptop: any) {
    probe.on((e:any)=>this.emit({...e, source:"PROBE"}));
    laptop.on((e:any)=>this.emit({...e, source:"LAPTOP"}));
  }
  on(cb:(e:any)=>void){ this.subs.add(cb); return ()=>this.subs.delete(cb); }
  setProbeStatus(s:"UP"|"DOWN"){ const want = s==="UP" ? "PROBE" : "LAPTOP"; if (this.source!==want && this.state!=="REPLYING") this.source = want, this.emit({type:"source",source:this.source}) }
  async toggleMic(){ this.state==="IDLE" ? this.start() : this.stop(); }
  private async start(){ await (this.source==="PROBE"?this.probe:this.laptop).start(); this.state="LISTENING"; this.emit({type:"state",state:this.state}); }
  private async stop(){ await (this.source==="PROBE"?this.probe:this.laptop).stop(); this.state="IDLE"; this.emit({type:"state",state:this.state}); }
  private emit(e:any){ this.subs.forEach(fn=>fn(e)); }
}