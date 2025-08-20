"use client";
import React, { useState, useEffect } from "react";
import { ErrorBoundary } from "./ErrorBoundary";
import { useSafeBootMode } from "./SafeBootMode";

/**
 * OverlayModules - Calendar, email, task overlays for Alice HUD
 * 
 * Provides overlay modules including:
 * - Calendar view
 * - Email/mail interface
 * - Task management
 * - Financial overview
 * - Reminder system
 * - Video feed integration
 */

// Utility functions
const generateId = () => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `item-${Math.random().toString(36).slice(2)}-${Date.now()}`;
};

// Context for overlay state management
const OverlayContext = React.createContext(null);

export const useOverlay = () => {
  const context = React.useContext(OverlayContext);
  if (!context) {
    throw new Error('useOverlay must be used within OverlayProvider');
  }
  return context;
};

// Overlay Provider
export function OverlayProvider({ children }) {
  const [overlayState, setOverlayState] = useState({
    isOpen: false,
    currentModule: null,
    data: null
  });

  const openModule = (module, data = null) => {
    setOverlayState({
      isOpen: true,
      currentModule: module,
      data
    });
  };

  const closeOverlay = () => {
    setOverlayState({
      isOpen: false,
      currentModule: null,
      data: null
    });
  };

  const toggleModule = (module) => {
    if (overlayState.currentModule === module && overlayState.isOpen) {
      closeOverlay();
    } else {
      openModule(module);
    }
  };

  return (
    <OverlayContext.Provider value={{
      ...overlayState,
      openModule,
      closeOverlay,
      toggleModule
    }}>
      {children}
    </OverlayContext.Provider>
  );
}

// Calendar Module
const CalendarModule = () => {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth();
  
  // Get first day of month and number of days
  const firstDayOfMonth = new Date(year, month, 1);
  const lastDayOfMonth = new Date(year, month + 1, 0);
  const firstDayWeekday = firstDayOfMonth.getDay(); // 0 = Sunday
  const daysInMonth = lastDayOfMonth.getDate();
  
  // Generate calendar grid
  const calendarDays = [];
  
  // Add empty cells for days before month starts
  for (let i = 0; i < firstDayWeekday; i++) {
    calendarDays.push(null);
  }
  
  // Add days of the month
  for (let day = 1; day <= daysInMonth; day++) {
    calendarDays.push(day);
  }

  const monthNames = [
    'Januari', 'Februari', 'Mars', 'April', 'Maj', 'Juni',
    'Juli', 'Augusti', 'September', 'Oktober', 'November', 'December'
  ];

  const dayNames = ['Sön', 'Mån', 'Tis', 'Ons', 'Tor', 'Fre', 'Lör'];

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
          <line x1="16" y1="2" x2="16" y2="6" />
          <line x1="8" y1="2" x2="8" y2="6" />
          <line x1="3" y1="10" x2="21" y2="10" />
        </svg>
        <h2 className="text-xl font-semibold text-cyan-200">
          {monthNames[month]} {year}
        </h2>
      </div>

      <div className="grid grid-cols-7 gap-2 mb-4">
        {dayNames.map((day, index) => (
          <div key={index} className="text-center text-xs font-semibold text-cyan-300/80 p-2">
            {day}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-2">
        {calendarDays.map((day, index) => (
          <div
            key={index}
            className={`
              h-12 rounded-lg border text-center p-2 text-sm
              ${day ? 'border-cyan-400/20 bg-cyan-900/20 text-cyan-100 hover:bg-cyan-400/10 cursor-pointer' : 'border-transparent'}
              ${day === today.getDate() && month === today.getMonth() && year === today.getFullYear() 
                ? 'bg-cyan-500/20 border-cyan-400/50 font-semibold' 
                : ''}
            `}
          >
            {day}
          </div>
        ))}
      </div>
    </div>
  );
};

// Mail Module
const MailModule = () => {
  const [emails] = useState([
    {
      id: generateId(),
      from: 'Alice Team',
      subject: 'Välkommen till nya Alice HUD',
      time: '09:15',
      unread: true,
      preview: 'Upptäck de nya funktionerna i Alice HUD...'
    },
    {
      id: generateId(),
      from: 'System',
      subject: 'Säkerhetsuppdatering installerad',
      time: '08:42',
      unread: false,
      preview: 'Din Alice installation har uppdaterats...'
    },
    {
      id: generateId(),
      from: 'Support',
      subject: 'Tips för att optimera Alice',
      time: 'Igår',
      unread: false,
      preview: 'Lär dig hur du får ut mest av Alice...'
    }
  ]);

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
          <polyline points="22,6 12,13 2,6" />
        </svg>
        <h2 className="text-xl font-semibold text-cyan-200">E-post</h2>
        <div className="ml-auto text-sm text-cyan-300/70">
          {emails.filter(email => email.unread).length} olästa
        </div>
      </div>

      <div className="space-y-3">
        {emails.map(email => (
          <div
            key={email.id}
            className={`
              p-4 rounded-lg border cursor-pointer transition-colors
              ${email.unread 
                ? 'border-cyan-400/30 bg-cyan-900/30 hover:bg-cyan-900/40' 
                : 'border-cyan-400/20 bg-cyan-900/20 hover:bg-cyan-900/30'}
            `}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-3">
                {email.unread && <div className="w-2 h-2 rounded-full bg-cyan-400" />}
                <span className={`font-medium ${email.unread ? 'text-cyan-100' : 'text-cyan-200'}`}>
                  {email.from}
                </span>
              </div>
              <span className="text-xs text-cyan-300/60">{email.time}</span>
            </div>
            <h3 className={`text-sm mb-1 ${email.unread ? 'font-semibold text-cyan-100' : 'text-cyan-200'}`}>
              {email.subject}
            </h3>
            <p className="text-xs text-cyan-300/70 line-clamp-2">
              {email.preview}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

// Task/Todo Module
const TaskModule = () => {
  const [tasks, setTasks] = useState([
    { id: generateId(), text: 'Testa nya Alice HUD', completed: false, priority: 'high' },
    { id: generateId(), text: 'Konfigurera röstkommandos', completed: false, priority: 'medium' },
    { id: generateId(), text: 'Uppdatera systemdokumentation', completed: true, priority: 'low' }
  ]);
  const [newTask, setNewTask] = useState('');

  const addTask = () => {
    if (newTask.trim()) {
      setTasks([
        { id: generateId(), text: newTask.trim(), completed: false, priority: 'medium' },
        ...tasks
      ]);
      setNewTask('');
    }
  };

  const toggleTask = (id) => {
    setTasks(tasks.map(task => 
      task.id === id ? { ...task, completed: !task.completed } : task
    ));
  };

  const removeTask = (id) => {
    setTasks(tasks.filter(task => task.id !== id));
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high': return 'border-red-500/30 bg-red-900/20';
      case 'medium': return 'border-yellow-500/30 bg-yellow-900/20';
      case 'low': return 'border-green-500/30 bg-green-900/20';
      default: return 'border-cyan-500/30 bg-cyan-900/20';
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path d="M9 11l3 3L22 4" />
          <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
        </svg>
        <h2 className="text-xl font-semibold text-cyan-200">Uppgifter</h2>
        <div className="ml-auto text-sm text-cyan-300/70">
          {tasks.filter(task => !task.completed).length} kvar
        </div>
      </div>

      {/* Add new task */}
      <div className="flex gap-3 mb-6">
        <input
          type="text"
          value={newTask}
          onChange={(e) => setNewTask(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && addTask()}
          placeholder="Lägg till ny uppgift..."
          className="flex-1 bg-transparent border border-cyan-400/30 rounded-lg px-3 py-2 text-cyan-100 placeholder-cyan-300/40 focus:outline-none focus:border-cyan-400/60"
        />
        <button
          onClick={addTask}
          disabled={!newTask.trim()}
          className="px-4 py-2 border border-cyan-400/30 rounded-lg text-cyan-200 hover:bg-cyan-400/10 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Lägg till
        </button>
      </div>

      {/* Task list */}
      <div className="space-y-3">
        {tasks.map(task => (
          <div
            key={task.id}
            className={`
              flex items-center gap-3 p-3 rounded-lg border transition-all
              ${getPriorityColor(task.priority)}
              ${task.completed ? 'opacity-60' : ''}
            `}
          >
            <button
              onClick={() => toggleTask(task.id)}
              className={`
                w-5 h-5 rounded border-2 flex items-center justify-center transition-colors
                ${task.completed 
                  ? 'border-green-500 bg-green-500/20' 
                  : 'border-cyan-400/50 hover:border-cyan-400'}
              `}
            >
              {task.completed && (
                <svg className="w-3 h-3 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <polyline points="20,6 9,17 4,12" />
                </svg>
              )}
            </button>
            
            <span className={`flex-1 ${task.completed ? 'line-through text-cyan-300/60' : 'text-cyan-100'}`}>
              {task.text}
            </span>
            
            <div className={`text-xs px-2 py-1 rounded uppercase tracking-wide ${
              task.priority === 'high' ? 'text-red-300 bg-red-900/30' :
              task.priority === 'medium' ? 'text-yellow-300 bg-yellow-900/30' :
              'text-green-300 bg-green-900/30'
            }`}>
              {task.priority}
            </div>
            
            <button
              onClick={() => removeTask(task.id)}
              className="text-cyan-300/60 hover:text-red-400 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M18 6L6 18M6 6L18 18" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

// Finance Module (simplified)
const FinanceModule = () => {
  const [data] = useState({
    balance: 45230,
    change: 2.4,
    investments: [
      { name: 'TSLA', value: 245.50, change: 1.2 },
      { name: 'AAPL', value: 178.32, change: -0.8 },
      { name: 'BTC', value: 43250, change: 4.2 }
    ]
  });

  const generateChart = () => {
    return Array.from({ length: 30 }, (_, i) => 
      80 + Math.sin(i / 5) * 10 + Math.random() * 20
    );
  };

  const chartData = generateChart();
  const maxValue = Math.max(...chartData);
  const minValue = Math.min(...chartData);
  
  const points = chartData.map((value, index) => {
    const x = (index / (chartData.length - 1)) * 100;
    const y = 100 - ((value - minValue) / (maxValue - minValue)) * 100;
    return `${x},${y}`;
  }).join(' ');

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <line x1="12" y1="1" x2="12" y2="23" />
          <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
        </svg>
        <h2 className="text-xl font-semibold text-cyan-200">Finanser</h2>
      </div>

      {/* Balance */}
      <div className="mb-6 p-4 rounded-lg border border-cyan-400/20 bg-cyan-900/20">
        <div className="text-sm text-cyan-300/70 mb-1">Totalt saldo</div>
        <div className="text-2xl font-bold text-cyan-100 mb-1">
          {data.balance.toLocaleString('sv-SE')} SEK
        </div>
        <div className={`text-sm flex items-center gap-1 ${data.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path d={data.change >= 0 ? "M7 14l5-5 5 5" : "M17 10l-5 5-5-5"} />
          </svg>
          {Math.abs(data.change)}%
        </div>
      </div>

      {/* Chart */}
      <div className="mb-6 p-4 rounded-lg border border-cyan-400/20 bg-cyan-900/20">
        <div className="text-sm text-cyan-300/70 mb-3">30-dagars trend</div>
        <div className="h-24">
          <svg viewBox="0 0 100 100" className="w-full h-full">
            <polyline
              points={points}
              fill="none"
              stroke="url(#gradient)"
              strokeWidth="2"
              className="text-cyan-400"
            />
            <defs>
              <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#22d3ee" />
                <stop offset="100%" stopColor="#38bdf8" />
              </linearGradient>
            </defs>
          </svg>
        </div>
      </div>

      {/* Investments */}
      <div className="space-y-3">
        <div className="text-sm font-semibold text-cyan-200">Investeringar</div>
        {data.investments.map(investment => (
          <div key={investment.name} className="flex items-center justify-between p-3 rounded-lg border border-cyan-400/20 bg-cyan-900/20">
            <div>
              <div className="font-semibold text-cyan-100">{investment.name}</div>
              <div className="text-sm text-cyan-300/70">{investment.value}</div>
            </div>
            <div className={`text-sm font-semibold ${investment.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {investment.change >= 0 ? '+' : ''}{investment.change}%
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Video Module
const VideoModule = ({ source }) => {
  const { isCameraDisabled } = useSafeBootMode();
  const videoRef = React.useRef(null);
  const [error, setError] = useState(null);
  const [isActive, setIsActive] = useState(false);

  useEffect(() => {
    if (isCameraDisabled) {
      setError('Kamera är inaktiverad i privacy-läge');
      return;
    }

    const startVideo = async () => {
      try {
        if (source?.url) {
          // Remote video source
          if (videoRef.current) {
            videoRef.current.src = source.url;
          }
        } else {
          // Local webcam
          const stream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: false
          });
          
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
            setIsActive(true);
          }
        }
      } catch (err) {
        setError(`Kunde inte aktivera video: ${err.message}`);
      }
    };

    startVideo();

    return () => {
      if (videoRef.current?.srcObject) {
        const stream = videoRef.current.srcObject;
        if (stream.getTracks) {
          stream.getTracks().forEach(track => track.stop());
        }
      }
    };
  }, [source, isCameraDisabled]);

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path d="M23 7l-7 5 7 5V7z" />
          <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
        </svg>
        <h2 className="text-xl font-semibold text-cyan-200">Video</h2>
      </div>

      <div className="relative overflow-hidden rounded-lg border border-cyan-400/20 bg-cyan-900/20">
        {error ? (
          <div className="aspect-video flex items-center justify-center p-6 text-cyan-300/70">
            {error}
          </div>
        ) : (
          <>
            <video 
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full aspect-video"
            />
            <div className="absolute bottom-2 right-2 px-2 py-1 bg-black/60 rounded text-xs text-cyan-200">
              {isActive ? 'Aktiv' : 'Inaktiv'}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

// Main Overlay Component
export function OverlayModules() {
  const { isOpen, currentModule, closeOverlay, data } = useOverlay();

  if (!isOpen || !currentModule) return null;

  const renderModule = () => {
    switch (currentModule) {
      case 'calendar': return <CalendarModule />;
      case 'mail': return <MailModule />;
      case 'tasks': return <TaskModule />;
      case 'finance': return <FinanceModule />;
      case 'video': return <VideoModule source={data} />;
      default: return <div className="p-6 text-cyan-300">Okänd modul: {currentModule}</div>;
    }
  };

  return (
    <ErrorBoundary componentName="OverlayModules">
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
        <div className="relative w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-2xl border border-cyan-400/30 bg-cyan-950/90 backdrop-blur-xl shadow-2xl">
          {/* Close button */}
          <button
            onClick={closeOverlay}
            className="absolute top-4 right-4 z-10 p-2 rounded-lg border border-cyan-400/30 text-cyan-300 hover:bg-cyan-400/10 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path d="M18 6L6 18M6 6L18 18" />
            </svg>
          </button>

          {/* Module content */}
          <div className="max-h-[90vh] overflow-y-auto">
            {renderModule()}
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}

// Quick access buttons for triggering overlays
export function OverlayTriggers({ className = "" }) {
  const { toggleModule } = useOverlay();

  const triggers = [
    { id: 'calendar', label: 'Kalender', icon: 'calendar' },
    { id: 'mail', label: 'E-post', icon: 'mail' },
    { id: 'tasks', label: 'Uppgifter', icon: 'check' },
    { id: 'finance', label: 'Finans', icon: 'dollar' },
    { id: 'video', label: 'Video', icon: 'camera' }
  ];

  const getIcon = (iconType) => {
    const iconClass = "w-4 h-4";
    switch (iconType) {
      case 'calendar':
        return <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></svg>;
      case 'mail':
        return <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" /><polyline points="22,6 12,13 2,6" /></svg>;
      case 'check':
        return <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M9 11l3 3L22 4" /></svg>;
      case 'dollar':
        return <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24"><line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></svg>;
      case 'camera':
        return <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M23 7l-7 5 7 5V7z" /><rect x="1" y="5" width="15" height="14" rx="2" /></svg>;
      default:
        return null;
    }
  };

  return (
    <div className={`flex gap-3 ${className}`}>
      {triggers.map(trigger => (
        <button
          key={trigger.id}
          onClick={() => toggleModule(trigger.id)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl border border-cyan-400/30 bg-cyan-900/30 text-cyan-200 hover:bg-cyan-400/10 transition-colors backdrop-blur"
        >
          {getIcon(trigger.icon)}
          <span className="text-xs uppercase tracking-widest">{trigger.label}</span>
        </button>
      ))}
    </div>
  );
}

export default OverlayModules;