# Gmail Integration Setup för Alice

Alice kan nu skicka, läsa och söka e-post via Gmail API. Följ dessa steg för att konfigurera Gmail-integration.

## 1. Skapa Gmail API Credentials

1. Gå till [Google Cloud Console](https://console.cloud.google.com/)
2. Skapa ett nytt projekt eller använd ett befintligt
3. Aktivera Gmail API:
   - Gå till "APIs & Services" > "Library"
   - Sök efter "Gmail API" och aktivera det
4. Skapa credentials:
   - Gå till "APIs & Services" > "Credentials"
   - Klicka "Create Credentials" > "OAuth 2.0 Client IDs"
   - Välj "Desktop application" som typ
   - Ladda ner JSON-filen

## 2. Installera Credentials

1. Döp om den nedladdade filen till `gmail_credentials.json`
2. Placera filen i `/Users/evil/Desktop/EVIL/PROJECT/Alice/alice/server/`
3. Filen kommer automatiskt upptäckas av Alice

## 3. Första Autentisering

När du använder Gmail-funktioner första gången:

1. Alice kommer visa en URL för autentisering
2. Öppna URL:en i webbläsaren
3. Logga in med ditt Google-konto
4. Kopiera auktoriseringskoden
5. Klistra in koden när Alice frågar

Detta behöver bara göras en gång - Alice sparar credentials automatiskt.

## 4. Aktivera Gmail-verktyg

Lägg till Gmail-verktygen i din `.env` fil:

```bash
ENABLED_TOOLS=PLAY,PAUSE,SET_VOLUME,SEND_EMAIL,READ_EMAILS,SEARCH_EMAILS
```

## 5. Använda Gmail-funktioner

### Skicka E-post
```
"Skicka mail till chef@företag.se med ämne 'Projektuppdatering'"
"Send email to john@example.com subject 'Meeting tomorrow'"
```

### Läsa E-post
```
"Visa nya mail"
"Läs de senaste 5 e-posten"
"Check emails"
```

### Söka E-post
```
"Sök mail från chef"
"Hitta mail om projekt"
"Search emails from last week"
```

## Säkerhetsnoter

- Gmail credentials sparas lokalt och skickas aldrig till externa servrar
- Alice har endast access till ditt Gmail (inte andra Google-tjänster)
- Du kan återkalla access när som helst via Google Account Settings

## Felsökning

**Problem: "Gmail-tjänst inte tillgänglig"**
- Kontrollera att `gmail_credentials.json` finns i server-mappen
- Verifiera internetanslutning
- Kör autentiseringsprocessen igen

**Problem: "Invalid credentials"**
- Ta bort `gmail_token.pickle` och autentisera igen
- Kontrollera att Gmail API är aktiverat i Google Cloud Console

**Problem: Import-fel**
- Installera Gmail-beroenden: `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`