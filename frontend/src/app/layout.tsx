import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Akademik Bellek Asistanı",
  description:
    "Multimodal RAG tabanlı akademik yardımcı. Ders PDF, ses ve görsellerini yükle, doğal dille sorgula.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr">
      <body>{children}</body>
    </html>
  );
}
