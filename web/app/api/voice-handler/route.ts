/**
 * Voice Handler API - Processes voice input with OpenAI integration
 * Used by Alice Core HUD for voice interactions
 */
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { text, session_id } = await request.json();
    
    if (!text) {
      return NextResponse.json({
        error: 'Text required'
      }, { status: 400 });
    }

    const q = text.trim();
    if (!q) {
      return NextResponse.json({
        error: 'Empty text'
      }, { status: 400 });
    }

    // Check if this might be a knowledge/document query that should use RAG
    const lowerQ = q.toLowerCase();
    const isKnowledgeQuery = (
      lowerQ.includes('när slutar') || 
      lowerQ.includes('när börjar') || 
      lowerQ.includes('schema') ||
      lowerQ.includes('arbetstid') ||
      lowerQ.includes('skola') ||
      lowerQ.includes(' lo ') ||
      lowerQ.startsWith('lo ') ||
      lowerQ.endsWith(' lo') ||
      lowerQ === 'lo'
    );

    let ragResponse = null;
    
    // Try RAG first for knowledge queries
    if (isKnowledgeQuery) {
      try {
        console.log('Knowledge query detected, trying RAG first:', q);
        
        // Add current date/time context to RAG queries
        const now = new Date();
        const currentDate = now.toLocaleDateString('sv-SE');
        const currentTime = now.toLocaleTimeString('sv-SE', { hour: '2-digit', minute: '2-digit' });
        const dayName = now.toLocaleDateString('sv-SE', { weekday: 'long' });
        
        const contextualPrompt = `Idag är ${dayName} den ${currentDate} klockan ${currentTime}. ${q}`;
        console.log('RAG query with context:', contextualPrompt);
        
        ragResponse = await fetch('http://127.0.0.1:8000/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            prompt: contextualPrompt,
            model: 'gpt-oss:20b',
            stream: false,
            provider: 'local',
            raw: false  // Enable RAG for document searches
          })
        });

        if (ragResponse.ok) {
          const ragData = await ragResponse.json();
          if (ragData && ragData.text && ragData.text.length > 10) {
            // RAG found a good answer
            return NextResponse.json({
              success: true,
              response: ragData.text,
              session_id: session_id || `alice_rag_${Date.now()}`,
              tool_used: 'rag_memory',
              timestamp: new Date().toISOString()
            });
          }
        }
      } catch (error) {
        console.error('RAG attempt failed:', error);
      }
    }

    // Use OpenAI agent API with session for other queries or if RAG failed
    const sessionId = session_id || `alice_hud_${Date.now()}`;
    
    // Add current date/time context for OpenAI too
    const now = new Date();
    const currentDate = now.toLocaleDateString('sv-SE');
    const currentTime = now.toLocaleTimeString('sv-SE', { hour: '2-digit', minute: '2-digit' });
    const dayName = now.toLocaleDateString('sv-SE', { weekday: 'long' });
    
    const response = await fetch(`${request.url.replace('/api/voice-handler', '')}/api/agent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        messages: [
          { 
            role: 'system', 
            content: `Du är Alice, en hjälpsam AI-assistent. Aktuell tid och datum: ${dayName} den ${currentDate} klockan ${currentTime}. Svara på svenska och håll svaren korta för röstkonversation.`
          },
          { role: 'user', content: q }
        ]
      })
    });

    let aiResponse = '';
    let toolUsed = null;
    
    if (response.ok) {
      const data = await response.json();
      
      // Handle tool calls - OpenAI wants to use a tool
      if (data.next_action === 'tool_call' && data.assistant?.tool_calls) {
        const toolCall = data.assistant.tool_calls[0];
        toolUsed = toolCall.name;
        
        if (toolCall.name === 'weather_get') {
          try {
            // Call the actual weather tool
            const weatherResponse = await fetch(`${request.url.replace('/api/voice-handler', '')}/api/tools/weather.get`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(toolCall.arguments)
            });
            
            if (weatherResponse.ok) {
              const weatherData = await weatherResponse.json();
              if (weatherData.ok && weatherData.now) {
                const location = weatherData.location_resolved.name;
                const temp = weatherData.now.temp;
                const condition = weatherData.now.condition;
                const humidity = Math.round(weatherData.now.humidity * 100);
                
                const conditionText = {
                  'clear': 'klart',
                  'partly_cloudy': 'delvis molnigt', 
                  'foggy': 'dimmigt',
                  'drizzle': 'duggregn',
                  'rain': 'regn',
                  'snow': 'snö',
                  'rain_showers': 'regnskurar',
                  'snow_showers': 'snöskurar',
                  'thunderstorm': 'åska'
                }[condition] || condition;
                
                aiResponse = `I ${location} är det ${temp} grader och ${conditionText}. Luftfuktigheten är ${humidity}%.`;
              }
            }
            
            if (!aiResponse) {
              const location = toolCall.arguments.location || 'den platsen';
              aiResponse = `Jag kunde inte hämta väderinformationen för ${location} just nu.`;
            }
            
          } catch (error) {
            console.error('Weather tool error:', error);
            aiResponse = `Ett fel uppstod när jag försökte hämta väderinformation.`;
          }
        } else {
          aiResponse = `Jag ville använda verktyget ${toolCall.name} men det är inte helt konfigurerat än.`;
        }
      } else {
        // Handle final response with content
        aiResponse = data.assistant?.content || data.content || data.message || 'Jag förstod inte riktigt vad du menade.';
      }
    } else {
      // Fallback to old backend system with RAG for knowledge queries
      try {
        console.log('OpenAI failed, trying RAG backend for:', q);
        
        // Add current date/time context to fallback RAG query too
        const now = new Date();
        const currentDate = now.toLocaleDateString('sv-SE');
        const currentTime = now.toLocaleTimeString('sv-SE', { hour: '2-digit', minute: '2-digit' });
        const dayName = now.toLocaleDateString('sv-SE', { weekday: 'long' });
        
        const contextualPrompt = `Idag är ${dayName} den ${currentDate} klockan ${currentTime}. ${q}`;
        
        const ragResponse = await fetch('http://127.0.0.1:8000/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            prompt: contextualPrompt,
            model: 'gpt-oss:20b',
            stream: false,
            provider: 'local',
            raw: false  // Enable RAG for document searches
          })
        });

        if (ragResponse.ok) {
          const ragData = await ragResponse.json();
          if (ragData && ragData.text) {
            aiResponse = ragData.text;
            console.log('RAG backend provided response');
          } else {
            aiResponse = 'Jag kunde inte hitta ett svar på den frågan.';
          }
        } else {
          // Final fallback to basic response
          aiResponse = `Jag förstod inte riktigt frågan: "${q}". Kan du försöka igen?`;
        }
      } catch (error) {
        console.error('RAG backend error:', error);
        aiResponse = `Jag har problem att komma åt mitt minne just nu. Kan du försöka igen senare?`;
      }
    }

    return NextResponse.json({
      success: true,
      response: aiResponse,
      session_id: sessionId,
      tool_used: toolUsed,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Voice handler error:', error);
    return NextResponse.json({
      error: 'Failed to process voice input'
    }, { status: 500 });
  }
}