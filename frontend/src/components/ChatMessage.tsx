"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, FileText, Bot, User } from "lucide-react";
import type { Source } from "@/lib/api";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  isStreaming?: boolean;
}

export default function ChatMessage({
  role,
  content,
  sources,
  isStreaming,
}: ChatMessageProps) {
  const [showSources, setShowSources] = useState(false);
  const isUser = role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
          style={{ background: "var(--primary)", color: "var(--primary-foreground)" }}>
          <Bot size={16} />
        </div>
      )}

      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 ${
          isUser
            ? "rounded-br-md"
            : "rounded-bl-md"
        }`}
        style={{
          background: isUser ? "var(--primary)" : "var(--muted)",
          color: isUser ? "var(--primary-foreground)" : "var(--foreground)",
        }}
      >
        <div className="whitespace-pre-wrap text-sm leading-relaxed">
          {content}
          {isStreaming && (
            <span className="inline-block w-2 h-4 ml-1 animate-pulse"
              style={{ background: "var(--muted-foreground)" }} />
          )}
        </div>

        {/* Source citations */}
        {sources && sources.length > 0 && !isStreaming && (
          <div className="mt-2 pt-2" style={{ borderTop: "1px solid var(--border)" }}>
            <button
              onClick={() => setShowSources(!showSources)}
              className="flex items-center gap-1 text-xs font-medium opacity-70 hover:opacity-100 transition-opacity"
            >
              {showSources ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              {sources.length} source{sources.length > 1 ? "s" : ""}
            </button>
            {showSources && (
              <div className="mt-1.5 space-y-1">
                {sources.map((s, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-1.5 text-xs opacity-60 py-0.5"
                  >
                    <FileText size={10} />
                    <span>
                      {s.source_file} (chunk {s.chunk_index})
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
          style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}>
          <User size={16} />
        </div>
      )}
    </div>
  );
}
