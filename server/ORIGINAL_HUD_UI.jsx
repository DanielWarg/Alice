"use client";

// Single‑file React HUD. Sandbox-säker, inga externa paket.
// - Ren JS (ingen TS)
// - SAFE_BOOT stänger av röst/video/tunga effekter i sandlådan
// - Ingen MetaMask eller externa ikonbibliotek

import React, { useEffect, useMemo, useRef, useState, useContext, createContext } from "react";

const SAFE_BOOT = true; // håll true i sandlådan

// ────────────────────────────────────────────────────────────────────────────────
// Error boundary + global catcher (FIX för "ErrorBoundary is not defined")
class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error) { return { error }; }
  componentDidCatch(error, info) { console.error("HUD crashed:", error, info); }
  render() {
    if (this.state.error) {
      const message = String(this.state.error?.message || this.state.error || "Unknown error");
      return (
        <div className="min-h-screen bg-[#030b10] text-cyan-100 p-8">
          <h1 className="text-xl font-semibold text-cyan-200">HUD Error</h1>
          <p className="mt-2 text-cyan-300/80">{message}</p>
          <button className="mt-6 rounded-xl border border-cyan-400/30 px-3 py-1 text-xs hover:bg-cyan-400/10" onClick={() => (location.href = location.href)}>Ladda om</button>
        </div>
      );
    }
    return this.props.children;
  }
}
function useGlobalErrorCatcher() {
  const [globalError, setGlobalError] = useState(null);
  useEffect(() => {
    const onError = (e) => setGlobalError(e?.message || "Unhandled error");
    const onRej = (e) => setGlobalError(String(e.reason?.message || e.reason || "Unhandled rejection"));
    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRej);
    return () => { window.removeEventListener("error", onError); window.removeEventListener("unhandledrejection", onRej); };
  }, []);
  return { globalError };
}

// ────────────────────────────────────────────────────────────────────────────────
// Ikoner (inline SVG)
const Svg = (p) => (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" {...p} />);
const IconPlay = (p) => (<Svg {...p}><polygon points="5 3 19 12 5 21 5 3" /></Svg>);
const IconPause = (p) => (<Svg {...p}><rect x="6" y="4" width="4" height="16" /><rect x="14" y="4" width="4" height="16" /></Svg>);
const IconShuffle = (p) => (<Svg {...p}><polyline points="16 3 21 3 21 8" /><line x1="4" y1="20" x2="21" y2="3" /><polyline points="21 16 21 21 16 21" /><line x1="15" y1="15" x2="21" y2="21" /><line x1="4" y1="4" x2="9" y2="9" /></Svg>);
const IconSkipBack = (p) => (<Svg {...p}><polyline points="19 20 9 12 19 4" /><line x1="5" y1="19" x2="5" y2="5" /></Svg>);
const IconSkipForward = (p) => (<Svg {...p}><polyline points="5 4 15 12 5 20" /><line x1="19" y1="5" x2="19" y2="19" /></Svg>);
const IconThermometer = (p) => (<Svg {...p}><path d="M14 14.76V3a2 2 0 0 0-4 0v11.76" /><path d="M8 15a4 4 0 1 0 8 0" /></Svg>);
const IconCloudSun = (p) => (<Svg {...p}><circle cx="7" cy="7" r="3" /><path d="M12 3v2M12 19v2M4.22 4.22 5.64 5.64M18.36 18.36 19.78 19.78M1 12h2M21 12h2" /></Svg>);
const IconCpu = (p) => (<Svg {...p}><rect x="9" y="9" width="6" height="6" /><rect x="4" y="4" width="16" height="16" rx="2" /></Svg>);
const IconDrive = (p) => (<Svg {...p}><rect x="2" y="7" width="20" height="10" rx="2" /><circle cx="6.5" cy="12" r="1" /><circle cx="17.5" cy="12" r="1" /></Svg>);
const IconActivity = (p) => (<Svg {...p}><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></Svg>);
const IconMic = (p) => (<Svg {...p}><rect x="9" y="2" width="6" height="11" rx="3" /><path d="M12 13v6" /></Svg>);
const IconX = (p) => (<Svg {...p}><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></Svg>);
const IconCheck = (p) => (<Svg {...p}><polyline points="20 6 9 17 4 12" /></Svg>);
const IconClock = (p) => (<Svg {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v6h5" /></Svg>);
const IconSettings = (p) => (<Svg {...p}><circle cx="12" cy="12" r="3" /></Svg>);
const IconBell = (p) => (<Svg {...p}><path d="M6 8a6 6 0 1 1 12 0v6H6z" /></Svg>);
const IconSearch = (p) => (<Svg {...p}><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></Svg>);
const IconWifi = (p) => (<Svg {...p}><path d="M2 8c6-5 14-5 20 0" /><path d="M5 12c4-3 10-3 14 0" /><path d="M8.5 15.5c2-1.5 5-1.5 7 0" /><circle cx="12" cy="19" r="1" /></Svg>);
const IconBattery = (p) => (<Svg {...p}><rect x="2" y="7" width="18" height="10" rx="2" /><rect x="20" y="10" width="2" height="4" /></Svg>);
const IconGauge = (p) => (<Svg {...p}><circle cx="12" cy="12" r="9" /><line x1="12" y1="12" x2="18" y2="10" /></Svg>);
const IconCalendar = (p) => (<Svg {...p}><rect x="3" y="4" width="18" height="18" rx="2" /><line x1="3" y1="10" x2="21" y2="10" /></Svg>);
const IconMail = (p) => (<Svg {...p}><rect x="3" y="5" width="18" height="14" rx="2" /><polyline points="3 7 12 13 21 7" /></Svg>);
const IconDollar = (p) => (<Svg {...p}><path d="M12 2v20" /><path d="M17 7a4 4 0 0 0-4-4 4 4 0 1 0 0 8 4 4 0 1 1 0 8 4 4 0 0 1-4-4" /></Svg>);
const IconAlarm = (p) => (<Svg {...p}><circle cx="12" cy="13" r="7" /><path d="M12 10v4l2 2" /><path d="M5 3l3 3M19 3l-3 3" /></Svg>);
const IconCamera = (p) => (<Svg {...p}><rect x="3" y="7" width="18" height="14" rx="2" /><circle cx="12" cy="14" r="4" /></Svg>);

// ────────────────────────────────────────────────────────────────────────────────
// Utils
const safeUUID = () => (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `id-${Math.random().toString(36).slice(2)}-${Date.now()}`);
const clampPercent = (v) => Math.max(0, Math.min(100, Number.isFinite(v) ? v : 0));
const formatTime = (s) => { const m = Math.floor(s / 60); const sec = Math.floor(s % 60); return `${m}:${sec.toString().padStart(2,'0')}`; };
const isoWeek = (d) => { const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())); const dayNum = date.getUTCDay() || 7; date.setUTCDate(date.getUTCDate() + 4 - dayNum); const yearStart = new Date(Date.UTC(date.getUTCFullYear(),0,1)); const weekNo = Math.ceil((((date - yearStart) / 86400000) + 1) / 7); return weekNo; };

// ────────────────────────────────────────────────────────────────────────────────
// HUD primitives
const GlowDot = ({ className }) => (<span className={`relative inline-block ${className || ""}`}><span className="absolute inset-0 rounded-full blur-[6px] bg-cyan-400/40" /><span className="absolute inset-0 rounded-full blur-[14px] bg-cyan-400/20" /><span className="relative block h-full w-full rounded-full bg-cyan-300" /></span>);
const RingGauge = ({ size = 116, value, label, sublabel, icon, showValue = true }) => { const pct = clampPercent(value); const r = size * 0.42; const c = 2 * Math.PI * r; const dash = (pct / 100) * c; return (<div className="relative grid place-items-center" style={{ width: size, height: size }}><svg width={size} height={size} className="-rotate-90"><defs><linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stopColor="#22d3ee" /><stop offset="100%" stopColor="#38bdf8" /></linearGradient><filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4" result="coloredBlur" /><feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs><circle cx={size / 2} cy={size / 2} r={r} stroke="#0ea5b7" strokeOpacity="0.25" strokeWidth={8} fill="none" strokeDasharray={c} /><circle cx={size / 2} cy={size / 2} r={r} stroke="url(#grad)" strokeWidth={8} fill="none" strokeLinecap="round" strokeDasharray={`${dash} ${c - dash}`} style={{ transition: "stroke-dasharray .6s ease" }} filter="url(#glow)" /></svg><div className="absolute inset-0 grid place-items-center"><div className="text-center">{(label || sublabel || showValue) && (<><div className="flex items-center justify-center gap-2 text-cyan-300">{icon}{label && <span className="text-xs uppercase tracking-widest opacity-80">{label}</span>}</div>{showValue && (<div className="text-4xl font-semibold text-cyan-100">{Math.round(pct)}<span className="text-cyan-400 text-xl">%</span></div>)}{sublabel && <div className="text-xs text-cyan-300/80 mt-1">{sublabel}</div>}</>)}</div></div></div>); };
function useAutoSize(min = 70, max = 96, pad = 8) { const ref = useRef(null); const [size, setSize] = useState(min); useEffect(() => { if (!ref.current || typeof ResizeObserver === 'undefined') return; const ro = new ResizeObserver((entries) => { for (const e of entries) { const w = Math.max(0, e.contentRect.width - pad); const s = Math.max(min, Math.min(max, Math.floor(w))); setSize(s); } }); ro.observe(ref.current); return () => ro.disconnect(); }, [min, max, pad]); return { ref, size }; }
const AutoRing = ({ value, icon }) => { const { ref, size } = useAutoSize(70, 96, 10); return (<div ref={ref} className="w-full max-w-[96px] min-w-[70px] aspect-square flex items-center justify-center mx-auto"><RingGauge size={size} value={value} icon={icon} showValue={false} /></div>); };
const Metric = ({ label, value, icon }) => (<div className="text-center"><div className="flex items-center justify-center gap-2 text-xs text-cyan-300/80">{icon} {label}</div><div className="text-2xl font-semibold text-cyan-100">{Math.round(value)}%</div></div>);
const Pane = ({ title, children, className, actions }) => (<div className={`relative rounded-2xl border border-cyan-500/20 bg-cyan-950/20 p-4 shadow-[0_0_60px_-20px_rgba(34,211,238,.5)] ${className || ""}`}>{title && (<div className="flex items-center justify-between mb-3"><div className="flex items-center gap-2"><GlowDot className="h-2 w-2" /><h3 className="text-cyan-200/90 text-xs uppercase tracking-widest">{title}</h3></div><div className="flex gap-2 text-cyan-300/70">{actions}</div></div>)}{children}<div className="pointer-events-none absolute inset-0 rounded-2xl ring-1 ring-inset ring-cyan-300/10" /></div>);

// ────────────────────────────────────────────────────────────────────────────────
// Hooks (simulerad data)
function useSystemMetrics() { const [cpu, setCpu] = useState(37); const [mem, setMem] = useState(52); const [net, setNet] = useState(8); useEffect(() => { const id = setInterval(() => { setCpu((v) => clampPercent(v + (Math.random() * 10 - 5))); setMem((v) => clampPercent(v + (Math.random() * 6 - 3))); setNet((v) => clampPercent(v + (Math.random() * 14 - 7))); }, 1100); return () => clearInterval(id); }, []); return { cpu, mem, net }; }
function useTodos() { const [todos, setTodos] = useState([{ id: safeUUID(), text: "Setup weather API key", done: false }, { id: safeUUID(), text: "Connect voice input", done: false }]); const add = (text) => setTodos((ts) => [{ id: safeUUID(), text, done: false }, ...ts]); const toggle = (id) => setTodos((ts) => ts.map((t) => (t.id === id ? { ...t, done: !t.done } : t))); const remove = (id) => setTodos((ts) => ts.filter((t) => t.id !== id)); return { todos, add, toggle, remove }; }
function useWeatherStub() { const [w, setW] = useState({ temp: 21, desc: "Partly cloudy" }); useEffect(() => { const id = setInterval(() => { setW({ temp: Math.round(18 + Math.random() * 10), desc: ["Sunny", "Cloudy", "Partly cloudy", "Light rain"][Math.floor(Math.random() * 4)] }); }, 5000); return () => clearInterval(id); }, []); return w; }
function useVoiceInput() { if (SAFE_BOOT) { return { transcript: "", isListening: true, start: () => {}, stop: () => {} }; } const [transcript, setTranscript] = useState(""); const [isListening, setIsListening] = useState(true); const recRef = useRef(null); useEffect(() => { const SR = typeof window !== 'undefined' && (window.webkitSpeechRecognition || window.SpeechRecognition); if (!SR) return; const rec = new SR(); rec.lang = "sv-SE"; rec.continuous = true; rec.interimResults = true; rec.onresult = (e) => { const text = Array.from(e.results).map((r) => r[0].transcript).join(" "); setTranscript(text); }; rec.onend = () => { setIsListening(false); try { rec.start(); setIsListening(true);} catch(_){} }; rec.start(); recRef.current = rec; return () => rec && rec.stop(); }, []); const start = () => { try { recRef.current && recRef.current.start(); setIsListening(true); } catch (_) {} }; const stop = () => recRef.current && recRef.current.stop(); return { transcript, isListening, start, stop }; }
function useAudioWaveBars(count = 48) { const [bars, setBars] = useState(Array.from({length: count},()=>0.2)); const phaseRef = useRef(Math.random()*Math.PI*2); useEffect(()=>{ const id = setInterval(()=>{ phaseRef.current += 0.22; const phase = phaseRef.current; setBars(prev => prev.map((v,i)=>{ const t = (i/(count-1)); const center = Math.abs(t-0.5); const envelope = 1 - (center*center*1.9); const wave = Math.abs(Math.sin(phase + i*0.32)) * 0.85 + Math.random()*0.12; const target = Math.max(0.06, Math.min(1, wave * envelope)); const alpha = target > v ? 0.6 : 0.22; return v*(1-alpha) + target*alpha; })); }, 60); return ()=> clearInterval(id); }, [count]); return bars; }

// ────────────────────────────────────────────────────────────────────────────────
// Command Bus / UI‑state
const HUDContext = createContext(null);
function useHUD() { const ctx = useContext(HUDContext); if (!ctx) throw new Error("useHUD must be inside provider"); return ctx; }
function HUDProvider({ children }) { const [state, setState] = useState({ overlayOpen: false, currentModule: null, videoSource: undefined }); const dispatch = (c) => { setState((s) => { switch (c.type) { case "SHOW_MODULE": return { ...s, overlayOpen: true, currentModule: c.module }; case "HIDE_OVERLAY": return { ...s, overlayOpen: false, currentModule: null }; case "TOGGLE_MODULE": return { ...s, overlayOpen: s.currentModule === c.module ? false : true, currentModule: s.currentModule === c.module ? null : c.module }; case "OPEN_VIDEO": return { ...s, overlayOpen: true, currentModule: "video", videoSource: c.source }; default: return s; } }); }; useEffect(() => { if (typeof window === 'undefined') return; window.HUD = { showModule: (m, payload) => dispatch({ type: "SHOW_MODULE", module: m, payload }), hideOverlay: () => dispatch({ type: "HIDE_OVERLAY" }), openVideo: (source) => dispatch({ type: "OPEN_VIDEO", source }), toggle: (m) => dispatch({ type: "TOGGLE_MODULE", module: m }) }; }, []); return <HUDContext.Provider value={{ state, dispatch }}>{children}</HUDContext.Provider>; }

// ────────────────────────────────────────────────────────────────────────────────
// Overlay + moduler
function Overlay() { const { state, dispatch } = useHUD(); if (!state.overlayOpen || !state.currentModule) return null; return (<div className="fixed inset-0 z-50 grid place-items-center pointer-events-none"><div className="pointer-events-auto relative w-[min(90vw,920px)] rounded-2xl border border-cyan-400/30 bg-cyan-950/60 backdrop-blur-xl p-5 shadow-[0_0_80px_-20px_rgba(34,211,238,.6)]"><button onClick={() => dispatch({ type: "HIDE_OVERLAY" })} className="absolute right-3 top-3 rounded-lg border border-cyan-400/30 px-2 py-1 text-xs hover:bg-cyan-400/10">Stäng</button>{state.currentModule === "calendar" && <CalendarView />}{state.currentModule === "mail" && <MailView />}{state.currentModule === "finance" && <FinanceView />}{state.currentModule === "reminders" && <RemindersView />}{state.currentModule === "video" && <VideoView source={state.videoSource} />}</div></div>); }
function CalendarView() { const today = new Date(); const year = today.getFullYear(); const month = today.getMonth(); const firstDay = new Date(year, month, 1).getDay(); const daysInMonth = new Date(year, month + 1, 0).getDate(); const cells = Array.from({ length: (firstDay || 7) - 1 }).map(() => null).concat(Array.from({ length: daysInMonth }, (_, i) => i + 1)); return (<div><div className="mb-3 flex items-center gap-2 text-cyan-200"><IconCalendar className="h-4 w-4" /><h3 className="text-sm uppercase tracking-widest">Kalender – {today.toLocaleString(undefined, { month: "long", year: "numeric" })}</h3></div><div className="grid grid-cols-7 gap-2">{['M','T','O','T','F','L','S'].map((d) => (<div key={d} className="text-[10px] uppercase tracking-widest text-cyan-300/80 text-center">{d}</div>))}{cells.map((d, idx) => (<div key={idx} className={`h-16 rounded-lg border ${d ? 'border-cyan-400/20 bg-cyan-900/20' : 'border-transparent'} p-2 text-cyan-100 text-sm`}>{d || ''}</div>))}</div></div>); }
function MailView() { const mails = [{ id: safeUUID(), from: "Team", subject: "Välkommen till HUD", time: "09:12" }, { id: safeUUID(), from: "Finans", subject: "Veckorapport klar", time: "08:27" }, { id: safeUUID(), from: "Kalender", subject: "Möte 14:00" }]; return (<div><div className="mb-3 flex items-center gap-2 text-cyan-200"><IconMail className="h-4 w-4" /><h3 className="text-sm uppercase tracking-widest">Mail</h3></div><ul className="divide-y divide-cyan-400/10">{mails.map(m => (<li key={m.id} className="py-2"><div className="text-cyan-100 text-sm">{m.subject}</div><div className="text-cyan-300/70 text-xs">{m.from} • {m.time}</div></li>))}</ul></div>); }
const MiniLine = ({ data }) => { const max = Math.max(...data, 1); const pts = data.map((v,i)=> `${(i/(data.length-1))*100},${100-(v/max)*100}`).join(' '); return (<svg viewBox="0 0 100 100" className="h-20 w-full"><polyline points={pts} fill="none" stroke="currentColor" strokeWidth={2} className="text-cyan-300"/></svg>); };
function FinanceView() { const prices = Array.from({length:32},()=> 80+Math.round(Math.random()*40)); return (<div><div className="mb-3 flex items-center gap-2 text-cyan-200"><IconDollar className="h-4 w-4" /><h3 className="text-sm uppercase tracking-widest">Finans</h3></div><div className="rounded-xl border border-cyan-400/20 p-3 text-cyan-100"><div className="text-xs text-cyan-300/80">Demo-kurva (dummy)</div><MiniLine data={prices} /><div className="mt-2 text-xs text-cyan-300/80">Senast: {prices[prices.length-1]}</div></div></div>); }
function RemindersView() { const [items, setItems] = useState([{ id: safeUUID(), text: "Ring Alex 15:00", done: false }]); const [text, setText] = useState(""); return (<div><div className="mb-3 flex items-center gap-2 text-cyan-200"><IconAlarm className="h-4 w-4" /><h3 className="text-sm uppercase tracking-widest">Påminnelser</h3></div><div className="mb-2 flex gap-2"><input value={text} onChange={(e)=>setText(e.target.value)} onKeyDown={(e)=>{ if(e.key==='Enter' && text.trim()){ setItems([{id:safeUUID(), text, done:false}, ...items]); setText(''); } }} placeholder="Lägg till påminnelse…" className="w-full bg-transparent text-sm text-cyan-100 placeholder:text-cyan-300/40 focus:outline-none"/><button onClick={()=>{ if(text.trim()){ setItems([{id:safeUUID(), text, done:false}, ...items]); setText(''); } }} className="rounded-xl border border-cyan-400/30 px-3 py-1 text-xs hover:bg-cyan-400/10">Lägg till</button></div><ul className="space-y-2">{items.map(it=> (<li key={it.id} className="group flex items-center gap-2 rounded-lg border border-cyan-500/10 bg-cyan-900/10 p-2"><button onClick={()=> setItems(items.map(x=> x.id===it.id ? {...x, done:!x.done}:x))} className={`grid h-5 w-5 place-items-center rounded-md border ${it.done? 'border-cyan-300 bg-cyan-300/20':'border-cyan-400/30'}`}>{it.done && <IconCheck className="h-3 w-3"/>}</button><span className={`flex-1 text-sm ${it.done? 'line-through text-cyan-300/50':'text-cyan-100'}`}>{it.text}</span><button onClick={()=> setItems(items.filter(x=> x.id!==it.id))} className="opacity-0 group-hover:opacity-100 transition-opacity"><IconX className="h-4 w-4 text-cyan-300/60"/></button></li>))}</ul></div>); }

// Video / Bakgrund (Safe Boot aware)
function VideoView({ source }) { return (<div><div className="mb-3 flex items-center gap-2 text-cyan-200"><IconCamera className="h-4 w-4" /><h3 className="text-sm uppercase tracking-widest">Video</h3></div><VideoFeed source={source} /></div>); }
function VideoFeed({ source }) { if (SAFE_BOOT) { return (<div className="relative overflow-hidden rounded-xl border border-cyan-400/20 bg-cyan-900/20 p-6 text-cyan-300/80 text-sm">Video inaktiverad i Safe Boot-läge</div>); } const videoRef = useRef(null); const [err, setErr] = useState(null); const [usingWebcam, setUsingWebcam] = useState(false); useEffect(() => { if (typeof navigator === 'undefined' || typeof window === 'undefined') { setErr('Video kräver en webbläsare'); return; } let currentStream = null; async function start() { setErr(null); if (source && source.kind === "remote" && source.url) { if (videoRef.current) { videoRef.current.srcObject = null; videoRef.current.src = source.url; await videoRef.current.play().catch(()=>{}); } setUsingWebcam(false); return; } try { const stream = await (navigator.mediaDevices && navigator.mediaDevices.getUserMedia ? navigator.mediaDevices.getUserMedia({ video: true, audio: false }) : null); if (!stream) throw new Error("Ingen åtkomst till kamera"); currentStream = stream; if (videoRef.current) { videoRef.current.srcObject = stream; await videoRef.current.play().catch(()=>{}); } setUsingWebcam(true); } catch (e) { setErr(e && e.message ? e.message : String(e)); } } start(); return () => { if (currentStream) currentStream.getTracks().forEach(t=>t.stop()); }; }, [source && source.kind, source && source.url]); return (<div className="relative overflow-hidden rounded-xl border border-cyan-400/20 bg-cyan-900/20"><video ref={videoRef} className="w-full aspect-video" playsInline muted /><div className="absolute bottom-0 right-0 m-2 rounded-md border border-cyan-400/30 bg-cyan-900/70 px-2 py-1 text-[10px] text-cyan-200">{usingWebcam? 'Källa: Webbkamera':'Källa: URL'}</div>{err && <div className="p-3 text-xs text-rose-300">{err}</div>}</div>); }
function ThreeBGAdvanced() { if (SAFE_BOOT) { return (<div className="absolute inset-0 -z-10"><div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-transparent to-blue-900/10" /></div>); } const [particles, setParticles] = useState([]); useEffect(() => { const newParticles = Array.from({ length: 30 }, (_, i) => ({ id: i, x: Math.random() * 100, y: Math.random() * 100, z: Math.random() * 100, speed: 0.1 + Math.random() * 0.2, size: 1 + Math.random() * 1.5 })); setParticles(newParticles); const interval = setInterval(() => { setParticles(prev => prev.map(p => ({ ...p, y: p.y >= 100 ? -5 : p.y + p.speed, x: p.x + Math.sin(Date.now() * 0.001 + p.id) * 0.05 }))); }, 50); return () => clearInterval(interval); }, []); return (<div className="absolute inset-0 -z-10"><div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-transparent to-blue-900/10" /><div className="absolute inset-0 overflow-hidden">{particles.map(p => (<div key={p.id} className="absolute rounded-full bg-cyan-400" style={{ left: `${p.x}%`, top: `${p.y}%`, width: `${p.size}px`, height: `${p.size}px`, opacity: 0.1 + (p.z / 100) * 0.2, transform: `scale(${0.5 + (p.z / 100) * 0.5})`, boxShadow: `0 0 ${p.size * 2}px rgba(34, 211, 238, ${0.1 + (p.z / 100) * 0.2})` }} />))}</div></div>); }

// ────────────────────────────────────────────────────────────────────────────────
// Alice Core – minimalistisk pulsvåg + mic-bars
function AliceCore({ aiLevel = 0 }) {
  // Ren pulsvåg från centrum som kan nå ända till 1px-ytterringen.
  // Ingen radar. Ljudliknande radial-bars nära mitten.
  const [t, setT] = React.useState(0);
  const rafRef = React.useRef(null);
  React.useEffect(() => {
    let prev = performance.now();
    const loop = (now) => {
      const dt = (now - prev) / 1000;
      prev = now;
      setT((v) => v + dt);
      rafRef.current = requestAnimationFrame(loop);
    };
    rafRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafRef.current);
  }, []);

  const size = 360;
  const cx = size / 2, cy = size / 2;
  const outerR = 170; // 1px ytterring
  const speak = Math.max(0, Math.min(1, aiLevel));

  // Pulsvågsparametrar
  const baseSpeed = 10; // grundtempo
  const speed = baseSpeed * (0.6 + speak * 1.8); // snabbare vid tal
  const minR = 12;
  const ringThickness = 5 + speak * 4; // tjockare vid tal
  const ringMaxR = outerR - 1 - ringThickness / 2; // så vi inte korsar 1px-ringen
  const span = Math.max(1, ringMaxR - minR);
  const r = minR + ((t * speed) % span);
  const ringAlpha = 0.22 + (1 - (r - minR) / span) * 0.5; // starkare nära centrum

  // Mic-liknande radial-bars kring centrum
  const barsCount = 48;
  const bars = Array.from({ length: barsCount }, (_, i) => {
    const ang = (i / barsCount) * Math.PI * 2;
    const wobble = Math.sin(t * 1.8 + i * 0.45) * 0.5 + 0.5; // 0..1
    const len = 6 + wobble * (16 + speak * 22); // längre vid tal
    const r0 = 26;
    const r1 = r0 + len;
    return {
      x0: cx + Math.cos(ang) * r0,
      y0: cy + Math.sin(ang) * r0,
      x1: cx + Math.cos(ang) * r1,
      y1: cy + Math.sin(ang) * r1,
      o: 0.12 + speak * 0.28
    };
  });

  return (
    <div className="relative w-full">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="mx-auto block [transform:perspective(900px)_rotateX(10deg)]">
        <defs>
          <linearGradient id="aliceStroke2" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#22d3ee"/>
            <stop offset="100%" stopColor="#38bdf8"/>
          </linearGradient>
          <filter id="glow2" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2.5" result="b"/>
            <feMerge>
              <feMergeNode in="b"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* Yttersta 1px-ringen */}
        <circle cx={cx} cy={cy} r={outerR} fill="none" stroke="url(#aliceStroke2)" strokeOpacity="0.9" strokeWidth="1" />

        {/* Mic-liknande radial-bars nära centrum */}
        <g stroke="url(#aliceStroke2)" strokeWidth={1.2} filter="url(#glow2)">
          {bars.map((b, i) => (
            <line key={i} x1={b.x0} y1={b.y0} x2={b.x1} y2={b.y1} strokeOpacity={b.o} />
          ))}
        </g>

        {/* Själva pulsvågs-ringen som expanderar hela vägen ut (utan att överlappa) */}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="url(#aliceStroke2)" strokeWidth={ringThickness} strokeOpacity={ringAlpha} filter="url(#glow2)" />

        {/* Liten ljus kärna i mitten */}
        <circle cx={cx} cy={cy} r={7} fill="#e0f2fe" />
        <circle cx={cx} cy={cy} r={10} fill="none" stroke="#a5f3fc" strokeOpacity="0.45" />
      </svg>
    </div>
  );
}

// Chat-komponenten för Alice (separerad från AliceCore)
function ChatAlice({ className = "", onSpeakLevel }) {
  const [messages, setMessages] = useState([
    { id: safeUUID(), role: 'assistant', text: 'Hej! Jag är Alice. Vad vill du göra?' }
  ]);
  const [input, setInput] = useState("");
  const fakeSpeak = (ms=1600) => {
    if (!onSpeakLevel) return;
    let t = 0; const dt = 80; onSpeakLevel(0.9);
    const id = setInterval(()=>{
      t += dt;
      const phase = (t/200)%Math.PI;
      const level = 0.25 + Math.abs(Math.sin(phase))*0.7;
      onSpeakLevel(level);
      if (t >= ms) { clearInterval(id); onSpeakLevel(0); }
    }, dt);
  };
  const send = () => {
    const text = input.trim(); if (!text) return;
    const user = { id: safeUUID(), role:'user', text };
    setMessages(m => [...m, user]);
    setInput("");
    fakeSpeak(1800);
    const reply = { id: safeUUID(), role:'assistant', text: `Okej — jag loggar: "${text}" (demo).` };
    setTimeout(()=> setMessages(m => [...m, reply]), 500);
  };
  return (
    <div className={`mt-6 rounded-xl border border-cyan-500/20 bg-cyan-900/20 p-3 flex flex-col min-h-[280px] ${className}`}>
      <div className="flex-1 min-h-0 overflow-y-auto space-y-2 pr-1">
        {messages.map(m => (
          <div key={m.id} className={`flex ${m.role==='user'?'justify-end':'justify-start'}`}>
            <div className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${m.role==='user'?'bg-cyan-500/20 text-cyan-100':'bg-cyan-950/40 text-cyan-100 border border-cyan-500/10'}`}>{m.text}</div>
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-2">
        <IconSearch className="h-4 w-4 text-cyan-300/70" />
        <input
          value={input}
          onChange={e=>setInput(e.target.value)}
          onKeyDown={e=> e.key==='Enter' && send()}
          placeholder="Fråga Alice…"
          className="w-full bg-transparent text-cyan-100 placeholder:text-cyan-300/40 focus:outline-none"
        />
        <button onClick={send} className="rounded-xl border border-cyan-400/30 px-3 py-1 text-xs hover:bg-cyan-400/10">Skicka</button>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────────
// Diagnostics → System‑uppstart (progress + status)
function Diagnostics() {
  const steps = [ { id: 'ui', label: 'Init UI' }, { id: 'bus', label: 'Start HUD bus' }, { id: 'data', label: 'Ladda stubbar' }, { id: 'voice', label: 'Init röstmotor' }, { id: 'video', label: 'Init video' }, { id: 'time', label: 'Synka tid' }, ];
  const [done, setDone] = useState(0);
  useEffect(() => { let i = 0; const id = setInterval(()=>{ i++; setDone(Math.min(i, steps.length)); if (i>=steps.length) clearInterval(id); }, 350); return () => clearInterval(id); }, []);
  const pct = Math.floor((done/steps.length)*100);
  return (<Pane title="System start"><div className="relative h-2 w-full overflow-hidden rounded bg-cyan-900/40 ring-1 ring-inset ring-cyan-400/20"><div className="absolute inset-y-0 left-0 bg-gradient-to-r from-cyan-500/50 to-cyan-400/70" style={{ width: `${pct}%` }} /></div><ul className="mt-2 space-y-1 text-xs text-cyan-300/80">{steps.map((s, i)=> (<li key={s.id} className="flex items-center gap-2"><span className={`h-2 w-2 rounded-full ${i<done? 'bg-cyan-300':'bg-cyan-300/30'}`}/><span>{s.label} {i<done && '— OK'}</span></li>))}</ul><div className="mt-2 text-[11px] text-cyan-300/70">{SAFE_BOOT ? 'Safe Boot aktiv' : 'Live‑motorer aktiva'}</div></Pane>);
}

// ────────────────────────────────────────────────────────────────────────────────
// TodoList
function TodoList({ todos, onToggle, onRemove, onAdd }) { const [text, setText] = useState(""); return (<div><div className="mb-3 flex gap-2"><input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && text.trim()) { onAdd(text.trim()); setText(""); } }} placeholder="Lägg till uppgift…" className="w-full bg-transparent text-sm text-cyan-100 placeholder:text-cyan-300/40 focus:outline-none" /><button onClick={() => { if (text.trim()) { onAdd(text.trim()); setText(""); } }} className="rounded-xl border border-cyan-400/30 px-3 py-1 text-xs hover:bg-cyan-400/10">Lägg till</button></div><ul className="space-y-2">{todos.map((t) => (<li key={t.id} className="group flex items-center gap-2 rounded-lg border border-cyan-500/10 bg-cyan-900/10 p-2"><button onClick={() => onToggle(t.id)} className={`grid h-5 w-5 place-items-center rounded-md border ${t.done ? 'border-cyan-300 bg-cyan-300/20' : 'border-cyan-400/30'}`}>{t.done && <IconCheck className="h-3 w-3" />}</button><span className={`flex-1 text-sm ${t.done ? 'line-through text-cyan-300/50' : 'text-cyan-100'}`}>{t.text}</span><button onClick={() => onRemove(t.id)} className="opacity-0 group-hover:opacity-100 transition-opacity"><IconX className="h-4 w-4 text-cyan-300/60" /></button></li>))}</ul></div>); }

// ────────────────────────────────────────────────────────────────────────────────
// Media Player (under To‑do)
function useMediaPlayer() { const playlist = [{ id: safeUUID(), title: 'Ambient Space', artist: 'NOVA', duration: 225 }, { id: safeUUID(), title: 'Blue Nebula', artist: 'Ion Drift', duration: 192 }, { id: safeUUID(), title: 'Cyan Pulse', artist: 'Aurora', duration: 248 }]; const [index, setIndex] = useState(0); const [isPlaying, setIsPlaying] = useState(true); const [shuffle, setShuffle] = useState(false); const [progress, setProgress] = useState(0); useEffect(()=>{ const id = setInterval(()=>{ if (!isPlaying) return; setProgress(p => { const d = playlist[index].duration; if (p + 1 >= d) { next(); return 0; } return p + 1; }); }, 1000); return ()=> clearInterval(id); }, [isPlaying, index]); const play = ()=> setIsPlaying(true); const pause = ()=> setIsPlaying(false); const toggle = ()=> setIsPlaying(s=>!s); const prev = ()=> setIndex(i => (i - 1 + playlist.length) % playlist.length); const next = ()=> setIndex(i => (i + 1) % playlist.length); const toggleShuffle = ()=> setShuffle(s=>!s); useEffect(()=>{ setProgress(0); }, [index]); return { playlist, index, isPlaying, shuffle, progress, play, pause, toggle, prev, next, toggleShuffle }; }
function MediaPane() { const mp = useMediaPlayer(); const track = mp.playlist[mp.index]; const pct = Math.min(100, Math.floor((mp.progress / track.duration) * 100)); return (<Pane title="Media"><div className="text-sm text-cyan-200 mb-2">{track.title} • <span className="text-cyan-300/80">{track.artist}</span></div><div className="relative h-2 w-full overflow-hidden rounded bg-cyan-900/40 ring-1 ring-inset ring-cyan-400/20"><div className="absolute inset-y-0 left-0 bg-gradient-to-r from-cyan-500/50 to-cyan-400/70" style={{ width: `${pct}%` }} /></div><div className="mt-1 text-[11px] text-cyan-300/70">{formatTime(mp.progress)} / {formatTime(track.duration)}</div><div className="mt-4 flex items-center gap-3"><button onClick={mp.prev} className="rounded-full border border-cyan-400/30 p-2 hover:bg-cyan-400/10"><IconSkipBack className="h-4 w-4" /></button><button onClick={mp.toggle} className="rounded-full border border-cyan-400/30 p-3 hover:bg-cyan-400/10">{mp.isPlaying ? <IconPause className="h-5 w-5" /> : <IconPlay className="h-5 w-5" />}</button><button onClick={mp.next} className="rounded-full border border-cyan-400/30 p-2 hover:bg-cyan-400/10"><IconSkipForward className="h-4 w-4" /></button><button onClick={mp.toggleShuffle} className={`ml-2 rounded-full border p-2 hover:bg-cyan-400/10 ${mp.shuffle? 'border-cyan-400/60 bg-cyan-400/10':'border-cyan-400/30'}`}><IconShuffle className="h-4 w-4" /></button></div></Pane>); }

// ────────────────────────────────────────────────────────────────────────────────
// HUD Button (saknades i vissa revisioner)
function HUDButton({ icon, label, onClick }) {
  return (
    <button onClick={onClick} className="rounded-xl border border-cyan-400/30 bg-cyan-900/30 px-3 py-2 text-xs backdrop-blur hover:bg-cyan-400/10">
      <div className="flex items-center gap-2 text-cyan-200">{icon}<span className="tracking-widest uppercase">{label}</span></div>
    </button>
  );
}

// ────────────────────────────────────────────────────────────────────────────────
// Main HUD
export default function JarvisHUD() { return (<ErrorBoundary><HUDProvider><HUDInner /></HUDProvider></ErrorBoundary>); }
function HUDInner() {
  const { cpu, mem, net } = useSystemMetrics();
  const weather = useWeatherStub();
  const { todos, add, toggle, remove } = useTodos();
  const { transcript, isListening } = useVoiceInput();
  const bars = useAudioWaveBars(48);
  const { globalError } = useGlobalErrorCatcher();
  const { dispatch } = useHUD();
  const [aiLevel, setAiLevel] = useState(0);
  useEffect(() => { if (SAFE_BOOT) return; const id = setInterval(() => { if (typeof window !== 'undefined' && Math.random() < 0.07) dispatch({ type: "OPEN_VIDEO", source: { kind: "webcam" } }); }, 4000); return () => clearInterval(id); }, [dispatch]);
  const [nowStr, setNowStr] = useState("");
  useEffect(() => { const tick = () => { const d = new Date(); const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); const date = d.toLocaleDateString('sv-SE', { day: '2-digit', month: 'short', year: 'numeric' }); const v = isoWeek(d); setNowStr(`${time}  |  ${date}  •  v.${v}`); }; tick(); const id = setInterval(tick, 1000); return () => clearInterval(id); }, []);
  return (<div className="relative min-h-screen w-full overflow-hidden bg-[#030b10] text-cyan-100"><ThreeBGAdvanced /><div className="pointer-events-none absolute inset-0 [background:radial-gradient(ellipse_at_top,rgba(13,148,136,.15),transparent_60%),radial-gradient(ellipse_at_bottom,rgba(3,105,161,.12),transparent_60%)]" /><div className="pointer-events-none absolute inset-0 bg-[linear-gradient(#0e7490_1px,transparent_1px),linear-gradient(90deg,#0e7490_1px,transparent_1px)] bg-[size:40px_40px] opacity-10" />
    <div className="mx-auto max-w-7xl px-6 pt-2 pb-2"><div className="grid grid-cols-3 items-center"><div className="flex items-center gap-3 opacity-80"><IconWifi className="h-4 w-4" /><IconBattery className="h-4 w-4" /><IconBell className="h-4 w-4" /></div><div className="justify-self-center"><div className="flex items-center justify-center gap-3 whitespace-nowrap"><HUDButton icon={<IconCalendar className="h-4 w-4" />} label="Kalender" onClick={()=> dispatch({ type: "SHOW_MODULE", module: "calendar" })} /><HUDButton icon={<IconMail className="h-4 w-4" />} label="Mail" onClick={()=> dispatch({ type: "SHOW_MODULE", module: "mail" })} /><HUDButton icon={<IconDollar className="h-4 w-4" />} label="Finans" onClick={()=> dispatch({ type: "SHOW_MODULE", module: "finance" })} /><HUDButton icon={<IconAlarm className="h-4 w-4" />} label="Påminnelser" onClick={()=> dispatch({ type: "SHOW_MODULE", module: "reminders" })} /><HUDButton icon={<IconCamera className="h-4 w-4" />} label="Video" onClick={()=> dispatch({ type: "OPEN_VIDEO", source: { kind: "webcam" } })} /></div></div><div className="flex items-center gap-2 justify-self-end text-cyan-300/80"><IconClock className="h-4 w-4" /><span className="tracking-widest text-xs uppercase">{nowStr}</span></div></div>{globalError && (<div className="mt-3 rounded-xl border border-cyan-500/20 bg-cyan-900/20 p-3 text-xs text-cyan-300/90"><strong>Observerat globalt fel:</strong> {globalError}</div>)}</div>
    <main className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-6 pb-36 pt-0 md:grid-cols-12"><div className="md:col-span-3 space-y-6"><Pane title="System" actions={<IconSettings className="h-4 w-4" />}><div className="grid grid-cols-3 gap-3"><Metric label="CPU" value={cpu} icon={<IconCpu className="h-3 w-3" />} /><Metric label="MEM" value={mem} icon={<IconDrive className="h-3 w-3" />} /><Metric label="NET" value={net} icon={<IconActivity className="h-3 w-3" />} /></div><div className="mt-4 grid grid-cols-3 gap-3"><AutoRing value={cpu} icon={<IconCpu className="h-3 w-3" />} /><AutoRing value={mem} icon={<IconDrive className="h-3 w-3" />} /><AutoRing value={net} icon={<IconGauge className="h-3 w-3" />} /></div></Pane><Pane title="Röst – Auto"><div className="relative h-24 w-full overflow-hidden rounded-lg border border-cyan-500/20 bg-cyan-900/20 p-2"><div className="absolute inset-x-2 top-1/2 h-px bg-cyan-400/10" /><div className="relative flex h-full items-center gap-[2px]">{bars.map((v,i)=> (<div key={i} className="flex-1 rounded bg-gradient-to-b from-cyan-300/80 via-cyan-400/40 to-cyan-300/80" style={{ height: `${Math.max(10, v*100)}%` }} />))}</div></div><div className="mt-2 text-[11px] text-cyan-300/70">{SAFE_BOOT ? 'Simulerad ljuddetektering (Safe Boot)' : (isListening ? 'Lyssnar…' : 'Av')}</div></Pane><Diagnostics /></div>
      <div className="md:col-span-6 space-y-6"><Pane title="Alice Core" className="min-h-[calc(100vh-140px)] flex flex-col"><div className="flex justify-center py-6 shrink-0"><AliceCore aiLevel={aiLevel} /></div><ChatAlice className="mt-4 flex-1" onSpeakLevel={setAiLevel} /></Pane></div>
      <div className="md:col-span-3 space-y-6"><Pane title="Weather" actions={<IconCloudSun className="h-4 w-4" />}><div className="flex items-center gap-4"><IconThermometer className="h-10 w-10 text-cyan-300" /><div><div className="text-3xl font-semibold">{weather.temp}°C</div><div className="text-cyan-300/80 text-sm">{weather.desc}</div></div></div></Pane><Pane title="To‑do"><TodoList todos={todos} onToggle={toggle} onRemove={remove} onAdd={add} /></Pane><MediaPane /></div></main>
      <Overlay />
      <footer className="pointer-events-none absolute inset-x-0 bottom-0 mx-auto max-w-7xl px-6 pb-8"><div className="grid grid-cols-5 gap-4 opacity-80">{["SYS", "NET", "AUX", "NAV", "CTRL"].map((t, i) => (<div key={i} className="relative h-14 overflow-hidden rounded-xl border border-cyan-500/20 bg-cyan-900/10"><div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(34,211,238,.15),transparent_50%)]" /><div className="absolute inset-0 grid place-items-center text-xs tracking-[.35em] text-cyan-200/70">{t}</div><div className="absolute bottom-0 h-[2px] w-full bg-gradient-to-r from-cyan-500/0 via-cyan-500/60 to-cyan-500/0" /></div>))}</div></footer></div>);
}