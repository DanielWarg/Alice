"use client";
import { Zap, Globe } from "lucide-react";

export function RouteIcon({ source }) {
  if (source === "router") return <Zap className="h-4 w-4 text-cyan-400" />;
  if (source === "harmony") return <Globe className="h-4 w-4 text-teal-400" />;
  return null;
}