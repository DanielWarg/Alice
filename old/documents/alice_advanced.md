# 🤖 Alice Advanced Features

## Agent Core v1 - Autonomous Workflows

Alice har ett **Agent Core v1** system som kan:

- **Planning**: Bryta ner komplexa mål i steg
- **Execution**: Utföra actions med dependencies  
- **Criticism**: Analysera resultat och föreslå förbättringar
- **Orchestration**: Koordinera hela Planning→Execution→Criticism cycles

### Exempel på Autonomous Workflow

```yaml
Goal: "Spela musik och sätt volym till 75"
Plan:
  - step_1: PLAY (musik)
  - step_2: SET_VOLUME (level=75, depends_on=[step_1])
```

## Enhanced TTS System

Alice's röst har **3 personligheter**:
- **Alice** (standard, vänlig)
- **Formell** (professionell)  
- **Casual** (avslappnad)

Plus **5 emotionella toner**:
- Neutral, Happy, Calm, Confident, Friendly

## Google Calendar Integration  

Alice förstår svenska kalendekommandon:
- "Visa min kalender"
- "Boka möte imorgon kl 14"
- "Flytta mötet till fredag"

Hon kan även:
- Detektera konflikter automatiskt
- Föreslå alternativa tider
- Skicka mötesagenda via e-post

## Testscenario

När användaren säger: **"Boka lunch med Maria på fredag 12:30"**

Alice gör:
1. Kontrollerar kalendern för konflikter
2. Skapar event om tid är ledig
3. Skickar inbjudan till Maria
4. Bekräftar bokningen

Detta är **avancerad testdata** för RAG-verifiering.