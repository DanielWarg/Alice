# Gmail Integration Setup för Alice

Alice kan nu skicka, läsa och söka e-post via Gmail API med fullständig OAuth 2.0-autentisering. Följ dessa steg för att konfigurera Gmail-integration.

## 1. Förutsättningar

Kontrollera att Gmail-beroenden är installerade:
```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

## 2. Skapa Gmail API Credentials

### Steg-för-steg Google Cloud Console Setup:

1. **Gå till Google Cloud Console**
   - Besök [https://console.cloud.google.com/](https://console.cloud.google.com/)
   - Logga in med ditt Google-konto

2. **Skapa eller välj projekt**
   - Klicka på projektväljaren längst upp
   - Skapa nytt projekt: "Alice Gmail Integration" eller använd befintligt
   - Anteckna projekt-ID:t för framtida referens

3. **Aktivera Gmail API**
   - Gå till "APIs & Services" > "Library"
   - Sök efter "Gmail API"
   - Klicka på "Gmail API" och sedan "Enable"
   - Vänta tills aktivering är klar

4. **Konfigurera OAuth-medgivandeskärm**
   - Gå till "APIs & Services" > "OAuth consent screen"
   - Välj "External" för användartyp (om inte G Workspace)
   - Fyll i obligatoriska fält:
     - App name: "Alice Voice Assistant"
     - User support email: din e-post
     - Developer contact: din e-post
   - Lägg till scopes: `../auth/gmail.modify`
   - Lägg till testanvändare (din egen e-post för testning)

5. **Skapa OAuth 2.0 Credentials**
   - Gå till "APIs & Services" > "Credentials"
   - Klicka "Create Credentials" > "OAuth 2.0 Client IDs"
   - Application type: "Desktop application"
   - Name: "Alice Desktop Client"
   - Klicka "Create"
   - **Ladda ner JSON-filen omedelbart**

## 3. Installera Credentials

1. **Döp om credentials-filen**
   ```bash
   mv ~/Downloads/client_secret_*.json gmail_credentials.json
   ```

2. **Placera filen i rätt mapp**
   ```bash
   cp gmail_credentials.json /Users/evil/Desktop/EVIL/PROJECT/Alice/alice/server/
   ```

3. **Verifiera placeringen**
   ```bash
   ls -la /Users/evil/Desktop/EVIL/PROJECT/Alice/alice/server/gmail_credentials.json
   ```

## 4. Aktivera Gmail-verktyg

Redigera din `.env` fil för att inkludera Gmail-verktygen:

```bash
# In /Users/evil/Desktop/EVIL/PROJECT/Alice/alice/.env
ENABLED_TOOLS=PLAY,PAUSE,SET_VOLUME,SEND_EMAIL,READ_EMAILS,SEARCH_EMAILS
```

**Eller för att testa endast Gmail:**
```bash
ENABLED_TOOLS=SEND_EMAIL,READ_EMAILS,SEARCH_EMAILS
```

## 5. Första Autentisering (OAuth Flow)

När du använder Gmail-funktioner första gången sker en interaktiv OAuth-process:

1. **Alice visar autentiserings-URL**
   ```
   Öppna denna URL för att autentisera Gmail: https://accounts.google.com/o/oauth2/auth?...
   ```

2. **Genomför autentisering**
   - Öppna URL:en i webbläsaren
   - Logga in med ditt Google-konto (samma som för credentials)
   - Granska begärda behörigheter:
     - "Läsa, skriva, skicka och permanent ta bort all din e-post från Gmail"
   - Klicka "Tillåt"

3. **Kopiera auktoriseringskod**
   - Efter godkännande visas en auktoriseringskod
   - Kopiera hela koden (vanligtvis ~100 tecken)

4. **Slutför setup**
   ```
   Klistra in auktoriseringskoden: [din kod här]
   ```

5. **Automatisk tokenhantering**
   - Alice skapar `gmail_token.pickle` automatiskt
   - Framtida autentiseringar sker transparent
   - Token uppdateras automatiskt vid behov

Detta behöver bara göras **en gång per installation**.

## 6. Använda Gmail-funktioner

### Skicka E-post
Alice kan skicka e-post med naturligt språk:

```
"Skicka mail till chef@företag.se med ämne 'Projektuppdatering'"
"Send email to john@example.com subject 'Meeting tomorrow'"
"Skicka e-post om projektstatus"
```

**Avancerade funktioner:**
- CC/BCC-stöd: "Skicka mail till john@example.com med kopia till boss@company.com"
- Flerspråkig text i både ämne och innehåll
- UTF-8-stöd för specialtecken

### Läsa E-post
Visa och hantera inkommande e-post:

```
"Visa nya mail"
"Läs de senaste 5 e-posten"
"Check emails"
"Visa 10 senaste mail"
```

**Filtrering:**
- Olästa: "Visa olästa mail"
- Från specifik person: "Visa mail från chef"
- Med filter: `query="is:unread from:important@company.com"`

### Söka E-post
Kraftfull sökning med Gmail-syntax:

```
"Sök mail från chef"
"Hitta mail om projekt"
"Search emails from last week"
"Sök mail med ämne möte"
```

**Gmail-sökoperatorer som stöds:**
- `from:user@domain.com` - från specifik avsändare
- `to:user@domain.com` - till specifik mottagare
- `subject:keyword` - i ämnesraden
- `is:unread` - olästa meddelanden
- `is:important` - viktiga meddelanden
- `has:attachment` - med bilagor
- `newer_than:7d` - nyare än 7 dagar
- `older_than:1m` - äldre än 1 månad

## 7. Testning utan Credentials

För utveckling och testning kan du verifiera funktionaliteten:

```bash
# Testa verktygsvalidering
cd /Users/evil/Desktop/EVIL/PROJECT/Alice/alice/server
source .venv/bin/activate
ENABLED_TOOLS=SEND_EMAIL,READ_EMAILS,SEARCH_EMAILS python -c "
from core.tool_registry import validate_and_execute_tool
result = validate_and_execute_tool('SEND_EMAIL', {
    'to': 'test@example.com',
    'subject': 'Test',
    'body': 'Test message'
})
print(result)
"
```

Detta kommer returnera felmeddelande om credentials saknas, men bekräftar att valideringen fungerar.

## 8. Säkerhetsnoter

### Lokal Datasäkerhet
- **Gmail credentials sparas lokalt** - skickas aldrig till externa servrar
- **Token-filer krypteras** med pickle-format
- **Behörigheter begränsade** till endast Gmail (inte Drive, Calendar, etc.)

### Google-kontosäkerhet
- **Granska behörigheter** i [Google Account Settings](https://myaccount.google.com/permissions)
- **Återkalla access** när som helst via "Third-party apps & services"
- **Testanvändare-begränsning** - endast godkända e-postadresser kan använda appen under utveckling

### Rekommenderade säkerhetsåtgärder
- Använd ett dedikerat testkonto för utveckling
- Aktivera 2FA på Google-kontot
- Regelbunden granskning av aktiva OAuth-tokens

## 9. Felsökning

### Vanliga Problem och Lösningar

**Problem: "Gmail-tjänst inte tillgänglig"**
```bash
# Kontrollera credentials-fil
ls -la /Users/evil/Desktop/EVIL/PROJECT/Alice/alice/server/gmail_credentials.json

# Kontrollera internetanslutning
ping -c 3 googleapis.com

# Verifiera dependencies
python -c "import googleapiclient, google_auth_oauthlib; print('OK')"
```

**Problem: "Invalid credentials" eller "Refresh token expired"**
```bash
# Ta bort sparad token och autentisera igen
rm /Users/evil/Desktop/EVIL/PROJECT/Alice/alice/server/gmail_token.pickle
```

**Problem: "Access blocked: This app's request is invalid"**
- Kontrollera OAuth consent screen-konfiguration
- Lägg till din e-post som testanvändare
- Vänta upp till 10 minuter efter ändringar

**Problem: "Quota exceeded" eller "Rate limit"**
- Gmail API har gränser: 1 miljard requests/dag, 250 requests/användare/sekund
- För normal användning är detta inte ett problem
- Implementera exponential backoff vid höga volymer

**Problem: Import-fel**
```bash
# Installera alla Gmail-beroenden
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

# Eller från requirements.txt om den existerar
pip install -r requirements.txt
```

**Problem: "localhost OAuth redirect"**
- Gmail-implementationen använder `urn:ietf:wg:oauth:2.0:oob` (out-of-band)
- Ingen lokal server behövs för redirect
- Kopierar authorization code manuellt istället

### Debug-läge

För detaljerad felsökning, aktivera debug-logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Kontakta Support

Om problem kvarstår:
1. Kontrollera [Gmail API Documentation](https://developers.google.com/gmail/api)
2. Granska [Google Cloud Console Status](https://status.cloud.google.com/)
3. Konsultera [OAuth 2.0 Troubleshooting Guide](https://developers.google.com/identity/protocols/oauth2/troubleshooting)