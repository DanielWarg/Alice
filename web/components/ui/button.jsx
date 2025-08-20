"use client";

import * as React from "react";

function Button({ className, type = "button", ...props }) {
  return (
    <button
      type={type}
      className={className}
      {...props}
    />
  );
}

export { Button };