"use client";
import React from "react";
import AliceHUD from "../../components/AliceHUD";

/**
 * Demo page for the modular Alice HUD system
 * 
 * This page demonstrates all the modular components working together:
 * - AliceCore visualization
 * - ChatInterface with backend integration
 * - SystemMetrics with real-time updates
 * - OverlayModules for calendar, email, tasks, etc.
 * - ErrorBoundary protection for each component
 * - SafeBootMode for privacy and reliability
 */

export default function HUDDemo() {
  return (
    <div className="min-h-screen">
      <AliceHUD 
        apiEndpoint="http://localhost:8000"
        wsEndpoint="ws://localhost:8000/ws"
        enableWebSocket={true}
      />
    </div>
  );
}