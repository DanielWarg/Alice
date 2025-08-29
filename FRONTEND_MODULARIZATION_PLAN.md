# Frontend Modularization Plan - Alice System

**Datum:** 2025-08-29  
**Context:** Post Voice v2 Implementation - Architecture cleanup  
**Priority:** HIGH - Required för text-chat functionality

## 🎯 Problem Statement

**Current Issue:** Frontend har tight coupling med voice components
- **page.jsx** importerar alla voice-komponenter direkt
- **Hard dependencies** - frontend kraschar om voice-filer saknas  
- **No graceful degradation** när optional features inte finns
- **Missing feature flags** - kan inte disable voice cleanly

## 📋 Immediate Action Plan

### **Phase 1: Dependency Elimination (Critical)**
> *Gör text-chat fungerande utan voice dependencies*

1. **Analyze current imports** i page.jsx
   ```typescript
   // Identifiera alla voice-relaterade imports
   import VoiceBox from './components/VoiceBox'
   import VoiceGatewayClient from './lib/voice/gateway' 
   // etc...
   ```

2. **Remove hard imports** från page.jsx
   - Comment out alla voice component imports
   - Remove voice components från JSX render
   - Test att text-chat fungerar utan voice

3. **Create stub components** för graceful fallback
   ```typescript
   // components/stubs/VoiceBoxStub.tsx
   export default function VoiceBoxStub() {
     return <div className="voice-disabled">Voice module not loaded</div>
   }
   ```

4. **Test basic text chat** med backend
   - Verify API calls fungerar
   - Test agent responses
   - Ensure no voice dependencies

### **Phase 2: Conditional Loading (Architecture)**
> *Implementera feature flags och dynamic imports*

1. **Implement feature flag system**
   ```typescript
   // lib/config/features.ts
   export const FEATURES = {
     VOICE_ENABLED: process.env.NEXT_PUBLIC_VOICE_ENABLED === 'true',
     CALENDAR_ENABLED: true,
     WEATHER_ENABLED: true
   }
   ```

2. **Dynamic component loading**
   ```typescript
   // Conditional imports baserat på feature flags
   const VoiceBox = FEATURES.VOICE_ENABLED 
     ? lazy(() => import('./components/VoiceBox'))
     : () => import('./components/stubs/VoiceBoxStub')
   ```

3. **Environment configuration**
   ```bash
   # .env.local
   NEXT_PUBLIC_VOICE_ENABLED=false  # Default off
   NEXT_PUBLIC_DEBUG_MODE=true
   ```

### **Phase 3: Interface Standardization (Long-term)**
> *Plugin system för modulära komponenter*

1. **Define component interfaces**
   ```typescript
   // types/components.ts
   export interface VoiceInterface {
     isEnabled: boolean
     startRecording: () => Promise<void>
     stopRecording: () => Promise<AudioData>
     playAudio: (url: string) => Promise<void>
   }
   ```

2. **Plugin registration system**
   ```typescript
   // lib/plugins/registry.ts  
   export class ComponentRegistry {
     register(name: string, component: any) { ... }
     get(name: string) { ... }
     isAvailable(name: string): boolean { ... }
   }
   ```

## 🗂️ File Structure Changes

### **Current Problematic Structure:**
```
web/
├── app/page.jsx              # ❌ Hard imports all voice
├── components/
│   ├── VoiceBox.tsx         # ❌ Tight coupling
│   └── VoiceGatewayClient.ts # ❌ No graceful degradation
└── lib/voice/               # ❌ Always loaded
```

### **Target Modular Structure:**
```
web/
├── app/page.jsx              # ✅ Dynamic imports only
├── components/
│   ├── core/                 # ✅ Always available
│   │   ├── LLMStatusBadge.tsx
│   │   └── CalendarWidget.tsx  
│   ├── optional/             # ✅ Feature-gated
│   │   └── VoiceBox.tsx
│   └── stubs/                # ✅ Fallback components
│       └── VoiceBoxStub.tsx
├── lib/
│   ├── config/
│   │   └── features.ts       # ✅ Feature flags
│   └── plugins/
│       └── registry.ts       # ✅ Plugin system
└── types/
    └── components.ts         # ✅ Interfaces
```

## 🧪 Testing Strategy

### **Phase 1 Validation**
- [ ] Text chat works without voice imports
- [ ] No JavaScript errors på page load
- [ ] Backend API calls fungerar normalt
- [ ] LLM responses visas korrekt

### **Phase 2 Validation**  
- [ ] Feature flags toggle components correctly
- [ ] Dynamic imports load when enabled
- [ ] Stub components show when disabled
- [ ] No performance impact från conditional loading

### **Phase 3 Validation**
- [ ] Plugin system loads components dynamically
- [ ] Interface compliance verified
- [ ] Graceful degradation tested
- [ ] Performance benchmarks met

## 🚦 Implementation Priority

### **🔴 Critical (Do First)**
1. Remove voice imports från page.jsx
2. Create basic stubs för missing components
3. Test text-chat functionality

### **🟡 Important (Next)**  
1. Implement feature flag system
2. Add dynamic component loading
3. Environment configuration

### **🟢 Nice-to-Have (Later)**
1. Full plugin architecture  
2. Interface standardization
3. Advanced graceful degradation

## 🎯 Success Criteria

### **Phase 1 Complete When:**
- ✅ Frontend startar utan voice dependencies
- ✅ Text chat fungerar fullt ut  
- ✅ No breaking errors or missing imports
- ✅ Basic UI components (LLMStatusBadge, Calendar) fungerar

### **Phase 2 Complete When:**
- ✅ Feature flags control component loading
- ✅ Voice kan enables/disables via environment
- ✅ Dynamic imports work without performance issues
- ✅ Graceful fallbacks for all optional features

### **Final Goal:**
> *Alice frontend fungerar perfekt som text-only chat, med voice som optional plugin som kan laddas dynamiskt utan att påverka core functionality.*

---

## 📝 Implementation Notes

### **Key Considerations:**
1. **Backward Compatibility** - Voice v2 ska fortfarande fungera när enabled
2. **Performance** - Dynamic imports får inte påverka load times
3. **Developer Experience** - Feature flags ska vara enkla att använda  
4. **Testing** - Both enabled/disabled states måste testas

### **Risk Mitigation:**
1. **Backup plan** - Keep working voice-complete.html som fallback
2. **Gradual rollout** - Test varje fas innan nästa
3. **Documentation** - Update all docs när changes görs

---

*Detta är roadmapen för att göra Alice frontend modulär och robust, med voice som optional feature istället för hard dependency.*