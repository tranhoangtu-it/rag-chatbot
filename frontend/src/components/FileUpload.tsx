"use client";

import { useState, useCallback } from "react";
import { Upload, FileText, Check, AlertCircle, Loader2 } from "lucide-react";
import { uploadPdf, type UploadResponse } from "@/lib/api";

interface FileUploadProps {
  onUploadSuccess: (result: UploadResponse) => void;
}

export default function FileUpload({ onUploadSuccess }: FileUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploads, setUploads] = useState<UploadResponse[]>([]);

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);

      if (!file.name.toLowerCase().endsWith(".pdf")) {
        setError("Only PDF files are accepted.");
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        setError("File too large. Maximum size is 5MB.");
        return;
      }

      setUploading(true);
      try {
        const result = await uploadPdf(file);
        setUploads((prev) => [...prev, result]);
        onUploadSuccess(result);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [onUploadSuccess]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
      e.target.value = "";
    },
    [handleFile]
  );

  return (
    <div className="space-y-3">
      {/* Drop zone */}
      <label
        className={`flex flex-col items-center justify-center gap-2 p-6 border-2 border-dashed rounded-xl cursor-pointer transition-all ${
          isDragOver ? "border-[var(--primary)] bg-[var(--accent)]" : "border-[var(--border)] hover:border-[var(--primary)]"
        }`}
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={onDrop}
      >
        <input
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={onFileSelect}
          disabled={uploading}
        />
        {uploading ? (
          <Loader2 size={24} className="animate-spin" style={{ color: "var(--primary)" }} />
        ) : (
          <Upload size={24} style={{ color: "var(--muted-foreground)" }} />
        )}
        <span className="text-sm" style={{ color: "var(--muted-foreground)" }}>
          {uploading ? "Uploading..." : "Drop PDF here or click to browse"}
        </span>
        <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
          Max 5MB, text-based PDFs only
        </span>
      </label>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 text-sm text-red-500">
          <AlertCircle size={14} />
          {error}
        </div>
      )}

      {/* Upload list */}
      {uploads.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs font-medium" style={{ color: "var(--muted-foreground)" }}>
            Uploaded Documents
          </p>
          {uploads.map((u, i) => (
            <div
              key={i}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm"
              style={{ background: "var(--muted)" }}
            >
              <FileText size={14} style={{ color: "var(--primary)" }} />
              <span className="flex-1 truncate">{u.filename}</span>
              <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                {u.chunk_count} chunks
              </span>
              <Check size={14} className="text-green-500" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
