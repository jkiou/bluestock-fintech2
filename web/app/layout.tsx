import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Nifty 100 — Financial Dashboard",
  description: "Institutional-grade analytics for all 92 Nifty 100 companies",
};

const NAV = [
  { href: "/",          icon: "🏠", label: "Home" },
  { href: "/company",   icon: "📋", label: "Company Profile" },
  { href: "/screener",  icon: "🔍", label: "Screener" },
  { href: "/peers",     icon: "👥", label: "Peer Comparison" },
  { href: "/trends",    icon: "📈", label: "Trend Analysis" },
  { href: "/sector",    icon: "🏭", label: "Sector Analysis" },
  { href: "/capital",   icon: "💰", label: "Capital Allocation" },
  { href: "/reports",   icon: "📄", label: "Annual Reports" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body style={{ fontFamily: "'Inter', sans-serif", display: "flex", minHeight: "100vh", margin: 0 }}>
        {/* Sidebar */}
        <nav className="sidebar" style={{ padding: "24px 0" }}>
          <div style={{ padding: "0 20px 24px", borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
            <div style={{ color: "#00C9A7", fontWeight: 700, fontSize: 18 }}>📈 Nifty 100</div>
            <div style={{ color: "#7a98b8", fontSize: 11, marginTop: 4 }}>Financial Dashboard</div>
          </div>
          <div style={{ padding: "12px 0" }}>
            {NAV.map(({ href, icon, label }) => (
              <Link key={href} href={href} className="nav-link">
                <span style={{ fontSize: 16 }}>{icon}</span>
                {label}
              </Link>
            ))}
          </div>
          <div style={{ padding: "16px 20px", marginTop: "auto", borderTop: "1px solid rgba(255,255,255,0.08)", color: "#4a6a8a", fontSize: 11 }}>
            <div>🗄️ NSE Nifty 100</div>
            <div>📊 92 Companies · 50+ KPIs</div>
          </div>
        </nav>

        {/* Main content */}
        <main style={{ flex: 1, padding: "28px 32px", background: "#f0f4f8", minHeight: "100vh", overflow: "auto" }}>
          {children}
        </main>
      </body>
    </html>
  );
}
