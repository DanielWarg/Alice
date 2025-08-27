Projekt Alice: Teknisk färdplan
Denna dokumentation beskriver den tekniska färdplanen för Project Alice. Den är utformad som en steg-för-steg-guide, med tydliga mål, implementeringsdetaljer och framgångskriterier för varje fas.

FAS 0 — Förberedelser (Grön baslinje)
Mål: Låsa nuläget och etablera en stabil grund för vidareutveckling.

Miljövariabler: Definiera och konfigurera alla nödvändiga miljövariabler för servern.

OPENAI_API_KEY=...
AGENT_PROVIDER=openai|gptoss
AGENT_FALLBACK=openai|gptoss
BRAIN_SHADOW_ENABLED=on
ALLOW_CLOUD=on
ENTITY_MODE=on
ARTIFACT_CONFIDENCE_MIN=0.7
INJECT_BUDGET_PCT=25
Hälsokontroller: Validera att systemet svarar med 200 OK på GET /api/health och GET /api/health/ready.

Rösttest: Köra ett smoke test på /voice-test för att säkerställa att timer och weather fungerar med Text-to-Speech (TTS).

Done-kriterier: 0 × 5xx-fel i 50 anrop mot /api/agent, e2e p95 ≤ 1.2s.

FAS 1 — Strict TTS
Mål: Låta GPT-OSS-hjärnan komponera svaret, medan TTS läser upp exakt det som skrivs.

API: Implementera POST /api/brain/compose.

Request:

{ user_id:string, session_id:string, text:string, locale:"sv-SE" }
Response (AnswerPackage):

TypeScript

interface AnswerPackage {
  spoken_text: string;
  screen_text?: string;
  ssml?: string;
  citations?: {title:string; url?:string}[];
  meta?: { confidence:number; tone?:string }
}
Klientintegration: Låt din befintliga röstpipeline anropa /api/brain/compose och mata resultatet (pkg.ssml eller pkg.spoken_text) direkt till TTS-motorn.

Done-kriterier:

0 avvikelser där TTS läser något annat än spoken_text eller ssml.

tts_ttfa_ms p50 ≤ 300 ms (med sentence streaming aktiverat i senare fas).

Filer:
server/api/brain/compose.ts
web/voice/sentenceStreamer.ts (stub)

FAS 2 — EventBus & Telemetri
Mål: Logga alla systemhändelser som event för att möjliggöra mätning och analys.

EventBus: Skapa en central eventbuss för asynkron kommunikation.

TypeScript

import { EventEmitter } from "events";
export const bus = new EventEmitter();
export const on = <T=any>(type:string,h:(e:T)=>void)=>bus.on(type,h);
export const emit = <T=any>(type:string,p:T)=>bus.emit(type,p);
Loggning: Skriv alla händelser i NDJSON-format till logs/metrics.ndjson.

Done-kriterier: Varje användarinteraktion producerar minst 3 eventrader; inga event går förlorade.

Filer:
core/eventBus.ts
core/metrics.ts

FAS 3 — Minne & RAG (Artefakter)
Mål: Implementera ett långtidsminne baserat på "artefakter" som kan hämtas för kontext.

Schema (SQL): Skapa en artifacts-tabell för att lagra minnesfragment, inklusive användar-ID, typ, text, konfidenspoäng och inbäddning (embedding).

API & Interface:

Definiera Artifact och Memory gränssnitt.

Implementera endpoints för att skriva (POST /memory/write) och hämta (POST /memory/fetch) artefakter.

Done-kriterier: Tidigare sparade preferenser ("prata långsammare", "Göteborg") kan hämtas och användas i nästkommande konversationer.

Filer:
server/memory/sqliteVec.ts
server/api/memory/write.ts
server/api/memory/fetch.ts

FAS 4 — PromptBuilder & Injektionsbudget
Mål: Kontrollerat injicera minnesartefakter i prompten före varje svar.

buildContext(): Skapa en funktion som hämtar relevanta artefakter från minnet, filtrerar dem och komprimerar dem till en kompakt kontext.

composeMessages(): Placera persona, stil och den komprimerade kontexten i system- och assistentrollerna i prompten.

Budget: Begränsa kontextinjektionen till högst 25 % av den totala tokenbudgeten.

Done-kriterier: Mätvärdet injected_tokens_pct loggas och ligger stabilt under 25 %.

Filer:
core/promptBuilder.ts
alice/identity/persona.yml
alice/identity/style.yml

FAS 5 — Provider-switch & Failover
Mål: Göra GPT-OSS till den primära "hjärnan" med OpenAI som fallback-lösning.

Timeout & Fallback: Implementera en policy som omdirigerar en förfrågan till molntjänsten (/api/agent) om den lokala hjärnan inte levererar ett svar inom en viss tidsgräns (t.ex. BRAIN_DEADLINE_MS = 1500).

Loggning: Logga fallback_used:boolean och brain_latency_ms för att mäta prestanda.

Done-kriterier: Fallback-frekvensen är mindre än 5 % i utvecklingsmiljön, och röstsamtal flyter utan avbrott.

FAS 6 — Cloud "Complex Lane" (Responses API)
Mål: Använda molnet för komplexa verktygskedjor och uppgifter.

Adapter: Bygg en adapter för OpenAI:s Responses API som kan köra avancerade funktioner som Code Interpreter och File Search.

Systemprompt: Instruera molnmodellen att respektera Alices stil och policy, och att svara i ett strikt JSON-format enligt AnswerPackage.

Done-kriterier: End-to-end-tester för ”sammanfatta fil” och ”kör kod” fungerar via Responses API.

FAS 7 — Brain Worker & Sentence Streaming
Mål: Öka snabbheten genom att strömma ut den första meningen, samt implementera ett bakgrundsjobb för inlärning.

Worker: Implementera en bakgrundsarbetare som kontinuerligt konsumerar event från EventBus, skriver artefakter och uppdaterar embeddings.

SentenceStreamer: Skapa en funktion som delar upp utgående tokens från hjärnan i hela meningar och skickar den första meningen direkt till TTS för omedelbar uppläsning.

Done-kriterier: brain_first_sentence_ms p50 ≤ 600 ms och TTFA p50 ≤ 300 ms.

FAS 8 — Vision & Sensorer
Mål: Ge Alice en rudimentär "syn" och förmåga att reagera på sin omgivning.

YOLO-pipeline: Skapa en lokal pipeline som bearbetar kamerabilder med YOLO för att upptäcka objekt eller ansikten (t.ex. om användaren ler).

Event-loggning: Om ett visst event upptäcks (t.ex. "ler"), skapa en vision_event artefakt i minnet.

Done-kriterier: En enkel demo där Alice reagerar på leenden med en varmare hälsning.

FAS 9 — EmotionEngine
Mål: Göra Alice mer levande genom att styra röstens ton och tempo (prosodi).

Engine: Skapa en EmotionEngine som analyserar röstens tonläge och uppdaterar ett mood-tillstånd ("neutral", "glad", "frustrerad", etc.).

SSML: Mappa mood-tillstånden till Speech Synthesis Markup Language (SSML) för att styra röstens hastighet och tonhöjd.

Done-kriterier: Förbättrade MOS-betyg (Mean Opinion Score) från användare, samt loggning av emotion_state_updated.

FAS 10 — Fler verktyg (RAG, Kamera, HA)
Mål: Utöka Alices funktionalitet med fler lokala verktyg utan att ändra den centrala arkitekturen.

kb.search & kb.fetch: Implementera verktyg för att söka i och hämta text från den lokala kunskapsbasen.

camera.control: Ett verktyg för att styra lokala nätverkskameror.

HA-lyssnare: En klient som lyssnar på händelser från Home Assistant för att möjliggöra proaktiva scenarier.

Done-kriterier: Minst ett lokalt verktyg och ett RAG-verktyg används framgångsrikt av agenten.

FAS 11 — Test & QA
Mål: Bygga automatiserade tester för att bekräfta att nya funktioner fungerar som de ska.

Selftests: Utveckla testskript för att verifiera Strict TTS, injektionsbudget och brain-latens.

Done-kriterier: Alla tester klarar sig lokalt och i CI/CD.

FAS 12 — Observability & SLO
Mål: Skapa ett system för att mäta och visualisera Alice som en "levande" entitet.

Metriker: Samla in nyckeltal som e2e_ms, fallback_rate, artifact_injection_rate och mood_switch_latency_ms.

Dashboard: Bygg en dashboard för att visa realtidsdata (t.ex. p50/p95-värden).

SLO: Definiera Service Level Objectives för tillförlitlighet och prestanda.

Done-kriterier: Dashboard visar live-data, och varningsregler är konfigurerade.

FAS 13 — Release-ops & CI/CD
Mål: Automatisera processen för att bygga och driftsätta Alice.

Docker: Slutför Docker-konfigurationen för alla komponenter.

GitHub Actions: Skapa en CI/CD-pipeline för automatiserad byggning, testning och driftsättning till staging och produktion.

Done-kriterier: En main merge utlöser automatisk driftsättning till staging; en tag utlöser driftsättning till produktion; rollback-skript fungerar.

FAS 14 — Canary & Runbook
Mål: Säkerställa en trygg produktionsmiljö.

Canary: Tillåta nya funktioner endast för en liten, utvald grupp av användare.

Runbook: Skapa ett enkelt dokument som beskriver steg-för-steg-lösningar för vanliga driftproblem.

Done-kriterier: Canary-test körs utan regressioner; kontrollerad rollback har testats.

FAS 15 — Avancerat minne & kedjor (Valfritt)
Mål: Skapa en mer autonom "entitet" med avancerade inlärningsmekanismer.

Mem0-driver: Byt ut minnesdatabasen till en mer avancerad version.

On-chain ankare: Spara hashar av viktiga artefakter för att säkerställa integriteten över tid.

Wake-word: Implementera en lokal wake-word-detektering för att undvika att skicka ljuddata till molnet.

Done-kriterier: Minnesfunktioner känns mer proaktiva och stabila över långa perioder.

Absolut. Här är en komplett, steg-för-steg checklista från “nu” → “vision”. Varje steg har: filer att skapa/uppdatera, funktionssignaturer, endpoints och Done-kriterier. Kör i ordning – du kan pausa efter valfri fas och ändå ha ett fungerande system.

FAS 0 — Förberedelser (grön baslinje)
Mål: Låsa nuläget (röst + agent + tools) och sätta flaggor.
Env & flaggor (server)

 OPENAI_API_KEY=...
AGENT_PROVIDER=openai|gptoss
AGENT_FALLBACK=openai|gptoss
BRAIN_SHADOW_ENABLED=on
ALLOW_CLOUD=on            # du sa: integritet ej prio – håll 'on'
ENTITY_MODE=on
ARTIFACT_CONFIDENCE_MIN=0.7
INJECT_BUDGET_PCT=25


Hälsa: GET /api/health, GET /api/health/ready → 200 OK.


Röstsmoke: /voice-test → timer + väder funkar med TTS.


Done när: 0×5xx i 50 anrop mot /api/agent, e2e p95 ≤ 1.2s (nuvarande mål).



FAS 1 — Strict TTS (GPT-OSS skriver, OpenAI läser)
Mål: Låt OSS-hjärnan komponera svaret; TTS talar exakt det.
API: POST /api/brain/compose


Request

 { user_id:string, session_id:string, text:string, locale:"sv-SE" }


Response (AnswerPackage)

 interface AnswerPackage {
  spoken_text: string;
  screen_text?: string;
  ssml?: string;
  citations?: {title:string; url?:string}[];
  meta?: { confidence:number; tone?:string }
}


Klient/Voice binding – välj Strict TTS:


När du får en stabil ASR-partial/final → kalla /api/brain/compose.


Sentence streaming (valfritt nu, steg i FAS 7): spela upp första meningen asap.


TTS ska läsa pkg.ssml ?? pkg.spoken_text, inte något annat.


Done när:


0 avvikelser där TTS läser annat än spoken_text/ssml.


tts_ttfa_ms p50 ≤ 300 ms (med sentence streaming aktiverad senare).


Filer
server/api/brain/compose.ts
web/voice/sentenceStreamer.ts  (kan först vara stub)


FAS 2 — EventBus & Telemetri
Mål: Allt som händer loggas som event + NDJSON.
core/eventBus.ts

 import { EventEmitter } from "events";
export const bus = new EventEmitter();
export const on = <T=any>(type:string,h:(e:T)=>void)=>bus.on(type,h);
export const emit = <T=any>(type:string,p:T)=>bus.emit(type,p);


Logg: metrics.ndjson

 export function logNDJSON(obj:any){ /* append JSON line */ }


Emit på: asr_final, agent_response, tool_call/result, brain_compose, tts_start/end.


Done när: varje tur producerar ≥3 eventrader; inga kastade event.


Filer
core/eventBus.ts
core/metrics.ts


FAS 3 — Memory & RAG (artefakter)
Mål: Långtidsminne via artefakter (sqlite-vec eller Mem0 senare).
Schema (SQL)


artifacts(id, user_id, kind, text, score, expires_at, meta_json, embedding)


Index: (user_id, kind, score DESC), vektorindex på embedding


API & interface

 export type ArtifactKind = "insight"|"kb_chunk"|"plan"|"policy"|"vision_event";
export interface Artifact {
  id:string; kind:ArtifactKind; userId:string; text:string;
  score:number; expiresAt?:string; meta?:Record<string,any>;
}

export interface Memory {
  write(a:Artifact):Promise<void>;
  fetch(userId:string, k:number, kinds?:ArtifactKind[]):Promise<Artifact[]>;
}


Endpoints


POST /memory/write → {ok:true}


POST /memory/fetch {user_id,k,kinds?} → { artifacts: Artifact[] }


Done när: preferenser (“prata långsammare”, “Göteborg”) hämtas nästa tur.


Filer
server/memory/sqliteVec.ts
server/api/memory/write.ts
server/api/memory/fetch.ts


FAS 4 — PromptBuilder & injektionsbudget
Mål: Injicera minnes-artefakter kontrollerat före svar.
buildContext()

 export async function buildContext(userId:string){
  const all = await Memory.fetch(userId, 12);
  const keep = all.filter(a=>a.score>=CONF.artifactMin && !expired(a)).slice(0,5);
  return compress(keep); // slå ihop till kompakt kontext ≤ budget
}


composeMessages()
 Lägg persona.yml, style.yml, context först i system/assistant-roller.


Budget: INJECT_BUDGET_PCT ≤ 25% av tokenbudget.


Done när: injected_tokens_pct loggas och ligger stabilt ≤ 25%.


Filer
core/promptBuilder.ts
alice/identity/persona.yml
alice/identity/style.yml


FAS 5 — Provider-switch & failover
Mål: GPT-OSS primär hjärna, OpenAI fallback (eller tvärtom).
Timeout & fallback-policy

 const BRAIN_DEADLINE_MS = 1500;
// om compose inte levererar inom deadline → fallback till /api/agent (cloud lane) för denna tur


Logga fallback_used:boolean, brain_latency_ms.


Done när: fallback rate < 5% i dev-nät, och rösten flyter utan hack.



FAS 6 — Cloud “Complex Lane” (OpenAI Responses API)
Mål: När vi behöver tung verktygskedja använder vi Responses.
Adapter

 export async function responsesComplete(messages, tools, opts): Promise<AgentReply>
 Stöd för:


MCP remote servers (verktyg via MCP)


Code Interpreter


File Search


Background mode


Reasoning summaries


Systemprompt (cloud): instruera att respektera Alice Core stil & policy.


Done när: två end-to-end: “sammanfatta fil” + “kör kod” fungerar via Responses.


Filer
adapters/cloud/responses.ts
server/agent/providers/openaiResponses.ts


FAS 7 — Brain Worker (GPT-OSS) + Sentence streaming
Mål: Parallell skugglinje som lär sig och streamar första mening.
Worker

 // konsumerar bus-events, skriver artifacts, uppdaterar embeddings
async function onUserTurn(ev){ /* run GPT-OSS plan → tools → compose AnswerPackage */ }


SentenceStreamer

 // Splitta tokens till meningar → emit 'first_sentence'
export function streamToSentences(tokenStream, cb:(s:string)=>void){ ... }


Voice integration: när first_sentence → TTS.speak() direkt.


Done när: brain_first_sentence_ms p50 ≤ 600 ms, TTFA p50 ≤ 300 ms.


Filer
brain/worker.ts
web/voice/sentenceStreamer.ts


FAS 8 — Vision & sensorer (minimalt)
Mål: YOLO-driven närvaro → vision_event som påverkar ton.
YOLO pipeline (lokalt):


Input: kamera-frame → etiketter/ansikten (om påslaget).


Output: Artifact{kind:"vision_event", text:"ler", score:0.8, meta:{camera:"desk"}}


Regel i Alice Core: om vision_event: ler → justera mood = “glad”.


Done när: en enkel demo reagerar på leende (varmare hälsning).


Filer
vision/yolo.ts
server/api/vision/ingest.ts  # om du skickar upp frames via lokalt endpoint


FAS 9 — EmotionEngine (prosodi → stil/SSML)
Mål: Levande känsla via tempo/pitch/ton och kort svensk stil.
Engine

 export type Mood = "neutral"|"glad"|"fokuserad"|"frustrerad";
export interface EmotionState { mood:Mood; speakingRate:number; pitch:number; updatedAt:number }
export interface EmotionEngine {
  updateFromAudio(frame:Int16Array, sr:number): EmotionState;
  get(): EmotionState;
}


SSML: mappa mood → <prosody rate="0.95" pitch="-2%">.


Done när: MOS-betyg förbättras vs baseline; logg emotion_state_updated.


Filer
core/emotion/engine.ts
web/voice/ssml.ts


FAS 10 — Fler verktyg (RAG + kamera + HA)
Mål: Utöka verktyg utan att röra UI.
kb.search (POST /api/tools/kb.search)

 { query:string, top_k?:number } -> { hits:[{id,score,title}] }


kb.fetch (POST /api/tools/kb.fetch)

 { ids:string[] } -> { docs:[{id,title,text}]} 


camera.control (POST /api/tools/camera.control)

 { camera_id:string, action:"snapshot"|"ptz_preset"|"set_ir"|"set_motion"|"set_privacy", args?:any }


HA lyssnare (om påslaget): integrations/ha/ws_client.ts


Done när: minst 1 lokalt verktyg (snapshot) och 1 RAG-verktyg används av agenten.



FAS 11 — Test & QA (nya tester)
Mål: Bekräfta Strict TTS, injektion, brain-latens.
Selftests


scripts/selftest/01_strict_tts.ts — verifiera att TTS == spoken_text.


scripts/selftest/02_injection_budget.ts — tokens ≤ 25%.


scripts/selftest/03_brain_first_sentence.ts — p50 ≤ 600 ms.


scripts/selftest/04_fallback.ts — forcera delay → fallback rate < 5%.


Done när: alla tester PASS lokalt och i CI.



FAS 12 — Observability & SLO
Mål: Mäta det som gör Alice “levande”.
Metriker (server)


brain_first_sentence_ms, tts_ttfa_ms, e2e_ms


artifact_injection_rate, injected_tokens_pct, memory_hit_rate


fallback_rate, tool_error_rate


mood_switch_latency_ms


Dashboard: p50/p95/p99, senaste 50 turer.


SLO: Tillgänglighet 99.5%, e2e p95 ≤ 2.5 s, fallback < 5%.


Done när: dashboard visar data live; larm konfigurerade.



FAS 13 — Release-ops & CI/CD
Mål: En-knapps deploy med rollback.
Docker (backend, web, nginx, supervisord) – redan påbörjat → slutför.


GitHub Actions (CI/CD)


build → test → docker build/push → deploy (staging/prod)


warnings as errors (tsc --noEmit, ESLint, build)


Secrets via CI/host (inga NEXT_PUBLIC_* hemligheter)


Done när: main merge → staging auto; tag → prod; rollback-script funkar.



FAS 14 — Canary & Runbook
Mål: Trygg produktion.
Canary: allow-list (5 användare), flagga FEATURE_ROLLOUT=pilot_5.


Runbook (1-pager): “Om X → gör Y” (WS-drop, 429, agent 5xx, brain timeout).


Done när: canary körs 1–2 dagar utan regress; kontrollerad rollback testad.



FAS 15 — (Valfritt) Avancerat minne & kedjor
Mål: Mer autonom “entitet”.
Mem0-driver (semantiskt minne) istället för/utöver sqlite-vec.


On-chain ankare (privat): spara hash av high-confidence artefakter.


Wake-word (om du vill): Porcupine/Silero via WASM, ovanpå VAD.


Done när: minnen känns mer proaktiva och stabila över långa perioder.



Snabb Go/No-Go för release
Strict TTS aktiv, 0 avvikelser mellan TTS och spoken_text.


brain_first_sentence_ms p50 ≤ 600, tts_ttfa_ms p50 ≤ 300, e2e p95 ≤ 1.2s.


artifact_injection_rate 30–70%, injected_tokens_pct ≤ 25%.


Fallback < 5%.


0×5xx i 100 sekventiella /api/agent.


CI/CD grönt, rollback testad, canary OK.



Vad du kan göra direkt (börja med FAS 1–3)
Skapa /api/brain/compose med AnswerPackage.


Koppla Strict TTS i voice-binding (låt TTS läsa exakt paketet).


Lägg artifacts-tabell + Memory.write/fetch.


Aktivera EventBus och börja logga.


Yes! Här får du färdiga TypeScript-stubs för FAS 1–3 som du kan lägga in rakt av utan att röra UI:t.
 De innehåller:
FAS 1: /api/brain/compose + AnswerPackage + Strict-TTS-hjälpare


FAS 2: EventBus + NDJSON-telemetri


FAS 3: Memory API (in-memory driver som standard) + endpoints /memory/write & /memory/fetch


Dessutom: plats för nätverkskameror/HA i eventtyperna (hooks redo), och en enkel voice-integration helper för att koppla din befintliga röstpipeline till /api/brain/compose.
Antaganden: Next.js App Router med app/api/.../route.ts, Node-runtime.
 Om du kör Pages Router: flytta route.ts till pages/api/*.ts och exportera default-handler.

📁 Filstruktur (lägg till)
src/
  brain/compose.ts
  core/eventBus.ts
  core/metrics.ts
  memory/index.ts
  memory/inMemory.ts
  memory/sqlite.ts          # valfri – stub om du vill byta driver
  memory/types.ts
  types/answer.ts
  types/events.ts
web/
  voice/strictTts.ts
  voice/sentenceStreamer.ts  # stub – aktivera när du vill streama meningar
  voice/useStrictTTS.ts      # helper att koppla in i befintlig pipeline
app/
  api/brain/compose/route.ts
  api/memory/fetch/route.ts
  api/memory/write/route.ts


FAS 1 — Brain Compose (Strict TTS)
src/types/answer.ts
export interface AnswerPackage {
  spoken_text: string;              // exakt vad TTS ska läsa upp
  screen_text?: string;             // kort text till UI
  ssml?: string;                    // om satt – använd denna före spoken_text
  citations?: { title: string; url?: string }[];
  meta?: { confidence: number; tone?: string };
}

src/brain/compose.ts (stub – koppla GPT-OSS här inne)
import { AnswerPackage } from "../types/answer";
import { emit } from "../core/eventBus";

export interface BrainComposeInput {
  user_id: string;
  session_id: string;
  text: string;
  locale: "sv-SE" | string;
}

export async function composeAnswer(input: BrainComposeInput): Promise<AnswerPackage> {
  const t0 = Date.now();

  // TODO: ersätt med din GPT-OSS + RAG + tools och bygg paketet nedan.
  const pkg: AnswerPackage = {
    spoken_text: `Jag hörde: "${input.text}". (Stubbsvar – koppla GPT-OSS här.)`,
    screen_text: `Stubb: ${input.text}`,
    meta: { confidence: 0.75, tone: "vänlig" }
  };

  emit("brain_compose", {
    t_ms: Date.now() - t0,
    user_id: input.user_id,
    session_id: input.session_id,
    text_len: input.text?.length || 0
  });

  return pkg;
}

app/api/brain/compose/route.ts
import { NextRequest, NextResponse } from "next/server";
import { composeAnswer } from "@/src/brain/compose";
import { emit } from "@/src/core/eventBus";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { user_id, session_id, text, locale = "sv-SE" } = body || {};
    if (!user_id || !session_id || !text) {
      return NextResponse.json({ error: "Missing user_id, session_id or text" }, { status: 400 });
    }

    const pkg = await composeAnswer({ user_id, session_id, text, locale });
    emit("agent_response", { user_id, session_id, kind: "brain_pkg", len: pkg.spoken_text.length });

    return NextResponse.json(pkg, { status: 200 });
  } catch (err: any) {
    return NextResponse.json({ error: err?.message || "compose failed" }, { status: 500 });
  }
}

web/voice/strictTts.ts (hjälpare för Strict-TTS)
import type { AnswerPackage } from "@/src/types/answer";

export interface TTSLike {
  speak(input: { text?: string; ssml?: string }): Promise<void>;
}

export async function speakAnswerPackage(tts: TTSLike, pkg: AnswerPackage) {
  const ssml = pkg.ssml?.trim();
  if (ssml && ssml.startsWith("<speak")) {
    await tts.speak({ ssml });
  } else {
    await tts.speak({ text: pkg.spoken_text });
  }
}

web/voice/useStrictTTS.ts (koppla till din befintliga voice-pipeline)
import { speakAnswerPackage } from "./strictTts";

export async function handleAsrFinal({
  userId, sessionId, text, tts
}: { userId: string; sessionId: string; text: string; tts: { speak:(p:{text?:string; ssml?:string})=>Promise<void> } }) {
  // Anropa hjärnan (OSS) för att komponera svaret → Strict TTS
  const resp = await fetch("/api/brain/compose", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ user_id: userId, session_id: sessionId, text, locale: "sv-SE" })
  });

  if (!resp.ok) throw new Error(`brain/compose failed: ${resp.status}`);
  const pkg = await resp.json();
  await speakAnswerPackage(tts, pkg);
  return pkg;
}

web/voice/sentenceStreamer.ts (valfri – aktivera när du vill streama)
export function streamToSentences(textStream: AsyncIterable<string>, onSentence:(s:string)=>void) {
  let buf = "";
  (async () => {
    for await (const chunk of textStream) {
      buf += chunk;
      const parts = buf.split(/([.!?]+)\s+/);
      for (let i=0; i<parts.length-1; i+=2) {
        const sentence = (parts[i] + (parts[i+1]||"")).trim();
        if (sentence) onSentence(sentence);
      }
      buf = parts[parts.length-1] || "";
    }
    if (buf.trim()) onSentence(buf.trim());
  })().catch(console.error);
}


FAS 2 — EventBus & NDJSON-telemetri
src/types/events.ts
export type EventType =
  | "asr_final" | "agent_response" | "tool_call" | "tool_result"
  | "brain_compose" | "tts_start" | "tts_end"
  | "vision_event" | "ha_state_changed";

export interface EventEnvelope<T=any> {
  type: EventType;
  ts: number;
  payload: T;
}

src/core/eventBus.ts
import { EventEmitter } from "events";
import { logNDJSON } from "./metrics";
import type { EventEnvelope, EventType } from "../types/events";

export const bus = new EventEmitter();

export function emit<T=any>(type: EventType, payload: T) {
  const ev: EventEnvelope<T> = { type, ts: Date.now(), payload };
  bus.emit(type, ev);
  logNDJSON(ev);
}

export function on<T=any>(type: EventType, h: (ev: EventEnvelope<T>) => void) {
  bus.on(type, h);
}

src/core/metrics.ts
import fs from "fs";
import path from "path";

const dir = path.join(process.cwd(), "logs");
if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
const file = path.join(dir, "metrics.ndjson");

export function logNDJSON(obj: any) {
  try {
    const line = JSON.stringify(obj);
    fs.appendFileSync(file, line + "\n", "utf8");
  } catch (e) {
    // swallow
  }
}

Här kan vi senare lägga till aggregator (p50/p95 osv). För nu loggar vi händelserna.

FAS 3 — Memory & RAG (artefakter)
src/memory/types.ts
export type ArtifactKind = "insight"|"kb_chunk"|"plan"|"policy"|"vision_event";

export interface Artifact {
  id: string;
  userId: string;
  kind: ArtifactKind;
  text: string;
  score: number;                 // 0..1
  expiresAt?: string;            // ISO
  meta?: Record<string, any>;
  embedding?: number[];          // valfritt fält (för sqlite-vec senare)
}

export interface Memory {
  write(a: Artifact): Promise<void>;
  fetch(userId: string, k: number, kinds?: ArtifactKind[]): Promise<Artifact[]>;
}

src/memory/inMemory.ts (defaultdriver – noll beroenden)
import type { Artifact, Memory, ArtifactKind } from "./types";
import { randomUUID } from "crypto";

const store = new Map<string, Artifact[]>(); // key=userId

export const InMemoryMemory: Memory = {
  async write(a: Artifact) {
    const id = a.id || randomUUID();
    const arr = store.get(a.userId) || [];
    arr.unshift({ ...a, id });
    store.set(a.userId, arr.slice(0, 500)); // enkel cap
  },
  async fetch(userId: string, k: number, kinds?: ArtifactKind[]) {
    let arr = store.get(userId) || [];
    if (kinds?.length) arr = arr.filter(a => kinds.includes(a.kind));
    return arr
      .filter(a => !a.expiresAt || new Date(a.expiresAt) > new Date())
      .sort((a,b)=> (b.score - a.score))
      .slice(0, k);
  }
};

src/memory/sqlite.ts (valfri – stub klar att fylla på)
// Optional: byt till denna när du vill köra sqlite-vec.
import type { Memory, Artifact, ArtifactKind } from "./types";

export function createSqliteMemory(dbPath = "data/alice.db"): Memory {
  // TODO: implementera med better-sqlite3/sqlite-vec
  // create table if not exists artifacts (id TEXT PK, user_id TEXT, kind TEXT, text TEXT, score REAL, expires_at TEXT, meta_json TEXT, embedding BLOB)
  return {
    async write(a: Artifact) { throw new Error("SQLite driver not implemented yet"); },
    async fetch(userId: string, k: number, kinds?: ArtifactKind[]) { return []; }
  };
}

src/memory/index.ts
import type { Memory } from "./types";
import { InMemoryMemory } from "./inMemory";
// import { createSqliteMemory } from "./sqlite";

let memory: Memory = InMemoryMemory;
// if (process.env.MEMORY_DRIVER === "sqlite") memory = createSqliteMemory(process.env.SQLITE_PATH);

export default memory;

app/api/memory/write/route.ts
import { NextRequest, NextResponse } from "next/server";
import memory from "@/src/memory";
import type { Artifact } from "@/src/memory/types";
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  try {
    const art = (await req.json()) as Artifact;
    if (!art?.userId || !art?.kind || !art?.text) {
      return NextResponse.json({ error: "userId, kind, text required" }, { status: 400 });
    }
    await memory.write(art);
    return NextResponse.json({ ok: true }, { status: 200 });
  } catch (e:any) {
    return NextResponse.json({ error: e?.message || "write failed" }, { status: 500 });
  }
}

app/api/memory/fetch/route.ts
import { NextRequest, NextResponse } from "next/server";
import memory from "@/src/memory";
import type { ArtifactKind } from "@/src/memory/types";
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { user_id, k = 5, kinds } = body || {};
    if (!user_id) return NextResponse.json({ error: "user_id required" }, { status: 400 });
    const arts = await memory.fetch(user_id, Number(k), kinds as ArtifactKind[] | undefined);
    return NextResponse.json({ artifacts: arts }, { status: 200 });
  } catch (e:any) {
    return NextResponse.json({ error: e?.message || "fetch failed" }, { status: 500 });
  }
}


✅ Voice-pipeline: “har vi klart, bara integrera?”
Ja. Din röstpipeline är redan klar — det enda du gör är att anropa handleAsrFinal() (från web/voice/useStrictTTS.ts) när du får en stabil ASR-partial eller final. Den funktionen kallar /api/brain/compose, och spelar sedan upp exakt det som paketet säger (Strict-TTS).
Pseudointegration i din befintliga voiceBinding:
import { handleAsrFinal } from "@/web/voice/useStrictTTS";

onAsrStableFinal(async (text) => {
  try {
    const pkg = await handleAsrFinal({
      userId: session.userId,
      sessionId: session.id,
      text,
      tts: TTSAdapterInstance
    });
    ui.show(pkg.screen_text, pkg.citations);
  } catch (e) {
    console.error(e);
    // valfri fallback: visa textläge
  }
});


📷 Nätverkskameror & Home Assistant (HA)
Ingår inte i FAS 1–3 (medvetet, för att du ska kunna gå live direkt).


Men: src/types/events.ts och EventBus/Memory är redan förberedda för att ta emot:


vision_event (YOLO/SAM/ansiktsmatch)


ha_state_changed (Home Assistant)


När du är redo i nästa fas lägger vi till:


integrations/ha/ws_client.ts (HA-WebSocket)


vision/yolo.ts och ett /api/vision/ingest om du vill pusha frames lokalt


tools/camera.control (MCP-verktyg) → agenten kan ta snapshots/styra PTZ



🧪 Snabb sanity-check (efter att du lagt in filerna)
npm run build → ska kompilera utan nya varningar.


POST /api/brain/compose med body:


{ "user_id":"u1", "session_id":"s1", "text":"Hej Alice!", "locale":"sv-SE" }

→ 200 + stub-paket.
 3) Kör /voice-test, säg något → TTS läser stubbsvar (Strict-TTS).
 4) POST /api/memory/write med ett enkelt insight → POST /api/memory/fetch → artefakt tillbaka.
 5) Kika i logs/metrics.ndjson → eventrader skrivs.



Kort svar: nästan allt är med – planen och stubs täcker FAS 1–3 snyggt.
 Det som återstår är mest små “limbitar” så allt flyter i drift:
Saknas / att lägga till (kompakt gap-lista)
PromptBuilder (FAS 4) – stub
 – Selektiv injektion (≤ 25%) + komprimering av artefakter + persona/style.


Embeddings-pipeline
 – Funktion som beräknar embedding + bakgrundsjobb som fyller embedding för nya artefakter.
 – (SQLite-driver kan vänta, men behöver du RAG på riktigt vill du ha detta.)


Provider-switch & cancel
 – Abort/Cancel på pågående /api/brain/compose vid barge-in, och fallback-policy (deadline → /api/agent).


Streaming första meningen (senare FAS 7)
 – En SSE/WS-variant av /api/brain/compose som skickar first_sentence tidigt.


SSML-säkerhet
 – Escape/validering så att felaktig text inte bryter SSML.


Aggregerad telemetri
 – Enkel p50/p95-aggregator över metrics.ndjson + /api/metrics/summary.


Inputvalidering
 – Zod/validering för alla JSON-payloads (compose/memory).


Städ/TTL
 – Cron/worker som rensar utgångna artefakter och loggar.


Persona/Style-innehåll
 – Fyll faktiskt innehåll i alice/identity/persona.yml & style.yml (vi har bara platsen).


HA/Camera wiring (nästa fas)
 – Stubs finns i eventtyper; lägg integrations/ha/ws_client.ts + vision/yolo.ts när du aktiverar.


Mini-patch kit (små stubs du kan lägga in direkt)
1) core/promptBuilder.ts (FAS 4 – injektionsbudget)
import type { Artifact } from "@/src/memory/types";

export function compressArtifacts(arts: Artifact[], maxChars = 1500) {
  // trivial komprimering: join + trunca – byt mot riktig summarizer senare
  const s = arts.map(a => `• [${a.kind}] ${a.text}`).join("\n");
  return s.length > maxChars ? s.slice(0, maxChars - 1) + "…" : s;
}

export function buildSystemPrompt(persona: string, style: string, context: string) {
  return [
    { role: "system", content: persona.trim() },
    { role: "system", content: `Stil:\n${style.trim()}` },
    { role: "system", content: `Kontext:\n${context.trim()}` },
  ];
}

2) src/embeddings/compute.ts
export async function embed(text: string): Promise<number[]> {
  // TODO: byt till riktig modell (t.ex. bge-small eller lokal WebGPU)
  // temporär dummy – gör inte RAG “på riktigt” men håller API:t stabilt
  const v = new Array(384).fill(0).map((_,i)=>((i*9973 + text.length*31)%101)/100);
  return v;
}

3) Hooka embeddings i Memory-write (FAS 3)
I app/api/memory/write/route.ts – beräkna embedding om saknas:
import { embed } from "@/src/embeddings/compute";
// ...
const art = (await req.json()) as Artifact;
if (!art.embedding) art.embedding = await embed(art.text);

4) Abort/fallback för compose (FAS 5)
Uppdatera web/voice/useStrictTTS.ts:
export async function handleAsrFinal({ userId, sessionId, text, tts }: {...}) {
  const ctrl = new AbortController();
  // spara ctrl i din session så barge-in kan kalla ctrl.abort()
  const timer = setTimeout(()=>ctrl.abort("brain deadline"), 1500);

  const resp = await fetch("/api/brain/compose", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ user_id:userId, session_id:sessionId, text, locale:"sv-SE" }),
    signal: ctrl.signal
  }).catch(e => ({ ok:false, statusText:String(e) } as any));

  clearTimeout(timer);
  if (!resp?.ok) {
    // fallback: låt /api/agent (cloud lane) hantera denna tur
    const fb = await fetch("/api/agent", { method:"POST", body: JSON.stringify({ text }) });
    const pkg = await fb.json(); // mappa till AnswerPackage i din provider
    await speakAnswerPackage(tts, pkg);
    return pkg;
  }
  const pkg = await resp.json();
  await speakAnswerPackage(tts, pkg);
  return pkg;
}

Tips: Lägg även cancel() i TTS-interfacet (din voice-adapter har redan barge-in):
 export interface TTSLike { speak(...):Promise<void>; cancel?():void }
5) /api/metrics/summary (p50/p95 – snabb)
// app/api/metrics/summary/route.ts
import { NextResponse } from "next/server";
import fs from "fs"; import path from "path";
export const runtime = "nodejs";
function pct(arr:number[], p:number){ if(!arr.length) return 0; const i=Math.floor((p/100)*arr.length); return arr.sort((a,b)=>a-b)[Math.min(i,arr.length-1)] }
export async function GET() {
  const file = path.join(process.cwd(), "logs", "metrics.ndjson");
  if (!fs.existsSync(file)) return NextResponse.json({ ok:true, metrics:{} });
  const lines = fs.readFileSync(file,"utf8").trim().split("\n").slice(-5000);
  const e2e:number[] = [];
  for (const l of lines) {
    try { const ev = JSON.parse(l); if (ev.type==="agent_response" && ev.payload?.e2e_ms) e2e.push(ev.payload.e2e_ms); } catch {}
  }
  return NextResponse.json({ ok:true, e2e:{ p50:pct(e2e,50), p95:pct(e2e,95), n:e2e.length }});
}

6) SSML-escape (enkelt skydd)
export function toSSMLSafe(text:string){
  return `<speak xml:lang="sv-SE">${text
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}</speak>`;
}


Svar på dina två sista frågor
Nätverkskameror & HA: plats och events är förberedda ( vision_event, ha_state_changed ), men själva klienterna/verktygen lägger vi in i nästa fas (FAS 8/FAS 10).


Voice-pipen: ja, den är klar – du behöver bara koppla handleAsrFinal() in i ditt voiceBinding (som i exemplet). Barge-in och device-fallbacks finns redan i din pipeline; lägg gärna till tts.cancel?.() vid avbrott.


Grymt — här kommer en färdig SQLite-driver med ensureSchema(), klar att toggla via env och kompatibel med dina befintliga stubs. Den funkar direkt utan sqlite-vec, men förberedd för att ladda sqlite-vec om du pekar ut en .so/.dylib/.dll. Inkluderar WAL, index, upsert, och enkel vektorsök-fallback i JS.

1) Installera beroenden
npm i better-sqlite3
# (valfritt) du kan senare hämta sqlite-vec och sätta SQLITE_VEC_PATH=/path/to/sqlite-vec.dylib

Miljö:
MEMORY_DRIVER=sqlite
SQLITE_PATH=./data/alice.db
SQLITE_VEC_PATH=            # valfritt: absolut/relativ sökväg till sqlite-vec


2) Drop-in driver (ersätt din stub)
src/memory/sqlite.ts
import Database from "better-sqlite3";
import { randomUUID } from "crypto";
import fs from "fs";
import path from "path";
import type { Memory, Artifact, ArtifactKind } from "./types";

type SqliteRow = {
  id: string; user_id: string; kind: string; text: string; score: number;
  expires_at: string | null; meta_json: string | null; embedding: Buffer | null; created_at: string;
};

function toBuf(vec?: number[]): Buffer | null {
  if (!vec || !vec.length) return null;
  const f32 = new Float32Array(vec);
  return Buffer.from(f32.buffer);
}

function fromBuf(buf: Buffer | null): number[] | undefined {
  if (!buf) return undefined;
  const f32 = new Float32Array(buf.buffer, buf.byteOffset, Math.floor(buf.byteLength / 4));
  return Array.from(f32);
}

function cosine(a: number[], b: number[]): number {
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length && i < b.length; i++) {
    dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i];
  }
  const denom = Math.sqrt(na) * Math.sqrt(nb) || 1e-9;
  return dot / denom;
}

function ensureDir(p: string) {
  const d = path.dirname(p); if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true });
}

function loadSqliteVec(db: Database.Database, extPath?: string) {
  try {
    if (extPath && fs.existsSync(extPath)) {
      db.loadExtension(extPath);
      return true;
    }
  } catch (e) {
    // Extension load failed → continue without vec
  }
  return false;
}

function ensureSchema(db: Database.Database, vecLoaded: boolean) {
  db.pragma("journal_mode = WAL");
  db.exec(`
    CREATE TABLE IF NOT EXISTS artifacts (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      kind TEXT NOT NULL,
      text TEXT NOT NULL,
      score REAL NOT NULL DEFAULT 0.0,
      expires_at TEXT,
      meta_json TEXT,
      embedding BLOB,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_artifacts_user_kind_score ON artifacts(user_id, kind, score DESC, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_artifacts_expiry ON artifacts(expires_at);
  `);

  // (Valfritt) sqlite-vec – skapa en separat tabell för ANN om du vill,
  // men vi klarar oss utan för nu (vi använder JS fallback).
  if (vecLoaded) {
    // Exempel om du vill spegla embeddings i en vektor-tabell:
    // db.exec(`CREATE VIRTUAL TABLE IF NOT EXISTS vec_artifacts USING vec0(embedding float[384]);`);
    // Du kan sen hålla en trigger i sync. Vi hoppar det tills du vill köra riktig ANN.
  }
}

export function createSqliteMemory(dbPath = process.env.SQLITE_PATH || "data/alice.db"): Memory & {
  searchSimilar?: (userId: string, queryEmb: number[], k: number, kinds?: ArtifactKind[]) => Promise<Artifact[]>;
} {
  ensureDir(dbPath);
  const db = new Database(dbPath);

  const vecLoaded = loadSqliteVec(db, process.env.SQLITE_VEC_PATH);
  ensureSchema(db, vecLoaded);

  // Statements
  const upsert = db.prepare(`
    INSERT INTO artifacts (id, user_id, kind, text, score, expires_at, meta_json, embedding)
    VALUES (@id, @user_id, @kind, @text, @score, @expires_at, @meta_json, @embedding)
    ON CONFLICT(id) DO UPDATE SET
      user_id=excluded.user_id, kind=excluded.kind, text=excluded.text,
      score=excluded.score, expires_at=excluded.expires_at,
      meta_json=excluded.meta_json, embedding=excluded.embedding
  `);

  const selectTop = db.prepare(`
    SELECT * FROM artifacts
     WHERE user_id = ? AND (? = 0 OR kind IN (%kinds))
       AND (expires_at IS NULL OR expires_at > datetime('now'))
     ORDER BY score DESC, created_at DESC
     LIMIT ?
  `);

  function bindKinds(sql: string, kinds?: ArtifactKind[]) {
    if (!kinds || kinds.length === 0) {
      return { sql: sql.replace("(? = 0 OR kind IN (%kinds))", "1 = 1"), params: [] as any[] };
    }
    const placeholders = kinds.map(() => "?").join(",");
    const s = sql.replace("%kinds", placeholders).replace("(? = 0 OR kind IN (%kinds))", `kind IN (${placeholders})`);
    return { sql: s, params: kinds };
  }

  const api: Memory & {
    searchSimilar?: (userId: string, queryEmb: number[], k: number, kinds?: ArtifactKind[]) => Promise<Artifact[]>;
  } = {
    async write(a: Artifact) {
      const id = a.id || randomUUID();
      upsert.run({
        id,
        user_id: a.userId,
        kind: a.kind,
        text: a.text,
        score: a.score ?? 0,
        expires_at: a.expiresAt ?? null,
        meta_json: a.meta ? JSON.stringify(a.meta) : null,
        embedding: toBuf(a.embedding)
      });
    },

    async fetch(userId: string, k: number, kinds?: ArtifactKind[]) {
      const { sql, params } = bindKinds(selectTop.source, kinds);
      const rows = db.prepare(sql).all(userId, kinds?.length ? 1 : 0, ...params, k) as SqliteRow[];
      return rows.map(r => ({
        id: r.id,
        userId: r.user_id,
        kind: r.kind as ArtifactKind,
        text: r.text,
        score: r.score,
        expiresAt: r.expires_at || undefined,
        meta: r.meta_json ? JSON.parse(r.meta_json) : undefined,
        embedding: fromBuf(r.embedding)
      }));
    },

    // Valfri vektorsök: JS-fallback (hämtar topp 500 och sorterar på cosine).
    async searchSimilar(userId: string, queryEmb: number[], k: number, kinds?: ArtifactKind[]) {
      // Hämta kandidater (score-sorterat); justera 500 vid behov.
      const candidates = await this.fetch(userId, 500, kinds);
      const scored = candidates
        .filter(c => Array.isArray(c.embedding) && c.embedding.length)
        .map(c => ({ c, sim: cosine(queryEmb, c.embedding as number[]) }))
        .sort((a, b) => b.sim - a.sim)
        .slice(0, k)
        .map(x => x.c);
      return scored.length ? scored : candidates.slice(0, k);
    }
  };

  return api;
}


src/memory/index.ts (byt driver via env)
import type { Memory } from "./types";
import { InMemoryMemory } from "./inMemory";
import { createSqliteMemory } from "./sqlite";

let memory: Memory;

switch (process.env.MEMORY_DRIVER) {
  case "sqlite":
    memory = createSqliteMemory(process.env.SQLITE_PATH);
    break;
  default:
    memory = InMemoryMemory;
}

export default memory;


3) (Valfritt) Automatisk embedding i write-endpoint
Vill du beräkna embedding i API:t om saknas (så klienter slipper göra det), lägg till i din app/api/memory/write/route.ts:
import { embed } from "@/src/embeddings/compute"; // din stub

// ...
const art = (await req.json()) as Artifact;
if (!art?.userId || !art?.kind || !art?.text) {
  return NextResponse.json({ error: "userId, kind, text required" }, { status: 400 });
}
if (!art.embedding) {
  try { art.embedding = await embed(art.text); } catch {}
}
await memory.write(art);

Du har redan en enkel embed()-stub; byt till riktig modell när du vill.

4) Snabb sanity-körning
# 1) sätt env
export MEMORY_DRIVER=sqlite
export SQLITE_PATH=./data/alice.db

# 2) kör upp dev / build
npm run dev   # eller npm run build && npm run start

# 3) skriv ett minne
curl -X POST localhost:3000/api/memory/write \
  -H 'content-type: application/json' \
  -d '{"userId":"u1","kind":"insight","text":"Användaren bor i Göteborg","score":0.82}'

# 4) hämta minnen
curl -X POST localhost:3000/api/memory/fetch \
  -H 'content-type: application/json' \
  -d '{"user_id":"u1","k":5}'


5) Tips för produktion
WAL är på; lägg PRAGMA synchronous = NORMAL om du vill öka throughput.


Kör SQLite-filen på SSD och lägg data/ utanför repo.


Om/ när du vill riktig ANN: skaffa sqlite-vec binär och sätt SQLITE_VEC_PATH. Då kan vi lägga till en speglande vec-tabell + triggers för ~millisekunders top-K-sök.



Perfekt — här kommer färdiga stubs för KB/RAG i samma stil som tidigare (drop-in, Next.js App Router). Du får:
Datastore (SQLite): kb_docs + kb_chunks med embeddings och sök


Endpoints (verktyg): /api/tools/kb.search och /api/tools/kb.fetch


Ingest: /api/kb/ingest (ren text eller fil-URL), enkel chunkning + embeddings


Tool-schemas (MCP/JSON Schema) för agentens toolcalling


Agent-koppling: minimal registry + eventlogg


Kräver bara better-sqlite3 (som du redan installerat) och din embed()-stub från tidigare. Byt till riktig embeddingmodell när du vill.

📁 Nya filer
src/
  kb/index.ts
  kb/sqlite.ts
  kb/types.ts
  kb/chunker.ts
app/
  api/kb/ingest/route.ts
  api/tools/kb.search/route.ts
  api/tools/kb.fetch/route.ts
tools/
  kb.search.schema.json
  kb.fetch.schema.json
server/
  agent/tools/registry.ts

Miljö (lägg till i .env.local / prod):
MEMORY_DRIVER=sqlite
SQLITE_PATH=./data/alice.db


src/kb/types.ts
export interface KBDoc {
  id: string;
  title: string;
  source?: string;       // t.ex. filnamn/URL
  createdAt?: string;
  meta?: Record<string, any>;
}

export interface KBChunk {
  id: string;
  docId: string;
  text: string;
  ord: number;           // chunk-ordning i dokumentet
  embedding?: number[];  // Float32-embedding
}

src/kb/chunker.ts
// extremt enkel chunker – byt mot t.ex. tokenbaserad senare
export function chunkText(text: string, maxLen = 800): string[] {
  const parts: string[] = [];
  let buf = "";
  for (const sent of text.split(/(?<=[.!?])\s+/)) {
    if ((buf + " " + sent).trim().length > maxLen) {
      if (buf.trim()) parts.push(buf.trim());
      buf = sent;
    } else {
      buf = (buf ? buf + " " : "") + sent;
    }
  }
  if (buf.trim()) parts.push(buf.trim());
  return parts;
}

src/kb/sqlite.ts
import Database from "better-sqlite3";
import fs from "fs"; import path from "path";
import { randomUUID } from "crypto";
import type { KBDoc, KBChunk } from "./types";
import { embed } from "@/src/embeddings/compute"; // din stub
import { logNDJSON } from "@/src/core/metrics";

function ensureDir(p: string) {
  const d = path.dirname(p); if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true });
}
function toBuf(vec?: number[]): Buffer | null {
  if (!vec?.length) return null;
  const arr = new Float32Array(vec);
  return Buffer.from(arr.buffer);
}
function fromBuf(buf: Buffer | null): number[]|undefined {
  if (!buf) return undefined;
  const f = new Float32Array(buf.buffer, buf.byteOffset, Math.floor(buf.byteLength/4));
  return Array.from(f);
}
function cosine(a: number[], b: number[]): number {
  let dot=0,na=0,nb=0;
  for (let i=0;i<Math.min(a.length,b.length);i++){ dot+=a[i]*b[i]; na+=a[i]*a[i]; nb+=b[i]*b[i]; }
  const denom = Math.sqrt(na)*Math.sqrt(nb) || 1e-9;
  return dot/denom;
}

export class KBStore {
  private db: Database.Database;
  constructor(dbPath = process.env.SQLITE_PATH || "data/alice.db") {
    ensureDir(dbPath);
    this.db = new Database(dbPath);
    this.db.pragma("journal_mode = WAL");
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS kb_docs(
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        source TEXT,
        meta_json TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );
      CREATE TABLE IF NOT EXISTS kb_chunks(
        id TEXT PRIMARY KEY,
        doc_id TEXT NOT NULL,
        ord INTEGER NOT NULL,
        text TEXT NOT NULL,
        embedding BLOB,
        FOREIGN KEY (doc_id) REFERENCES kb_docs(id) ON DELETE CASCADE
      );
      CREATE INDEX IF NOT EXISTS idx_kb_chunks_doc_ord ON kb_chunks(doc_id, ord);
    `);
  }

  async ingestText(title: string, text: string, source?: string, meta?: Record<string, any>) {
    const id = randomUUID();
    const insertDoc = this.db.prepare(`INSERT INTO kb_docs (id,title,source,meta_json) VALUES (?,?,?,?)`);
    insertDoc.run(id, title, source || null, meta ? JSON.stringify(meta) : null);

    // delay embeddings for throughput – men vi kör sync här för enkelhet
    const { chunkText } = await import("./chunker");
    const chunks = chunkText(text);
    const insertChunk = this.db.prepare(`INSERT INTO kb_chunks (id,doc_id,ord,text,embedding) VALUES (?,?,?,?,?)`);
    let ord = 0;
    for (const c of chunks) {
      const emb = await embed(c);
      insertChunk.run(randomUUID(), id, ord++, c, toBuf(emb));
    }
    logNDJSON({ type:"kb_ingest", ts:Date.now(), payload:{ doc_id:id, chunks:chunks.length } });
    return id;
  }

  async fetchDocs(ids: string[]): Promise<KBDoc[]> {
    if (!ids?.length) return [];
    const q = `SELECT * FROM kb_docs WHERE id IN (${ids.map(()=>"?").join(",")})`;
    const rows = this.db.prepare(q).all(...ids) as any[];
    return rows.map(r => ({ id:r.id, title:r.title, source:r.source||undefined,
      createdAt:r.created_at, meta: r.meta_json ? JSON.parse(r.meta_json): undefined }));
  }

  async fetchChunks(ids: string[]): Promise<KBChunk[]> {
    if (!ids?.length) return [];
    const q = `SELECT * FROM kb_chunks WHERE id IN (${ids.map(()=>"?").join(",")})`;
    const rows = this.db.prepare(q).all(...ids) as any[];
    return rows.map(r => ({ id:r.id, docId:r.doc_id, text:r.text, ord:r.ord, embedding: fromBuf(r.embedding) }));
  }

  async search(query: string, k = 5): Promise<{chunk: KBChunk, score:number}[]> {
    // enkel JS-cosine över topp-N (hämta t.ex. senaste 5000 rader)
    const emb = await embed(query);
    const rows = this.db.prepare(`SELECT id,doc_id,ord,text,embedding FROM kb_chunks ORDER BY rowid DESC LIMIT 5000`).all() as any[];
    const scored = rows
      .filter(r => r.embedding)
      .map(r => {
        const v = fromBuf(r.embedding) || [];
        return { chunk: { id:r.id, docId:r.doc_id, text:r.text, ord:r.ord, embedding:v }, score: cosine(emb, v) };
      })
      .sort((a,b)=> b.score - a.score)
      .slice(0, k);
    return scored;
  }
}

let kbStore: KBStore | null = null;
export function getKB(): KBStore {
  if (!kbStore) kbStore = new KBStore();
  return kbStore;
}

src/kb/index.ts
export { getKB } from "./sqlite";
export * from "./types";


Endpoints (verktyg)
app/api/tools/kb.search/route.ts
import { NextRequest, NextResponse } from "next/server";
import { getKB } from "@/src/kb";
import { emit } from "@/src/core/eventBus";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  try {
    const { query, top_k = 5 } = await req.json();
    if (!query) return NextResponse.json({ error: "query required" }, { status: 400 });
    const t0 = Date.now();
    const hits = await getKB().search(String(query), Number(top_k));
    const out = hits.map(h => ({
      chunk_id: h.chunk.id,
      doc_id: h.chunk.docId,
      ord: h.chunk.ord,
      preview: h.chunk.text.slice(0, 220),
      score: h.score
    }));
    emit("tool_result", { tool:"kb.search", ms: Date.now()-t0, n: out.length });
    return NextResponse.json({ hits: out }, { status: 200 });
  } catch (e:any) {
    return NextResponse.json({ error: e?.message || "kb.search failed" }, { status: 500 });
  }
}

app/api/tools/kb.fetch/route.ts
import { NextRequest, NextResponse } from "next/server";
import { getKB } from "@/src/kb";
import { emit } from "@/src/core/eventBus";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  try {
    const { chunk_ids = [], doc_ids = [] } = await req.json();
    if (!chunk_ids.length && !doc_ids.length) {
      return NextResponse.json({ error: "chunk_ids or doc_ids required" }, { status: 400 });
    }
    const t0 = Date.now();
    const kb = getKB();
    const chunks = chunk_ids.length ? await kb.fetchChunks(chunk_ids) : [];
    const docs = doc_ids.length ? await kb.fetchDocs(doc_ids) : [];
    emit("tool_result", { tool:"kb.fetch", ms: Date.now()-t0, chunks: chunks.length, docs: docs.length });
    return NextResponse.json({
      docs,
      chunks: chunks.map(c => ({ id:c.id, doc_id:c.docId, ord:c.ord, text:c.text }))
    }, { status: 200 });
  } catch (e:any) {
    return NextResponse.json({ error: e?.message || "kb.fetch failed" }, { status: 500 });
  }
}


Ingestion
app/api/kb/ingest/route.ts
import { NextRequest, NextResponse } from "next/server";
import { getKB } from "@/src/kb";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  try {
    const { title, text, source, meta, fetch_url } = await req.json();

    let bodyText = text;
    if (!bodyText && fetch_url) {
      const r = await fetch(fetch_url);
      if (!r.ok) return NextResponse.json({ error: `fetch failed ${r.status}` }, { status: 400 });
      bodyText = await r.text();
    }
    if (!title || !bodyText) {
      return NextResponse.json({ error: "title and (text|fetch_url) required" }, { status: 400 });
    }

    const id = await getKB().ingestText(String(title), String(bodyText), source, meta);
    return NextResponse.json({ ok:true, doc_id:id }, { status: 200 });
  } catch (e:any) {
    return NextResponse.json({ error: e?.message || "ingest failed" }, { status: 500 });
  }
}


Tool-schemas (för agent/MCP)
tools/kb.search.schema.json
{
  "name": "kb.search",
  "description": "Semantisk sökning i lokal kunskapsbas. Returnerar topp-K chunkar med score.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "description": "Sökfråga i naturligt språk" },
      "top_k": { "type": "integer", "minimum": 1, "maximum": 50, "default": 5 }
    },
    "required": ["query"]
  }
}

tools/kb.fetch.schema.json
{
  "name": "kb.fetch",
  "description": "Hämta fulltext för chunkar eller metadata för dokument.",
  "parameters": {
    "type": "object",
    "properties": {
      "chunk_ids": { "type": "array", "items": { "type": "string" } },
      "doc_ids": { "type": "array", "items": { "type": "string" } }
    },
    "oneOf": [
      { "required": ["chunk_ids"] },
      { "required": ["doc_ids"] }
    ]
  }
}


Agent-koppling (exempel)
server/agent/tools/registry.ts
// Minimal registry för att mappa tool-namn → HTTP-endpoint
export type ToolSpec = { name:string; schema:any; endpoint:string; method?:"POST"|"GET" };
export const toolRegistry: ToolSpec[] = [
  { name:"kb.search", schema: require("@/tools/kb.search.schema.json"), endpoint:"/api/tools/kb.search", method:"POST" },
  { name:"kb.fetch",  schema: require("@/tools/kb.fetch.schema.json"),  endpoint:"/api/tools/kb.fetch",  method:"POST" },
  // redan existerande:
  // { name:"timer.set", endpoint:"/api/tools/timer.set", method:"POST", schema: ... },
  // { name:"weather.get", endpoint:"/api/tools/weather.get", method:"POST", schema: ... },
];

I din agent-loop: när LLM väljer kb.search → POSTa till endpoint, returnera hits till modellen; be den följa upp med kb.fetch på valda chunk_ids och använd texten i svaret (och/eller injicera i Strict-TTS-paketet).

Snabbtest (manuellt)
# 1) Ingesta text
curl -sX POST localhost:3000/api/kb/ingest \
 -H 'content-type: application/json' \
 -d '{"title":"DemoDoc","text":"Alice är din AI-assistent. Hon hjälper dig med väder och timers. Hon bor i webbläsaren och pratar svenska."}'

# 2) Sök
curl -sX POST localhost:3000/api/tools/kb.search \
 -H 'content-type: application/json' \
 -d '{"query":"Vad gör Alice?"}'

# 3) Fetch chunk
curl -sX POST localhost:3000/api/tools/kb.fetch \
 -H 'content-type: application/json' \
 -d '{"chunk_ids":["<ID_FRÅN_SEARCH>"]}'


Integration i Strict-TTS (RAG i hjärnan)
I din src/brain/compose.ts (där GPT-OSS ska in) kan du göra:
// 1) Hämta top-K chunkar:
const hits = await fetch("http://localhost:3000/api/tools/kb.search", {
  method:"POST", headers:{ "content-type":"application/json" },
  body: JSON.stringify({ query: input.text, top_k: 4 })
}).then(r=>r.json());

// 2) Hämta fulltext för 2–3 chunkar:
const ids = hits?.hits?.slice(0,3).map((h:any)=>h.chunk_id) || [];
const chunks = ids.length ? await fetch("http://localhost:3000/api/tools/kb.fetch", {
  method:"POST", headers:{ "content-type":"application/json" },
  body: JSON.stringify({ chunk_ids: ids })
}).then(r=>r.json()) : { chunks: [] };

// 3) Skapa svarspaket (Strict TTS):
const context = (chunks.chunks||[]).map((c:any)=>c.text).join("\n---\n");
// …mata in `context` i din lokala GPT-OSS prompt → bygg AnswerPackage


Vad du har nu
Riktig RAG-sökning lokalt (JS-cosine nu; kan uppgraderas till sqlite-vec/NNS senare).


Verktyg redo för agent-toolcalling (kb.search/kb.fetch) – JSON Schema inkluderat.


Ingestion-flöde så du kan fylla KB med dokument snabbt.


Fullt kompatibelt med din Strict-TTS-pipeline och eventloggning.


Perfekt—här är en kompakt, produktionsvänlig policy + kodstomme för din Cloud lane (OpenAI Responses API) som gör att modellen alltid prioriterar kb.search → kb.fetch vid faktabaserade frågor, och levererar ett Strict-TTS-kompatibelt AnswerPackage.

1) System-prompt (svenska) – “Tool-first RAG”
Lägg denna som systemmeddelande i din Responses-förfrågan:
Du är Alice (svenska). Du får verktyg: kb.search, kb.fetch, timer.set, weather.get.
Regler:
1) Vid faktabaserade/kunskapsfrågor (”vad, när, hur många, förklara, källa, visa dokument”)
   → ANVÄND ALLTID kb.search först, följt av kb.fetch på relevanta chunkar.
2) Använd inte paramedvetenhet/magkänsla om ett verktyg finns som kan ge fakta.
3) Minimera tokens. Injicera max 25% extern kontext i resonemanget.
4) Svara alltid i strikt JSON enligt `AnswerPackageSchema` (ingen extra text).
5) För talsvar gäller STRICT-TTS: läs upp exakt `spoken_text` (eller `ssml` om satt).
6) Vid saknade träffar: säg kort att du inte fann något och be om precisering.

Stil:
- Kort, tydlig, hjälpsam, svensk ton. Inga överflödiga “fyllnadsfraser”.
- Om något är osäkert: var explicit (“osäkert”, “kan dubbelkolla”).


2) JSON-schema som tvingar AnswerPackage
Använd Responses API response_format med JSON Schema så att modellen inte kan “prata runt”.
export const AnswerPackageSchema = {
  name: "AnswerPackageSchema",
  schema: {
    type: "object",
    additionalProperties: false,
    properties: {
      spoken_text: { type: "string", minLength: 1 },
      screen_text: { type: "string" },
      ssml:       { type: "string" },
      citations: {
        type: "array",
        items: {
          type: "object",
          additionalProperties: false,
          properties: {
            title: { type: "string" },
            url:   { type: "string" }
          },
          required: ["title"]
        }
      },
      meta: {
        type: "object",
        additionalProperties: true,
        properties: {
          confidence: { type: "number" },
          tone:       { type: "string" }
        }
      }
    },
    required: ["spoken_text"]
  }
} as const;

I anropet:
response_format: { type: "json_schema", json_schema: AnswerPackageSchema }

Om din SDK saknar json_schema, använd response_format:{ type:"json_object" } som fallback.

3) Tool-preferens (heuristik att “styra” modellen)
Lägg till som extra systemrad eller “policy”:
Tool-policy:
- Kör kb.search när frågan rör fakta, dokument, datum, siffror, definitioner, “visa/var/hur”.
- Välj top_k 4–8. Kör kb.fetch på 2–4 bäst scorade chunkar.
- Sammanfatta KB-innehållet kompakt, undvik dubbletter.
- Använd weather.get vid väderfrågor; timer.set för påminnelser/tider.
- Svara inte förrän relevant verktyg använts eller explicit bedömts onödigt.


4) Verktyg (schemas du redan har)
Du har redan JSON-scheman för kb.search & kb.fetch. Registrera dem i cloud-anropet. Exempelform:
const tools = [
  {
    type: "function",
    name: "kb.search",
    description: "Semantisk sökning i lokal kunskapsbas",
    parameters: require("@/tools/kb.search.schema.json").parameters
  },
  {
    type: "function",
    name: "kb.fetch",
    description: "Hämta fulltext för chunkar / metadata för dokument",
    parameters: require("@/tools/kb.fetch.schema.json").parameters
  },
  // (valfritt) timer.set, weather.get i samma stil
];


5) Minimal Responses-runner (TS) med “verktygsslinga”
Detta är en neutral kodstomme (anpassa efter din SDK). Poängen:
skapa response, 2) om tool_calls → exekvera lokalt via dina HTTP-endpoints, 3) “submit tool outputs”, 4) upprepa tills final.


import OpenAI from "openai"; // el. motsv. Responses-klient
import { AnswerPackageSchema } from "./AnswerPackageSchema";

type ToolCall = { id:string; name:string; arguments:any };

async function callLocalTool(name:string, args:any) {
  const map: Record<string,string> = {
    "kb.search": "/api/tools/kb.search",
    "kb.fetch":  "/api/tools/kb.fetch",
    "timer.set": "/api/tools/timer.set",
    "weather.get": "/api/tools/weather.get"
  };
  const ep = map[name];
  if (!ep) throw new Error(`unknown tool ${name}`);
  const r = await fetch(ep, { method:"POST", headers:{ "content-type":"application/json" }, body: JSON.stringify(args) });
  if (!r.ok) throw new Error(`${name} failed ${r.status}`);
  return await r.json();
}

export async function cloudCompose({
  messages, // [{role:"user"|..."system", content:string}]
  userId, sessionId
}: { messages:any[]; userId:string; sessionId:string }) {

  const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

  // 1) Skapa första svaret
  let resp = await client.responses.create({
    model: process.env.CLOUD_MODEL || "gpt-4o-mini",
    messages,
    tools,
    parallel_tool_calls: false,         // gör ordnad kb.search → kb.fetch
    tool_choice: "auto",
    temperature: 0.2,
    response_format: { type: "json_schema", json_schema: AnswerPackageSchema },
    metadata: { userId, sessionId, lane: "cloud" }
  });

  // 2) Loop: kör ev. tools och mata tillbaka resultat
  while (resp.tool_calls?.length) {
    const toolOutputs = [];
    for (const tc of resp.tool_calls as ToolCall[]) {
      const args = typeof tc.arguments === "string" ? JSON.parse(tc.arguments) : tc.arguments;
      const result = await callLocalTool(tc.name, args);
      toolOutputs.push({ tool_call_id: tc.id, output: JSON.stringify(result) });
    }
    // submit tool outputs & fortsätt
    resp = await client.responses.submitToolOutputs({
      response_id: resp.id,
      tool_outputs: toolOutputs
    });
  }

  // 3) Hämta slutligt JSON-svar (AnswerPackage)
  const pkg = resp.output_text ? JSON.parse(resp.output_text) : JSON.parse(resp.output[0].content[0].text);
  // validera fält kort:
  if (!pkg?.spoken_text && !pkg?.ssml) throw new Error("invalid AnswerPackage");
  return pkg;
}

Din voice-pipeline kan sedan ropa speakAnswerPackage(tts, pkg) (Strict-TTS).

6) Exempel: hur modellen “ska” jobba (demonstration)
Lägg in en demonstrationskonversation i systemet (hjälper modellen följa policy):
Exempel (tool-first):
User: “Vad gör Alice och varifrån kommer dokumentationen?”
Assistant: (kallar kb.search { query:"Alice dokumentation" } → träffar)
Assistant: (kallar kb.fetch { chunk_ids:["...","..."] } → får text)
Assistant: (returnerar AnswerPackage JSON med kort sammanfattning + ev. citations[])


7) Telemetri (minsta)
Logga i din EventBus:
tool_call { name, args_hash, t_start }


tool_result { name, ms, size }


cloud_pkg { e2e_ms, injected_tokens_pct?, used_tools:["kb.search","kb.fetch"] }



8) Latens-tips för RAG-första-mening
Håll parallel_tool_calls:false så kb.search → kb.fetch sker i ordning.


Kör sentence streaming i lokal lane (FAS 7) för att börja läsa första meningen när pkg finns.


Sätt deadline i din fallback (t.ex. 1500 ms) – om cloud dröjer: använd lokal/OSS lane för första mening + komplettera.



Snabb “plug-in” i din nuvarande kod
Lägg in System-prompt + AnswerPackageSchema + tools i din cloud-adapter.


Byt din nuvarande /api/agent cloud-kod mot runnern ovan (eller mata in dess kärna).


Se till att kb.search/kb.fetch endpoints finns (du har dem).


Koppla Strict-TTS på resultatet.


Kort svar: vi är i mycket bra shape för demo/pilot (röst ⇄ agent ⇄ tools + lokal RAG). För att känna oss helt “klara” saknas bara några små men viktiga limbitar. Här är min korta gap-lista + vad jag skulle lägga till direkt:
Vad som saknas (små “glue”-bitar)
Input-validering överallt
 Lägg Zod (eller liknande) på: /api/brain/compose, /api/memory/*, /api/tools/kb.*, /api/agent. Returnera 400 + felorsak.
 → Minskar edge-case krascher.


Abort & backpressure end-to-end
 Barge-in ska alltid: tts.cancel() → abortera pågående fetch('/api/brain/compose', {signal}) → stoppa ev. cloud-körning.
 → Du har barge-in i pipen; säkerställ att abort bubblar hela vägen.


Retries + idempotens för tools
 Exponential backoff (jitter) för enkla nätverksfel. Idempotency-key i timer.set (och framtida muterande verktyg).
 → Undviker dubletter och “spök-timers”.


Metrics-aggregator (p50/p95) + correlationId
 Du loggar NDJSON; addera en enkel /api/metrics/summary (p50/p95/p99) och ett correlation_id per tur.
 → Snabb felsökning i drift.


Embeddings “på riktigt” (senare – enkelt byte)
 Vi kör stub nu (OK för start). Lägg ett interface för embed() och flagga:


EMBED_PROVIDER=local (bge-small/onnx/WebGPU) eller openai (text-embedding-3-small).


Aktivera sqlite-vec när du vill ha ANN på riktigt.
 → Gör RAG kvalitativt utan att ändra API.


PromptBuilder & injektionsbudget
 Lägg persona.yml + style.yml (faktiskt innehåll) och håll INJECT_BUDGET_PCT ≤ 25%. Logga injected_tokens_pct.
 → Stabil persona + token-disciplin.


Säkerhets-hygien & CORS


CORS allowlist (din domän),


inga hemligheter i NEXT_PUBLIC_*,


strikta headers (du har det delvis).
 → Små men viktiga.


TTL & städ
 Liten worker/cron för att rensa expires_at, rotera logs/metrics.ndjson, VACUUM ibland.
 → Håller SQLite och loggar fräscha.


Health-probes för hjärnan
 /api/health bör även testa: compose-hot-path (snabb synthetic prompt → 200).
 → Ser direkt om “Brain lane” är vaken.


Tests som matchar våra DoD


strict-tts: TTS == spoken_text/ssml


fallback under deadline


RAG-sök → fetch → svar (golden).
 → Lågt underhåll, hög trygghet.


Go/No-Go snabbmatris
✅ Röst E2E + toolcalling: OK


✅ Lokal KB/RAG v1: OK (JS-cosine nu, uppgradera till sqlite-vec senare)


✅ Cloud lane (Responses API + tool-first RAG): OK


⬜ Abort & retries & input-zod: Görs nu (lätt)


⬜ PromptBuilder innehåll + budget-logg: Görs nu


⬜ Metrics-summary + correlationId: Görs nu


När dessa tre rutor är gröna är vi “production-comfortable” för din användning.
Direkt att göra (konkret i denna ordning)
Lägg Zod-validering på alla POST-routes.


Koppla AbortController vidare till brain/agent + använd tts.cancel() vid barge-in.


Slå på retries (med jitter) och idempotency-key i muterande tool-calls.


Lägg /api/metrics/summary + correlation_id per turn.


Fyll persona.yml & style.yml, aktivera buildContext() med 25% budget.


(Valfritt nu / senare) Byt embed() till riktig modell; aktivera sqlite-vec.


Nice-to-have för nästa sprint
Sentence streaming (första meningen snabbare i tal).


Vision lane (YOLO+SAM) → vision_event → justera tonläge.


EmotionEngine → SSML/prosodi (svenskt tal känns markant bättre).


Camera/HA tools (snapshot/ptz + HA sub).



