"use client";

import React, { useState, useEffect, useRef, createContext, useContext } from "react";

// ═══════════════════════════════════════════════════════════════════════════════
// MODULÄR ALICE HUD - BYGGT FRÅN SCRATCH MED ORIGINAL UI REFERENS
// ═══════════════════════════════════════════════════════════════════════════════

const SAFE_BOOT = true;

// ═══════════════════════════════════════════════════════════════════════════════
// CORE UTILITIES (kopierat från original)
// ═══════════════════════════════════════════════════════════════════════════════

const safeUUID = () => (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `id-${Math.random().toString(36).slice(2)}-${Date.now()}`);
const clampPercent = (v) => Math.max(0, Math.min(100, Number.isFinite(v) ? v : 0));
const formatTime = (s) => { const m = Math.floor(s / 60); const sec = Math.floor(s % 60); return `${m}:${sec.toString().padStart(2,'0')}`; };
const isoWeek = (d) => { const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())); const dayNum = date.getUTCDay() || 7; date.setUTCDate(date.getUTCDate() + 4 - dayNum); const yearStart = new Date(Date.UTC(date.getUTCFullYear(),0,1)); const weekNo = Math.ceil((((date - yearStart) / 86400000) + 1) / 7); return weekNo; };

// ═══════════════════════════════════════════════════════════════════════════════
// ICON SYSTEM (exakt från original)
// ═══════════════════════════════════════════════════════════════════════════════

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

// ═══════════════════════════════════════════════════════════════════════════════
// PRIMITIVE COMPONENTS (exakt kopierade från original) 
// ═══════════════════════════════════════════════════════════════════════════════

const GlowDot = ({ className }) => (
  <span className={`relative inline-block ${className || ""}`}>
    <span className="absolute inset-0 rounded-full blur-[6px] bg-cyan-400/40" />
    <span className="absolute inset-0 rounded-full blur-[14px] bg-cyan-400/20" />
    <span className="relative block h-full w-full rounded-full bg-cyan-300" />
  </span>
);

const Pane = ({ title, children, className, actions }) => (
  <div className={`relative rounded-2xl border border-cyan-500/20 bg-cyan-950/20 p-4 shadow-[0_0_60px_-20px_rgba(34,211,238,.5)] ${className || ""}`}>
    {title && (
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <GlowDot className="h-2 w-2" />
          <h3 className="text-cyan-200/90 text-xs uppercase tracking-widest">{title}</h3>
        </div>
        <div className="flex gap-2 text-cyan-300/70">{actions}</div>
      </div>
    )}
    {children}
    <div className="pointer-events-none absolute inset-0 rounded-2xl ring-1 ring-inset ring-cyan-300/10" />
  </div>
);

const HUDButton = ({ icon, label, onClick }) => (
  <button onClick={onClick} className="rounded-xl border border-cyan-400/30 bg-cyan-900/30 px-3 py-2 text-xs backdrop-blur hover:bg-cyan-400/10">
    <div className="flex items-center gap-2 text-cyan-200">
      {icon}
      <span className="tracking-widest uppercase">{label}</span>
    </div>
  </button>
);

// ═══════════════════════════════════════════════════════════════════════════════
// ERROR BOUNDARY (exakt kopierat från original)
// ═══════════════════════════════════════════════════════════════════════════════

class ErrorBoundary extends React.Component {
  constructor(props) { 
    super(props); 
    this.state = { error: null }; 
  }
  
  static getDerivedStateFromError(error) { 
    return { error }; 
  }
  
  componentDidCatch(error, info) { 
    console.error("HUD crashed:", error, info); 
  }
  
  render() {
    if (this.state.error) {
      const message = String(this.state.error?.message || this.state.error || "Unknown error");
      return (
        <div className="min-h-screen bg-[#030b10] text-cyan-100 p-8">
          <h1 className="text-xl font-semibold text-cyan-200">HUD Error</h1>
          <p className="mt-2 text-cyan-300/80">{message}</p>
          <button 
            className="mt-6 rounded-xl border border-cyan-400/30 px-3 py-1 text-xs hover:bg-cyan-400/10" 
            onClick={() => (location.href = location.href)}
          >
            Ladda om
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// HEADER COMPONENT (modulärt men med original styling)
// ═══════════════════════════════════════════════════════════════════════════════

const Header = ({ onModuleClick }) => {
  const [nowStr, setNowStr] = useState("");
  
  useEffect(() => {
    const tick = () => {
      const d = new Date();
      const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      const date = d.toLocaleDateString('sv-SE', { day: '2-digit', month: 'short', year: 'numeric' });
      const v = isoWeek(d);
      setNowStr(`${time}  |  ${date}  •  v.${v}`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="mx-auto max-w-7xl px-6 pt-2 pb-2">
      <div className="grid grid-cols-3 items-center">
        <div className="flex items-center gap-3 opacity-80">
          <IconWifi className="h-4 w-4" />
          <IconBattery className="h-4 w-4" />
          <IconBell className="h-4 w-4" />
        </div>
        
        <div className="justify-self-center">
          <div className="flex items-center justify-center gap-3 whitespace-nowrap">
            <HUDButton 
              icon={<IconCalendar className="h-4 w-4" />} 
              label="Kalender" 
              onClick={() => onModuleClick("calendar")} 
            />
            <HUDButton 
              icon={<IconMail className="h-4 w-4" />} 
              label="Mail" 
              onClick={() => onModuleClick("mail")} 
            />
            <HUDButton 
              icon={<IconDollar className="h-4 w-4" />} 
              label="Finans" 
              onClick={() => onModuleClick("finance")} 
            />
            <HUDButton 
              icon={<IconAlarm className="h-4 w-4" />} 
              label="Påminnelser" 
              onClick={() => onModuleClick("reminders")} 
            />
            <HUDButton 
              icon={<IconCamera className="h-4 w-4" />} 
              label="Video" 
              onClick={() => onModuleClick("video")} 
            />
          </div>
        </div>
        
        <div className="flex items-center gap-2 justify-self-end text-cyan-300/80">
          <IconClock className="h-4 w-4" />
          <span className="tracking-widest text-xs uppercase">{nowStr}</span>
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// SYSTEM METRICS COMPONENT (modulärt men med original logik)
// ═══════════════════════════════════════════════════════════════════════════════

const SystemMetrics = () => {
  const [cpu, setCpu] = useState(37);
  const [mem, setMem] = useState(52);
  const [net, setNet] = useState(8);

  useEffect(() => {
    const id = setInterval(() => {
      setCpu((v) => clampPercent(v + (Math.random() * 10 - 5)));
      setMem((v) => clampPercent(v + (Math.random() * 6 - 3)));
      setNet((v) => clampPercent(v + (Math.random() * 14 - 7)));
    }, 1100);
    return () => clearInterval(id);
  }, []);

  const Metric = ({ label, value, icon }) => (
    <div className="text-center">
      <div className="flex items-center justify-center gap-2 text-xs text-cyan-300/80">
        {icon} {label}
      </div>
      <div className="text-2xl font-semibold text-cyan-100">{Math.round(value)}%</div>
    </div>
  );

  return (
    <Pane title="System" actions={<IconSettings className="h-4 w-4" />}>
      <div className="grid grid-cols-3 gap-3">
        <Metric label="CPU" value={cpu} icon={<IconCpu className="h-3 w-3" />} />
        <Metric label="MEM" value={mem} icon={<IconDrive className="h-3 w-3" />} />
        <Metric label="NET" value={net} icon={<IconActivity className="h-3 w-3" />} />
      </div>
    </Pane>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN HUD LAYOUT (NY MODULÄR STRUKTUR)
// ═══════════════════════════════════════════════════════════════════════════════

export default function AliceHUD() {
  const [currentModule, setCurrentModule] = useState(null);

  const handleModuleClick = (module) => {
    setCurrentModule(module);
  };

  return (
    <ErrorBoundary>
      <div className="relative min-h-screen w-full overflow-hidden bg-[#030b10] text-cyan-100">
        {/* Background (exakt från original) */}
        <div className="absolute inset-0 -z-10">
          <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-transparent to-blue-900/10" />
        </div>
        <div className="pointer-events-none absolute inset-0 [background:radial-gradient(ellipse_at_top,rgba(13,148,136,.15),transparent_60%),radial-gradient(ellipse_at_bottom,rgba(3,105,161,.12),transparent_60%)]" />
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(#0e7490_1px,transparent_1px),linear-gradient(90deg,#0e7490_1px,transparent_1px)] bg-[size:40px_40px] opacity-10" />
        
        {/* Header */}
        <Header onModuleClick={handleModuleClick} />
        
        {/* Main Content */}
        <main className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-6 pb-36 pt-0 md:grid-cols-12">
          {/* Left Sidebar */}
          <div className="md:col-span-3 space-y-6">
            <SystemMetrics />
            <Pane title="Röst – Auto">
              <div className="relative h-24 w-full overflow-hidden rounded-lg border border-cyan-500/20 bg-cyan-900/20 p-2">
                <div className="absolute inset-x-2 top-1/2 h-px bg-cyan-400/10" />
                <div className="relative flex h-full items-center gap-[2px]">
                  {Array.from({length: 48}, (_, i) => (
                    <div 
                      key={i} 
                      className="flex-1 rounded bg-gradient-to-b from-cyan-300/80 via-cyan-400/40 to-cyan-300/80" 
                      style={{ height: `${Math.max(10, Math.random() * 100)}%` }} 
                    />
                  ))}
                </div>
              </div>
              <div className="mt-2 text-[11px] text-cyan-300/70">
                {SAFE_BOOT ? 'Simulerad ljuddetektering (Safe Boot)' : 'Lyssnar…'}
              </div>
            </Pane>
          </div>
          
          {/* Center - Alice Core */}
          <div className="md:col-span-6 space-y-6">
            <Pane title="Alice Core" className="min-h-[calc(100vh-140px)] flex flex-col">
              <div className="flex justify-center py-6 shrink-0">
                <div className="text-4xl text-cyan-200 text-center">
                  🤖 ALICE CORE
                  <div className="text-sm mt-2 text-cyan-300/70">Modulär design - UI fungerar!</div>
                </div>
              </div>
            </Pane>
          </div>
          
          {/* Right Sidebar */}
          <div className="md:col-span-3 space-y-6">
            <Pane title="Weather" actions={<IconCloudSun className="h-4 w-4" />}>
              <div className="flex items-center gap-4">
                <IconThermometer className="h-10 w-10 text-cyan-300" />
                <div>
                  <div className="text-3xl font-semibold">21°C</div>
                  <div className="text-cyan-300/80 text-sm">Partly cloudy</div>
                </div>
              </div>
            </Pane>
            
            <Pane title="Status">
              <div className="text-green-400 text-sm">
                ✅ Modulär design funkar!<br/>
                ✅ Ikoner rätt storlek<br/>
                ✅ Original styling behållen
              </div>
            </Pane>
          </div>
        </main>
        
        {/* Footer (exakt från original) */}
        <footer className="pointer-events-none absolute inset-x-0 bottom-0 mx-auto max-w-7xl px-6 pb-8">
          <div className="grid grid-cols-5 gap-4 opacity-80">
            {["SYS", "NET", "AUX", "NAV", "CTRL"].map((t, i) => (
              <div key={i} className="relative h-14 overflow-hidden rounded-xl border border-cyan-500/20 bg-cyan-900/10">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(34,211,238,.15),transparent_50%)]" />
                <div className="absolute inset-0 grid place-items-center text-xs tracking-[.35em] text-cyan-200/70">{t}</div>
                <div className="absolute bottom-0 h-[2px] w-full bg-gradient-to-r from-cyan-500/0 via-cyan-500/60 to-cyan-500/0" />
              </div>
            ))}
          </div>
        </footer>
      </div>
    </ErrorBoundary>
  );
}