"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2, MessageSquare, Upload as UploadIcon } from "lucide-react";
import ChatMessage from "@/components/ChatMessage";
import FileUpload from "@/components/FileUpload";
import { sendMessageStream, type Source, type UploadResponse } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [sessionId] = useState(() => `session-${Date.now()}`);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (directQuestion?: string) => {
    const question = (directQuestion || input).trim();
    if (!question || isLoading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setIsLoading(true);

    // Add empty assistant message for streaming
    const assistantIdx = messages.length + 1;
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      const sources = await sendMessageStream(
        question,
        sessionId,
        (chunk) => {
          setMessages((prev) => {
            const updated = [...prev];
            const msg = updated[assistantIdx];
            if (msg) {
              updated[assistantIdx] = { ...msg, content: msg.content + chunk };
            }
            return updated;
          });
        }
      );

      // Update with sources after streaming completes
      setMessages((prev) => {
        const updated = [...prev];
        const msg = updated[assistantIdx];
        if (msg) {
          updated[assistantIdx] = { ...msg, sources };
        }
        return updated;
      });
    } catch (e) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[assistantIdx] = {
          role: "assistant",
          content: `Error: ${e instanceof Error ? e.message : "Something went wrong"}`,
        };
        return updated;
      });
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleUploadSuccess = (result: UploadResponse) => {
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: `Uploaded "${result.filename}" successfully! ${result.chunk_count} chunks indexed. You can now ask questions about this document.`,
      },
    ]);
  };

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto">
      {/* Header */}
      <header
        className="flex items-center justify-between px-6 py-4 border-b"
        style={{ borderColor: "var(--border)" }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: "var(--primary)", color: "var(--primary-foreground)" }}
          >
            <MessageSquare size={20} />
          </div>
          <div>
            <h1 className="text-lg font-semibold">RAG Support Bot</h1>
            <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
              AI-powered document Q&A with source citations
            </p>
          </div>
        </div>
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors hover:opacity-80"
          style={{
            background: showUpload ? "var(--primary)" : "var(--muted)",
            color: showUpload ? "var(--primary-foreground)" : "var(--foreground)",
          }}
        >
          <UploadIcon size={16} />
          Upload PDF
        </button>
      </header>

      {/* Upload panel */}
      {showUpload && (
        <div className="px-6 py-4 border-b" style={{ borderColor: "var(--border)" }}>
          <FileUpload onUploadSuccess={handleUploadSuccess} />
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-4">
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center"
              style={{ background: "var(--muted)" }}
            >
              <MessageSquare size={32} style={{ color: "var(--muted-foreground)" }} />
            </div>
            <div>
              <h2 className="text-xl font-semibold mb-1">Welcome to RAG Support Bot</h2>
              <p className="text-sm max-w-md" style={{ color: "var(--muted-foreground)" }}>
                Upload a PDF document or ask questions about the preloaded TechFlow support docs.
                Every answer includes source citations.
              </p>
            </div>
            <div className="flex flex-wrap gap-2 mt-2">
              {[
                "What pricing plans are available?",
                "How do I reset my password?",
                "What integrations do you support?",
                "What is the refund policy?",
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => handleSend(q)}
                  className="px-3 py-1.5 rounded-full text-xs transition-colors hover:opacity-80"
                  style={{ background: "var(--muted)", color: "var(--foreground)" }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatMessage
            key={i}
            role={msg.role}
            content={msg.content}
            sources={msg.sources}
            isStreaming={isLoading && i === messages.length - 1 && msg.role === "assistant"}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t" style={{ borderColor: "var(--border)" }}>
        <div
          className="flex items-end gap-2 rounded-xl px-4 py-3"
          style={{ background: "var(--muted)" }}
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your documents..."
            rows={1}
            className="flex-1 bg-transparent resize-none outline-none text-sm leading-relaxed"
            style={{ color: "var(--foreground)", maxHeight: "120px" }}
            disabled={isLoading}
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isLoading}
            className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-opacity disabled:opacity-30"
            style={{ background: "var(--primary)", color: "var(--primary-foreground)" }}
          >
            {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </div>
        <p className="text-center text-xs mt-2" style={{ color: "var(--muted-foreground)" }}>
          Powered by GPT-4o &middot; Answers based on uploaded documents only
        </p>
      </div>
    </div>
  );
}
