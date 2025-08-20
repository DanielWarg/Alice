"use client";

import * as React from "react";

function Badge({ className, ...props }) {
  return (
    <div
      className={className}
      {...props}
    />
  );
}

export { Badge };