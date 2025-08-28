/**
 * Guardian Metrics Test Page
 * =========================
 * 
 * Test page for Guardian Metrics API endpoints and React hooks.
 * This page demonstrates all the Guardian metrics functionality and
 * can be used to verify API integration.
 */

'use client';

import { useState } from 'react';
import { 
  useGuardianSummary, 
  useGuardianCorrelation, 
  useGuardianAlerts, 
  useGuardianHistory, 
  useGuardianAnalysis,
  useGuardianDashboard,
  formatGuardianStatus,
  formatMetricValue 
} from '@/lib/guardian-metrics-hooks';

export default function GuardianMetricsTestPage() {
  const [selectedTab, setSelectedTab] = useState('dashboard');
  const [analysisType, setAnalysisType] = useState<'correlation' | 'optimization' | 'capacity' | 'prediction' | 'comprehensive'>('comprehensive');
  
  // Test all hooks
  const summary = useGuardianSummary();
  const correlation = useGuardianCorrelation(24);
  const alerts = useGuardianAlerts(24, true);
  const history = useGuardianHistory(24, 'auto', ['ram_pct', 'cpu_pct']);
  const analysis = useGuardianAnalysis(analysisType, 24, { autoRun: false });
  const dashboard = useGuardianDashboard();

  const tabs = [
    { id: 'dashboard', name: 'Dashboard Overview' },
    { id: 'summary', name: 'System Summary' },
    { id: 'correlation', name: 'Correlation Analysis' },
    { id: 'alerts', name: 'Alerts & Warnings' },
    { id: 'history', name: 'Historical Data' },
    { id: 'analysis', name: 'On-Demand Analysis' }
  ];

  const runAnalysis = () => {
    analysis.runAnalysis({
      analysis_type: analysisType,
      time_window: 24,
      include_predictions: analysisType === 'prediction' || analysisType === 'comprehensive'
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Guardian Metrics Test</h1>
          <p className="text-gray-600">
            Test interface for Guardian system monitoring and metrics API endpoints.
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setSelectedTab(tab.id)}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  selectedTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.name}
              </button>
            ))}
          </nav>
        </div>

        {/* Dashboard Overview */}
        {selectedTab === 'dashboard' && (
          <div className="space-y-6">
            <h2 className="text-2xl font-semibold text-gray-900">Dashboard Overview</h2>
            
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* System Status Card */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">System Status</h3>
                {dashboard.summary.isLoading ? (
                  <div className="animate-pulse">Loading...</div>
                ) : dashboard.summary.error ? (
                  <div className="text-red-600">Error: {dashboard.summary.error.message}</div>
                ) : dashboard.summary.data ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span>Status:</span>
                      <span className={`px-2 py-1 rounded text-sm font-medium ${
                        formatGuardianStatus(dashboard.summary.data.status).color === 'green' ? 'bg-green-100 text-green-800' :
                        formatGuardianStatus(dashboard.summary.data.status).color === 'yellow' ? 'bg-yellow-100 text-yellow-800' :
                        formatGuardianStatus(dashboard.summary.data.status).color === 'red' ? 'bg-red-100 text-red-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {formatGuardianStatus(dashboard.summary.data.status).label}
                      </span>
                    </div>
                    {dashboard.summary.data.current_metrics && (
                      <>
                        <div className="flex justify-between">
                          <span>RAM:</span>
                          <span>{formatMetricValue(dashboard.summary.data.current_metrics.ram_pct, 'percentage')}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>CPU:</span>
                          <span>{formatMetricValue(dashboard.summary.data.current_metrics.cpu_pct, 'percentage')}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Ollama PIDs:</span>
                          <span>{dashboard.summary.data.current_metrics.ollama_pids.length}</span>
                        </div>
                      </>
                    )}
                  </div>
                ) : (
                  <div>No data available</div>
                )}
              </div>

              {/* Alerts Card */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Active Alerts</h3>
                {dashboard.alerts.isLoading ? (
                  <div className="animate-pulse">Loading...</div>
                ) : dashboard.alerts.error ? (
                  <div className="text-red-600">Error: {dashboard.alerts.error.message}</div>
                ) : dashboard.alerts.data ? (
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span>Total Active:</span>
                      <span className="font-semibold">{dashboard.alerts.data.alert_summary.active_count}</span>
                    </div>
                    <div className="space-y-2">
                      {Object.entries(dashboard.alerts.data.alert_summary.by_level).map(([level, count]) => (
                        <div key={level} className="flex justify-between text-sm">
                          <span className={`px-2 py-1 rounded text-xs ${
                            level === 'CRITICAL' ? 'bg-red-100 text-red-800' :
                            level === 'ERROR' ? 'bg-orange-100 text-orange-800' :
                            level === 'WARN' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-blue-100 text-blue-800'
                          }`}>
                            {level}
                          </span>
                          <span>{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div>No alerts data</div>
                )}
              </div>

              {/* Correlation Card */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">RAM-Performance Correlation</h3>
                {dashboard.correlation.isLoading ? (
                  <div className="animate-pulse">Loading...</div>
                ) : dashboard.correlation.error ? (
                  <div className="text-red-600">Error: {dashboard.correlation.error.message}</div>
                ) : dashboard.correlation.data ? (
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span>Correlation:</span>
                      <span className="font-mono">
                        {dashboard.correlation.data.ram_performance_correlation.correlation_coefficient.toFixed(3)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Samples:</span>
                      <span>{dashboard.correlation.data.ram_performance_correlation.sample_count}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Degradations:</span>
                      <span>{dashboard.correlation.data.degradation_events}</span>
                    </div>
                    <div className="text-sm text-gray-600">
                      <strong>Top Recommendation:</strong>
                      <p className="mt-1">{dashboard.correlation.data.recommendations[0] || 'No recommendations'}</p>
                    </div>
                  </div>
                ) : (
                  <div>No correlation data</div>
                )}
              </div>
            </div>

            {/* Dashboard Actions */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Dashboard Actions</h3>
              <div className="flex space-x-4">
                <button
                  onClick={() => dashboard.refetchAll()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                  disabled={dashboard.isLoading}
                >
                  {dashboard.isLoading ? 'Refreshing...' : 'Refresh All'}
                </button>
                <div className="flex items-center text-sm text-gray-600">
                  Last updated: {dashboard.lastUpdated ? new Date(dashboard.lastUpdated).toLocaleTimeString() : 'Never'}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* System Summary Tab */}
        {selectedTab === 'summary' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-semibold text-gray-900">System Summary</h2>
              <button
                onClick={() => summary.refetch()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                disabled={summary.isLoading}
              >
                {summary.isLoading ? 'Loading...' : 'Refresh'}
              </button>
            </div>

            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-6">
                {summary.isLoading ? (
                  <div className="animate-pulse h-32 bg-gray-200 rounded"></div>
                ) : summary.error ? (
                  <div className="text-red-600 p-4 bg-red-50 rounded">
                    Error: {summary.error.message}
                  </div>
                ) : summary.data ? (
                  <div className="space-y-4">
                    <pre className="bg-gray-50 p-4 rounded overflow-auto text-sm">
                      {JSON.stringify(summary.data, null, 2)}
                    </pre>
                  </div>
                ) : (
                  <div>No data available</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Correlation Analysis Tab */}
        {selectedTab === 'correlation' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-semibold text-gray-900">Correlation Analysis</h2>
              <button
                onClick={() => correlation.refetch()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                disabled={correlation.isLoading}
              >
                {correlation.isLoading ? 'Loading...' : 'Refresh'}
              </button>
            </div>

            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-6">
                {correlation.isLoading ? (
                  <div className="animate-pulse h-32 bg-gray-200 rounded"></div>
                ) : correlation.error ? (
                  <div className="text-red-600 p-4 bg-red-50 rounded">
                    Error: {correlation.error.message}
                  </div>
                ) : correlation.data ? (
                  <div className="space-y-4">
                    <pre className="bg-gray-50 p-4 rounded overflow-auto text-sm max-h-96">
                      {JSON.stringify(correlation.data, null, 2)}
                    </pre>
                  </div>
                ) : (
                  <div>No data available</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Alerts Tab */}
        {selectedTab === 'alerts' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-semibold text-gray-900">Alerts & Warnings</h2>
              <button
                onClick={() => alerts.refetch()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                disabled={alerts.isLoading}
              >
                {alerts.isLoading ? 'Loading...' : 'Refresh'}
              </button>
            </div>

            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-6">
                {alerts.isLoading ? (
                  <div className="animate-pulse h-32 bg-gray-200 rounded"></div>
                ) : alerts.error ? (
                  <div className="text-red-600 p-4 bg-red-50 rounded">
                    Error: {alerts.error.message}
                  </div>
                ) : alerts.data ? (
                  <div className="space-y-4">
                    <pre className="bg-gray-50 p-4 rounded overflow-auto text-sm max-h-96">
                      {JSON.stringify(alerts.data, null, 2)}
                    </pre>
                  </div>
                ) : (
                  <div>No data available</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* History Tab */}
        {selectedTab === 'history' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-semibold text-gray-900">Historical Data</h2>
              <button
                onClick={() => history.refetch()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                disabled={history.isLoading}
              >
                {history.isLoading ? 'Loading...' : 'Refresh'}
              </button>
            </div>

            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-6">
                {history.isLoading ? (
                  <div className="animate-pulse h-32 bg-gray-200 rounded"></div>
                ) : history.error ? (
                  <div className="text-red-600 p-4 bg-red-50 rounded">
                    Error: {history.error.message}
                  </div>
                ) : history.data ? (
                  <div className="space-y-4">
                    <div className="text-sm text-gray-600 mb-4">
                      Data points: {history.data.meta?.total_points || 0} | 
                      Resolution: {history.data.meta?.resolution || 'unknown'} | 
                      Time range: {history.data.meta?.time_range.start ? new Date(history.data.meta.time_range.start).toLocaleString() : 'N/A'} - 
                      {history.data.meta?.time_range.end ? new Date(history.data.meta.time_range.end).toLocaleString() : 'N/A'}
                    </div>
                    <pre className="bg-gray-50 p-4 rounded overflow-auto text-sm max-h-96">
                      {JSON.stringify(history.data, null, 2)}
                    </pre>
                  </div>
                ) : (
                  <div>No data available</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Analysis Tab */}
        {selectedTab === 'analysis' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-semibold text-gray-900">On-Demand Analysis</h2>
              <div className="flex items-center space-x-4">
                <select
                  value={analysisType}
                  onChange={(e) => setAnalysisType(e.target.value as any)}
                  className="border border-gray-300 rounded-md px-3 py-2"
                >
                  <option value="comprehensive">Comprehensive</option>
                  <option value="correlation">Correlation Only</option>
                  <option value="optimization">Optimization</option>
                  <option value="capacity">Capacity</option>
                  <option value="prediction">Prediction</option>
                </select>
                <button
                  onClick={runAnalysis}
                  className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
                  disabled={analysis.isLoading}
                >
                  {analysis.isLoading ? 'Analyzing...' : 'Run Analysis'}
                </button>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-6">
                {analysis.isLoading ? (
                  <div className="flex items-center justify-center h-32">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
                    <span className="ml-2">Running {analysisType} analysis...</span>
                  </div>
                ) : analysis.error ? (
                  <div className="text-red-600 p-4 bg-red-50 rounded">
                    Error: {analysis.error.message}
                  </div>
                ) : analysis.data ? (
                  <div className="space-y-4">
                    <div className="text-sm text-gray-600 mb-4">
                      Analysis type: {analysisType} | 
                      Last run: {analysis.lastUpdated ? new Date(analysis.lastUpdated).toLocaleString() : 'Never'}
                    </div>
                    <pre className="bg-gray-50 p-4 rounded overflow-auto text-sm max-h-96">
                      {JSON.stringify(analysis.data, null, 2)}
                    </pre>
                  </div>
                ) : (
                  <div>No analysis data. Click "Run Analysis" to start.</div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}