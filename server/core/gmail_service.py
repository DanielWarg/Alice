"""
Gmail service för att hantera Gmail API-operationer.
Används av tool_registry för att skicka, läsa och söka e-post.
"""

import os
import pickle
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional

try:
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import Flow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False

class GmailService:
    def __init__(self):
        self.service = None
        self.credentials_path = os.path.join(os.path.dirname(__file__), '..', 'gmail_credentials.json')
        self.token_path = os.path.join(os.path.dirname(__file__), '..', 'gmail_token.pickle')
        
    def _get_credentials(self):
        """Hämta eller skapa Gmail API-inloggning"""
        creds = None
        
        # Ladda sparad token
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # Om inga giltiga credentials finns, be användaren logga in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    return None
                    
                flow = Flow.from_client_secrets_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/gmail.modify']
                )
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                
                auth_url, _ = flow.authorization_url(prompt='consent')
                print(f"Öppna denna URL för att autentisera Gmail: {auth_url}")
                code = input("Klistra in auktoriseringskoden: ")
                
                flow.fetch_token(code=code)
                creds = flow.credentials
            
            # Spara credentials för nästa gång
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return creds
    
    def _initialize_service(self):
        """Initialisera Gmail service"""
        if not GMAIL_AVAILABLE:
            return False
            
        if self.service:
            return True
            
        creds = self._get_credentials()
        if not creds:
            return False
            
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            return True
        except Exception:
            return False
    
    def send_email(self, to: str, subject: str, body: str, cc: str = None, bcc: str = None) -> str:
        """Skicka e-post via Gmail"""
        if not self._initialize_service():
            return "Gmail-tjänst inte tillgänglig. Kontrollera credentials och internetanslutning."
        
        try:
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            
            message.attach(MIMEText(body, 'plain', 'utf-8'))
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            result = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return f"E-post skickad till {to} med ämne '{subject}'"
            
        except Exception as e:
            return f"Fel vid e-postsändning: {str(e)}"
    
    def read_emails(self, max_results: int = 10, query: str = None) -> str:
        """Läs senaste e-post från Gmail"""
        if not self._initialize_service():
            return "Gmail-tjänst inte tillgänglig. Kontrollera credentials och internetanslutning."
        
        try:
            # Hämta meddelande-ID:n
            results = self.service.users().messages().list(
                userId='me',
                q=query or '',
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                return "Inga e-post hittades."
            
            email_summaries = []
            
            for msg in messages:
                # Hämta meddelandedetaljer
                message = self.service.users().messages().get(
                    userId='me',
                    id=msg['id']
                ).execute()
                
                headers = message['payload'].get('headers', [])
                
                # Extrahera viktiga headers
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Inget ämne')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Okänd avsändare')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Okänt datum')
                
                # Begränsa längden för läsbarhet
                if len(subject) > 60:
                    subject = subject[:60] + "..."
                
                email_summaries.append(f"• {subject}\n  Från: {sender}\n  Datum: {date}")
            
            return f"Senaste {len(email_summaries)} e-post:\n\n" + "\n\n".join(email_summaries)
            
        except Exception as e:
            return f"Fel vid läsning av e-post: {str(e)}"
    
    def search_emails(self, query: str, max_results: int = 20) -> str:
        """Sök e-post i Gmail"""
        if not self._initialize_service():
            return "Gmail-tjänst inte tillgänglig. Kontrollera credentials och internetanslutning."
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                return f"Inga e-post hittades för sökningen: '{query}'"
            
            email_summaries = []
            
            for msg in messages:
                message = self.service.users().messages().get(
                    userId='me',
                    id=msg['id']
                ).execute()
                
                headers = message['payload'].get('headers', [])
                
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Inget ämne')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Okänd avsändare')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Okänt datum')
                
                if len(subject) > 60:
                    subject = subject[:60] + "..."
                
                email_summaries.append(f"• {subject}\n  Från: {sender}\n  Datum: {date}")
            
            return f"Hittade {len(email_summaries)} e-post för '{query}':\n\n" + "\n\n".join(email_summaries)
            
        except Exception as e:
            return f"Fel vid sökning av e-post: {str(e)}"

# Global instans
gmail_service = GmailService()