"use client";

import * as React from "react";

function Tooltip({ children, content, ...props }) {
  return (
    <div className="relative" {...props}>
      {children}
      <div className="absolute bottom-full mb-2 hidden group-hover:block">
        <div className="bg-black text-white text-sm rounded p-2">
          {content}
        </div>
      </div>
    </div>
  );
}

export { Tooltip };