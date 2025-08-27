/**
 * Router - Route Policy and Cloud Degrade Logic
 * 
 * Decides how to process user input based on complexity, privacy requirements,
 * and cloud availability. Implements intelligent fallback strategies.
 */

import { logNDJSON } from "./metrics";

export type RouteDecision = "local_fast" | "local_reason" | "cloud_complex";

export interface RoutingContext {
  text: string;
  hasPII: boolean;
  needsTools: boolean;
  estTokens: number;
  cloudEnabled: boolean;
  cloudDegraded: boolean;
  privacyLevel: "strict" | "normal" | "permissive";
  userPreferences?: {
    preferLocal?: boolean;
    allowCloud?: boolean;
    maxLatency?: number;
  };
}

export interface RouteResult {
  route: RouteDecision;
  reason: string;
  estimatedLatency: number;
  confidence: number;
  fallbackOptions: RouteDecision[];
}

/**
 * Main routing decision function
 */
export function decideRoute(context: RoutingContext): RouteDecision {
  const { text, hasPII, needsTools, estTokens, cloudEnabled, cloudDegraded, privacyLevel } = context;

  // Log routing decision attempt
  logNDJSON({
    event: "routing_decision",
    timestamp: Date.now(),
    context: {
      textLength: text.length,
      hasPII,
      needsTools,
      estTokens,
      cloudEnabled,
      cloudDegraded,
      privacyLevel
    }
  });

  // Privacy violations always go local
  if (hasPII) {
    logNDJSON({
      event: "routing_blocked_pii",
      timestamp: Date.now(),
      reason: "PII detected, forcing local processing"
    });
    return "local_reason";
  }

  // Cloud disabled or degraded
  if (!cloudEnabled || cloudDegraded) {
    logNDJSON({
      event: "routing_cloud_unavailable",
      timestamp: Date.now(),
      reason: cloudDegraded ? "Cloud degraded" : "Cloud disabled"
    });
    return needsTools ? "local_reason" : "local_fast";
  }

  // Simple queries go local fast
  if (!needsTools && estTokens <= 40 && text.length <= 100) {
    return "local_fast";
  }

  // Complex queries with tools
  if (needsTools && estTokens > 60) {
    if (cloudEnabled && !cloudDegraded) {
      return "cloud_complex";
    }
    return "local_reason";
  }

  // Medium complexity
  if (estTokens > 40 || text.length > 100) {
    return "local_reason";
  }

  // Default to local fast
  return "local_fast";
}

/**
 * Get detailed routing analysis
 */
export function analyzeRoute(context: RoutingContext): RouteResult {
  const route = decideRoute(context);
  const { text, estTokens, needsTools } = context;

  // Calculate estimated latency
  let estimatedLatency = 0;
  let confidence = 0.8;
  let reason = "";

  switch (route) {
    case "local_fast":
      estimatedLatency = 200 + (estTokens * 2); // Base + token processing
      reason = "Simple query, local processing";
      break;

    case "local_reason":
      estimatedLatency = 500 + (estTokens * 5) + (needsTools ? 300 : 0);
      reason = "Medium complexity, local reasoning";
      break;

    case "cloud_complex":
      estimatedLatency = 800 + (estTokens * 3) + (needsTools ? 500 : 0);
      reason = "Complex query, cloud processing";
      break;
  }

  // Determine fallback options
  const fallbackOptions: RouteDecision[] = [];
  if (route !== "local_fast") fallbackOptions.push("local_fast");
  if (route !== "local_reason") fallbackOptions.push("local_reason");
  if (route !== "cloud_complex" && context.cloudEnabled && !context.cloudDegraded) {
    fallbackOptions.push("cloud_complex");
  }

  return {
    route,
    reason,
    estimatedLatency,
    confidence,
    fallbackOptions
  };
}

/**
 * Check if route should be degraded due to performance issues
 */
export function shouldDegradeRoute(
  currentRoute: RouteDecision,
  performanceMetrics: {
    avgLatency: number;
    errorRate: number;
    timeoutRate: number;
  }
): boolean {
  const { avgLatency, errorRate, timeoutRate } = performanceMetrics;

  // Degrade cloud if performance is poor
  if (currentRoute === "cloud_complex") {
    if (avgLatency > 2000 || errorRate > 0.1 || timeoutRate > 0.05) {
      logNDJSON({
        event: "route_degraded",
        timestamp: Date.now(),
        from: currentRoute,
        to: "local_reason",
        reason: "Poor cloud performance",
        metrics: performanceMetrics
      });
      return true;
    }
  }

  // Degrade local reasoning if too slow
  if (currentRoute === "local_reason" && avgLatency > 1500) {
    logNDJSON({
      event: "route_degraded",
      timestamp: Date.now(),
      from: currentRoute,
      to: "local_fast",
      reason: "Local reasoning too slow",
      metrics: performanceMetrics
    });
    return true;
  }

  return false;
}

/**
 * Get degraded route
 */
export function getDegradedRoute(currentRoute: RouteDecision): RouteDecision {
  switch (currentRoute) {
    case "cloud_complex":
      return "local_reason";
    case "local_reason":
      return "local_fast";
    case "local_fast":
      return "local_fast"; // Already at lowest level
  }
}

/**
 * Route based on user intent classification
 */
export function routeByIntent(
  intent: string,
  confidence: number,
  context: RoutingContext
): RouteDecision {
  // High-confidence intents can use more complex routes
  if (confidence > 0.8) {
    switch (intent) {
      case "greeting":
      case "farewell":
      case "thanks":
        return "local_fast";
      
      case "weather":
      case "time":
      case "calculator":
        return "local_reason";
      
      case "complex_analysis":
      case "creative_writing":
      case "code_generation":
        return context.cloudEnabled && !context.cloudDegraded ? "cloud_complex" : "local_reason";
    }
  }

  // Low confidence or unknown intent - use conservative routing
  return "local_reason";
}

/**
 * Adaptive routing based on historical performance
 */
export class AdaptiveRouter {
  private performanceHistory: Array<{
    route: RouteDecision;
    latency: number;
    success: boolean;
    timestamp: number;
  }> = [];

  /**
   * Record performance for a route
   */
  recordPerformance(route: RouteDecision, latency: number, success: boolean): void {
    this.performanceHistory.push({
      route,
      latency,
      success,
      timestamp: Date.now()
    });

    // Keep only last 1000 records
    if (this.performanceHistory.length > 1000) {
      this.performanceHistory = this.performanceHistory.slice(-1000);
    }
  }

  /**
   * Get performance statistics for a route
   */
  getRoutePerformance(route: RouteDecision): {
    avgLatency: number;
    successRate: number;
    sampleCount: number;
  } {
    const records = this.performanceHistory.filter(r => r.route === route);
    
    if (records.length === 0) {
      return { avgLatency: 0, successRate: 0, sampleCount: 0 };
    }

    const avgLatency = records.reduce((sum, r) => sum + r.latency, 0) / records.length;
    const successRate = records.filter(r => r.success).length / records.length;

    return {
      avgLatency,
      successRate,
      sampleCount: records.length
    };
  }

  /**
   * Get best performing route for current conditions
   */
  getBestRoute(context: RoutingContext): RouteDecision {
    const routes: RouteDecision[] = ["local_fast", "local_reason", "cloud_complex"];
    
    let bestRoute: RouteDecision = "local_fast";
    let bestScore = -1;

    for (const route of routes) {
      const perf = this.getRoutePerformance(route);
      
      if (perf.sampleCount < 10) {
        continue; // Not enough data
      }

      // Calculate score: success rate * (1 / latency factor)
      const latencyFactor = Math.max(perf.avgLatency / 1000, 0.1);
      const score = perf.successRate * (1 / latencyFactor);

      if (score > bestScore) {
        bestScore = score;
        bestRoute = route;
      }
    }

    // Apply context constraints
    if (bestRoute === "cloud_complex" && (!context.cloudEnabled || context.cloudDegraded)) {
      bestRoute = "local_reason";
    }

    if (context.hasPII) {
      bestRoute = "local_reason";
    }

    return bestRoute;
  }
}

// Export singleton adaptive router
export const adaptiveRouter = new AdaptiveRouter();
export default adaptiveRouter;
