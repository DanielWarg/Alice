/**
 * Simple backend test proxy to avoid CORS issues
 */
import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const response = await fetch('http://localhost:8000/api/tools/spec');
    
    if (response.ok) {
      const data = await response.json();
      const toolCount = data.specs ? data.specs.length : 0;
      
      return NextResponse.json({
        status: 'ok',
        message: `Backend connected (${toolCount} tools)`,
        toolCount
      });
    } else {
      return NextResponse.json({
        status: 'error',
        message: `Backend error (${response.status})`
      }, { status: response.status });
    }
  } catch (error) {
    return NextResponse.json({
      status: 'error',
      message: 'Backend connection failed'
    }, { status: 500 });
  }
}