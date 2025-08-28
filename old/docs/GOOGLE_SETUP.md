# 📱 Google Integration Setup Guide

Steg-för-steg guide för att konfigurera Gmail och Google Calendar integration för Alice.

## 🚀 Översikt

Alice kan integreras med:
- **Gmail** - Läsa, skicka, organisera email
- **Google Calendar** - Skapa, läsa, uppdatera kalenderhändelser
- **Google OAuth** - Säker autentisering

## 📋 Förutsättningar

- Google-konto med Gmail och Calendar aktiverat
- Åtkomst till Google Cloud Console
- Alice backend och frontend konfigurerade

## 🔧 Steg 1: Google Cloud Console Setup

### 1.1 Skapa Projekt

1. Gå till [Google Cloud Console](https://console.cloud.google.com/)
2. Klicka **"New Project"** eller välj befintligt projekt
3. Namnge projektet (t.ex. "Alice AI Assistant")
4. Klicka **"Create"**

### 1.2 Aktivera APIs

1. Navigera till **"APIs & Services" → "Library"**
2. Sök och aktivera följande APIs:
   - **Gmail API**
   - **Google Calendar API** 
   - **Google+ API** (för profil-info)

För varje API:
- Klicka på API:t
- Klicka **"Enable"**
- Vänta tills aktiveringen är klar

## 🛡️ Steg 2: OAuth Consent Screen

### 2.1 Grundkonfiguration

1. Gå till **"APIs & Services" → "OAuth consent screen"**
2. Välj **"External"** (för testning) eller **"Internal"** (för organisationsanvändning)
3. Klicka **"Create"**

### 2.2 App Information

Fyll i följande fält:

```
App name: Alice AI Assistant
User support email: [din-email]
Developer contact information: [din-email]
```

**App domain** (valfritt för utveckling):
```
Application home page: http://localhost:3000
Application privacy policy: http://localhost:3000/privacy
Application terms of service: http://localhost:3000/terms
```

### 2.3 Scopes

Klicka **"Add or Remove Scopes"** och lägg till:

```
../auth/userinfo.email
../auth/userinfo.profile
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/calendar.readonly  
https://www.googleapis.com/auth/calendar.events
```

### 2.4 Test Users (för External apps)

Lägg till test-användare:
- Din egen email-adress
- Andra utvecklare som ska testa

## 🔑 Steg 3: OAuth Credentials

### 3.1 Skapa Credentials

1. Gå till **"APIs & Services" → "Credentials"**
2. Klicka **"+ Create Credentials" → "OAuth client ID"**
3. Välj **"Web application"**

### 3.2 Konfigurera Web Client

**Name**: `Alice Web Client`

**Authorized JavaScript origins**:
```
http://localhost:3000
http://127.0.0.1:3000
http://localhost:8000
http://127.0.0.1:8000
```

**Authorized redirect URIs**:
```
http://localhost:8000/api/auth/callback/google
http://127.0.0.1:8000/api/auth/callback/google
```

### 3.3 Ladda ner Credentials

1. Klicka **"Create"**
2. **Kopiera Client ID och Client Secret** - du behöver dessa för `.env`
3. Valfritt: Ladda ner JSON-filen för säkerhets skull

## ⚙️ Steg 4: Alice Backend Konfiguration

### 4.1 Miljövariabler

Öppna `server/.env` och uppdatera:

```bash
# Google APIs
GOOGLE_CLIENT_ID=123456789-abcdef.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=ditt-client-secret-här  
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/callback/google
```

### 4.2 Verifiera Backend

Starta backend och kontrollera:

```bash
cd server
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Testa endpoint:
```bash
curl http://127.0.0.1:8000/api/auth/status
```

## 🎨 Steg 5: Alice Frontend Konfiguration  

### 5.1 Frontend Environment

Uppdatera `web/.env.local`:

```bash
NEXT_PUBLIC_GOOGLE_CLIENT_ID=123456789-abcdef.apps.googleusercontent.com
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

### 5.2 Verifiera Frontend

```bash
cd web  
npm run dev
```

Öppna http://localhost:3000 och kontrollera att inga OAuth-fel visas i konsolen.

## 🧪 Steg 6: Testa Integration

### 6.1 OAuth Flow Test

1. Öppna Alice i webbläsaren
2. Gå till **Settings → Integrations**
3. Klicka **"Connect Google"**
4. Logga in med ditt Google-konto
5. Acceptera permissions
6. Kontrollera att du redirectas tillbaka till Alice

### 6.2 Gmail Test

```bash
# Testa Gmail API via Alice
curl -X POST http://127.0.0.1:8000/api/gmail/inbox \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

### 6.3 Calendar Test

```bash  
# Testa Calendar API via Alice
curl -X GET http://127.0.0.1:8000/api/calendar/events \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🐛 Troubleshooting

### Common Issues

**1. "Error 400: redirect_uri_mismatch"**
- Kontrollera att redirect URI:n matchar exakt i Google Console
- Ingen trailing slash: `http://localhost:8000/api/auth/callback/google`

**2. "Error 403: access_blocked"**  
- OAuth consent screen inte konfigurerad
- Användaren inte listad som test user
- App inte "published" för external användning

**3. "Error 401: invalid_client"**
- GOOGLE_CLIENT_ID eller GOOGLE_CLIENT_SECRET felaktig
- Kontrollera att API:erna är aktiverade

**4. CORS Errors**
- Kontrollera Authorized JavaScript origins i Google Console
- Verifiera ALICE_ALLOWED_ORIGINS i backend `.env`

### Debug Tips

**Backend logs**:
```bash
tail -f server/logs/alice.log
```

**Frontend console**:
- Öppna Developer Tools → Console
- Leta efter OAuth-relaterade fel

**Test OAuth direkt**:
```
https://accounts.google.com/oauth/authorize?
  client_id=YOUR_CLIENT_ID&
  redirect_uri=http://localhost:8000/api/auth/callback/google&
  scope=openid email profile&
  response_type=code
```

## 🔒 Säkerhet Best Practices

1. **Aldrig committa credentials** - använd bara `.env.example`
2. **Rotera secrets** regelbundet  
3. **Minimal scopes** - begär bara nödvändiga permissions
4. **HTTPS i produktion** - aldrig OAuth över HTTP i prod
5. **Rate limiting** - implementera för OAuth endpoints

## 📚 Nästa Steg

Efter lyckad setup:
1. **Testa röstkommandon**: "Alice, läs mina emails"  
2. **Konfigurera kalenderhändelser**: "Alice, boka möte imorgon"
3. **Sätt upp notifikationer** för nya emails
4. **Implementera Gmail-filter** för viktiga meddelanden

## 📞 Support

Om du stöter på problem:
1. Kontrollera [Google OAuth dokumentation](https://developers.google.com/identity/protocols/oauth2)
2. Kolla Alice GitHub Issues
3. Se [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) för mer hjälp