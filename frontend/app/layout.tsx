import "./globals.css";
import Providers from "./providers";

export const metadata = {
  title: "Agent Console",
  description: "Interruptible Agent Console",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
