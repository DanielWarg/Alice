"use client";

import * as React from "react";

function Card({ className, ...props }) {
  return (
    <div
      className={className}
      {...props}
    />
  );
}

export { Card };