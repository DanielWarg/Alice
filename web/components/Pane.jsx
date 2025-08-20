"use client";
import React from 'react';

/**
 * Pane - Core UI component for Alice HUD panels
 * 
 * Provides consistent styling and layout for all HUD sections:
 * - Glowing borders and shadows
 * - Proper backdrop blur effects
 * - Header with glow dots and actions
 * - Responsive design
 */

// GlowDot component for panel headers
export const GlowDot = ({ className = "" }) => (
  <span className={`relative inline-block ${className}`}>
    <span className="absolute inset-0 rounded-full blur-[6px] bg-cyan-400/40" />
    <span className="absolute inset-0 rounded-full blur-[14px] bg-cyan-400/20" />
    <span className="relative block h-full w-full rounded-full bg-cyan-300" />
  </span>
);

// Main Pane component
export const Pane = ({ 
  title, 
  children, 
  className = "", 
  actions, 
  headerClassName = "",
  contentClassName = "" 
}) => {
  return (
    <div className={`
      relative rounded-2xl border border-cyan-500/20 bg-cyan-950/20 p-4 
      shadow-[0_0_60px_-20px_rgba(34,211,238,.5)]
      hud-glow-cyan
      ${className}
    `}>
      {/* Header */}
      {title && (
        <div className={`flex items-center justify-between mb-3 ${headerClassName}`}>
          <div className="flex items-center gap-2">
            <GlowDot className="h-2 w-2" />
            <h3 className="text-cyan-200/90 text-xs uppercase tracking-widest">
              {title}
            </h3>
          </div>
          {actions && (
            <div className="flex gap-2 text-cyan-300/70">
              {actions}
            </div>
          )}
        </div>
      )}
      
      {/* Content */}
      <div className={contentClassName}>
        {children}
      </div>
      
      {/* Inner ring highlight */}
      <div className="pointer-events-none absolute inset-0 rounded-2xl ring-1 ring-inset ring-cyan-300/10" />
    </div>
  );
};

// Ring gauge component for metrics visualization
export const RingGauge = ({ 
  size = 116, 
  value = 0, 
  label, 
  sublabel, 
  icon, 
  showValue = true 
}) => {
  const clampPercent = (v) => Math.max(0, Math.min(100, Number.isFinite(v) ? v : 0));
  const pct = clampPercent(value);
  const r = size * 0.42;
  const c = 2 * Math.PI * r;
  const dash = (pct / 100) * c;

  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#22d3ee" />
            <stop offset="100%" stopColor="#38bdf8" />
          </linearGradient>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <circle 
          cx={size / 2} 
          cy={size / 2} 
          r={r} 
          stroke="#0ea5b7" 
          strokeOpacity="0.25" 
          strokeWidth={8} 
          fill="none" 
          strokeDasharray={c} 
        />
        <circle 
          cx={size / 2} 
          cy={size / 2} 
          r={r} 
          stroke="url(#grad)" 
          strokeWidth={8} 
          fill="none" 
          strokeLinecap="round" 
          strokeDasharray={`${dash} ${c - dash}`} 
          style={{ transition: "stroke-dasharray .6s ease" }} 
          filter="url(#glow)" 
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center">
        <div className="text-center">
          {(label || sublabel || showValue) && (
            <>
              <div className="flex items-center justify-center gap-2 text-cyan-300">
                {icon}
                {label && (
                  <span className="text-xs uppercase tracking-widest opacity-80">
                    {label}
                  </span>
                )}
              </div>
              {showValue && (
                <div className="text-4xl font-semibold text-cyan-100">
                  {Math.round(pct)}
                  <span className="text-cyan-400 text-xl">%</span>
                </div>
              )}
              {sublabel && (
                <div className="text-xs text-cyan-300/80 mt-1">
                  {sublabel}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

// Auto-sizing ring component
export const AutoRing = ({ value, icon, min = 70, max = 96, padding = 10 }) => {
  const [size, setSize] = React.useState(min);
  const ref = React.useRef(null);

  React.useEffect(() => {
    if (!ref.current || typeof ResizeObserver === 'undefined') return;
    
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const width = Math.max(0, entry.contentRect.width - padding);
        const newSize = Math.max(min, Math.min(max, Math.floor(width)));
        setSize(newSize);
      }
    });
    
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, [min, max, padding]);

  return (
    <div 
      ref={ref} 
      className="w-full max-w-[96px] min-w-[70px] aspect-square flex items-center justify-center mx-auto"
    >
      <RingGauge size={size} value={value} icon={icon} showValue={false} />
    </div>
  );
};

// Simple metric display component
export const Metric = ({ label, value, icon }) => (
  <div className="text-center">
    <div className="flex items-center justify-center gap-2 text-xs text-cyan-300/80">
      {icon} {label}
    </div>
    <div className="text-2xl font-semibold text-cyan-100">
      {Math.round(value)}%
    </div>
  </div>
);

export default Pane;