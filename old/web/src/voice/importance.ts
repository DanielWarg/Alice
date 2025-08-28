// Heuristik för att bedöma "viktighet" i transkriberat tal
// Score 0-3: endast ≥2 går in i summary highlights

export interface ImportanceScore {
  score: number;
  reasons: string[];
}

export function scoreImportance(text: string): ImportanceScore {
  const reasons: string[] = [];
  let score = 0;
  
  const lowerText = text.toLowerCase().trim();
  
  // Ignorera om för kort
  if (lowerText.length < 8) {
    return { score: 0, reasons: ['too_short'] };
  }
  
  // Named entities och specifika detaljer (+1)
  if (hasNamedEntities(lowerText)) {
    score += 1;
    reasons.push('named_entities');
  }
  
  // Tider och datum (+1)
  if (hasTimeReferences(lowerText)) {
    score += 1;
    reasons.push('time_references');
  }
  
  // Första-person intention/minne (+1)
  if (hasFirstPersonIntention(lowerText)) {
    score += 1;
    reasons.push('first_person_intention');
  }
  
  // Siffror och kvantiteter (+1)
  if (hasNumbersOrQuantities(lowerText)) {
    score += 1;
    reasons.push('numbers_quantities');
  }
  
  // Financial context gets extra importance (+1)
  if (hasFinancialContext(lowerText)) {
    score += 1;
    reasons.push('financial_context');
  }
  
  // Frågor och kommandon utan svar (0) - markera men spara inte
  if (isUnansweredQuestion(lowerText)) {
    score = Math.max(0, score - 1);
    reasons.push('unanswered_question');
  }
  
  // Småprat eller fyllnadsord (-1) - men bara om inget viktigt redan hittat
  if (isSmallTalk(lowerText) && score === 0) {
    score = Math.max(0, score - 1);
    reasons.push('small_talk');
  }
  
  return { score: Math.min(3, score), reasons };
}

function hasNamedEntities(text: string): boolean {
  // Enkla heuristiker för svenska namn, platser, företag
  const patterns = [
    /\b[A-ZÅÄÖ][a-zåäöé]+(?:\s+[A-ZÅÄÖ][a-zåäöé]+)*\b/, // Versaler (namn)
    /\b(?:stockholm|göteborg|malmö|uppsala|linköping|örebro|västerås|helsingborg|jönköping|norrköping)\b/i,
    /\b(?:ica|coop|willys|hemköp|city gross|maxi)\b/i,
    /\b(?:spotify|google|microsoft|apple|amazon|netflix)\b/i,
  ];
  
  return patterns.some(pattern => pattern.test(text));
}

function hasTimeReferences(text: string): boolean {
  const timePatterns = [
    /\b(?:idag|imorgon|igår|nästa\s+\w+|förra\s+\w+)\b/i,
    /\b(?:måndag|tisdag|onsdag|torsdag|fredag|lördag|söndag)\b/i,
    /\b(?:\d{1,2}[:.]\d{2}|\d{1,2}\s+(?:på|för))\b/i,
    /\b(?:januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)\b/i,
    /\b(?:klockan|tiden|tid|schema|möte|träff)\b/i,
  ];
  
  return timePatterns.some(pattern => pattern.test(text));
}

function hasFirstPersonIntention(text: string): boolean {
  const intentionPatterns = [
    /\b(?:jag\s+ska|jag\s+kommer|jag\s+planerar|jag\s+tänker)\b/i,
    /\b(?:kom\s+ihåg|påminn|notera|spara)\b/i,
    /\b(?:jag\s+behöver|jag\s+vill|jag\s+måste)\b/i,
    /\b(?:min\s+plan|mina\s+mål|mitt\s+schema)\b/i,
    /\b(?:betala|betalar|betalning)\b/i,  // Financial actions
  ];
  
  return intentionPatterns.some(pattern => pattern.test(text));
}

function hasNumbersOrQuantities(text: string): boolean {
  const numberPatterns = [
    /\b\d+(?:[.,]\d+)?\s*(?:kr|kronor|euro|dollar|sek|usd|eur)\b/i,
    /\b\d+(?:[.,]\d+)?\s*(?:kg|gram|liter|meter|km|mil|timmar|dagar|veckor)\b/i,
    /\b(?:en|två|tre|fyra|fem|sex|sju|åtta|nio|tio)\s+(?:tusen|miljoner|miljarder)\b/i,
    /\b\d+(?:[.,]\d+)?%\b/,
    /\b\d{1,2}[:.]\d{2}\b/, // Tider
  ];
  
  return numberPatterns.some(pattern => pattern.test(text));
}

function isUnansweredQuestion(text: string): boolean {
  // Frågor som verkar ställas till Alice men inte besvarats
  return /[?]$/.test(text.trim()) || /\b(?:vad|hur|när|var|varför|vem)\b.*[?]?$/i.test(text);
}

function isSmallTalk(text: string): boolean {
  const smallTalkPatterns = [
    /\b(?:mm|hmm|ah|eh|öh|ja|nej|okej|ok)\b$/i,
    /\b(?:hej|hejdå|tack|tack så mycket|bra|fine|okej då)\b$/i,
    /^(?:.*\s)?(?:mm|hmm|ja|nej|okej)(?:\s.*)?$/i,
  ];
  
  // Endast småprat om korta meddelanden UTAN siffror, namn eller specifikt innehåll
  const hasSpecificContent = hasNamedEntities(text) || hasNumbersOrQuantities(text) || hasTimeReferences(text);
  
  return !hasSpecificContent && (
    smallTalkPatterns.some(pattern => pattern.test(text)) || 
    (text.length < 15 && !/\d/.test(text))
  );
}

function hasFinancialContext(text: string): boolean {
  const financialPatterns = [
    /\b(?:betala|betalning|hyra|lön|lån|skuld|faktura|räkning|kostnad)\b/i,
    /\b(?:bank|sparkonto|swish|kort|mastercard|visa)\b/i,
    /\b\d+\s*(?:kr|kronor)\b/i,
  ];
  
  return financialPatterns.some(pattern => pattern.test(text));
}