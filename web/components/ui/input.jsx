"use client";

import * as React from "react";

function Input({ className, type = "text", ...props }) {
  return (
    <input
      type={type}
      className={className}
      {...props}
    />
  );
}

export { Input };