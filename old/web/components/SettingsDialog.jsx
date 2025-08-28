'use client'

import React, { useState, useEffect } from 'react'

const SettingsDialog = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState('voice')
  const [settings, setSettings] = useState({
    voice: {
      inputDeviceId: null,
      vad: 0.6,
      bargeIn: true,
      latencyTarget: 300
    },
    proactivity: {
      level: 'standard',
      maxPromptsPerDay: 1,
      quietHours: ['00:00', '07:00']
    },
    privacy: {
      ttlDays: 30,
      sensitiveTtlHours: 24,
      autoForgetAck: true
    },
    integrations: {
      ha: { baseUrl: '', ok: false },
      spotify: { connected: false },
      tts: 'piper'
    },
    system: {
      devVerbose: false,
      version: '1.0.0'
    }
  })

  const [showAdvanced, setShowAdvanced] = useState({
    voice: false,
    proactivity: false,
    privacy: false,
    integrations: false,
    system: false
  })

  const [showSuggestionsHistory, setShowSuggestionsHistory] = useState(false)

  const tabs = [
    { id: 'voice', name: 'Voice & Audio', icon: '🎙️' },
    { id: 'proactivity', name: 'Proactivity', icon: '🧠' },
    { id: 'privacy', name: 'Privacy', icon: '🔒' },
    { id: 'integrations', name: 'Integrations', icon: '🔌' },
    { id: 'system', name: 'System', icon: '⚙️' }
  ]

  // Load settings on mount
  useEffect(() => {
    if (isOpen) {
      fetchSettings()
    }
  }, [isOpen])

  const fetchSettings = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/settings')
      if (response.ok) {
        const data = await response.json()
        setSettings(prev => ({ ...prev, ...data }))
      }
    } catch (error) {
      console.warn('Could not load settings:', error)
    }
  }

  const saveSettings = async () => {
    try {
      // Save general settings
      await fetch('http://127.0.0.1:8000/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      })
      
      // Save proactive settings specifically
      await fetch('http://127.0.0.1:8000/api/proactive/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          level: settings.proactivity.level,
          quiet_hours_start: parseInt(settings.proactivity.quietHours[0].split(':')[0]),
          quiet_hours_end: parseInt(settings.proactivity.quietHours[1].split(':')[0]),
          max_prompts_per_day: settings.proactivity.maxPromptsPerDay
        })
      })
      
      console.log('Settings saved successfully')
    } catch (error) {
      console.error('Failed to save settings:', error)
    }
  }

  const updateSetting = (category, key, value) => {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value
      }
    }))
  }

  const toggleAdvanced = (tab) => {
    setShowAdvanced(prev => ({
      ...prev,
      [tab]: !prev[tab]
    }))
  }

  const renderVoiceTab = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-cyan-200 mb-2">
          Input Device
        </label>
        <select
          className="w-full bg-cyan-950/40 border border-cyan-400/30 rounded-xl px-3 py-2 text-cyan-100 backdrop-blur-sm focus:border-cyan-400/50 focus:outline-none"
          value={settings.voice.inputDeviceId || ''}
          onChange={(e) => updateSetting('voice', 'inputDeviceId', e.target.value)}
        >
          <option value="">Default Microphone</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-cyan-200 mb-2">
          Voice Activity Detection: {settings.voice.vad.toFixed(1)}
        </label>
        <input
          type="range"
          min="0.1"
          max="1.0"
          step="0.1"
          value={settings.voice.vad}
          onChange={(e) => updateSetting('voice', 'vad', parseFloat(e.target.value))}
          className="w-full accent-cyan-500"
        />
        <div className="flex justify-between text-xs text-cyan-300/70 mt-1">
          <span>Sensitive</span>
          <span>Conservative</span>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-medium text-cyan-200">Barge-in Detection</div>
          <div className="text-xs text-cyan-300/70">Interrupt Alice when you speak</div>
        </div>
        <button
          onClick={() => updateSetting('voice', 'bargeIn', !settings.voice.bargeIn)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            settings.voice.bargeIn ? 'bg-cyan-500' : 'bg-cyan-800/50'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              settings.voice.bargeIn ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      {/* Advanced Voice Settings */}
      <div>
        <button
          onClick={() => toggleAdvanced('voice')}
          className="flex items-center text-sm text-cyan-300/70 hover:text-cyan-200"
        >
          <span className={`mr-2 transform transition-transform ${showAdvanced.voice ? 'rotate-90' : ''}`}>
            ▸
          </span>
          Advanced Voice Settings
        </button>
        
        {showAdvanced.voice && (
          <div className="mt-4 pl-6 space-y-4 border-l border-cyan-400/30">
            <div>
              <label className="block text-sm font-medium text-cyan-200 mb-2">
                Latency Target: {settings.voice.latencyTarget}ms
              </label>
              <input
                type="range"
                min="100"
                max="1000"
                step="50"
                value={settings.voice.latencyTarget}
                onChange={(e) => updateSetting('voice', 'latencyTarget', parseInt(e.target.value))}
                className="w-full accent-cyan-500"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )

  const renderProactivityTab = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-cyan-200 mb-2">
          Proactivity Level
        </label>
        <select
          className="w-full bg-cyan-950/40 border border-cyan-400/30 rounded-xl px-3 py-2 text-cyan-100 backdrop-blur-sm focus:border-cyan-400/50 focus:outline-none"
          value={settings.proactivity.level}
          onChange={(e) => updateSetting('proactivity', 'level', e.target.value)}
        >
          <option value="off">Off - No suggestions</option>
          <option value="minimal">Minimal - Very few suggestions</option>
          <option value="standard">Standard - Balanced suggestions</option>
          <option value="eager">Eager - Frequent suggestions</option>
        </select>
        <div className="text-xs text-cyan-300/70 mt-1">
          {settings.proactivity.level === 'off' && 'Alice will not make proactive suggestions'}
          {settings.proactivity.level === 'minimal' && 'Alice will only suggest with high confidence patterns'}
          {settings.proactivity.level === 'standard' && 'Alice will suggest based on learned patterns'}
          {settings.proactivity.level === 'eager' && 'Alice will suggest frequently with lower confidence patterns'}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-cyan-200 mb-2">
          Max Prompts Per Day: {settings.proactivity.maxPromptsPerDay}
        </label>
        <input
          type="range"
          min="0"
          max="10"
          step="1"
          value={settings.proactivity.maxPromptsPerDay}
          onChange={(e) => updateSetting('proactivity', 'maxPromptsPerDay', parseInt(e.target.value))}
          className="w-full accent-cyan-500"
        />
        <div className="text-xs text-cyan-300/70 mt-1">
          {settings.proactivity.maxPromptsPerDay === 0 ? 'No daily limit' : `Maximum ${settings.proactivity.maxPromptsPerDay} suggestions per day`}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-cyan-200 mb-2">
          Quiet Hours
        </label>
        <div className="flex items-center space-x-4">
          <input
            type="time"
            value={settings.proactivity.quietHours[0]}
            onChange={(e) => updateSetting('proactivity', 'quietHours', [e.target.value, settings.proactivity.quietHours[1]])}
            className="bg-cyan-950/40 backdrop-blur-sm border border-cyan-400/30 rounded px-3 py-2 text-cyan-100 focus:border-cyan-400/50 focus:outline-none"
          />
          <span className="text-cyan-300/70">to</span>
          <input
            type="time"
            value={settings.proactivity.quietHours[1]}
            onChange={(e) => updateSetting('proactivity', 'quietHours', [settings.proactivity.quietHours[0], e.target.value])}
            className="bg-cyan-950/40 backdrop-blur-sm border border-cyan-400/30 rounded px-3 py-2 text-cyan-100 focus:border-cyan-400/50 focus:outline-none"
          />
        </div>
        <div className="text-xs text-cyan-300/70 mt-1">
          Alice will not make suggestions during these hours
        </div>
      </div>

      {showAdvanced.proactivity && (
        <div className="space-y-4 border-t border-cyan-400/30 pt-4">
          <div>
            <h4 className="text-sm font-medium text-cyan-200 mb-3">Pattern Learning</h4>
            <div className="space-y-2 text-sm text-cyan-300/70">
              <div className="flex justify-between">
                <span>Confidence threshold:</span>
                <span>50%</span>
              </div>
              <div className="flex justify-between">
                <span>Pattern cooldown:</span>
                <span>24 hours</span>
              </div>
              <div className="flex justify-between">
                <span>Min pattern occurrences:</span>
                <span>3</span>
              </div>
            </div>
          </div>

          <div>
            <button
              onClick={async () => {
                try {
                  const response = await fetch('http://127.0.0.1:8000/api/proactive/patterns/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ lookback_days: 7 })
                  })
                  const result = await response.json()
                  alert(`Pattern analysis complete: ${result.patterns_found} patterns found`)
                } catch (error) {
                  alert('Failed to trigger pattern analysis')
                }
              }}
              className="w-full bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400/30 text-cyan-200 py-2 px-4 rounded-xl transition-colors backdrop-blur-sm"
            >
              🔄 Trigger Pattern Analysis
            </button>
          </div>

          <div>
            <button
              onClick={() => setShowSuggestionsHistory(!showSuggestionsHistory)}
              className="w-full bg-cyan-900/40 hover:bg-cyan-900/60 border border-cyan-400/30 text-cyan-200 py-2 px-4 rounded-xl transition-colors backdrop-blur-sm"
            >
              📊 {showSuggestionsHistory ? 'Hide' : 'View'} Recent Suggestions
            </button>
          </div>
        </div>
      )}

      {showSuggestionsHistory && (
        <div className="space-y-4 border-t border-cyan-400/30 pt-4">
          <h4 className="text-sm font-medium text-cyan-200 mb-3">Recent Suggestions</h4>
          <div className="bg-cyan-950/40 backdrop-blur-sm border border-cyan-400/30 rounded-xl p-4 max-h-60 overflow-y-auto">
            <div className="space-y-2">
              <div className="text-xs text-cyan-300/70 flex justify-between">
                <span>Loading suggestions...</span>
                <span>--:--</span>
              </div>
              <div className="text-xs text-cyan-300/50 italic">
                Connect to the backend to view suggestion history
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="border-t border-cyan-400/30 pt-4">
        <button
          onClick={() => setShowAdvanced(prev => ({ ...prev, proactivity: !prev.proactivity }))}
          className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
        >
          {showAdvanced.proactivity ? '▲ Hide Advanced' : '▼ Show Advanced'}
        </button>
      </div>
    </div>
  )

  const renderPrivacyTab = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-cyan-200 mb-2">
          Data Retention: {settings.privacy.ttlDays} days
        </label>
        <input
          type="range"
          min="1"
          max="365"
          step="1"
          value={settings.privacy.ttlDays}
          onChange={(e) => updateSetting('privacy', 'ttlDays', parseInt(e.target.value))}
          className="w-full accent-cyan-500"
        />
        <div className="text-xs text-cyan-300/70 mt-1">
          General conversation data will be automatically deleted after this period
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-cyan-200 mb-2">
          Sensitive Data TTL: {settings.privacy.sensitiveTtlHours} hours
        </label>
        <input
          type="range"
          min="1"
          max="168"
          step="1"
          value={settings.privacy.sensitiveTtlHours}
          onChange={(e) => updateSetting('privacy', 'sensitiveTtlHours', parseInt(e.target.value))}
          className="w-full accent-cyan-500"
        />
        <div className="text-xs text-cyan-300/70 mt-1">
          Sensitive information (passwords, personal details) deleted faster
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-medium text-cyan-200">Auto-confirm "Forget"</div>
          <div className="text-xs text-cyan-300/70">Skip confirmation for "glöm det där" commands</div>
        </div>
        <button
          onClick={() => updateSetting('privacy', 'autoForgetAck', !settings.privacy.autoForgetAck)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            settings.privacy.autoForgetAck ? 'bg-cyan-500' : 'bg-cyan-800/50'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              settings.privacy.autoForgetAck ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      <div className="border-t border-cyan-400/30 pt-6">
        <button
          onClick={() => {
            if (confirm('This will delete all conversation history. Are you sure?')) {
              fetch('http://127.0.0.1:8000/api/privacy/wipe', { method: 'POST' })
            }
          }}
          className="w-full bg-red-500/20 hover:bg-red-500/30 border border-red-400/30 text-red-200 py-2 px-4 rounded-xl transition-colors backdrop-blur-sm"
        >
          Delete All Data
        </button>
      </div>
    </div>
  )

  const renderIntegrationsTab = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-cyan-100 mb-4">🏠 Home Assistant</h3>
        <div className="space-y-3">
          <input
            type="url"
            placeholder="http://homeassistant.local:8123"
            value={settings.integrations.ha.baseUrl}
            onChange={(e) => updateSetting('integrations', 'ha', { ...settings.integrations.ha, baseUrl: e.target.value })}
            className="w-full bg-cyan-950/40 backdrop-blur-sm border border-cyan-400/30 rounded-xl px-3 py-2 text-cyan-100 focus:border-cyan-400/50 focus:outline-none"
          />
          <div className="flex items-center">
            <span className={`w-3 h-3 rounded-full mr-2 ${settings.integrations.ha.ok ? 'bg-green-500' : 'bg-red-500'}`}></span>
            <span className="text-sm text-cyan-300/70">
              {settings.integrations.ha.ok ? 'Connected' : 'Not connected'}
            </span>
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-medium text-cyan-100 mb-4">🎵 Spotify</h3>
        <div className="flex items-center">
          <span className={`w-3 h-3 rounded-full mr-2 ${settings.integrations.spotify.connected ? 'bg-green-500' : 'bg-red-500'}`}></span>
          <span className="text-sm text-cyan-300/70">
            {settings.integrations.spotify.connected ? 'Connected' : 'Not connected'}
          </span>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-cyan-200 mb-2">
          TTS Provider
        </label>
        <select
          className="w-full bg-cyan-950/40 backdrop-blur-sm border border-cyan-400/30 rounded-xl px-3 py-2 text-cyan-100 focus:border-cyan-400/50 focus:outline-none"
          value={settings.integrations.tts}
          onChange={(e) => updateSetting('integrations', 'tts', e.target.value)}
        >
          <option value="piper">Piper (Local Swedish)</option>
          <option value="openai">OpenAI (Cloud)</option>
        </select>
      </div>
    </div>
  )

  const renderSystemTab = () => (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-medium text-cyan-200">Verbose Logging</div>
          <div className="text-xs text-cyan-300/70">Enable detailed debug output</div>
        </div>
        <button
          onClick={() => updateSetting('system', 'devVerbose', !settings.system.devVerbose)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            settings.system.devVerbose ? 'bg-cyan-500' : 'bg-cyan-800/50'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              settings.system.devVerbose ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      <div className="border-t border-cyan-400/30 pt-6">
        <div className="text-sm text-cyan-300/70 mb-2">Alice Version</div>
        <div className="text-white font-mono">{settings.system.version}</div>
      </div>

      <div>
        <button
          onClick={() => window.open('http://127.0.0.1:8000/metrics', '_blank')}
          className="w-full bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400/30 text-cyan-100 py-2 px-4 rounded-xl transition-colors backdrop-blur-sm"
        >
          Open Metrics Dashboard
        </button>
      </div>
    </div>
  )

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 grid place-items-center pointer-events-none" onClick={onClose}>
      <div 
        className="pointer-events-auto relative w-[min(95vw,1200px)] rounded-2xl border border-cyan-400/30 bg-cyan-950/60 backdrop-blur-xl shadow-[0_0_80px_-20px_rgba(34,211,238,.6)] overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Background Effects */}
        <div className="pointer-events-none absolute inset-0 [background:radial-gradient(ellipse_at_top,rgba(13,148,136,.15),transparent_60%),radial-gradient(ellipse_at_bottom,rgba(3,105,161,.12),transparent_60%)]" />
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(#0e7490_1px,transparent_1px),linear-gradient(90deg,#0e7490_1px,transparent_1px)] bg-[size:40px_40px] opacity-10" />
        {/* Close Button */}
        <button 
          aria-label="Stäng" 
          onClick={onClose} 
          className="absolute right-3 top-3 z-10 rounded-lg border border-cyan-400/30 px-2 py-1 text-xs hover:bg-cyan-400/10 bg-cyan-950/80 backdrop-blur"
        >
          Stäng
        </button>
        
        {/* Header */}
        <div className="p-5 pt-12">
          <div className="mb-6">
            <h2 className="text-cyan-200/90 text-xl uppercase tracking-widest font-semibold">Settings</h2>
            <div className="text-xs text-cyan-300/70 mt-1">Configure Alice system preferences</div>
          </div>

        <div className="flex h-[600px]">
          {/* Tab Navigation */}
          <div className="w-64 bg-cyan-950/40 border-r border-cyan-400/20">
            <nav className="p-4 space-y-2">
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full text-left px-4 py-3 rounded-xl transition-colors ${
                    activeTab === tab.id
                      ? 'bg-cyan-500/20 text-cyan-100 border border-cyan-400/30 shadow-[0_0_20px_-8px_rgba(34,211,238,.4)]'
                      : 'text-cyan-300/80 hover:bg-cyan-400/10 hover:text-cyan-100'
                  }`}
                >
                  <span className="mr-3">{tab.icon}</span>
                  {tab.name}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="flex-1 p-6 overflow-y-auto bg-cyan-950/20">
            {activeTab === 'voice' && renderVoiceTab()}
            {activeTab === 'proactivity' && renderProactivityTab()}
            {activeTab === 'privacy' && renderPrivacyTab()}
            {activeTab === 'integrations' && renderIntegrationsTab()}
            {activeTab === 'system' && renderSystemTab()}
          </div>
        </div>

          {/* Footer */}
          <div className="flex justify-end space-x-4 pt-6 mt-6 border-t border-cyan-400/20">
            <button
              onClick={onClose}
              className="px-6 py-2 text-cyan-300/70 hover:text-cyan-100 transition-colors rounded-xl hover:bg-cyan-400/10"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                saveSettings()
                onClose()
              }}
              className="px-6 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400/30 text-cyan-100 rounded-xl transition-colors hover:scale-105"
            >
              Save Changes
            </button>
          </div>
        </div>
        
        {/* Inset Ring Effect */}
        <div className="pointer-events-none absolute inset-0 rounded-2xl ring-1 ring-inset ring-cyan-300/10"></div>
      </div>
    </div>
  )
}

export default SettingsDialog