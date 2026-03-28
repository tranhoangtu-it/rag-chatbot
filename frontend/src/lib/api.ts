/** API client for RAG chatbot backend. */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ChatResponse {
  answer: string;
  sources: Source[];
  session_id: string;
}

export interface Source {
  source_file: string;
  chunk_index: number;
  distance: number;
}

export interface UploadResponse {
  filename: string;
  chunk_count: number;
  status: string;
}

/** Upload a PDF file to the backend. */
export async function uploadPdf(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Upload failed");
  }

  return res.json();
}

/** Send a chat message (non-streaming). */
export async function sendMessage(
  question: string,
  sessionId: string = "default"
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId, stream: false }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Chat request failed");
  }

  return res.json();
}

/** Send a chat message with streaming response. Calls onChunk for each text chunk. */
export async function sendMessageStream(
  question: string,
  sessionId: string = "default",
  onChunk: (text: string) => void
): Promise<Source[]> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId, stream: true }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Chat request failed");
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let sources: Source[] = [];
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Check if buffer contains the sources marker
    const sourcesIdx = buffer.indexOf("\n<<SOURCES>>");
    if (sourcesIdx !== -1) {
      // Send text before marker
      const textPart = buffer.slice(0, sourcesIdx);
      if (textPart) onChunk(textPart);

      // Parse sources JSON
      const sourcesJson = buffer.slice(sourcesIdx + "\n<<SOURCES>>".length);
      try {
        sources = JSON.parse(sourcesJson);
      } catch {
        // Sources might be split across chunks, keep buffering
      }
      buffer = "";
    } else {
      // No marker yet, send accumulated text
      onChunk(buffer);
      buffer = "";
    }
  }

  return sources;
}
