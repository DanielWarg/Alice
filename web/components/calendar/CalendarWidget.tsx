'use client'

import React, { useState, useEffect } from 'react'

// Ikoner (följer samma mönster som huvudapplikationen)
const Svg = (p: any) => (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" {...p} />)
const IconCalendar = (p: any) => (<Svg {...p}><rect x="3" y="4" width="18" height="18" rx="2" /><line x1="3" y1="10" x2="21" y2="10" /></Svg>)
const IconChevronLeft = (p: any) => (<Svg {...p}><polyline points="15 18 9 12 15 6" /></Svg>)
const IconChevronRight = (p: any) => (<Svg {...p}><polyline points="9 18 15 12 9 6" /></Svg>)
const IconPlus = (p: any) => (<Svg {...p}><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></Svg>)

// GlowDot komponent från huvudapplikationen
const GlowDot = ({ className }: { className?: string }) => (
  <div className={`relative ${className}`}>
    <span className="absolute inset-0 rounded-full blur-[6px] bg-cyan-400/40" />
    <span className="absolute inset-0 rounded-full blur-[14px] bg-cyan-400/20" />
    <span className="relative block h-full w-full rounded-full bg-cyan-300" />
  </div>
)

export interface CalendarEvent {
  id: string
  title: string
  start: Date
  end: Date
  description?: string
  color?: string
  type?: 'meeting' | 'reminder' | 'task' | 'personal'
}

export interface CalendarWidgetProps {
  onEventClick?: (event: CalendarEvent) => void
  onDateSelect?: (date: Date) => void
  onQuickAdd?: () => void
  onEventCreate?: (event: Partial<CalendarEvent>) => void
  onEventUpdate?: (event: CalendarEvent) => void
  onEventDelete?: (eventId: string) => void
  events?: CalendarEvent[]
  loading?: boolean
  compact?: boolean
  className?: string
  enableVoiceCommands?: boolean
}

// Svenska månadsnamn och veckodagar
const SWEDISH_MONTHS = [
  'Januari', 'Februari', 'Mars', 'April', 'Maj', 'Juni',
  'Juli', 'Augusti', 'September', 'Oktober', 'November', 'December'
]

const SWEDISH_WEEKDAYS = ['Mån', 'Tis', 'Ons', 'Tor', 'Fre', 'Lör', 'Sön']

export default function CalendarWidget({
  onEventClick,
  onDateSelect,
  onQuickAdd,
  onEventCreate,
  onEventUpdate,
  onEventDelete,
  events = [],
  loading = false,
  compact = false,
  className = "",
  enableVoiceCommands = false
}: CalendarWidgetProps) {
  const [currentDate, setCurrentDate] = useState(new Date())
  const [selectedDate, setSelectedDate] = useState<Date | null>(null)

  const today = new Date()
  const year = currentDate.getFullYear()
  const month = currentDate.getMonth()

  // Kalender-grid logik
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const daysInMonth = lastDay.getDate()
  
  // Svensk veckostart (måndag = 0)
  const firstDayOfWeek = (firstDay.getDay() + 6) % 7
  
  // Skapa kalender-celler
  const calendarCells = []
  
  // Tomma celler för föregående månad
  for (let i = 0; i < firstDayOfWeek; i++) {
    const prevDate = new Date(year, month, -firstDayOfWeek + i + 1)
    calendarCells.push({
      date: prevDate,
      isCurrentMonth: false,
      isPrevMonth: true
    })
  }
  
  // Aktuell månads dagar
  for (let day = 1; day <= daysInMonth; day++) {
    const date = new Date(year, month, day)
    calendarCells.push({
      date,
      isCurrentMonth: true,
      isPrevMonth: false
    })
  }
  
  // Fyll ut resten av veckan med nästa månads dagar
  const remainingCells = 42 - calendarCells.length // 6 rader * 7 dagar
  for (let day = 1; day <= remainingCells; day++) {
    const nextDate = new Date(year, month + 1, day)
    calendarCells.push({
      date: nextDate,
      isCurrentMonth: false,
      isPrevMonth: false
    })
  }

  // Hitta events för ett specifikt datum
  const getEventsForDate = (date: Date) => {
    return events.filter(event => {
      const eventDate = new Date(event.start)
      return eventDate.toDateString() === date.toDateString()
    })
  }

  // Navigering
  const goToPreviousMonth = () => {
    setCurrentDate(new Date(year, month - 1))
  }

  const goToNextMonth = () => {
    setCurrentDate(new Date(year, month + 1))
  }

  const goToToday = () => {
    setCurrentDate(new Date())
    setSelectedDate(new Date())
  }

  const handleDateClick = (date: Date) => {
    setSelectedDate(date)
    onDateSelect?.(date)
  }

  const isToday = (date: Date) => {
    return date.toDateString() === today.toDateString()
  }

  const isSelected = (date: Date) => {
    return selectedDate && date.toDateString() === selectedDate.toDateString()
  }

  return (
    <div className={`relative rounded-2xl border border-cyan-500/20 bg-cyan-950/20 p-4 shadow-[0_0_60px_-20px_rgba(34,211,238,.5)] ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <GlowDot className="h-2 w-2" />
          <h3 className="text-cyan-200/90 text-xs uppercase tracking-widest">Kalender</h3>
        </div>
        <div className="flex gap-2 text-cyan-300/70">
          <button 
            onClick={onQuickAdd}
            className="p-1 rounded hover:bg-cyan-400/10 transition-colors"
            title="Lägg till händelse"
          >
            <IconPlus className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Månadsnavigering */}
      <div className="flex items-center justify-between mb-4">
        <button 
          onClick={goToPreviousMonth}
          className="p-1 rounded-lg hover:bg-cyan-400/10 transition-colors text-cyan-300"
        >
          <IconChevronLeft className="h-4 w-4" />
        </button>
        
        <div className="flex items-center gap-2">
          <h4 className="text-cyan-100 font-medium">
            {SWEDISH_MONTHS[month]} {year}
          </h4>
          <button 
            onClick={goToToday}
            className="text-xs px-2 py-1 rounded bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/30 transition-colors"
          >
            Idag
          </button>
        </div>
        
        <button 
          onClick={goToNextMonth}
          className="p-1 rounded-lg hover:bg-cyan-400/10 transition-colors text-cyan-300"
        >
          <IconChevronRight className="h-4 w-4" />
        </button>
      </div>

      {/* Veckodagar */}
      <div className="grid grid-cols-7 gap-1 mb-2">
        {SWEDISH_WEEKDAYS.map((day) => (
          <div key={day} className="text-center text-[10px] uppercase tracking-widest text-cyan-300/60 py-1">
            {day}
          </div>
        ))}
      </div>

      {/* Kalender-grid */}
      <div className="grid grid-cols-7 gap-1">
        {calendarCells.map((cell, index) => {
          const dayEvents = getEventsForDate(cell.date)
          const hasEvents = dayEvents.length > 0
          const isTodayCell = isToday(cell.date)
          const isSelectedCell = isSelected(cell.date)
          
          return (
            <button
              key={index}
              onClick={() => handleDateClick(cell.date)}
              className={`
                relative aspect-square text-sm p-1 rounded-lg transition-all duration-200
                ${cell.isCurrentMonth 
                  ? 'text-cyan-100 hover:bg-cyan-400/10' 
                  : 'text-cyan-300/30 hover:text-cyan-300/50'
                }
                ${isTodayCell 
                  ? 'bg-cyan-500/20 border border-cyan-400/40 text-cyan-100 font-medium' 
                  : ''
                }
                ${isSelectedCell && !isTodayCell
                  ? 'bg-cyan-400/10 border border-cyan-400/30'
                  : ''
                }
                ${hasEvents && !isTodayCell && !isSelectedCell
                  ? 'bg-cyan-900/30'
                  : ''
                }
              `}
            >
              <span className="relative z-10">
                {cell.date.getDate()}
              </span>
              
              {/* Event-indikator */}
              {hasEvents && (
                <div className="absolute bottom-1 left-1/2 transform -translate-x-1/2 flex gap-0.5">
                  {dayEvents.slice(0, 3).map((_, eventIndex) => (
                    <div 
                      key={eventIndex}
                      className="w-1 h-1 rounded-full bg-cyan-400/80"
                    />
                  ))}
                  {dayEvents.length > 3 && (
                    <div className="w-1 h-1 rounded-full bg-cyan-300/60" />
                  )}
                </div>
              )}
            </button>
          )
        })}
      </div>

      {/* Dagens events (om compact är false) */}
      {!compact && selectedDate && (
        <div className="mt-4 pt-3 border-t border-cyan-500/20">
          <div className="flex items-center gap-2 mb-2">
            <div className="text-xs text-cyan-300/80">
              {selectedDate.toLocaleDateString('sv-SE', { 
                weekday: 'long', 
                day: 'numeric', 
                month: 'long' 
              })}
            </div>
          </div>
          
          {getEventsForDate(selectedDate).length > 0 ? (
            <div className="space-y-1">
              {getEventsForDate(selectedDate).slice(0, 3).map((event) => (
                <button
                  key={event.id}
                  onClick={() => onEventClick?.(event)}
                  className="w-full text-left p-2 rounded-lg bg-cyan-900/20 hover:bg-cyan-900/30 transition-colors border border-cyan-500/10"
                >
                  <div className="text-xs text-cyan-100 font-medium truncate">
                    {event.title}
                  </div>
                  <div className="text-[10px] text-cyan-300/70">
                    {event.start.toLocaleTimeString('sv-SE', { 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  </div>
                </button>
              ))}
              {getEventsForDate(selectedDate).length > 3 && (
                <div className="text-[10px] text-cyan-300/60 text-center py-1">
                  +{getEventsForDate(selectedDate).length - 3} fler händelser
                </div>
              )}
            </div>
          ) : (
            <div className="text-xs text-cyan-300/50 italic">
              Inga händelser denna dag
            </div>
          )}
        </div>
      )}

      {/* Inner ring för konsistent stil */}
      <div className="pointer-events-none absolute inset-0 rounded-2xl ring-1 ring-inset ring-cyan-300/10" />
    </div>
  )
}