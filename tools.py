import requests
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from duckduckgo_search import DDGS
from typing import Optional
from datetime import datetime

class AliceTools:
    
    @staticmethod
    def get_weather(city: str) -> str:
        """Hämta väder för en stad"""
        try:
            response = requests.get(f"https://wttr.in/{city}?format=3&lang=sv")
            if response.status_code == 200:
                return f"Vädret i {city}: {response.text.strip()}"
            else:
                return f"Kunde inte hämta väder för {city}"
        except Exception as e:
            return f"Fel vid väderförfrågan: {e}"
    
    @staticmethod
    def search_web(query: str, max_results: int = 5) -> str:
        """Sök på webben med DuckDuckGo"""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results, region='se-sv'))
                
            if not results:
                return "Inga sökresultat hittades."
            
            formatted_results = f"Sökresultat för '{query}':\n\n"
            for i, result in enumerate(results, 1):
                formatted_results += f"{i}. {result['title']}\n"
                formatted_results += f"   {result['body'][:200]}...\n"
                formatted_results += f"   Länk: {result['href']}\n\n"
            
            return formatted_results
            
        except Exception as e:
            return f"Fel vid websökning: {e}"
    
    @staticmethod
    def send_email(to_email: str, subject: str, message: str, cc_email: Optional[str] = None) -> str:
        """Skicka e-post via Gmail"""
        try:
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
            
            gmail_user = os.getenv("GMAIL_USER")
            gmail_password = os.getenv("GMAIL_APP_PASSWORD")
            
            if not gmail_user or not gmail_password:
                return "E-post misslyckades: Gmail-inställningar saknas i miljövariabler."
            
            msg = MIMEMultipart()
            msg['From'] = gmail_user
            msg['To'] = to_email
            msg['Subject'] = subject
            
            recipients = [to_email]
            if cc_email:
                msg['Cc'] = cc_email
                recipients.append(cc_email)
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(gmail_user, gmail_password)
            
            server.sendmail(gmail_user, recipients, msg.as_string())
            server.quit()
            
            return f"E-post skickat till {to_email}"
            
        except Exception as e:
            return f"Fel vid e-post: {e}"
    
    @staticmethod
    def get_time() -> str:
        """Hämta aktuell tid"""
        now = datetime.now()
        return now.strftime("Klockan är %H:%M, %A %d %B %Y")
    
    @staticmethod
    def calculate(expression: str) -> str:
        """Säker kalkylator"""
        try:
            # Enkel säkerhetskontroll
            allowed_chars = set('0123456789+-*/.() ')
            if not all(c in allowed_chars for c in expression):
                return "Endast grundläggande matematiska operationer är tillåtna"
            
            result = eval(expression)
            return f"{expression} = {result}"
            
        except Exception as e:
            return f"Fel i beräkning: {e}"