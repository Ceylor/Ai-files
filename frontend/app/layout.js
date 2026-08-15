import "./globals.css";

export const metadata = {
  title: "AI AutoClip Pro 2.0",
  description: "ИИ-генерация клипов: многослойный анализ, самообучение, пакетная обработка.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}