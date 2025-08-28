'use client'

import React from 'react'

interface AmbientVisualizerProps {
  isActive: boolean
  className?: string
}

export default function AmbientVisualizer({ isActive, className = '' }: AmbientVisualizerProps) {
  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      {/* Central ambient orb */}
      <div className={`
        relative w-24 h-24 rounded-full transition-all duration-1000 ease-out
        ${isActive 
          ? 'bg-gradient-to-r from-cyan-400 to-blue-500 animate-pulse-active shadow-cyan-glow' 
          : 'bg-gradient-to-r from-gray-400 to-gray-600 animate-pulse-idle shadow-gray-glow'
        }
      `}>
        {/* Inner glow */}
        <div className={`
          absolute inset-2 rounded-full opacity-60
          ${isActive 
            ? 'bg-gradient-to-r from-cyan-200 to-blue-300 animate-pulse-inner-active' 
            : 'bg-gradient-to-r from-gray-300 to-gray-500 animate-pulse-inner-idle'
          }
        `} />
        
        {/* Core */}
        <div className={`
          absolute inset-6 rounded-full opacity-80
          ${isActive 
            ? 'bg-white animate-pulse-core-active' 
            : 'bg-gray-200 animate-pulse-core-idle'
          }
        `} />
      </div>

      {/* Ambient rings */}
      <div className={`
        absolute w-32 h-32 rounded-full border opacity-30
        ${isActive 
          ? 'border-cyan-400 animate-ring-active-1' 
          : 'border-gray-400 animate-ring-idle-1'
        }
      `} />
      
      <div className={`
        absolute w-40 h-40 rounded-full border opacity-20
        ${isActive 
          ? 'border-cyan-300 animate-ring-active-2' 
          : 'border-gray-300 animate-ring-idle-2'
        }
      `} />
      
      <div className={`
        absolute w-48 h-48 rounded-full border opacity-10
        ${isActive 
          ? 'border-cyan-200 animate-ring-active-3' 
          : 'border-gray-200 animate-ring-idle-3'
        }
      `} />

      <style jsx>{`
        .shadow-cyan-glow {
          box-shadow: 0 0 30px rgba(6, 182, 212, 0.6), 0 0 60px rgba(6, 182, 212, 0.4);
        }
        .shadow-gray-glow {
          box-shadow: 0 0 20px rgba(107, 114, 128, 0.4), 0 0 40px rgba(107, 114, 128, 0.2);
        }

        @keyframes pulse-active {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.05); opacity: 0.9; }
        }
        
        @keyframes pulse-idle {
          0%, 100% { transform: scale(1); opacity: 0.7; }
          50% { transform: scale(1.02); opacity: 0.8; }
        }
        
        @keyframes pulse-inner-active {
          0%, 100% { opacity: 0.6; transform: scale(1); }
          50% { opacity: 0.8; transform: scale(1.1); }
        }
        
        @keyframes pulse-inner-idle {
          0%, 100% { opacity: 0.4; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.05); }
        }
        
        @keyframes pulse-core-active {
          0%, 100% { opacity: 0.8; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.2); }
        }
        
        @keyframes pulse-core-idle {
          0%, 100% { opacity: 0.6; transform: scale(1); }
          50% { opacity: 0.7; transform: scale(1.1); }
        }
        
        @keyframes ring-active-1 {
          0%, 100% { transform: scale(1); opacity: 0.3; }
          50% { transform: scale(1.1); opacity: 0.5; }
        }
        
        @keyframes ring-active-2 {
          0%, 100% { transform: scale(1); opacity: 0.2; }
          50% { transform: scale(1.08); opacity: 0.4; }
        }
        
        @keyframes ring-active-3 {
          0%, 100% { transform: scale(1); opacity: 0.1; }
          50% { transform: scale(1.06); opacity: 0.3; }
        }
        
        @keyframes ring-idle-1 {
          0%, 100% { transform: scale(1); opacity: 0.2; }
          50% { transform: scale(1.03); opacity: 0.3; }
        }
        
        @keyframes ring-idle-2 {
          0%, 100% { transform: scale(1); opacity: 0.15; }
          50% { transform: scale(1.02); opacity: 0.2; }
        }
        
        @keyframes ring-idle-3 {
          0%, 100% { transform: scale(1); opacity: 0.1; }
          50% { transform: scale(1.01); opacity: 0.15; }
        }
        
        .animate-pulse-active { animation: pulse-active 2s ease-in-out infinite; }
        .animate-pulse-idle { animation: pulse-idle 4s ease-in-out infinite; }
        .animate-pulse-inner-active { animation: pulse-inner-active 2s ease-in-out infinite 0.2s; }
        .animate-pulse-inner-idle { animation: pulse-inner-idle 4s ease-in-out infinite 0.2s; }
        .animate-pulse-core-active { animation: pulse-core-active 2s ease-in-out infinite 0.4s; }
        .animate-pulse-core-idle { animation: pulse-core-idle 4s ease-in-out infinite 0.4s; }
        .animate-ring-active-1 { animation: ring-active-1 3s ease-in-out infinite; }
        .animate-ring-active-2 { animation: ring-active-2 3s ease-in-out infinite 0.5s; }
        .animate-ring-active-3 { animation: ring-active-3 3s ease-in-out infinite 1s; }
        .animate-ring-idle-1 { animation: ring-idle-1 6s ease-in-out infinite; }
        .animate-ring-idle-2 { animation: ring-idle-2 6s ease-in-out infinite 1s; }
        .animate-ring-idle-3 { animation: ring-idle-3 6s ease-in-out infinite 2s; }
      `}</style>
    </div>
  )
}