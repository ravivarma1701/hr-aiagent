"use client";

import { Fragment, ReactNode } from "react";

function renderInline(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g).filter(Boolean);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return <em key={index}>{part.slice(1, -1)}</em>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={index} className="rounded bg-slate-100 px-1 py-0.5 text-xs text-slate-800">
          {part.slice(1, -1)}
        </code>
      );
    }
    return <Fragment key={index}>{part}</Fragment>;
  });
}

export function RichText({ content }: { content: string }) {
  const lines = content.split("\n");
  return (
    <div className="space-y-2 text-sm text-slate-700">
      {lines.map((line, index) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={index} className="h-1" />;
        }
        if (trimmed.startsWith("### ")) {
          return (
            <h4 key={index} className="text-sm font-semibold text-slate-900">
              {renderInline(trimmed.slice(4))}
            </h4>
          );
        }
        if (trimmed.startsWith("## ")) {
          return (
            <h3 key={index} className="text-base font-semibold text-slate-900">
              {renderInline(trimmed.slice(3))}
            </h3>
          );
        }
        if (trimmed.startsWith("# ")) {
          return (
            <h2 key={index} className="text-lg font-semibold text-slate-900">
              {renderInline(trimmed.slice(2))}
            </h2>
          );
        }
        if (trimmed.startsWith("- ")) {
          return (
            <p key={index} className="pl-3 text-sm text-slate-700">
              • {renderInline(trimmed.slice(2))}
            </p>
          );
        }
        return <p key={index}>{renderInline(trimmed)}</p>;
      })}
    </div>
  );
}
