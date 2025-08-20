// ────────────────────────────────────────────────────────────────────────────────
// Utility functions for Alice HUD
// ────────────────────────────────────────────────────────────────────────────────

// Class name utility for conditional styling
function cn(...inputs) {
  return inputs.filter(Boolean).join(" ");
}

// Clamp percentage values between 0 and 100
function clampPercent(value) {
  return Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
}

// Format time in MM:SS format
function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

// Get ISO week number for a date
function isoWeek(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
  return weekNo;
}

// Generate safe UUID (with fallback for environments without crypto.randomUUID)
function safeUUID() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `id-${Math.random().toString(36).slice(2)}-${Date.now()}`;
}

// Debounce function for performance optimization
function debounce(func, wait, immediate) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      timeout = null;
      if (!immediate) func(...args);
    };
    const callNow = immediate && !timeout;
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
    if (callNow) func(...args);
  };
}

// Throttle function for performance optimization
function throttle(func, limit) {
  let inThrottle;
  return function executedFunction(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

// Format number with appropriate suffixes (K, M, B)
function formatNumber(num) {
  if (num >= 1000000000) {
    return (num / 1000000000).toFixed(1) + 'B';
  }
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
}

// Validate if object has required properties
function validateObject(obj, requiredProps) {
  return requiredProps.every(prop => obj.hasOwnProperty(prop));
}

// Deep merge objects (simple implementation)
function mergeDeep(target, source) {
  const result = { ...target };
  
  for (const key in source) {
    if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
      result[key] = mergeDeep(result[key] || {}, source[key]);
    } else {
      result[key] = source[key];
    }
  }
  
  return result;
}

// Create animation frame loop with cleanup
function createAnimationLoop(callback) {
  let animationId;
  let isRunning = false;
  
  const loop = (timestamp) => {
    if (isRunning) {
      callback(timestamp);
      animationId = requestAnimationFrame(loop);
    }
  };
  
  return {
    start: () => {
      if (!isRunning) {
        isRunning = true;
        animationId = requestAnimationFrame(loop);
      }
    },
    stop: () => {
      isRunning = false;
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
    },
    isRunning: () => isRunning
  };
}

export { 
  cn, 
  clampPercent, 
  formatTime, 
  isoWeek, 
  safeUUID,
  debounce,
  throttle,
  formatNumber,
  validateObject,
  mergeDeep,
  createAnimationLoop
};