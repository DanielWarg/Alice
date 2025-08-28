#!/bin/bash
# 🔍 Alice Activity Watcher - Kombinerad loggning av all aktivitet

echo "================================================================================"
echo "🔍 Alice Activity Watcher - Realtidsloggning av all aktivitet"
echo "================================================================================"
echo "Tid: $(date)"
echo

# Skapa loggfiler för de olika komponenterna
LOGDIR="alice_logs_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOGDIR"

echo "📁 Skapar loggmapp: $LOGDIR"
echo

# Bakgrundsfunktion för att logga systemresurser
monitor_system() {
    while true; do
        echo "[$(date +%H:%M:%S)] SYSTEM: CPU=$(top -l 1 -n 0 | grep "CPU usage" | awk '{print $3}') RAM=$(vm_stat | head -1 | awk '{print $4}')" >> "$LOGDIR/system.log"
        sleep 5
    done
}

# Bakgrundsfunktion för att övervaka API-aktivitet  
monitor_api() {
    while true; do
        # Test backend hälsa
        if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
            echo "[$(date +%H:%M:%S)] API: Backend OK" >> "$LOGDIR/api.log"
        else
            echo "[$(date +%H:%M:%S)] API: Backend EJ TILLGÄNGLIG" >> "$LOGDIR/api.log"
        fi
        
        # Test chat API
        response=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/chat \
                  -H "Content-Type: application/json" \
                  -d '{"prompt": "monitor test"}' 2>/dev/null)
        
        if [ "$response" = "200" ]; then
            echo "[$(date +%H:%M:%S)] API: Chat API OK (200)" >> "$LOGDIR/api.log"
        else
            echo "[$(date +%H:%M:%S)] API: Chat API fel ($response)" >> "$LOGDIR/api.log"
        fi
        
        sleep 10
    done
}

# Bakgrundsfunktion för att övervaka processer
monitor_processes() {
    while true; do
        echo "[$(date +%H:%M:%S)] PROCESSES:" >> "$LOGDIR/processes.log"
        ps aux | grep -E "(alice|ollama|uvicorn|next)" | grep -v grep >> "$LOGDIR/processes.log"
        echo "---" >> "$LOGDIR/processes.log"
        sleep 15
    done
}

# Funktion för att visa live-loggar
show_live_logs() {
    echo "📊 Visar live-loggar (tryck Ctrl+C för att stoppa)"
    echo
    
    # Kombinera och visa alla loggar i realtid
    tail -f "$LOGDIR"/*.log 2>/dev/null | while read line; do
        # Färgkoda baserat på typ
        if [[ "$line" =~ SYSTEM ]]; then
            echo -e "\033[94m$line\033[0m"  # Blå för system
        elif [[ "$line" =~ API ]]; then
            echo -e "\033[92m$line\033[0m"  # Grön för API
        elif [[ "$line" =~ PROCESS ]]; then
            echo -e "\033[93m$line\033[0m"  # Gul för processer
        elif [[ "$line" =~ ERROR ]] || [[ "$line" =~ fel ]]; then
            echo -e "\033[91m$line\033[0m"  # Röd för fel
        else
            echo "$line"
        fi
    done
}

# Cleanup-funktion
cleanup() {
    echo
    echo "🛑 Stoppar Alice Activity Watcher..."
    
    # Döda bakgrundsprocesser
    jobs -p | xargs -r kill 2>/dev/null
    
    echo "📊 Sammanfattning av loggar:"
    echo "  System-events: $(wc -l < "$LOGDIR/system.log" 2>/dev/null || echo "0")"
    echo "  API-events: $(wc -l < "$LOGDIR/api.log" 2>/dev/null || echo "0")"  
    echo "  Process-events: $(wc -l < "$LOGDIR/processes.log" 2>/dev/null || echo "0")"
    echo
    echo "📁 Loggar sparade i: $LOGDIR"
    
    exit 0
}

# Registrera cleanup vid Ctrl+C
trap cleanup SIGINT SIGTERM

# Starta bakgrundsövervakare
monitor_system &
monitor_api &
monitor_processes &

echo "🚀 Alla monitorer startade!"
echo "📁 Loggar sparas i: $LOGDIR"
echo

# Vänta lite för att logs ska börja komma
sleep 3

# Visa live-loggar
show_live_logs