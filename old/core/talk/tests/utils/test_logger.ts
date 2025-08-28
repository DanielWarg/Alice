/**
 * Test Logger for Autonomous Voice Pipeline Testing
 * Structured logging with telemetry and performance tracking
 */

import * as fs from 'fs';
import * as path from 'path';

export interface TestLogEntry {
  timestamp: number;
  sessionId: string;
  level: 'debug' | 'info' | 'warn' | 'error' | 'metric';
  category: 'validation' | 'audio' | 'performance' | 'privacy' | 'barge_in' | 'system';
  message: string;
  data?: any;
  duration?: number;
  success?: boolean;
}

export interface TestMetrics {
  tests_started: number;
  tests_completed: number;
  tests_passed: number;
  tests_failed: number;
  average_duration_ms: number;
  validation_failures: Record<string, number>;
  privacy_violations: number;
  latency_violations: number;
  barge_in_failures: number;
}

export class TestLogger {
  private logFilePath: string;
  private metricsFilePath: string;
  private testMetrics: TestMetrics;
  private logBuffer: TestLogEntry[] = [];
  private flushInterval: NodeJS.Timeout;

  constructor(testRunId: string = 'unknown', logDir: string = 'logs/tests') {
    // Ensure log directory exists
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true });
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    this.logFilePath = path.join(logDir, `test-log-${testRunId}-${timestamp}.ndjson`);
    this.metricsFilePath = path.join(logDir, `test-metrics-${testRunId}-${timestamp}.json`);

    this.testMetrics = {
      tests_started: 0,
      tests_completed: 0,
      tests_passed: 0,
      tests_failed: 0,
      average_duration_ms: 0,
      validation_failures: {},
      privacy_violations: 0,
      latency_violations: 0,
      barge_in_failures: 0
    };

    // Flush logs every 5 seconds
    this.flushInterval = setInterval(() => this.flush(), 5000);

    this.info('system', 'Test logger initialized', { logFile: this.logFilePath, metricsFile: this.metricsFilePath });
  }

  public debug(category: TestLogEntry['category'], message: string, data?: any, sessionId: string = 'system'): void {
    this.log('debug', category, message, data, sessionId);
  }

  public info(category: TestLogEntry['category'], message: string, data?: any, sessionId: string = 'system'): void {
    this.log('info', category, message, data, sessionId);
  }

  public warn(category: TestLogEntry['category'], message: string, data?: any, sessionId: string = 'system'): void {
    this.log('warn', category, message, data, sessionId);
  }

  public error(category: TestLogEntry['category'], message: string, data?: any, sessionId: string = 'system'): void {
    this.log('error', category, message, data, sessionId);
  }

  public metric(category: TestLogEntry['category'], message: string, data?: any, sessionId: string = 'system'): void {
    this.log('metric', category, message, data, sessionId);
  }

  private log(level: TestLogEntry['level'], category: TestLogEntry['category'], message: string, data?: any, sessionId: string = 'system'): void {
    const entry: TestLogEntry = {
      timestamp: Date.now(),
      sessionId,
      level,
      category,
      message,
      data
    };

    this.logBuffer.push(entry);

    // Also log to console with colors
    this.consoleLog(entry);

    // Update metrics based on log content
    this.updateMetrics(entry);
  }

  private consoleLog(entry: TestLogEntry): void {
    const timestamp = new Date(entry.timestamp).toISOString();
    const sessionPrefix = entry.sessionId !== 'system' ? `[${entry.sessionId.slice(0, 8)}]` : '[SYSTEM]';
    const categoryPrefix = `[${entry.category.toUpperCase()}]`;

    let emoji = '';
    let color = '';

    switch (entry.level) {
      case 'debug':
        emoji = '🔍';
        color = '\x1b[37m'; // White
        break;
      case 'info':
        emoji = '📋';
        color = '\x1b[36m'; // Cyan
        break;
      case 'warn':
        emoji = '⚠️';
        color = '\x1b[33m'; // Yellow
        break;
      case 'error':
        emoji = '❌';
        color = '\x1b[31m'; // Red
        break;
      case 'metric':
        emoji = '📊';
        color = '\x1b[35m'; // Magenta
        break;
    }

    const resetColor = '\x1b[0m';
    const formattedMessage = `${color}${emoji} ${sessionPrefix}${categoryPrefix} ${entry.message}${resetColor}`;

    console.log(formattedMessage);
    
    // Log structured data if present
    if (entry.data && Object.keys(entry.data).length > 0) {
      console.log('  ', JSON.stringify(entry.data, null, 2).split('\n').join('\n   '));
    }
  }

  private updateMetrics(entry: TestLogEntry): void {
    // Update metrics based on log patterns
    if (entry.category === 'system') {
      if (entry.message.includes('Test started')) {
        this.testMetrics.tests_started++;
      } else if (entry.message.includes('Test completed')) {
        this.testMetrics.tests_completed++;
        if (entry.success === true) {
          this.testMetrics.tests_passed++;
        } else if (entry.success === false) {
          this.testMetrics.tests_failed++;
        }

        if (entry.duration) {
          // Update average duration
          const totalTests = this.testMetrics.tests_completed;
          this.testMetrics.average_duration_ms = 
            (this.testMetrics.average_duration_ms * (totalTests - 1) + entry.duration) / totalTests;
        }
      }
    }

    // Track validation failures
    if (entry.level === 'error' && entry.category === 'validation') {
      const validationType = entry.data?.validationType || 'unknown';
      this.testMetrics.validation_failures[validationType] = 
        (this.testMetrics.validation_failures[validationType] || 0) + 1;
    }

    // Track specific violation types
    if (entry.category === 'privacy' && entry.level === 'error') {
      this.testMetrics.privacy_violations++;
    }

    if (entry.category === 'performance' && entry.level === 'error') {
      this.testMetrics.latency_violations++;
    }

    if (entry.category === 'barge_in' && entry.level === 'error') {
      this.testMetrics.barge_in_failures++;
    }
  }

  public logTestStart(sessionId: string, testType: string, scenario: string): void {
    this.info('system', 'Test started', { 
      testType, 
      scenario,
      startTime: Date.now()
    }, sessionId);
  }

  public logTestComplete(sessionId: string, testType: string, success: boolean, duration: number, details?: any): void {
    this.info('system', 'Test completed', { 
      testType, 
      success,
      duration,
      endTime: Date.now(),
      ...details
    }, sessionId);
    
    // Also create a metric entry
    this.metric('system', `Test ${success ? 'passed' : 'failed'}: ${testType}`, {
      duration,
      success,
      ...details
    }, sessionId);
  }

  public logValidationResult(sessionId: string, validationType: string, result: any): void {
    const level = result.passed ? 'info' : 'error';
    const message = `${validationType} validation ${result.passed ? 'passed' : 'failed'}`;
    
    this.log(level, 'validation', message, {
      validationType,
      passed: result.passed,
      score: result.score,
      failures: result.failures,
      warnings: result.warnings,
      metrics: result.timings || result.metrics
    }, sessionId);
  }

  public logPrivacyViolation(sessionId: string, violation: any): void {
    this.error('privacy', `Privacy violation detected: ${violation.type}`, {
      violationType: violation.type,
      severity: violation.severity,
      location: violation.location,
      content: violation.content.substring(0, 50) + '...', // Truncate for safety
      context: violation.context
    }, sessionId);
  }

  public logLatencyViolation(sessionId: string, metric: string, actual: number, target: number): void {
    this.error('performance', `Latency violation: ${metric}`, {
      metric,
      actualMs: actual,
      targetMs: target,
      violation: actual - target
    }, sessionId);
  }

  public logBargeInFailure(sessionId: string, failure: string, timings?: any): void {
    this.error('barge_in', `Barge-in failure: ${failure}`, {
      failure,
      timings
    }, sessionId);
  }

  public logAudioGeneration(sessionId: string, text: string, method: string, duration: number): void {
    this.debug('audio', `Generated audio for text`, {
      textLength: text.length,
      method,
      generationTimeMs: duration,
      textPreview: text.substring(0, 50) + (text.length > 50 ? '...' : '')
    }, sessionId);
  }

  public logPerformanceSummary(summary: any): void {
    this.metric('performance', 'Performance summary generated', summary);
  }

  public getCurrentMetrics(): TestMetrics {
    return { ...this.testMetrics };
  }

  public flush(): void {
    if (this.logBuffer.length === 0) return;

    try {
      // Write all buffered logs to file
      const logLines = this.logBuffer.map(entry => JSON.stringify(entry)).join('\n') + '\n';
      fs.appendFileSync(this.logFilePath, logLines);

      // Write current metrics
      fs.writeFileSync(this.metricsFilePath, JSON.stringify(this.testMetrics, null, 2));

      // Clear buffer
      this.logBuffer = [];
    } catch (error) {
      console.error('❌ Failed to flush test logs:', error);
    }
  }

  public generateReport(): TestReport {
    const report: TestReport = {
      summary: this.testMetrics,
      logFile: this.logFilePath,
      metricsFile: this.metricsFilePath,
      testDuration: Date.now() - (this.testMetrics.tests_started > 0 ? 
        fs.statSync(this.logFilePath).birthtimeMs : Date.now()),
      recommendations: this.generateRecommendations()
    };

    // Write report to file
    const reportPath = this.logFilePath.replace('.ndjson', '-report.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));

    return report;
  }

  private generateRecommendations(): string[] {
    const recommendations: string[] = [];
    const metrics = this.testMetrics;

    if (metrics.tests_completed === 0) {
      recommendations.push('No tests completed. Verify test execution.');
      return recommendations;
    }

    const successRate = metrics.tests_passed / metrics.tests_completed;
    
    if (successRate < 0.8) {
      recommendations.push(`Low success rate (${(successRate * 100).toFixed(1)}%). Review failing tests.`);
    }

    if (metrics.privacy_violations > 0) {
      recommendations.push(`${metrics.privacy_violations} privacy violations detected. Review PII handling.`);
    }

    if (metrics.latency_violations > 0) {
      recommendations.push(`${metrics.latency_violations} latency violations detected. Optimize performance.`);
    }

    if (metrics.barge_in_failures > 0) {
      recommendations.push(`${metrics.barge_in_failures} barge-in failures detected. Review interrupt handling.`);
    }

    if (metrics.average_duration_ms > 10000) {
      recommendations.push(`Long average test duration (${metrics.average_duration_ms.toFixed(0)}ms). Consider optimization.`);
    }

    // Specific validation failure recommendations
    Object.entries(metrics.validation_failures).forEach(([type, count]) => {
      if (count > 0) {
        recommendations.push(`${count} ${type} validation failures. Review ${type} implementation.`);
      }
    });

    if (recommendations.length === 0) {
      recommendations.push('All tests passing! System performing well.');
    }

    return recommendations;
  }

  public cleanup(): void {
    // Clear flush interval
    if (this.flushInterval) {
      clearInterval(this.flushInterval);
    }

    // Final flush
    this.flush();

    // Generate final report
    const report = this.generateReport();
    
    console.log('\n📊 === Test Session Summary ===');
    console.log(`🎯 Tests completed: ${report.summary.tests_completed}`);
    console.log(`✅ Tests passed: ${report.summary.tests_passed}`);
    console.log(`❌ Tests failed: ${report.summary.tests_failed}`);
    console.log(`📈 Success rate: ${((report.summary.tests_passed / report.summary.tests_completed) * 100).toFixed(1)}%`);
    console.log(`⏱️ Average duration: ${report.summary.average_duration_ms.toFixed(0)}ms`);
    console.log(`🛡️ Privacy violations: ${report.summary.privacy_violations}`);
    console.log(`⚡ Latency violations: ${report.summary.latency_violations}`);
    console.log(`🎙️ Barge-in failures: ${report.summary.barge_in_failures}`);
    console.log(`📄 Log file: ${report.logFile}`);
    console.log(`📊 Report: ${report.logFile.replace('.ndjson', '-report.json')}`);
    console.log('================================\n');

    if (report.recommendations.length > 0) {
      console.log('💡 Recommendations:');
      report.recommendations.forEach(rec => console.log(`   • ${rec}`));
      console.log('');
    }
  }
}

interface TestReport {
  summary: TestMetrics;
  logFile: string;
  metricsFile: string;
  testDuration: number;
  recommendations: string[];
}