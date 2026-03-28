import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RAG Support Bot | AI-Powered Document Q&A",
  description:
    "Upload documents and get instant, accurate answers with source citations. Powered by GPT-4o and RAG technology.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
