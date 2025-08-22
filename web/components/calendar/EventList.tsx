'use client'

import React, { useState, useEffect } from 'react'
import { CalendarEvent } from './CalendarWidget'

// Ikoner
const Svg = (p: any) => (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" {...p} />)
const IconClock = (p: any) => (<Svg {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v6h5" /></Svg>)
const IconCalendar = (p: any) => (<Svg {...p}><rect x="3" y="4" width="18" height="18" rx="2" /><line x1="3" y1="10" x2="21" y2="10" /></Svg>)
const IconUsers = (p: any) => (<Svg {...p}><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></Svg>)
const IconAlertCircle = (p: any) => (<Svg {...p}><circle cx="12" cy="12" r="9" /><path d="M12 8v4M12 16v.01" /></Svg>)
const IconCheck = (p: any) => (<Svg {...p}><polyline points="20 6 9 17 4 12" /></Svg>)
const IconChevronRight = (p: any) => (<Svg {...p}><polyline points="9 18 15 12 9 6" /></Svg>)
const IconFilter = (p: any) => (<Svg {...p}><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" /></Svg>)

// GlowDot komponent
const GlowDot = ({ className }: { className?: string }) => (
  <div className={`relative ${className}`}>
    <span className="absolute inset-0 rounded-full blur-[6px] bg-cyan-400/40" />
    <span className="absolute inset-0 rounded-full blur-[14px] bg-cyan-400/20" />
    <span className="relative block h-full w-full rounded-full bg-cyan-300" />
  </div>
)

export interface EventListProps {
  events?: CalendarEvent[]
  onEventClick?: (event: CalendarEvent) => void
  onEventComplete?: (eventId: string) => void
  title?: string
  showFilter?: boolean
  showCompleted?: boolean
  maxItems?: number
  timeRange?: 'today' | 'week' | 'month' | 'all'
  className?: string
  compact?: boolean
}

type EventFilter = 'all' | 'meeting' | 'reminder' | 'task' | 'personal'

export default function EventList({
  events = [],
  onEventClick,
  onEventComplete,
  title = "Kommande händelser",
  showFilter = true,
  showCompleted = false,
  maxItems = 10,
  timeRange = 'week',
  className = "",
  compact = false
}: EventListProps) {
  const [filter, setFilter] = useState<EventFilter>('all')
  const [completedEvents, setCompletedEvents] = useState<Set<string>>(new Set())

  // Filtrera events baserat på tidsperiod
  const getFilteredEventsByTime = (events: CalendarEvent[]) => {
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    
    switch (timeRange) {
      case 'today':
        return events.filter(event => {
          const eventDate = new Date(event.start.getFullYear(), event.start.getMonth(), event.start.getDate())
          return eventDate.getTime() === today.getTime()
        })
      
      case 'week':
        const weekFromNow = new Date(today)
        weekFromNow.setDate(today.getDate() + 7)
        return events.filter(event => event.start >= today && event.start <= weekFromNow)
      
      case 'month':
        const monthFromNow = new Date(today)
        monthFromNow.setMonth(today.getMonth() + 1)
        return events.filter(event => event.start >= today && event.start <= monthFromNow)
      
      case 'all':
      default:
        return events.filter(event => event.start >= today)
    }
  }

  // Filtrera events baserat på typ
  const getFilteredEventsByType = (events: CalendarEvent[]) => {
    if (filter === 'all') return events
    return events.filter(event => event.type === filter)
  }

  // Filtrera bort completed events om showCompleted är false
  const getVisibleEvents = (events: CalendarEvent[]) => {
    if (showCompleted) return events
    return events.filter(event => !completedEvents.has(event.id))
  }

  // Kombinera alla filter
  const filteredEvents = getVisibleEvents(
    getFilteredEventsByType(
      getFilteredEventsByTime(events)
    )
  ).slice(0, maxItems)

  // Sortera events efter starttid
  const sortedEvents = [...filteredEvents].sort((a, b) => a.start.getTime() - b.start.getTime())

  // Få ikon baserat på event-typ
  const getEventIcon = (event: CalendarEvent) => {
    switch (event.type) {
      case 'meeting':
        return <IconUsers className="h-3 w-3" />
      case 'reminder':
        return <IconAlertCircle className="h-3 w-3" />
      case 'task':
        return <IconCheck className="h-3 w-3" />
      case 'personal':
      default:
        return <IconCalendar className="h-3 w-3" />
    }
  }

  // Få färg baserat på event-typ
  const getEventColor = (event: CalendarEvent) => {
    if (event.color) return event.color
    
    switch (event.type) {
      case 'meeting':
        return 'text-blue-400 bg-blue-500/10 border-blue-500/20'
      case 'reminder':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20'
      case 'task':
        return 'text-green-400 bg-green-500/10 border-green-500/20'
      case 'personal':
      default:
        return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20'
    }
  }

  // Formatera tid relativt (svenska)
  const getRelativeTime = (date: Date) => {
    const now = new Date()
    const diff = date.getTime() - now.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))

    if (days > 0) {
      return `om ${days} dag${days > 1 ? 'ar' : ''}`
    } else if (hours > 0) {
      return `om ${hours} timm${hours > 1 ? 'ar' : 'e'}`
    } else if (minutes > 0) {
      return `om ${minutes} min`
    } else if (minutes > -60) {
      return 'pågår'
    } else {
      return 'avslutad'
    }
  }

  // Är eventet idag?
  const isToday = (date: Date) => {
    const today = new Date()
    return date.toDateString() === today.toDateString()
  }

  // Hantera event completion
  const handleComplete = (eventId: string, event: React.MouseEvent) => {
    event.stopPropagation()
    setCompletedEvents(prev => new Set(prev.add(eventId)))
    onEventComplete?.(eventId)
  }

  return (
    <div className={`relative rounded-2xl border border-cyan-500/20 bg-cyan-950/20 p-4 shadow-[0_0_60px_-20px_rgba(34,211,238,.5)] ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <GlowDot className="h-2 w-2" />
          <h3 className="text-cyan-200/90 text-xs uppercase tracking-widest">{title}</h3>
        </div>
        {showFilter && (
          <div className="flex gap-2 text-cyan-300/70">
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as EventFilter)}
              className="text-xs bg-transparent border border-cyan-500/20 rounded px-2 py-1 text-cyan-300 focus:outline-none focus:border-cyan-400/40"
            >
              <option value="all">Alla</option>
              <option value="meeting">Möten</option>
              <option value="reminder">Påminnelser</option>
              <option value="task">Uppgifter</option>
              <option value="personal">Personligt</option>
            </select>
          </div>
        )}
      </div>

      {/* Tidsperiod-indikator */}
      <div className="text-[10px] text-cyan-300/60 uppercase tracking-wider mb-3">
        {timeRange === 'today' && 'Idag'}
        {timeRange === 'week' && 'Denna vecka'}
        {timeRange === 'month' && 'Denna månad'}
        {timeRange === 'all' && 'Alla kommande'}
        {sortedEvents.length > 0 && ` • ${sortedEvents.length} händelser`}
      </div>

      {/* Events-lista */}
      {sortedEvents.length > 0 ? (
        <div className="space-y-2">
          {sortedEvents.map((event) => {
            const isCompleted = completedEvents.has(event.id)
            const colorClasses = getEventColor(event)
            
            return (
              <button
                key={event.id}
                onClick={() => onEventClick?.(event)}
                className={`
                  w-full text-left p-3 rounded-lg transition-all duration-200 group
                  ${isCompleted 
                    ? 'opacity-50 bg-cyan-900/10 border border-cyan-500/10' 
                    : `${colorClasses} hover:bg-opacity-20 border`
                  }
                  ${compact ? 'p-2' : 'p-3'}
                `}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2 flex-1 min-w-0">
                    {/* Ikon och status */}
                    <div className="flex-shrink-0 flex items-center gap-1 mt-0.5">
                      {getEventIcon(event)}
                      {event.type === 'task' && onEventComplete && !isCompleted && (
                        <button
                          onClick={(e) => handleComplete(event.id, e)}
                          className="w-3 h-3 rounded border border-current opacity-60 hover:opacity-100 hover:bg-current/20 transition-all duration-150"
                          title="Markera som klar"
                        />
                      )}
                    </div>

                    {/* Event-info */}
                    <div className="flex-1 min-w-0">
                      <div className={`font-medium text-sm ${isCompleted ? 'line-through' : ''} truncate`}>
                        {event.title}
                      </div>
                      
                      <div className="flex items-center gap-2 mt-1">
                        <div className="flex items-center gap-1 text-xs opacity-70">
                          <IconClock className="h-2.5 w-2.5" />
                          {isToday(event.start) ? (
                            event.start.toLocaleTimeString('sv-SE', { 
                              hour: '2-digit', 
                              minute: '2-digit' 
                            })
                          ) : (
                            event.start.toLocaleDateString('sv-SE', {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit'
                            })
                          )}
                        </div>
                        
                        <div className="text-xs opacity-60">
                          {getRelativeTime(event.start)}
                        </div>
                      </div>

                      {/* Beskrivning (bara om inte compact) */}
                      {!compact && event.description && (
                        <div className="text-xs opacity-60 mt-1 line-clamp-1">
                          {event.description}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Pil-ikon */}
                  <div className="flex-shrink-0 opacity-0 group-hover:opacity-60 transition-opacity">
                    <IconChevronRight className="h-3 w-3" />
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      ) : (
        <div className="text-center py-8 text-cyan-300/50">
          <IconCalendar className="h-8 w-8 mx-auto mb-2 opacity-30" />
          <div className="text-sm">Inga händelser att visa</div>
          <div className="text-xs opacity-70 mt-1">
            {filter !== 'all' ? 'Prova att ändra filter' : 'Lägg till en händelse för att komma igång'}
          </div>
        </div>
      )}

      {/* Visa fler-indikator */}
      {events.length > maxItems && (
        <div className="text-center mt-3 pt-3 border-t border-cyan-500/20">
          <div className="text-xs text-cyan-300/60">
            Visar {Math.min(maxItems, sortedEvents.length)} av {events.length} händelser
          </div>
        </div>
      )}

      {/* Inner ring */}
      <div className="pointer-events-none absolute inset-0 rounded-2xl ring-1 ring-inset ring-cyan-300/10" />
    </div>
  )
}