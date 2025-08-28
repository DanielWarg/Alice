/**
 * Weather Tool - Get current weather and forecast
 */
import { NextRequest, NextResponse } from 'next/server';

interface WeatherRequest {
  location: string | { lat: number; lon: number };
  units?: 'metric' | 'imperial';
  include_forecast?: boolean;
  days?: number;
}

interface WeatherResponse {
  ok: boolean;
  location_resolved?: {
    name: string;
    country: string;
    lat: number;
    lon: number;
    tz: string;
  };
  now?: {
    temp: number;
    wind_ms: number;
    gust_ms?: number;
    humidity: number;
    condition: string;
    observed_at: string;
  };
  forecast?: Array<{
    date: string;
    tmin: number;
    tmax: number;
    precip_mm: number;
    condition: string;
  }>;
  sources?: string[];
  error?: {
    code: string;
    message: string;
  };
}

// Simple geocoding cache (in production, use proper geocoding service)
const LOCATION_CACHE: Record<string, { lat: number; lon: number; name: string; country: string }> = {
  'göteborg': { lat: 57.7089, lon: 11.9746, name: 'Göteborg', country: 'SE' },
  'stockholm': { lat: 59.3293, lon: 18.0686, name: 'Stockholm', country: 'SE' },
  'malmö': { lat: 55.6058, lon: 13.0007, name: 'Malmö', country: 'SE' },
  'uppsala': { lat: 59.8594, lon: 17.6389, name: 'Uppsala', country: 'SE' },
  'västerås': { lat: 59.6162, lon: 16.5528, name: 'Västerås', country: 'SE' },
  'örebro': { lat: 59.2741, lon: 15.2066, name: 'Örebro', country: 'SE' },
  'linköping': { lat: 58.4108, lon: 15.6214, name: 'Linköping', country: 'SE' },
  'helsingborg': { lat: 56.0467, lon: 12.6945, name: 'Helsingborg', country: 'SE' },
  'jönköping': { lat: 57.7826, lon: 14.1618, name: 'Jönköping', country: 'SE' },
  'norrköping': { lat: 58.5877, lon: 16.1924, name: 'Norrköping', country: 'SE' },
  'lund': { lat: 55.7047, lon: 13.1910, name: 'Lund', country: 'SE' },
  'umeå': { lat: 63.8258, lon: 20.2630, name: 'Umeå', country: 'SE' },
  'gävle': { lat: 60.6749, lon: 17.1413, name: 'Gävle', country: 'SE' },
  'borås': { lat: 57.7210, lon: 12.9401, name: 'Borås', country: 'SE' },
  'eskilstuna': { lat: 59.3707, lon: 16.5077, name: 'Eskilstuna', country: 'SE' }
};

function resolveLocation(location: string | { lat: number; lon: number }) {
  if (typeof location === 'object') {
    return {
      lat: location.lat,
      lon: location.lon,
      name: `${location.lat.toFixed(2)}, ${location.lon.toFixed(2)}`,
      country: 'Unknown'
    };
  }

  // Normalize location string
  const normalized = location.toLowerCase()
    .replace(/,?\s*(se|sweden|sverige)$/i, '')
    .trim();
  
  const cached = LOCATION_CACHE[normalized];
  if (cached) {
    return cached;
  }

  // Try partial matches
  for (const [key, value] of Object.entries(LOCATION_CACHE)) {
    if (key.includes(normalized) || normalized.includes(key)) {
      return value;
    }
  }

  return null;
}

async function fetchWeatherFromOpenMeteo(lat: number, lon: number, includeForecast: boolean, days: number) {
  const baseUrl = 'https://api.open-meteo.com/v1/forecast';
  const params = new URLSearchParams({
    latitude: lat.toString(),
    longitude: lon.toString(),
    current: 'temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_gusts_10m',
    timezone: 'auto',
    forecast_days: days.toString()
  });

  if (includeForecast) {
    params.append('daily', 'temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code');
  }

  const response = await fetch(`${baseUrl}?${params}`, {
    headers: {
      'User-Agent': 'Alice-Voice-Assistant/1.0'
    }
  });

  if (!response.ok) {
    throw new Error(`Open-Meteo API error: ${response.status}`);
  }

  return response.json();
}

function mapWeatherCode(code: number): string {
  // WMO Weather interpretation codes
  if (code === 0) return 'clear';
  if (code <= 3) return 'partly_cloudy';
  if (code <= 48) return 'foggy';
  if (code <= 57) return 'drizzle';
  if (code <= 67) return 'rain';
  if (code <= 77) return 'snow';
  if (code <= 82) return 'rain_showers';
  if (code <= 86) return 'snow_showers';
  if (code <= 99) return 'thunderstorm';
  return 'unknown';
}

export async function POST(request: NextRequest) {
  try {
    const body: WeatherRequest = await request.json();
    
    // Validate input
    if (!body.location) {
      return NextResponse.json<WeatherResponse>({
        ok: false,
        error: {
          code: 'BAD_REQUEST',
          message: 'location krävs'
        }
      }, { status: 400 });
    }

    const days = Math.min(Math.max(body.days || 1, 1), 7);
    const units = body.units || 'metric';
    const includeForecast = body.include_forecast !== false;

    // Resolve location
    const locationData = resolveLocation(body.location);
    if (!locationData) {
      return NextResponse.json<WeatherResponse>({
        ok: false,
        error: {
          code: 'NOT_FOUND',
          message: `Kunde inte hitta platsen: ${body.location}`
        }
      }, { status: 404 });
    }

    // Fetch weather data
    console.log(`🌤️ Fetching weather for ${locationData.name} (${locationData.lat}, ${locationData.lon})`);
    
    try {
      const weatherData = await fetchWeatherFromOpenMeteo(
        locationData.lat, 
        locationData.lon, 
        includeForecast, 
        days
      );

      // Parse current weather
      const current = weatherData.current;
      const now = {
        temp: Math.round(current.temperature_2m * 10) / 10,
        wind_ms: Math.round(current.wind_speed_10m * 2.78) / 10, // Convert km/h to m/s
        gust_ms: current.wind_gusts_10m ? Math.round(current.wind_gusts_10m * 2.78) / 10 : undefined,
        humidity: Math.round(current.relative_humidity_2m) / 100,
        condition: mapWeatherCode(current.weather_code),
        observed_at: new Date().toISOString()
      };

      // Parse forecast
      const forecast: WeatherResponse['forecast'] = [];
      if (includeForecast && weatherData.daily) {
        const daily = weatherData.daily;
        for (let i = 0; i < Math.min(daily.time.length, days); i++) {
          forecast.push({
            date: daily.time[i],
            tmin: Math.round(daily.temperature_2m_min[i] * 10) / 10,
            tmax: Math.round(daily.temperature_2m_max[i] * 10) / 10,
            precip_mm: Math.round(daily.precipitation_sum[i] * 10) / 10,
            condition: mapWeatherCode(daily.weather_code[i])
          });
        }
      }

      const response: WeatherResponse = {
        ok: true,
        location_resolved: {
          name: locationData.name,
          country: locationData.country,
          lat: locationData.lat,
          lon: locationData.lon,
          tz: weatherData.timezone || 'UTC'
        },
        now,
        forecast: includeForecast ? forecast : undefined,
        sources: ['open-meteo']
      };

      console.log(`🌤️ Weather fetched: ${locationData.name} ${now.temp}°C, ${now.condition}`);
      
      return NextResponse.json(response);

    } catch (fetchError) {
      console.error('Weather fetch error:', fetchError);
      
      return NextResponse.json<WeatherResponse>({
        ok: false,
        error: {
          code: 'UPSTREAM_UNAVAILABLE',
          message: 'Väderservice är tillfälligt otillgänglig'
        }
      }, { status: 502 });
    }

  } catch (error) {
    console.error('Weather tool error:', error);
    
    return NextResponse.json<WeatherResponse>({
      ok: false,
      error: {
        code: 'INTERNAL',
        message: 'Ett tekniskt fel uppstod med vädertjänsten'
      }
    }, { status: 500 });
  }
}

// Health check
export async function GET() {
  try {
    // Test Open-Meteo API availability
    const response = await fetch('https://api.open-meteo.com/v1/forecast?latitude=59.33&longitude=18.07&current=temperature_2m&forecast_days=1', {
      method: 'HEAD',
      timeout: 5000
    } as any);

    if (!response.ok) {
      throw new Error(`Open-Meteo unavailable: ${response.status}`);
    }

    return NextResponse.json({
      status: 'ok',
      service: 'open-meteo',
      locations_cached: Object.keys(LOCATION_CACHE).length,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    return NextResponse.json({
      status: 'error',
      service: 'open-meteo',
      error: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 503 });
  }
}