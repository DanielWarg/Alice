# B3.1 Härdning - Accepteringskriterier & Implementation

## 🔥 "Done or Not?" Kritiska Kriterier (P0)

### WebSocket Stabilitet
- [ ] **WS stabilitet:** /ws/voice/ambient håller ≥30 min utan disconnect
- [ ] **Reconnect logic:** Automatisk återanslutning med exponential backoff
- [ ] **Memory leak test:** <10MB minnestillväxt över 4h continuous session
- [ ] **Connection limits:** Max 10 samtidiga WS-anslutningar per IP

### ASR Prestanda (svenska)
- [ ] **Latens:** Partials inom ≤500 ms från röststart
- [ ] **Kvalitet:** WER (Word Error Rate) ≤10% i normalrum
- [ ] **Språkstöd:** Svenska tecken (å,ä,ö) transkriberas korrekt
- [ ] **Fallback chain:** OpenAI Whisper → Local Whisper → Mock (inga crashes)

### Barge-In Responsivitet
- [ ] **TTS-stop latens:** TTS avbryts ≤200 ms efter ny röstaktivitet
- [ ] **VAD precision:** <5% false positives på bakgrundsljud
- [ ] **Multi-source:** Kan stoppa TTS, musik, notifications simultaneously
- [ ] **Cooldown respect:** Ingen spam-triggering (500ms cooldown)

### TTL & Privacy
- [ ] **TTL enforcement:** Råtranskript försvinner efter konfigurerad TTL
- [ ] **"Glöm det där":** Tar bort målobjekt från både disk och vektorindex
- [ ] **Sensitive masking:** E-post/telefon/SSN maskas automatiskt
- [ ] **Audit log:** Alla forget-operationer loggas med timestamp + reason

### HUD & Controls
- [ ] **Real-time status:** Live/Mute/Hard-stop reflekteras ≤100ms i UI
- [ ] **Session info:** Frames processed, buffer size, duration visas korrekt
- [ ] **Error handling:** Graceful degradation vid ASR/network fails
- [ ] **Mobile responsive:** Fungerar på telefon (touch-friendly buttons)

## 📊 Test & Telemetri

### Metrics (Prometheus/OpenTelemetry)
- [ ] **asr_partial_latency_ms** - Histogram: tid från audio → partial
- [ ] **tts_stop_latency_ms** - Histogram: tid från barge-in trigger → TTS stop
- [ ] **vad_activation_rate** - Counter: röstaktivitet detektions per minut
- [ ] **ws_reconnects** - Counter: WebSocket återanslutningar
- [ ] **forget_ops_per_sec** - Rate: privacy operations
- [ ] **ttl_purges** - Counter: automatiska minnesrensningar

### E2E Testing
- [ ] **Playwright script:** Simulera mic on → partials → TTS → barge-in → resume
- [ ] **Soak test:** 2-4h always-on session utan crashes/memory leaks
- [ ] **Network resilience:** Fungerar vid intermittent nätverksavbrott
- [ ] **Browser compatibility:** Chrome, Firefox, Safari, Edge

### Performance Budgets
- [ ] **CPU usage:** VAD+ASR pipeline <1 CPU core i snitt
- [ ] **Memory growth:** <50MB per 24h session
- [ ] **Network bandwidth:** <100KB/min vid normal användning
- [ ] **Disk I/O:** <1MB/hour för logging + TTL cleanup

## 🛡️ Kvalitet & Resiliens

### ASR Fallback Strategy
- [ ] **Primary:** OpenAI Whisper API (svenska, hög kvalitet)
- [ ] **Secondary:** Local Whisper.cpp når nät saknas
- [ ] **Tertiary:** Mock transcriber (utveckling/testing)
- [ ] **Circuit breaker:** Exponential backoff vid API rate limits

### Audio Processing Robusthet  
- [ ] **Diarization-lite:** Tagga `speaker: user|assistant` för echo-undvikande
- [ ] **Noise suppression:** Fungerar i vardagsrum med TV/AC/trafikljud  
- [ ] **Mic switching:** Hanterar USB-mic inkoppling/urkoppling gracefully
- [ ] **Sample rate adaptation:** Stödjer 16kHz, 44.1kHz, 48kHz input

### Rate Limits & Circuit Breakers
- [ ] **OpenAI Whisper:** Max 100 req/min med exponential backoff
- [ ] **WebSocket messages:** Max 1000 msg/min per session
- [ ] **Privacy operations:** Max 10 forget requests/min per IP
- [ ] **Health checks:** Auto-disable features vid sustained failures

## 🔒 Privacy & Regelefterlevnad

### On-Device Data Protection
- [ ] **PII masking:** E-post, telefon, personnummer maskas före lagring
- [ ] **Geographic filtering:** GPS-koordinater anonymiseras
- [ ] **Device fingerprints:** MAC-adresser, serienummer filtreras bort
- [ ] **Biometric data:** Röstprints lagras ej permanent

### Compliance Documentation  
- [ ] **PRIVACY.md:** Förklarar ambient-läge, TTL, forget-funktioner
- [ ] **Data retention policy:** Tydliga regler för olika datatyper
- [ ] **User consent flow:** Opt-in för ambient recording med klar info
- [ ] **Export functionality:** Användare kan hämta sin data (GDPR)

## 📝 Logging & Observability

### Event Logging (strukturerad JSON)
- [ ] **asr_partial** - `{text, confidence, latency_ms, timestamp}`
- [ ] **barge_in** - `{trigger_source, stopped_processes, latency_ms}`
- [ ] **privacy_forget** - `{query, deleted_count, processing_time}`
- [ ] **ttl_purge** - `{purged_count, oldest_deleted, cleanup_duration}`
- [ ] **ws_connection** - `{session_id, duration, disconnect_reason}`
- [ ] **error_recovery** - `{error_type, recovery_action, success}`

### Alerting Thresholds
- [ ] **High latency:** ASR partial >1s eller barge-in >500ms
- [ ] **Error rate:** >5% failed operations över 5min window  
- [ ] **Memory usage:** >500MB per process
- [ ] **Disk space:** <1GB kvar för logs/temp files

## ⚡ Implementation Priorities

### P0 (Blockers)
1. WebSocket stability (30min+ sessions)
2. ASR latency <500ms för svenska
3. Barge-in <200ms TTS stop
4. Privacy forget functionality

### P1 (Launch Week)  
1. Metrics + basic alerting
2. E2E test automation
3. Privacy documentation
4. Mobile UI responsiveness

### P2 (Post-Launch)
1. Soak testing (multi-hour sessions)
2. Advanced audio processing (diarization)
3. GDPR compliance features
4. Performance optimization

---

**Status Tracking:**
- Create GitHub issues för varje [ ] checkbox
- Daily standup: review P0 items först
- Weekly: metrics review + performance testing
- Deploy när alla P0 + 80% P1 är klara