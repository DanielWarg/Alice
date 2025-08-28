"use client";

import React, { useEffect, useState } from "react";
import { Calendar, Clock, Plus } from 'lucide-react';
import { getJson } from "./lib/http";

type CalEvent = {
  id: string;
  title: string;
  start: string; // ISO
  end?: string;  // ISO
  location?: string;
};

interface CalendarWidgetProps {
  compact?: boolean;
  showCreateButton?: boolean;
  onEventCreate?: (event: CalEvent) => void;
  onEventClick?: (event: CalEvent) => void;
}

export default function CalendarWidget({
  compact = false,
  showCreateButton = true,
  onEventCreate,
  onEventClick
}: CalendarWidgetProps) {
  const [events, setEvents] = useState<CalEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const data = await getJson<{ ok?: boolean; events?: CalEvent[]; error?: string }>(
          "/api/calendar/today",
          { timeoutMs: 6000 }
        );
        if (!alive) return;
        if (data && ("events" in data)) {
          setEvents(data.events || []);
        } else {
          // Om backend inte returnerar {events:[]} – tolerera och visa tomt
          setEvents([]);
        }
      } catch (e: any) {
        if (!alive) return;
        setErr(e?.message || "Misslyckades hämta kalendern.");
        setEvents([]);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  if (compact) {
    return (
      <div className="bg-zinc-900/50 rounded-xl p-4 border border-zinc-700/50 backdrop-blur-sm" data-testid="calendar-widget-compact">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-cyan-400" />
            <span className="text-sm font-medium text-zinc-300" data-testid="calendar-widget-title">Kalender</span>
          </div>
          {showCreateButton && (
            <button 
              className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 transition-colors"
              data-testid="calendar-widget-create-button"
            >
              <Plus className="w-3 h-3" />
            </button>
          )}
        </div>
        
        <div className="space-y-2" data-testid="calendar-widget-events-list">
          {loading && <div className="text-xs text-zinc-500">Laddar kalender...</div>}
          
          {!loading && err && (
            <div className="text-xs text-rose-400">
              Kunde inte hämta kalendern
              <div className="mt-1 text-zinc-600 text-[10px] break-all">{err}</div>
            </div>
          )}

          {!loading && !err && events.length === 0 && (
            <div className="text-xs text-zinc-500" data-testid="calendar-widget-no-events">Inga events idag</div>
          )}

          {!loading && !err && events.length > 0 && (
            <ul className="space-y-1">
              {events.slice(0, 3).map((event) => ( // Visa max 3 i compact mode
                <li 
                  key={event.id}
                  className="flex items-start gap-2 p-2 rounded-lg bg-zinc-800/50 hover:bg-zinc-800/70 transition-colors cursor-pointer"
                  onClick={() => onEventClick?.(event)}
                >
                  <Clock className="w-3 h-3 text-cyan-400 mt-0.5 flex-shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-medium text-zinc-200 truncate">{event.title}</div>
                    <div className="text-[10px] text-zinc-500">
                      {formatTime(event.start)}{event.end ? `–${formatTime(event.end)}` : ""}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-cyan-400/20 p-4 bg-cyan-950/20 text-cyan-100">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-cyan-400" />
          <div className="text-xs text-cyan-300/80 uppercase tracking-widest">
            Dagens kalender
          </div>
        </div>
        {showCreateButton && (
          <button 
            className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 transition-colors"
            onClick={() => onEventCreate?.({ id: 'new', title: '', start: new Date().toISOString() })}
          >
            <Plus className="w-4 h-4" />
          </button>
        )}
      </div>

      {loading && <div className="text-cyan-300/70 text-sm">Laddar...</div>}

      {!loading && err && (
        <div className="text-rose-300 text-sm">
          Kunde inte hämta kalendern.
          <div className="mt-1 opacity-75 text-xs break-all">{err}</div>
          <div className="mt-2 text-cyan-300/80 text-xs">
            Tips: Kontrollera att backend kör på <code>127.0.0.1:8000</code> och att{" "}
            <code>NEXT_PUBLIC_API_BASE</code> är rätt i <code>.env.local</code>.
          </div>
        </div>
      )}

      {!loading && !err && events.length === 0 && (
        <div className="text-cyan-300/70 text-sm">Inga händelser idag.</div>
      )}

      {!loading && !err && events.length > 0 && (
        <ul className="space-y-2">
          {events.map((event) => (
            <li
              key={event.id}
              className="rounded-lg border border-cyan-500/10 bg-cyan-900/10 p-3 hover:bg-cyan-900/20 transition-colors cursor-pointer"
              onClick={() => onEventClick?.(event)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="text-sm font-medium">{event.title}</div>
                  <div className="text-xs text-cyan-300/70 mt-1">
                    <Clock className="w-3 h-3 inline mr-1" />
                    {formatTime(event.start)}{event.end ? `–${formatTime(event.end)}` : ""}{" "}
                    {event.location && (
                      <span className="ml-2">📍 {event.location}</span>
                    )}
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function formatTime(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString('sv-SE', { hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}