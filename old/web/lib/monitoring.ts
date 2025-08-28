/**
 * Monitoring and Alerting System
 * Production-grade observability for Alice voice system
 */

import { FeatureFlag } from './feature-flags';

export interface MetricEvent {
  name: string;
  value: number;
  unit?: 'ms' | 'count' | 'bytes' | 'percent' | 'rate';
  tags?: Record<string, string>;
  timestamp?: number;
}

export interface AlertRule {
  name: string;
  metric: string;
  condition: 'gt' | 'lt' | 'eq' | 'gte' | 'lte';
  threshold: number;
  windowMs: number;
  severity: 'critical' | 'warning' | 'info';
  description: string;
}

export interface Alert {
  id: string;
  rule: AlertRule;
  value: number;
  timestamp: number;
  status: 'firing' | 'resolved';
  description: string;
}

class MonitoringSystem {
  private metrics: Map<string, MetricEvent[]> = new Map();
  private alerts: Alert[] = [];
  private alertRules: AlertRule[] = [];
  private cleanupInterval?: NodeJS.Timeout;

  constructor() {
    this.setupDefaultAlertRules();
    this.startCleanup();
  }

  private setupDefaultAlertRules() {
    this.alertRules = [
      // Voice System Alerts
      {
        name: 'high_voice_latency',
        metric: 'voice_e2e_latency_ms',
        condition: 'gt',
        threshold: 2000,
        windowMs: 5 * 60 * 1000, // 5 minutes
        severity: 'warning',
        description: 'Voice end-to-end latency is above 2 seconds'
      },
      {
        name: 'critical_voice_latency',
        metric: 'voice_e2e_latency_ms',
        condition: 'gt',
        threshold: 5000,
        windowMs: 2 * 60 * 1000, // 2 minutes
        severity: 'critical',
        description: 'Voice end-to-end latency is critically high (>5s)'
      },
      
      // Agent System Alerts
      {
        name: 'high_agent_error_rate',
        metric: 'agent_error_rate',
        condition: 'gt',
        threshold: 0.1, // 10% error rate
        windowMs: 10 * 60 * 1000, // 10 minutes
        severity: 'warning',
        description: 'Agent error rate is above 10%'
      },
      {
        name: 'agent_timeout_rate',
        metric: 'agent_timeout_rate',
        condition: 'gt',
        threshold: 0.05, // 5% timeout rate
        windowMs: 5 * 60 * 1000, // 5 minutes
        severity: 'warning',
        description: 'Agent timeout rate is above 5%'
      },
      
      // Tool System Alerts
      {
        name: 'high_tool_error_rate',
        metric: 'tool_error_rate',
        condition: 'gt',
        threshold: 0.2, // 20% error rate
        windowMs: 10 * 60 * 1000, // 10 minutes
        severity: 'warning',
        description: 'Tool error rate is above 20%'
      },
      
      // System Health Alerts
      {
        name: 'openai_api_errors',
        metric: 'openai_error_count',
        condition: 'gt',
        threshold: 5,
        windowMs: 5 * 60 * 1000, // 5 minutes
        severity: 'critical',
        description: 'Multiple OpenAI API errors detected'
      },
      {
        name: 'backend_connection_errors',
        metric: 'backend_error_count',
        condition: 'gt',
        threshold: 3,
        windowMs: 5 * 60 * 1000, // 5 minutes
        severity: 'critical',
        description: 'Backend connection errors detected'
      },
      
      // Performance Alerts
      {
        name: 'high_memory_usage',
        metric: 'memory_usage_percent',
        condition: 'gt',
        threshold: 80, // 80%
        windowMs: 5 * 60 * 1000, // 5 minutes
        severity: 'warning',
        description: 'Memory usage is above 80%'
      },
      {
        name: 'request_rate_spike',
        metric: 'request_rate_per_minute',
        condition: 'gt',
        threshold: 1000,
        windowMs: 2 * 60 * 1000, // 2 minutes
        severity: 'info',
        description: 'Request rate spike detected'
      }
    ];
  }

  private startCleanup() {
    // Clean up old metrics every 10 minutes
    this.cleanupInterval = setInterval(() => {
      this.cleanupOldMetrics();
    }, 10 * 60 * 1000);
  }

  private cleanupOldMetrics() {
    const maxAge = 24 * 60 * 60 * 1000; // 24 hours
    const cutoff = Date.now() - maxAge;

    for (const [metricName, events] of this.metrics) {
      const filteredEvents = events.filter(event => 
        (event.timestamp || 0) > cutoff
      );
      
      if (filteredEvents.length === 0) {
        this.metrics.delete(metricName);
      } else {
        this.metrics.set(metricName, filteredEvents);
      }
    }
  }

  recordMetric(event: MetricEvent) {
    if (!FeatureFlag.isMetricsCollectionEnabled()) {
      return;
    }

    const enhancedEvent = {
      ...event,
      timestamp: event.timestamp || Date.now()
    };

    const existingEvents = this.metrics.get(event.name) || [];
    existingEvents.push(enhancedEvent);
    
    // Keep only last 1000 events per metric
    if (existingEvents.length > 1000) {
      existingEvents.splice(0, existingEvents.length - 1000);
    }
    
    this.metrics.set(event.name, existingEvents);

    // Check alert rules
    this.checkAlertRules(event.name);

    // Log in development
    if (FeatureFlag.isDebugModeEnabled()) {
      console.log(`📊 Metric recorded: ${event.name} = ${event.value}${event.unit || ''}`, event.tags);
    }
  }

  private checkAlertRules(metricName: string) {
    const relevantRules = this.alertRules.filter(rule => rule.metric === metricName);
    
    for (const rule of relevantRules) {
      const value = this.calculateMetricValue(metricName, rule);
      const shouldAlert = this.evaluateCondition(value, rule.condition, rule.threshold);
      
      const existingAlert = this.alerts.find(alert => 
        alert.rule.name === rule.name && alert.status === 'firing'
      );

      if (shouldAlert && !existingAlert) {
        // Fire new alert
        const alert: Alert = {
          id: `alert_${Date.now()}_${Math.random().toString(36).substring(2)}`,
          rule,
          value,
          timestamp: Date.now(),
          status: 'firing',
          description: rule.description
        };
        
        this.alerts.push(alert);
        this.handleAlert(alert);
        
      } else if (!shouldAlert && existingAlert) {
        // Resolve existing alert
        existingAlert.status = 'resolved';
        this.handleAlertResolution(existingAlert);
      }
    }
  }

  private calculateMetricValue(metricName: string, rule: AlertRule): number {
    const events = this.metrics.get(metricName) || [];
    const windowStart = Date.now() - rule.windowMs;
    const recentEvents = events.filter(event => 
      (event.timestamp || 0) >= windowStart
    );

    if (recentEvents.length === 0) {
      return 0;
    }

    // Calculate based on metric name pattern
    if (metricName.includes('_rate')) {
      // For rate metrics, calculate rate per minute
      const totalEvents = recentEvents.reduce((sum, event) => sum + event.value, 0);
      const windowMinutes = rule.windowMs / (60 * 1000);
      return totalEvents / windowMinutes;
    } else if (metricName.includes('_percent') || metricName.includes('_usage')) {
      // For percentage metrics, use latest value
      return recentEvents[recentEvents.length - 1].value;
    } else if (metricName.includes('latency') || metricName.includes('duration')) {
      // For latency metrics, use P95
      const values = recentEvents.map(e => e.value).sort((a, b) => a - b);
      const p95Index = Math.floor(values.length * 0.95);
      return values[p95Index] || 0;
    } else {
      // For count metrics, sum all values
      return recentEvents.reduce((sum, event) => sum + event.value, 0);
    }
  }

  private evaluateCondition(value: number, condition: AlertRule['condition'], threshold: number): boolean {
    switch (condition) {
      case 'gt': return value > threshold;
      case 'gte': return value >= threshold;
      case 'lt': return value < threshold;
      case 'lte': return value <= threshold;
      case 'eq': return Math.abs(value - threshold) < 0.001;
      default: return false;
    }
  }

  private handleAlert(alert: Alert) {
    const logLevel = alert.rule.severity === 'critical' ? 'error' : 'warn';
    console[logLevel](`🚨 ALERT [${alert.rule.severity.toUpperCase()}]: ${alert.rule.name}`, {
      description: alert.description,
      value: alert.value,
      threshold: alert.rule.threshold,
      metric: alert.rule.metric,
      timestamp: new Date(alert.timestamp).toISOString()
    });

    // In production, send to external alerting service
    if (FeatureFlag.isProduction()) {
      this.sendExternalAlert(alert);
    }
  }

  private handleAlertResolution(alert: Alert) {
    console.info(`✅ RESOLVED: ${alert.rule.name}`, {
      alert_id: alert.id,
      duration_ms: Date.now() - alert.timestamp
    });
  }

  private sendExternalAlert(alert: Alert) {
    // Example: Send to Slack, PagerDuty, email, etc.
    // This would integrate with your alerting infrastructure
    try {
      // Webhook example:
      // fetch('https://hooks.slack.com/services/...', {
      //   method: 'POST',
      //   body: JSON.stringify({
      //     text: `🚨 Alice Alert: ${alert.description}`,
      //     attachments: [{
      //       color: alert.rule.severity === 'critical' ? 'danger' : 'warning',
      //       fields: [
      //         { title: 'Metric', value: alert.rule.metric },
      //         { title: 'Value', value: alert.value.toString() },
      //         { title: 'Threshold', value: alert.rule.threshold.toString() }
      //       ]
      //     }]
      //   })
      // });
      
      console.log('External alert would be sent:', alert);
    } catch (error) {
      console.error('Failed to send external alert:', error);
    }
  }

  getMetrics(metricName?: string, windowMs: number = 60 * 60 * 1000): MetricEvent[] {
    if (metricName) {
      const events = this.metrics.get(metricName) || [];
      const windowStart = Date.now() - windowMs;
      return events.filter(event => (event.timestamp || 0) >= windowStart);
    }

    // Return all metrics
    const allMetrics: MetricEvent[] = [];
    const windowStart = Date.now() - windowMs;
    
    for (const events of this.metrics.values()) {
      allMetrics.push(...events.filter(event => (event.timestamp || 0) >= windowStart));
    }
    
    return allMetrics.sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));
  }

  getAlerts(includeResolved: boolean = false): Alert[] {
    if (includeResolved) {
      return [...this.alerts];
    }
    return this.alerts.filter(alert => alert.status === 'firing');
  }

  getSystemHealth(): {
    status: 'healthy' | 'warning' | 'critical';
    alerts: number;
    metrics_collected: number;
    last_metric_timestamp?: number;
  } {
    const firingAlerts = this.getAlerts(false);
    const criticalAlerts = firingAlerts.filter(alert => alert.rule.severity === 'critical');
    const warningAlerts = firingAlerts.filter(alert => alert.rule.severity === 'warning');
    
    let status: 'healthy' | 'warning' | 'critical';
    if (criticalAlerts.length > 0) {
      status = 'critical';
    } else if (warningAlerts.length > 0) {
      status = 'warning';
    } else {
      status = 'healthy';
    }

    // Get last metric timestamp
    let lastMetricTimestamp: number | undefined;
    for (const events of this.metrics.values()) {
      if (events.length > 0) {
        const lastEvent = events[events.length - 1];
        if (!lastMetricTimestamp || (lastEvent.timestamp || 0) > lastMetricTimestamp) {
          lastMetricTimestamp = lastEvent.timestamp;
        }
      }
    }

    return {
      status,
      alerts: firingAlerts.length,
      metrics_collected: Array.from(this.metrics.values()).reduce((sum, events) => sum + events.length, 0),
      last_metric_timestamp: lastMetricTimestamp
    };
  }

  destroy() {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }
  }
}

// Global monitoring instance
const monitoring = new MonitoringSystem();

// Convenience functions
export function recordMetric(name: string, value: number, unit?: MetricEvent['unit'], tags?: Record<string, string>) {
  monitoring.recordMetric({ name, value, unit, tags });
}

export function recordVoiceLatency(phase: string, latencyMs: number, sessionId?: string) {
  recordMetric(`voice_${phase}_latency_ms`, latencyMs, 'ms', { 
    session_id: sessionId || 'unknown',
    phase 
  });
}

export function recordAgentMetrics(llmLatencyMs: number, success: boolean, sessionId?: string) {
  recordMetric('agent_llm_latency_ms', llmLatencyMs, 'ms', { 
    session_id: sessionId || 'unknown',
    success: success.toString()
  });
  
  recordMetric('agent_request_count', 1, 'count', { 
    success: success.toString()
  });
  
  if (!success) {
    recordMetric('agent_error_count', 1, 'count');
  }
}

export function recordToolMetrics(toolName: string, durationMs: number, success: boolean, sessionId?: string) {
  recordMetric('tool_duration_ms', durationMs, 'ms', { 
    tool: toolName,
    session_id: sessionId || 'unknown',
    success: success.toString()
  });
  
  recordMetric('tool_call_count', 1, 'count', { tool: toolName });
  
  if (!success) {
    recordMetric('tool_error_count', 1, 'count', { tool: toolName });
  }
}

export function recordSystemMetrics() {
  if (typeof process !== 'undefined') {
    const memUsage = process.memoryUsage();
    recordMetric('memory_usage_bytes', memUsage.heapUsed, 'bytes');
    recordMetric('memory_usage_percent', (memUsage.heapUsed / memUsage.heapTotal) * 100, 'percent');
  }
}

// Export monitoring instance and types
export { monitoring };
export type { MetricEvent, Alert, AlertRule };