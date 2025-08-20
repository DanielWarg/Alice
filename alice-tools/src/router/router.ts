import { normalizeSv, extractTimeSlots, extractVolumeSlots, extractLanguage, extractRoomSlot, extractDeviceSlot } from "./slots.js";
import { logRouterTelemetry } from "./telemetry.js";
import pino from "pino";

const log = pino({ level: "info" });

type Match = { intent: string; score: number; phrase: string };

const LEXICON: Record<string, string[]> = {
  // Exakta kommandon med hög confidence
  PLAY: [
    "spela", "spela upp", "spela musik", "starta musik", "fortsätt spela", 
    "kör musik", "kör igång musiken", "starta", "fortsätt", "play",
    "kör", "kör låten", "starta låten", "spela låten", "sätt igång",
    "börja spela", "spela vidare", "kör vidare"
  ],
  PAUSE: [
    "pausa", "paus", "pausa musiken", "stoppa musiken", "pausa låten", 
    "stoppa låten", "ta paus", "gör paus", "pause", "vänta",
    "pausa lite", "håll upp", "ta en paus", "paus i musiken",
    "pausar", "pausar musiken", "pausar låten"
  ],
  STOP: [
    "stop", "stopp", "stoppa", "avsluta", "sluta spela",
    "avbryt", "stäng av musiken", "stäng av låten"
  ],
  NEXT: [
    "nästa", "nästa låt", "hoppa över", "byt låt", "hoppa fram", 
    "spela nästa", "nästa spår", "next", "skip", "skippa",
    "byt", "nästa sång", "framåt", "forward", "hoppa till nästa",
    "gå till nästa", "nästa track"
  ],
  PREV: [
    "föregående", "förra", "förra låten", "spela förra", "föregående låt",
    "gå tillbaka", "previous", "förra spåret", "bakåt", "back",
    "förra sången", "tillbaka", "backa", "förra track",
    "spela föregående", "föregående spår"
  ],
  SEEK_FWD: [
    "spola fram", "hoppa fram", "snabbspola framåt",
    "spola framåt", "fast forward", "ff"
  ],
  SEEK_BACK: [
    "spola tillbaka", "hoppa tillbaka", "snabbspola bakåt",
    "spola bakåt", "rewind", "rew"
  ],
  SEEK_TO: [
    "hoppa till", "gå till", "spela från", "börja vid",
    "starta från", "spola till", "spela från början"
  ],
  VOL_UP: [
    "höj volymen", "höj volym", "öka volym", "högre volym", "starkare", 
    "skruva upp", "spela högre", "spela starkare", "öka ljudet",
    "högre", "starkare ljud", "mer volym"
  ],
  VOL_DOWN: [
    "sänk volymen", "sänk volym", "minska volym", "lägre volym", "tystare", 
    "skruva ner", "spela lägre", "spela tystare", "minska ljudet",
    "lägre", "tystare ljud", "mindre volym"
  ],
  SET_VOL: [
    "volym", "sätt volymen till", "ställ volymen på", "volym procent",
    "sätt volym", "ställ in volym", "sätt ljudet på", "ställ ljudet på",
    "volym till", "ljudvolym", "volymnivå"
  ],
  MUTE: [
    "mute", "stäng av ljudet", "tysta", "ljud av", "tyst läge",
    "dämpa", "tystna", "håll tyst", "inget ljud", "stäng ljudet",
    "tysta musiken", "tysta låten", "muta"
  ],
  UNMUTE: [
    "unmute", "avmuta", "slå på ljud", "ljud på", "avdämpa",
    "sätt på ljudet", "aktivera ljud", "starta ljud", "återställ ljud",
    "ljud tillbaka", "sätt på ljudet igen"
  ],
  // Kortformer för fraser som "höj 20%" / "sänk 15%"
  VOL_UP_SHORT: ["höj"],
  VOL_DOWN_SHORT: ["sänk"],
  SET_VOL_MAX: ["max", "maximalt", "högsta", "full volym", "högsta volym"],
  SET_VOL_MIN: ["min", "minimalt", "tyst", "ingen volym", "lägsta volym"],
  // Nya kommandon för upprepning/shuffle
  REPEAT: [
    "repetera", "upprepa", "spela om", "spela igen", "repeat",
    "loop", "loopa", "om igen", "en gång till", "repetera låten",
    "upprepa låten", "spela om låten"
  ],
  SHUFFLE: [
    "shuffle", "blanda", "slumpa", "spela blandat", "random",
    "slumpvis", "blanda låtar", "slumpmässigt", "shuffla",
    "blanda spellistan", "spela random"
  ],
  // Favorithantering
  LIKE: [
    "gilla", "like", "tumme upp", "favorit", "spara låt",
    "lägg till favoriter", "markera som favorit", "gilla låten",
    "spara denna låt", "lägg till i favoriter"
  ],
  UNLIKE: [
    "ogilla", "unlike", "tumme ner", "ta bort favorit",
    "ta bort från favoriter", "avmarkera favorit", "ogilla låten",
    "ta bort denna låt", "sluta gilla"
  ]
};

// Mappa intent till verktygsnamn
const TOOL_MAP: Record<string, string> = {
  PLAY: "PLAY",
  PAUSE: "PAUSE",
  STOP: "STOP",
  NEXT: "NEXT",
  PREV: "PREV",
  SEEK_FWD: "SEEK",
  SEEK_BACK: "SEEK",
  SEEK_TO: "SEEK",
  VOL_UP: "SET_VOLUME",
  VOL_DOWN: "SET_VOLUME",
  SET_VOL: "SET_VOLUME",
  SET_VOL_MAX: "SET_VOLUME",
  SET_VOL_MIN: "SET_VOLUME",
  VOL_UP_SHORT: "SET_VOLUME",
  VOL_DOWN_SHORT: "SET_VOLUME",
  MUTE: "MUTE",
  UNMUTE: "UNMUTE",
  REPEAT: "REPEAT",
  SHUFFLE: "SHUFFLE",
  LIKE: "LIKE",
  UNLIKE: "UNLIKE"
};

function scoreMatch(input: string, phrase: string): number {
  const a = normalizeSv(input);
  const b = normalizeSv(phrase);
  
  // Exakt matchning
  if (a === b) {
    log.debug({ input: a, phrase: b, score: 1.0 }, 'Exact match');
    return 1.0;
  }
  
  // Exakt delmatchning (t.ex. "spela musik" matchar "spela")
  // Om input är längre än frasen, ge lägre score
  if (a.includes(b)) {
    log.debug({ input: a, phrase: b, score: 0.85 }, 'Input contains phrase');
    return 0.85;
  }
  // Om frasen är längre än input, ge högre score
  if (b.includes(a)) {
    log.debug({ input: a, phrase: b, score: 0.95 }, 'Phrase contains input');
    return 0.95;
  }
  
  // Ordöverlappning med striktare regler
  const aWords = a.split(" ");
  const bWords = b.split(" ");
  
  // Kräv att alla ord från den kortare frasen finns med
  const [shorter, longer] = aWords.length < bWords.length ? [aWords, bWords] : [bWords, aWords];
  const allWordsMatch = shorter.every(word => longer.includes(word));
  if (!allWordsMatch) return 0;
  
  // Beräkna överlappning med straffavdrag för extra ord
  const overlap = shorter.length / longer.length;
  const score = Math.min(0.85, overlap);
  log.debug({ input: a, phrase: b, shorter: shorter.join(' '), longer: longer.join(' '), overlap, score }, 'Word overlap');
  return score;
}

export function ruleFirstClassify(input: string): Match | null {
  let best: Match | null = null;
  
  try {
    for (const [intent, synonyms] of Object.entries(LEXICON)) {
      for (const s of synonyms) {
        const score = scoreMatch(input, s);
        if (!best || score > best.score) best = { intent, score, phrase: s };
      }
    }

    const result = best && best.score >= 0.85 ? best : null;
    
    // Log telemetry
    if (result) {
      log.info({ input, intent: result.intent, score: result.score, phrase: result.phrase }, 'Rule match found');
    } else {
      log.debug({ input }, 'No rule match found');
    }

    return result;
  } catch (error) {
    log.error({ error, input }, 'Error in ruleFirstClassify');
    throw error;
  }
}

export type RoutedCall = { name: string; args: any };

export function mapIntentToTool(input: string, intent: string): RoutedCall | null {
  try {
    const t = normalizeSv(input);
    let result: RoutedCall | null = null;
    const toolName = TOOL_MAP[intent];

    if (!toolName) {
      log.warn({ intent }, 'Unknown intent, no tool mapping found');
      return null;
    }

    switch (intent) {
      // Enkla kommandon utan args
      case "PLAY":
      case "PAUSE":
      case "STOP":
      case "NEXT":
      case "PREV":
      case "MUTE":
      case "UNMUTE":
      case "REPEAT":
      case "SHUFFLE":
      case "LIKE":
      case "UNLIKE":
        result = { name: toolName, args: {} };
        break;

      // Seek-kommandon med tidsinställningar
      case "SEEK_FWD": {
        const slots = extractTimeSlots(t);
        result = { name: toolName, args: { direction: "FWD", seconds: slots.seconds ?? 10 } };
        break;
      }
      case "SEEK_BACK": {
        const slots = extractTimeSlots(t);
        result = { name: toolName, args: { direction: "BACK", seconds: slots.seconds ?? 10 } };
        break;
      }
      case "SEEK_TO": {
        const slots = extractTimeSlots(t);
        if (slots.endpoint === "START") result = { name: toolName, args: { position: 0 } };
        else if (slots.endpoint === "END") result = { name: toolName, args: { position: 1 } };
        else if (slots.endpoint) result = { name: toolName, args: { endpoint: slots.endpoint } };
        else if (slots.to) result = { name: toolName, args: { to: slots.to } };
        break;
      }

      // Volymkommandon med nivå/delta
      case "VOL_UP":
      case "VOL_UP_SHORT": {
        const s = extractVolumeSlots(t);
        if (typeof (s as any).level === 'number') {
          result = { name: toolName, args: { level: (s as any).level } };
        } else {
          const delta = typeof s.delta === 'number' ? s.delta : 10;
          result = { name: toolName, args: { delta } };
        }
        break;
      }
      case "VOL_DOWN":
      case "VOL_DOWN_SHORT": {
        const s = extractVolumeSlots(t);
        if (typeof (s as any).level === 'number') {
          result = { name: toolName, args: { level: (s as any).level } };
        } else {
          const delta = typeof s.delta === 'number' ? -Math.abs(s.delta) : -10;
          result = { name: toolName, args: { delta } };
        }
        break;
      }
      case "SET_VOL": {
        const s = extractVolumeSlots(t);
        if (typeof s.level === 'number') {
          result = { name: toolName, args: { level: s.level } };
        }
        break;
      }
      case "SET_VOL_MAX":
        result = { name: toolName, args: { level: 100 } };
        break;
      case "SET_VOL_MIN":
        result = { name: toolName, args: { level: 0 } };
        break;
    }

    if (result) {
      log.info({ input, intent, tool: result }, 'Mapped intent to tool');
    } else {
      log.warn({ input, intent }, 'Failed to map intent to tool');
    }

    return result;
  } catch (error) {
    log.error({ error, input, intent }, 'Error in mapIntentToTool');
    throw error;
  }
}

export function ruleFirstRoute(input: string): RoutedCall | null {
  try {
    // Up-front: TRANSFER/CAST detection with room/device slots
    const t = normalizeSv(input);
    if (/\b(casta|cast|spela\s+pa|spela\s+p\u00e5|overfor|\u00f6verf\u00f6r|byt\s+till)\b/.test(t)) {
      const dev = extractDeviceSlot(t) || extractRoomSlot(t);
      if (dev) {
        const result = { name: "TRANSFER", args: { device: dev } };
        log.info({ input, result }, 'Device transfer detected');
        return result;
      }
    }

    const m = ruleFirstClassify(input);
    if (!m) {
      log.debug({ input }, 'No rule match found');
      return null;
    }

    const result = mapIntentToTool(input, m.intent);
    if (result) {
      log.info({ input, intent: m.intent, tool: result }, 'Successfully routed to tool');
    } else {
      log.warn({ input, intent: m.intent }, 'Failed to route to tool');
    }

    return result;
  } catch (error) {
    log.error({ error, input }, 'Error in ruleFirstRoute');
    throw error;
  }
}