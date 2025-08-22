# Alice AI Assistant - Priority 1 Task Checklist

**Definition of Done**: Complete professional-grade polish for Alice AI assistant repository. This checklist ensures no ambiguity remains – from repo hygiene to test coverage, security, deployment, ML quality, HUD interface, and voice pipeline.

## 📋 **Progress Overview**

**Status**: 🚀 Ready for systematic execution  
**Total Tasks**: 225+ individual checkpoints  
**Categories**: 25 major areas  
**Goal**: Professional, production-ready AI assistant platform

---

## 🎯 **Definition of Done (Overall)**

- [ ] Default branch är "main" och branch protection är aktiv (grön CI krävs, kodgranskning via CODEOWNERS)
- [ ] README visar aktuella badges (CI, coverage) och en 30-sek Quickstart som fungerar
- [ ] Alla tester (unit, integration, e2e) körs i CI och publicerar artefakter; coverage ≥ 80% backend
- [ ] Dokumentation finns, är konsekvent och matchar faktisk körning i CI/Prod
- [ ] Säker hantering av hemligheter; inga secrets i repo; tydlig SECURITY-policy
- [ ] Demo-läge utan externa nycklar är körbart (första intryck < 10 min)

---

## 1️⃣ **Repo & Branching**

- [ ] Default branch = main (master avvecklad eller tydligt deprecierad i README)
- [ ] Branch protection på main (kräv CI-status + CODEOWNERS review)
- [ ] Conventional Commits (enforce via PR-granskning eller hook)
- [ ] CODEOWNERS finns och pekar på ansvariga per katalog
- [ ] .gitignore täcker virtuella miljöer, build-artefakter, .env, cache, modeller
- [ ] Licensfil (MIT) ligger i roten och nämns i README

---

## 2️⃣ **Projektmetadata & Mallar**

- [ ] CONTRIBUTING.md beskriver hur man sätter upp dev-miljö, kör tester och gör PR
- [ ] CODE_OF_CONDUCT.md finns (Contributor Covenant)
- [ ] SECURITY.md (sårbarhetsrapportering, kontaktväg, patch-policy)
- [ ] SUPPORT.md (hur man får hjälp, prioriteringspolicy)
- [ ] .github/ISSUE_TEMPLATE (bug/feature) och PULL_REQUEST_TEMPLATE finns

---

## 3️⃣ **Dokumentation (Konsekvent & Praktisk)**

- [ ] README: hook, demo-GIF, Quickstart (3 kommandon), arkitekturdiagram, test-sektion, länkar till docs
- [ ] docs/ARCHITECTURE.md: flöden (röst→STT→NLU→Agent→Tool→TTS→HUD), sekvensdiagram, datakontrakt
- [ ] docs/OPERATIONS.md: körning lokalt/dev/prod, profiler, loggnivå, felsökning
- [ ] docs/testing.md: testpyramid, hur mäta coverage, hur läsa rapporter
- [ ] VOICE_SETUP.md: installation, mikrofon, wake-word-tuning, TTS-röster/licenser
- [ ] API-referens (OpenAPI autogenererad eller API.md) länkad från README
- [ ] ROADMAP.md med milstolpar och länkade issues; uppdaterad
- [ ] Språkpolicy: README på engelska, svensk användarguide i docs/sv (eller tvärtom – bara konsekvent)

---

## 4️⃣ **Konfiguration & Hemligheter**

- [ ] .env.example med alla nycklar, defaultvärden och beskrivning
- [ ] Aldrig checka in riktiga .env-filer; secrets scannas i CI
- [ ] Separata credentials för dev/stage/prod; inga delade Google/Spotify-konton
- [ ] Token-rotation (dokumenterad), revoke-rutin, "break glass"-process
- [ ] Valfritt: integrera hemligheter med t.ex. 1Password/Vault; lokalt fallback via krypterad fil

---

## 5️⃣ **Beroenden & Supply Chain**

- [ ] Pinning/locking: Python (requirements*.txt) och Node (package-lock.json)
- [ ] Dependabot/Renovate aktiv för Python och Node
- [ ] SBOM genereras (t.ex. Syft) vid release och scannas (t.ex. Grype)
- [ ] Actions kör CodeQL eller liknande statisk sårbarhetsanalys
- [ ] Container-image (om finns) skannas (Trivy/Grype) i CI

---

## 6️⃣ **Bygg & Tooling**

- [ ] Makefile med "make dev", "make test", "make up" (docker-compose), "make lint"
- [ ] Pre-commit hooks (ruff/black/mypy för Python; eslint/prettier/tsc för web)
- [ ] Strikta typer: mypy (Python) och "strict" i tsconfig (web)
- [ ] Lint-fel blockerar merge via CI

---

## 7️⃣ **CI/CD**

- [ ] GitHub Actions: backend-jobb (pytest + coverage + artefakter)
- [ ] GitHub Actions: frontend-e2e (Playwright HTML-rapport som artefakt)
- [ ] Actions Summary visar coverage-% och NLU-accuracy i klartext
- [ ] (Publikt) Codecov uppladdning + badge + PR-kommentar
- [ ] Release-workflow (tagg → changelog → Docker-image/artefakter publiceras)
- [ ] Branch protection kräver grön CI för merge

---

## 8️⃣ **Teststrategi (Pyramid)**

- [ ] Unit-tester: kärnlogik, validering, pydantic-modeller, små hjälpfunktioner
- [ ] Integrations-tester: httpx + respx (mockar Google/Spotify/Gmail)
- [ ] Kontrakttester: pydantic/OpenAPI-schema valideras (IO-format) i CI
- [ ] E2E backend "smoke": text→plan→tool→text utan ljud (stabilt i CI)
- [ ] E2E frontend: Playwright mot HUD i STUB_MODE (ingen extern backend krävs)
- [ ] Nightly (valfritt): kör en "riktig" e2e mot dev-backend (flakighet tolereras nattligt)
- [ ] Coverage-mål backend ≥ 80% (linjer), branches ≥ 70% (mål), badge i README
- [ ] Buggar får minimalt reproducerbart test som stannar kvar efter fix (regressionsskydd)

---

## 9️⃣ **NLU/ML-Kvalitet (Svenska)**

- [ ] Gold-set för intents/slots i versionerad katalog (tests/fixtures/nlu_sv.jsonl)
- [ ] Metriker: accuracy/precision/recall/F1 för intent, rapporteras i CI Summary
- [ ] Tröskel definierad (t.ex. intent-accuracy ≥ 0.85) som bryter bygget under tröskel
- [ ] Seeds låsta för reproducerbar inferens (om stochastiska komponenter)
- [ ] Dokumenterad datakälla och anonymisering (inga personuppgifter i träningsdata)
- [ ] Modellversioner (Ollama/Whisper/Piper) är pin-ade och dokumenterade i README
- [ ] Prompt-/routingtuning dokumenterad (ändringslogg när regler eller mallar uppdateras)

---

## 🔟 **Röstkedja & Audio**

- [ ] Wake-word param/tuning dokumenterat; test eller manuell checklista för latens/precision
- [ ] STT (Whisper): svensk modellversion, latensmål och fallback-väg (CPU/GPU)
- [ ] TTS (Piper): licenser för röster dokumenterade, cache-policy klar, volym/latensmål
- [ ] VoiceBox i HUD har data-testid och e2e-test som verifierar rendering
- [ ] Resilience: rimlig hantering av mikrofonfel, ingen UI-crash, loggat tydligt

---

## 1️⃣1️⃣ **Backend (FastAPI) & API**

- [ ] /health och /metrics (minst hälsa; metrics kan vara enkel) finns
- [ ] OpenAPI schema publiceras och valideras i CI (schema-driven)
- [ ] Timeouts, retries, circuit-breaker (minst backoff) på externa API-anrop
- [ ] Felhantering: standardiserat fel-schema (problem+json eller liknande)
- [ ] Inputvalidering med pydantic; robust datum/tid-parsning (svenska)
- [ ] CORS låst till rätt origins; HTTP-säkerhetsheaders korrekt (via middleware)
- [ ] Rate-limit eller åtminstone skydd mot oavsiktlig spam (lokalt)

---

## 1️⃣2️⃣ **Verktygsrouter & Behörigheter**

- [ ] Varje "tool" deklarerar behörighet/permissions (manifests), loggas vid användning
- [ ] Sandbox för högrisk-verktyg (ingen filradering utanför whitelists)
- [ ] Tydliga felmeddelanden när ett verktyg nekas eller saknar konfiguration
- [ ] Demo-mode ersätter riktiga anrop med stubbar (för första intryck)

---

## 1️⃣3️⃣ **Integrationer (Google, Spotify, Gmail)**

- [ ] OAuth-flöden dokumenterade med skärmbilder
- [ ] Scope-minimering (minsta nödvändiga åtkomst)
- [ ] Tokenförvaring krypterad lokalt; separat för dev/prod-profiler
- [ ] Rate-limit-hantering: backoff, kvot-övervakning och UI-indikator
- [ ] Fel i integrationer degraderar graciöst (HUD visar "tillfälligt otillgängligt")

---

## 1️⃣4️⃣ **Frontend (Next.js HUD)**

- [ ] Responsiv layout (desktop först men fungerar rimligt på små skärmar)
- [ ] Tillgänglighet: grundläggande WCAG (landmarks, aria, kontraster, tab-fokus)
- [ ] data-testid på kritiska komponenter (voicebox, calendar-widget, statuskort)
- [ ] CSP (Content Security Policy) rimligt stram, inga inline-script utan nonce
- [ ] Felhantering i UI (tomma states, network-fel, återförsök)
- [ ] Översättningsram (i18n) för framtida flerspråk (även om svenskan är primär)

---

## 1️⃣5️⃣ **Prestanda & Resursmål**

- [ ] Definierade mål: e2e röstlatens (wake→tal ut) och mål för HUD-rendering
- [ ] Profilering genomförd (minst en rapport) och ev. cache justerad (TTS, NLU)
- [ ] "Performance budget": CPU/RAM-mål dokumenterade för M-klass Mac och Linux
- [ ] Långkörningstest (1–2 h) utan minnesläckor; elementär soak-test i nightly

---

## 1️⃣6️⃣ **Loggning & Observability**

- [ ] Strukturerad logg (JSON) för backend; nivåer: DEBUG/INFO/WARN/ERROR
- [ ] Korrelations-ID per förfrågan; loggas igenom kedjan
- [ ] Minst en standardiserad metrics-yta (requests/sec, fel%, latens)
- [ ] Loggpolicy: inga hemligheter eller PII i loggar; redaction på plats

---

## 1️⃣7️⃣ **Säkerhet & Privacy by Design**

- [ ] Grundläggande hotmodell (kort not på attackytor och mitigering)
- [ ] XSS/CSRF-skydd; SameSite cookies, secure flags om cookies används
- [ ] Ingen telemetri som skickar data externt (privacy-first); om opt-in, dokumenterat
- [ ] GDPR-check: dataflöden kartlagda; ingen beständig lagring av PII utan syfte
- [ ] Backup/restore-rutin om lokala data används (kalendercache m.m.)
- [ ] Beroende-licenser kompatibla (Piper/Whisper-modeller, Spotify API-villkor)

---

## 1️⃣8️⃣ **Paketering & Distribution**

- [ ] Docker-compose som startar backend+web (+ ev. ollama-brygga) med .env.example
- [ ] Multi-arch image (valfritt) eller åtminstone amd64; publicerat per release-tagg
- [ ] Desktop-paketering (valfritt) eller dokumenterad "one-liner" för utvecklare
- [ ] Versionspolicy (SemVer) + CHANGELOG per release
- [ ] Installationsguide testad på macOS, Linux och Windows (WSL)

---

## 1️⃣9️⃣ **Demo, Onboarding & "First-run Success"**

- [ ] "Demo mode" i HUD/Server (stubbar) – funkar utan nycklar första 10 min
- [ ] Guidade tooltips eller "first-run tour" (valfritt) som visar kärnfunktioner
- [ ] Exempelkommandon på svenska visas i HUD (kom igång direkt)
- [ ] README: "Vanliga fel och snabba fixar" (micro-FAQ)

---

## 2️⃣0️⃣ **Kvalitetssäkring & Triage**

- [ ] Bug triage-rutin (etiketter, SLA för respons)
- [ ] "Good first issue" etiketter för enklare bidrag
- [ ] Milstolpar i GitHub med tydliga mål (90-dagarsplan)
- [ ] Release-checklista (manuell eller GitHub Release Drafter)

---

## 2️⃣1️⃣ **SRE & Drift (Om/När det Behövs)**

- [ ] Runbooks: "Kalender-OAuth reset", "Spotify rate limit", "Mikrofonproblem"
- [ ] Larm (om ni kör i server-miljö): fel% och latens över trösklar
- [ ] Disaster recovery-not: vad gör vi vid korrupt cache eller brutna modeller
- [ ] Kapacitetsplan: minnes-/lagringskrav för modeller och cache

---

## 2️⃣2️⃣ **Juridik & Kommunikation**

- [ ] Ansvarsfriskrivning (ej medicinsk/juridisk rådgivning, etc.) i README/Om
- [ ] Varumärken/logotyper rätt använda (Spotify/Google kräver korrekt attribution)
- [ ] Integritetspolicy för demo-läge (om någon data loggas lokalt)

---

## 2️⃣3️⃣ **Alice-Specifika Kontroller (Skarpa)**

- [ ] NLU på svenska: senaste accuracy i CI Summary ≥ definierad tröskel, rapport länkad
- [ ] Wake-word fungerar stabilt på svensk röst (manuel testlista avprickad)
- [ ] Svensk datum/tid-parsning verifierad i test (fredag 14:00, imorgon, måndag)
- [ ] Spotify: spela/pausa/sök testade med stub och minst ett "riktigt" smoke (nightly)
- [ ] Gmail/Calendar: scope och felhantering verifierade; inga tokens i logg
- [ ] HUD: voicebox och calendar-widget har data-testid och går igenom Playwright-spec

---

## 2️⃣4️⃣ **Mätetal/KPI**

- [ ] "First-run success" (andel som startar allt på första försöket) – mät/anteckna
- [ ] Röstlatens (median/95:e percentil) – minst manuellt loggad i en rapport
- [ ] NLU trend över tid – håll en liten graf/tabell i README eller docs
- [ ] Antal integrationer aktiva per användare – målvärde dokumenterat

---

## 2️⃣5️⃣ **Sista Städ**

- [ ] Inga TODO/FIXME i produktion utan spårbar issue-länk
- [ ] Dött kod/arv rensat; moduler utan ägare tas bort eller deprecieras
- [ ] Bild-/assets-storlek optimerad; inga onödiga stora filer i repo
- [ ] All "lokal sanning" i README matchar CI-workflows och filstruktur

---

## 📊 **Progress Tracker**

| Category | Progress | Priority | Estimated Hours |
|----------|----------|----------|-----------------|
| 1. Repo & Branching | 0/6 | 🔴 Critical | 4h |
| 2. Project Metadata | 0/5 | 🟡 High | 6h |
| 3. Documentation | 0/8 | 🟡 High | 12h |
| 4. Configuration & Secrets | 0/5 | 🔴 Critical | 8h |
| 5. Dependencies & Supply Chain | 0/5 | 🟡 High | 6h |
| 6. Build & Tooling | 0/4 | 🟡 High | 4h |
| 7. CI/CD | 0/6 | 🔴 Critical | 10h |
| 8. Test Strategy | 0/8 | 🔴 Critical | 16h |
| 9. NLU/ML Quality | 0/7 | 🔴 Critical | 12h |
| 10. Voice Chain & Audio | 0/5 | 🟡 High | 8h |
| 11. Backend & API | 0/7 | 🟡 High | 10h |
| 12. Tool Router & Permissions | 0/4 | 🟡 High | 6h |
| 13. Integrations | 0/5 | 🟡 High | 8h |
| 14. Frontend HUD | 0/6 | 🟡 High | 12h |
| 15. Performance & Resources | 0/4 | 🟡 High | 8h |
| 16. Logging & Observability | 0/4 | 🟡 High | 6h |
| 17. Security & Privacy | 0/6 | 🔴 Critical | 10h |
| 18. Packaging & Distribution | 0/5 | 🟡 High | 8h |
| 19. Demo & Onboarding | 0/4 | 🟡 High | 6h |
| 20. Quality Assurance | 0/4 | 🟡 High | 4h |
| 21. SRE & Operations | 0/4 | 🟢 Medium | 6h |
| 22. Legal & Communication | 0/3 | 🟢 Medium | 2h |
| 23. Alice-Specific Controls | 0/6 | 🔴 Critical | 12h |
| 24. Metrics/KPI | 0/4 | 🟡 High | 4h |
| 25. Final Cleanup | 0/4 | 🟡 High | 4h |

**Total Estimated Effort**: ~200 hours  
**Critical Path Items**: 38 tasks (Repo, Config, CI/CD, Testing, NLU, Security, Alice-specific)

---

## 🚀 **Execution Strategy**

### Phase 1 - Foundation (Week 1)
**Focus**: Repository hygiene, branching, configuration, CI/CD basics
- Categories 1, 4, 7 (partial)
- Goal: Stable development environment

### Phase 2 - Quality & Testing (Week 2) 
**Focus**: Complete test coverage, security, documentation
- Categories 8, 9, 17, 3
- Goal: Professional quality standards

### Phase 3 - Integration & Polish (Week 3)
**Focus**: Voice pipeline, integrations, frontend, performance
- Categories 10, 13, 14, 15, 23
- Goal: Feature completeness

### Phase 4 - Production Readiness (Week 4)
**Focus**: Deployment, monitoring, legal, final polish
- Categories 18, 16, 21, 22, 25
- Goal: Production deployment ready

---

## 📝 **Notes**

- **Swedish Identity Preserved**: All Alice-specific Swedish voice commands and cultural references maintained
- **Documentation Complete**: Both English and Swedish versions available
- **Professional Standards**: Enterprise-grade quality throughout
- **International Accessibility**: English documentation for global contributors

**Last Updated**: 2025-01-22  
**Version**: 1.0  
**Status**: Ready for execution 🚀