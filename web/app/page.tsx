"use client";
import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, PieChart, Pie, Legend,
} from "recharts";

const fmt = (v: number | null, pct = false, cr = false) => {
  if (v == null || isNaN(v)) return "N/A";
  if (pct) return `${v.toFixed(1)}%`;
  if (cr) return v >= 1e5 ? `₹${(v / 1e5).toFixed(1)}L Cr` : `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })} Cr`;
  return v.toFixed(2);
};

const KPI = ({ label, value, sub }: { label: string; value: string; sub: string }) => (
  <div className="kpi-card" style={{ flex: 1, minWidth: 160 }}>
    <div style={{ fontSize: 10, color: "#7a98b8", textTransform: "uppercase", letterSpacing: 1 }}>{label}</div>
    <div style={{ fontSize: 28, fontWeight: 700, color: "#00C9A7", margin: "4px 0 2px" }}>{value}</div>
    <div style={{ fontSize: 11, color: "#5a7a9a" }}>{sub}</div>
  </div>
);

const SECTOR_COLORS = ["#00C9A7","#3498db","#F4A261","#9b59b6","#e74c3c","#2ecc71","#f39c12","#1abc9c","#e67e22","#27ae60"];

export default function Home() {
  const [companies, setCompanies] = useState<any[]>([]);
  const [ratios, setRatios]       = useState<any[]>([]);

  useEffect(() => {
    fetch("/data/companies.json").then(r => r.json()).then(setCompanies);
    fetch("/data/ratios_latest.json").then(r => r.json()).then(setRatios);
  }, []);

  const totalMcap   = companies.reduce((s, c) => s + (c.market_cap_cr ?? 0), 0);
  const avgRoe      = ratios.length ? ratios.reduce((s, r) => s + (r.return_on_equity_pct ?? 0), 0) / ratios.length : 0;
  const avgNpm      = ratios.length ? ratios.reduce((s, r) => s + (r.net_profit_margin_pct ?? 0), 0) / ratios.length : 0;
  const sectors     = [...new Set(companies.map(c => c.sector).filter(Boolean))];

  // Sector market cap
  const sectorMcap = sectors.map(s => ({
    name: s,
    value: companies.filter(c => c.sector === s).reduce((sum, c) => sum + (c.market_cap_cr ?? 0), 0),
  })).sort((a, b) => b.value - a.value);

  // ROE distribution
  const roeData = ratios.map(r => r.return_on_equity_pct).filter(v => v != null && !isNaN(v));
  const bins: Record<string, number> = {};
  roeData.forEach(v => {
    const b = `${Math.floor(v / 10) * 10}–${Math.floor(v / 10) * 10 + 10}%`;
    bins[b] = (bins[b] ?? 0) + 1;
  });
  const roeDist = Object.entries(bins).sort((a, b) => parseFloat(a[0]) - parseFloat(b[0]))
    .map(([range, count]) => ({ range, count }));

  // Top 15 by market cap
  const top15 = companies.slice(0, 15).map(c => {
    const r = ratios.find(r => r.company_id === c.id) ?? {};
    return { ...r, ...c };
  });

  return (
    <div>
      <h1 style={{ fontSize: 26, fontWeight: 700, color: "#0A2342", marginBottom: 4 }}>
        📈 Nifty 100 Financial Dashboard
      </h1>
      <p style={{ color: "#64748b", marginBottom: 24, fontSize: 14 }}>
        Institutional-grade analytics for 92 Nifty 100 companies
      </p>

      {/* KPI Banner */}
      <div style={{ display: "flex", gap: 16, marginBottom: 28, flexWrap: "wrap" }}>
        <KPI label="Total Companies"    value={String(companies.length)}       sub="in Nifty 100 universe" />
        <KPI label="Total Market Cap"   value={fmt(totalMcap, false, true)}    sub="combined" />
        <KPI label="Sectors Covered"    value={String(sectors.length)}         sub="GICS sectors" />
        <KPI label="Avg ROE"            value={fmt(avgRoe, true)}              sub="universe mean" />
        <KPI label="Avg Net Margin"     value={fmt(avgNpm, true)}              sub="universe mean" />
      </div>

      {/* Charts Row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 28 }}>
        <div className="glass-card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: "#0A2342" }}>
            🗺️ Market Cap by Sector
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={sectorMcap} dataKey="value" nameKey="name" cx="50%" cy="50%"
                outerRadius={110} label={({ name, percent }) => `${(name || "").split(" ")[0]} ${((percent || 0) * 100).toFixed(0)}%`}>
                {sectorMcap.map((_, i) => <Cell key={i} fill={SECTOR_COLORS[i % SECTOR_COLORS.length]} />)}
              </Pie>
              <Tooltip formatter={(v: any) => fmt(Number(v), false, true)} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="glass-card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: "#0A2342" }}>
            📊 ROE Distribution Across Nifty 100
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={roeDist}>
              <XAxis dataKey="range" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#00A896" radius={[4, 4, 0, 0]} name="Companies" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top 15 Table */}
      <div className="glass-card" style={{ padding: 20 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: "#0A2342" }}>
          🏆 Top 15 Companies by Market Cap
        </h3>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#0A2342", color: "white" }}>
                {["Ticker","Company","Sector","Mkt Cap","ROE%","NPM%","D/E","FCF (Cr)"].map(h => (
                  <th key={h} style={{ padding: "10px 12px", textAlign: "left", fontWeight: 600, whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {top15.map((c, i) => (
                <tr key={c.id} style={{ background: i % 2 === 0 ? "white" : "#f8fafc" }}>
                  <td style={{ padding: "9px 12px", fontWeight: 600, color: "#0A2342" }}>{c.id}</td>
                  <td style={{ padding: "9px 12px" }}>{c.company_name?.slice(0, 22)}</td>
                  <td style={{ padding: "9px 12px", color: "#64748b", fontSize: 11 }}>{c.sector}</td>
                  <td style={{ padding: "9px 12px" }}>{fmt(c.market_cap_cr, false, true)}</td>
                  <td style={{ padding: "9px 12px", color: (c.return_on_equity_pct ?? 0) > 15 ? "#16a34a" : "#dc2626" }}>
                    {fmt(c.return_on_equity_pct, true)}
                  </td>
                  <td style={{ padding: "9px 12px" }}>{fmt(c.net_profit_margin_pct, true)}</td>
                  <td style={{ padding: "9px 12px" }}>{fmt(c.debt_to_equity)}</td>
                  <td style={{ padding: "9px 12px" }}>{fmt(c.free_cash_flow_cr, false, true)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
