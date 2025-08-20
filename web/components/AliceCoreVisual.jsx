"use client";
import React, { useState, useEffect, useRef } from "react";
import { ErrorBoundary } from "./ErrorBoundary";
import { useSafeBootMode } from "./SafeBootMode";

/**
 * AliceCoreVisual - Central AI visualization with voice animation
 * 
 * Provides the main visual representation of Alice with:
 * - Animated pulse wave visualization
 * - Voice level animation
 * - Safe boot mode compatibility
 * - Performance optimized rendering
 */

export function AliceCoreVisual({ 
  aiLevel = 0, 
  size = 360,
  className = "",
  onVisualizationUpdate,
  disabled = false
}) {
  const { safeBootEnabled, isWebGLDisabled } = useSafeBootMode();
  const [time, setTime] = useState(0);
  const rafRef = useRef(null);
  const canvasRef = useRef(null);
  const lastTimeRef = useRef(performance.now());

  // Animation loop for smooth rendering
  useEffect(() => {
    if (disabled) return;
    
    const animate = (currentTime) => {
      const deltaTime = (currentTime - lastTimeRef.current) / 1000;
      lastTimeRef.current = currentTime;
      
      setTime(prevTime => prevTime + deltaTime);
      rafRef.current = requestAnimationFrame(animate);
    };
    
    rafRef.current = requestAnimationFrame(animate);
    
    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [disabled]);

  // Clamp AI level to valid range
  const normalizedAiLevel = Math.max(0, Math.min(1, aiLevel));
  
  // Calculate animation parameters
  const cx = size / 2;
  const cy = size / 2;
  const outerRadius = size * 0.47;
  
  // Pulse wave parameters
  const baseSpeed = safeBootEnabled ? 5 : 10; // Slower in safe mode
  const animationSpeed = baseSpeed * (0.6 + normalizedAiLevel * 1.8);
  const minRadius = 12;
  const ringThickness = 5 + normalizedAiLevel * 4;
  const maxRadius = outerRadius - ringThickness / 2;
  const radiusRange = Math.max(1, maxRadius - minRadius);
  const currentRadius = minRadius + ((time * animationSpeed) % radiusRange);
  const ringAlpha = 0.22 + (1 - (currentRadius - minRadius) / radiusRange) * 0.5;

  // Generate radial bars for voice visualization
  const generateRadialBars = () => {
    if (safeBootEnabled) return []; // Simplified in safe mode
    
    const barCount = 48;
    const bars = [];
    
    for (let i = 0; i < barCount; i++) {
      const angle = (i / barCount) * Math.PI * 2;
      const wobble = Math.sin(time * 1.8 + i * 0.45) * 0.5 + 0.5;
      const length = 6 + wobble * (16 + normalizedAiLevel * 22);
      const innerRadius = 26;
      const outerRadius = innerRadius + length;
      
      bars.push({
        x1: cx + Math.cos(angle) * innerRadius,
        y1: cy + Math.sin(angle) * innerRadius,
        x2: cx + Math.cos(angle) * outerRadius,
        y2: cy + Math.sin(angle) * outerRadius,
        opacity: 0.12 + normalizedAiLevel * 0.28
      });
    }
    
    return bars;
  };

  const radialBars = generateRadialBars();

  // Safe boot fallback rendering
  if (safeBootEnabled) {
    return (
      <div className={`relative ${className}`} style={{ width: size, height: size }}>
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="relative">
            {/* Simple static visualization for safe mode */}
            <div className="h-32 w-32 rounded-full border-2 border-cyan-500/30 bg-cyan-950/20">
              <div className="absolute inset-4 rounded-full border border-cyan-400/40">
                <div className="absolute inset-4 rounded-full bg-cyan-400/10">
                  <div className="absolute inset-2 rounded-full bg-cyan-300/20" />
                </div>
              </div>
            </div>
            {/* Safe mode indicator */}
            <div className="absolute -bottom-8 left-1/2 transform -translate-x-1/2">
              <span className="text-xs text-orange-400 bg-orange-950/50 px-2 py-1 rounded">
                Safe Mode
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Full visualization rendering
  return (
    <div className={`relative ${className}`} style={{ width: size, height: size }}>
      <svg 
        width={size} 
        height={size} 
        viewBox={`0 0 ${size} ${size}`} 
        className="mx-auto block transform perspective-900 rotate-x-10"
        style={{ filter: 'drop-shadow(0 0 20px rgba(34, 211, 238, 0.3))' }}
      >
        <defs>
          {/* Gradient definitions */}
          <linearGradient id="aliceStroke" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#22d3ee" />
            <stop offset="100%" stopColor="#38bdf8" />
          </linearGradient>
          
          <radialGradient id="coreGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#e0f2fe" stopOpacity="1" />
            <stop offset="70%" stopColor="#a5f3fc" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#22d3ee" stopOpacity="0.2" />
          </radialGradient>
          
          {/* Glow filter */}
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2.5" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          
          {/* Stronger glow for active states */}
          <filter id="strongGlow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="5" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Outer boundary ring */}
        <circle
          cx={cx}
          cy={cy}
          r={outerRadius}
          fill="none"
          stroke="url(#aliceStroke)"
          strokeOpacity="0.9"
          strokeWidth="1"
        />

        {/* Radial bars for voice visualization */}
        <g stroke="url(#aliceStroke)" strokeWidth="1.2" filter="url(#glow)">
          {radialBars.map((bar, index) => (
            <line
              key={index}
              x1={bar.x1}
              y1={bar.y1}
              x2={bar.x2}
              y2={bar.y2}
              strokeOpacity={bar.opacity}
            />
          ))}
        </g>

        {/* Main pulse wave ring */}
        <circle
          cx={cx}
          cy={cy}
          r={currentRadius}
          fill="none"
          stroke="url(#aliceStroke)"
          strokeWidth={ringThickness}
          strokeOpacity={ringAlpha}
          filter={normalizedAiLevel > 0.5 ? "url(#strongGlow)" : "url(#glow)"}
        />

        {/* Core elements */}
        <circle
          cx={cx}
          cy={cy}
          r={7}
          fill="url(#coreGlow)"
        />
        
        <circle
          cx={cx}
          cy={cy}
          r={10}
          fill="none"
          stroke="#a5f3fc"
          strokeOpacity="0.45"
          strokeWidth="1"
        />
        
        {/* Activity indicator when AI is speaking */}
        {normalizedAiLevel > 0.3 && (
          <circle
            cx={cx}
            cy={cy}
            r={15}
            fill="none"
            stroke="#22d3ee"
            strokeOpacity={0.6}
            strokeWidth="2"
            strokeDasharray="4 4"
            transform={`rotate(${time * 50} ${cx} ${cy})`}
          />
        )}
      </svg>

      {/* Status text */}
      <div className="absolute -bottom-8 left-1/2 transform -translate-x-1/2 text-center">
        <div className="text-sm text-cyan-300/70">
          {normalizedAiLevel > 0.7 ? "Active" : 
           normalizedAiLevel > 0.3 ? "Processing" : 
           "Listening"}
        </div>
      </div>

      {/* Debug info (development only) */}
      {process.env.NODE_ENV === 'development' && (
        <div className="absolute top-2 right-2 text-xs text-cyan-400/50 bg-black/20 p-1 rounded">
          AI: {(normalizedAiLevel * 100).toFixed(0)}%
        </div>
      )}
    </div>
  );
}

/**
 * Wrapper component with error boundary and performance optimization
 */
export function AliceCoreVisualContainer(props) {
  const [isVisible, setIsVisible] = useState(true);
  const containerRef = useRef(null);

  // Intersection observer for performance optimization
  useEffect(() => {
    if (!containerRef.current || typeof IntersectionObserver === 'undefined') {
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting);
      },
      { threshold: 0.1 }
    );

    observer.observe(containerRef.current);
    
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={containerRef} className="w-full flex justify-center">
      <ErrorBoundary componentName="AliceCoreVisual">
        <AliceCoreVisual {...props} disabled={!isVisible} />
      </ErrorBoundary>
    </div>
  );
}

export default AliceCoreVisualContainer;