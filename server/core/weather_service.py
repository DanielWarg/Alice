"""
Weather service för att hantera väderinformation via OpenWeatherMap API.
Används av tool_registry för att ge Alice väderuppdateringar.
"""

import os
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import json

class WeatherService:
    def __init__(self):
        # OpenWeatherMap API key från miljövariabler
        self.api_key = os.getenv('OPENWEATHER_API_KEY')
        self.base_url = "http://api.openweathermap.org/data/2.5"
        
        # Default location (Stockholm)
        self.default_city = "Stockholm"
        self.default_country = "SE"
        
        # Svenska väderbeskrivningar
        self.weather_translations = {
            'clear sky': 'klart',
            'few clouds': 'lätt molnighet',
            'scattered clouds': 'växlande molnighet',
            'broken clouds': 'mulet',
            'overcast clouds': 'helt mulet',
            'light rain': 'lätt regn',
            'moderate rain': 'måttligt regn',
            'heavy rain': 'kraftigt regn',
            'thunderstorm': 'åska',
            'snow': 'snö',
            'mist': 'dimma',
            'fog': 'dimma'
        }
    
    def _translate_weather(self, description: str) -> str:
        """Översätt väderbeskrivning till svenska"""
        return self.weather_translations.get(description.lower(), description)
    
    def _format_temperature(self, temp: float) -> str:
        """Formatera temperatur för svenska"""
        return f"{round(temp)}°C"
    
    def get_current_weather(self, city: str = None, country: str = None) -> str:
        """Hämta aktuellt väder för en stad"""
        if not self.api_key:
            return "Väder-tjänst inte konfigurerad. Saknar OpenWeatherMap API-nyckel."
        
        city = city or self.default_city
        country = country or self.default_country
        
        try:
            # Skapa location string
            location = f"{city},{country}" if country else city
            
            # API call
            url = f"{self.base_url}/weather"
            params = {
                'q': location,
                'appid': self.api_key,
                'units': 'metric',  # Celsius
                'lang': 'sv'  # Svenska beskrivningar
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                if response.status_code == 404:
                    return f"Staden '{city}' hittades inte. Kontrollera stavningen."
                else:
                    return f"Kunde inte hämta väderinformation (fel {response.status_code})"
            
            data = response.json()
            
            # Extrahera väderinformation
            main = data['main']
            weather = data['weather'][0]
            wind = data.get('wind', {})
            
            temp = main['temp']
            feels_like = main['feels_like']
            humidity = main['humidity']
            description = weather['description']
            
            # Formatera svar på svenska
            result = f"Väder i {data['name']}:\n"
            result += f"🌡️ Temperatur: {self._format_temperature(temp)}"
            result += f" (känns som {self._format_temperature(feels_like)})\n"
            result += f"☁️ Beskrivning: {self._translate_weather(description)}\n"
            result += f"💧 Luftfuktighet: {humidity}%"
            
            if 'speed' in wind:
                wind_speed = round(wind['speed'])
                result += f"\n💨 Vind: {wind_speed} m/s"
            
            return result
            
        except requests.exceptions.Timeout:
            return "Väder-tjänsten svarar inte (timeout). Försök igen senare."
        except requests.exceptions.RequestException as e:
            return f"Nätverksfel vid väderförfrågan: {str(e)}"
        except Exception as e:
            return f"Fel vid hämtning av väderinformation: {str(e)}"
    
    def get_weather_forecast(self, city: str = None, country: str = None, days: int = 3) -> str:
        """Hämta väderprognos för flera dagar"""
        if not self.api_key:
            return "Väder-tjänst inte konfigurerad. Saknar OpenWeatherMap API-nyckel."
        
        city = city or self.default_city
        country = country or self.default_country
        
        try:
            location = f"{city},{country}" if country else city
            
            # API call för 5-dagars prognos
            url = f"{self.base_url}/forecast"
            params = {
                'q': location,
                'appid': self.api_key,
                'units': 'metric',
                'lang': 'sv'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                if response.status_code == 404:
                    return f"Staden '{city}' hittades inte för väderprognos."
                else:
                    return f"Kunde inte hämta väderprognos (fel {response.status_code})"
            
            data = response.json()
            
            # Gruppera prognoser per dag
            daily_forecasts = {}
            
            for item in data['list'][:days * 8]:  # 8 prognoser per dag (var 3e timme)
                dt = datetime.fromtimestamp(item['dt'])
                date_str = dt.strftime('%Y-%m-%d')
                
                if date_str not in daily_forecasts:
                    daily_forecasts[date_str] = {
                        'date': dt,
                        'temps': [],
                        'descriptions': [],
                        'humidity': []
                    }
                
                daily_forecasts[date_str]['temps'].append(item['main']['temp'])
                daily_forecasts[date_str]['descriptions'].append(item['weather'][0]['description'])
                daily_forecasts[date_str]['humidity'].append(item['main']['humidity'])
            
            # Formatera resultat
            result = f"Väderprognos för {data['city']['name']} ({days} dagar):\n\n"
            
            swedish_weekdays = ['måndag', 'tisdag', 'onsdag', 'torsdag', 'fredag', 'lördag', 'söndag']
            
            for date_str in sorted(daily_forecasts.keys())[:days]:
                day_data = daily_forecasts[date_str]
                date_obj = day_data['date']
                
                weekday = swedish_weekdays[date_obj.weekday()]
                date_formatted = date_obj.strftime('%d/%m')
                
                min_temp = min(day_data['temps'])
                max_temp = max(day_data['temps'])
                avg_humidity = sum(day_data['humidity']) // len(day_data['humidity'])
                
                # Mest vanliga väderbeskrivningen
                most_common_desc = max(set(day_data['descriptions']), key=day_data['descriptions'].count)
                
                result += f"📅 {weekday.title()} {date_formatted}:\n"
                result += f"   🌡️ {self._format_temperature(min_temp)} - {self._format_temperature(max_temp)}\n"
                result += f"   ☁️ {self._translate_weather(most_common_desc)}\n"
                result += f"   💧 {avg_humidity}% luftfuktighet\n\n"
            
            return result.strip()
            
        except Exception as e:
            return f"Fel vid hämtning av väderprognos: {str(e)}"
    
    def search_city_weather(self, query: str) -> str:
        """Sök väder för en stad baserat på sökning"""
        if not query or len(query) < 2:
            return "Ange en stad att söka väder för."
        
        # Försök först som vanlig stadsökning
        result = self.get_current_weather(city=query)
        
        # Om staden inte hittas, ge användbara tips
        if "hittades inte" in result.lower():
            suggestions = [
                "Stockholm", "Göteborg", "Malmö", "Uppsala", "Linköping",
                "London", "Paris", "Berlin", "Copenhagen", "Oslo"
            ]
            
            result += f"\n\nFörslag på städer: {', '.join(suggestions)}"
        
        return result

# Global instans
weather_service = WeatherService()

# Test function
def test_weather_service():
    """Test weather service"""
    service = WeatherService()
    
    print("🌤️ Testar Weather Service...")
    print(f"API Key konfigurerad: {'Ja' if service.api_key else 'Nej'}")
    
    if service.api_key:
        print("\n" + service.get_current_weather())
        print("\n" + service.get_weather_forecast(days=2))
    else:
        print("Sätt OPENWEATHER_API_KEY miljövariabel för att testa")

if __name__ == "__main__":
    test_weather_service()