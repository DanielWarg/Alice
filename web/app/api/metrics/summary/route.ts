/**
 * FAS 4 - Metrics Summary API  
 * Provides p50/p95 aggregation of system metrics
 */

import { NextResponse } from "next/server";
import { getRecentMetrics } from "@/src/core/metrics";

export const runtime = "nodejs";

function percentile(arr: number[], p: number): number {
  if (!arr.length) return 0;
  const sorted = arr.sort((a, b) => a - b);
  const index = Math.floor((p / 100) * sorted.length);
  return sorted[Math.min(index, sorted.length - 1)];
}

export async function GET() {
  try {
    const recentMetrics = getRecentMetrics(5000);
    
    // Extract different metrics
    const e2eTimes: number[] = [];
    const injectionPcts: number[] = [];
    const artifactsCounts: number[] = [];
    
    recentMetrics.forEach(event => {
      if (event.type === "brain_compose" && event.payload) {
        if (event.payload.t_ms && event.payload.stage === "complete") {
          e2eTimes.push(event.payload.t_ms);
        }
        if (event.payload.injected_tokens_pct !== undefined) {
          injectionPcts.push(event.payload.injected_tokens_pct);
        }
        if (event.payload.artifacts_used !== undefined) {
          artifactsCounts.push(event.payload.artifacts_used);
        }
      }
    });
    
    const summary = {
      ok: true,
      timestamp: new Date().toISOString(),
      metrics: {
        e2e_latency: {
          p50: percentile(e2eTimes, 50),
          p95: percentile(e2eTimes, 95),
          count: e2eTimes.length
        },
        injection_budget: {
          p50: percentile(injectionPcts, 50),
          p95: percentile(injectionPcts, 95),
          count: injectionPcts.length,
          budget_violations: injectionPcts.filter(p => p > 25).length,
          budget_compliance_rate: injectionPcts.length > 0 
            ? ((injectionPcts.filter(p => p <= 25).length / injectionPcts.length) * 100).toFixed(1) + '%'
            : '100%'
        },
        artifacts_usage: {
          avg: artifactsCounts.length > 0 
            ? (artifactsCounts.reduce((a, b) => a + b, 0) / artifactsCounts.length).toFixed(1)
            : 0,
          max: artifactsCounts.length > 0 ? Math.max(...artifactsCounts) : 0,
          count: artifactsCounts.length
        }
      }
    };

    return NextResponse.json(summary);
    
  } catch (error) {
    console.error('Metrics summary error:', error);
    return NextResponse.json({ 
      ok: false, 
      error: 'Failed to generate metrics summary' 
    }, { status: 500 });
  }
}