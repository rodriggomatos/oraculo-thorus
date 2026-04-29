import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Oráculo Thórus",
  description: "Oráculo técnico da Thórus Engenharia",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className="antialiased">{children}</body>
    </html>
  );
}
