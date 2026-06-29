"use client";

import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
  LineChart, Line, AreaChart, Area
} from "recharts";

const fmt = (v: number | null, pct = false, cr = false) => {
  if (v == null || isNaN(v)) return "N/A";
  if (pct) return `${v.toFixed(1)}%`;
  if (cr) return v >= 1e5 ? `₹${(v / 1e5).toFixed(1)}L Cr` : `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })} Cr`;
  return v.toFixed(2);
};

export default function CompanyProfile() {
  const [companies, setCompanies] = useState<any[]>([]);
  const [ratios, setRatios] = useState<any[]>([]);
  const [pl, setPl] = useState<any[]>([]);
  const [bs, setBs] = useState<any[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string>("");
  const [activeTab, setActiveTab] = useState<string>("revenue");

  useEffect(() => {
    Promise.all([
      fetch("/data/companies.json").then((r) => r.json()),
      fetch("/data/ratios_latest.json").then((r) => r.json()),
      fetch("/data/pl.json").then((r) => r.json()),
      fetch("/data/bs.json").then((r) => r.json()),
    ]).then(([comps, rats, plData, bsData]) => {
      setCompanies(comps);
      setRatios(rats);
      setPl(plData);
      setBs(bsData);
      if (comps.length > 0) {
        setSelectedTicker(comps[0].id);
      }
    });
  }, []);

  const selectedCompany = companies.find((c) => c.id === selectedTicker) || null;
  const companyRatios = ratios.filter((r) => r.company_id === selectedTicker);
  const latestRatio = companyRatios[companyRatios.length - 1] || null;

  const companyPl = pl.filter((p) => p.company_id === selectedTicker).sort((a, b) => a.year.localeCompare(b.year));
  const companyBs = bs.filter((b) => b.company_id === selectedTicker).sort((a, b) => a.year.localeCompare(b.year));

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1 style={{ fontSize: 26, fontWeight: 700, color: "#0A2342" }}>📋 Company Profile</h1>
        <div style={{ minWidth: 250 }}>
          <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 4, fontWeight: 600 }}>🔎 Search Company (Ticker)</label>
          <select
            value={selectedTicker}
            onChange={(e) => setSelectedTicker(e.target.value)}
            style={{
              width: "100%", padding: "10px 12px", borderRadius: 8,
              border: "1px solid #cbd5e1", background: "white", fontSize: 14,
              color: "#0A2342", fontWeight: 500, outline: "none"
            }}
          >
            {companies.map((c) => (
              <option key={c.id} value={c.id}>
                {c.id} - {c.company_name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {selectedCompany && (
        <>
          {/* Header Info */}
          <div className="glass-card" style={{ padding: 24, marginBottom: 24, display: "flex", gap: 24, flexWrap: "wrap" }}>
            <div style={{ flex: 1, minWidth: 250 }}>
              <h2 style={{ fontSize: 22, fontWeight: 700, color: "#0A2342", margin: 0 }}>
                {selectedCompany.company_name} <span style={{ color: "#00C9A7", fontSize: 16 }}>[{selectedCompany.id}]</span>
              </h2>
              <p style={{ color: "#64748b", margin: "6px 0 0", fontSize: 14, fontWeight: 500 }}>
                {selectedCompany.sector} &middot; {selectedCompany.industry}
              </p>
              {selectedCompany.website && (
                <a
                  href={selectedCompany.website}
                  target="_blank"
                  rel="noreferrer"
                  style={{ fontSize: 12, color: "#00A896", textDecoration: "none", display: "inline-block", marginTop: 8, fontWeight: 600 }}
                >
                  🌐 Visit Website
                </a>
              )}
            </div>
            <div style={{ display: "flex", gap: 20, flexWrap: "wrap", justifyContent: "flex-end", flex: 2 }}>
              <div style={{ padding: "8px 16px", background: "#f8fafc", borderRadius: 10, textAlign: "right" }}>
                <span style={{ fontSize: 10, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.5 }}>Market Cap</span>
                <div style={{ fontSize: 16, fontWeight: 700, color: "#0A2342", marginTop: 2 }}>
                  {fmt(selectedCompany.market_cap_cr, false, true)}
                </div>
              </div>
              <div style={{ padding: "8px 16px", background: "#f8fafc", borderRadius: 10, textAlign: "right" }}>
                <span style={{ fontSize: 10, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.5 }}>P/E Ratio</span>
                <div style={{ fontSize: 16, fontWeight: 700, color: "#0A2342", marginTop: 2 }}>
                  {fmt(selectedCompany.pe_ratio)}x
                </div>
              </div>
              <div style={{ padding: "8px 16px", background: "#f8fafc", borderRadius: 10, textAlign: "right" }}>
                <span style={{ fontSize: 10, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.5 }}>P/B Ratio</span>
                <div style={{ fontSize: 16, fontWeight: 700, color: "#0A2342", marginTop: 2 }}>
                  {fmt(selectedCompany.pb_ratio)}x
                </div>
              </div>
              <div style={{ padding: "8px 16px", background: "#f8fafc", borderRadius: 10, textAlign: "right" }}>
                <span style={{ fontSize: 10, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.5 }}>Div. Yield</span>
                <div style={{ fontSize: 16, fontWeight: 700, color: "#0A2342", marginTop: 2 }}>
                  {fmt(selectedCompany.dividend_yield_pct, true)}
                </div>
              </div>
            </div>
          </div>

          {/* About Company */}
          {selectedCompany.about_company && (
            <div className="glass-card" style={{ padding: 20, marginBottom: 24 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: "#0A2342", marginBottom: 8 }}>About the Company</h3>
              <p style={{ fontSize: 13, color: "#475569", lineHeight: 1.6, margin: 0 }}>{selectedCompany.about_company}</p>
            </div>
          )}

          {/* KPI Snapshot Tiles */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 16, marginBottom: 24 }}>
            <div className="kpi-card">
              <span style={{ fontSize: 10, color: "#7a98b8", textTransform: "uppercase", letterSpacing: 0.5 }}>Return on Equity (ROE)</span>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#00C9A7", marginTop: 4 }}>
                {fmt(selectedCompany.roe_percentage || (latestRatio ? latestRatio.return_on_equity_pct : null), true)}
              </div>
            </div>
            <div className="kpi-card">
              <span style={{ fontSize: 10, color: "#7a98b8", textTransform: "uppercase", letterSpacing: 0.5 }}>ROCE</span>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#00C9A7", marginTop: 4 }}>
                {fmt(selectedCompany.roce_percentage, true)}
              </div>
            </div>
            <div className="kpi-card">
              <span style={{ fontSize: 10, color: "#7a98b8", textTransform: "uppercase", letterSpacing: 0.5 }}>OPM% (Latest)</span>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#00C9A7", marginTop: 4 }}>
                {fmt(latestRatio ? latestRatio.operating_profit_margin_pct : null, true)}
              </div>
            </div>
            <div className="kpi-card">
              <span style={{ fontSize: 10, color: "#7a98b8", textTransform: "uppercase", letterSpacing: 0.5 }}>Net Margin%</span>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#00C9A7", marginTop: 4 }}>
                {fmt(latestRatio ? latestRatio.net_profit_margin_pct : null, true)}
              </div>
            </div>
            <div className="kpi-card">
              <span style={{ fontSize: 10, color: "#7a98b8", textTransform: "uppercase", letterSpacing: 0.5 }}>Debt/Equity</span>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#00C9A7", marginTop: 4 }}>
                {fmt(latestRatio ? latestRatio.debt_to_equity : null)}
              </div>
            </div>
            <div className="kpi-card">
              <span style={{ fontSize: 10, color: "#7a98b8", textTransform: "uppercase", letterSpacing: 0.5 }}>Free Cash Flow</span>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#00C9A7", marginTop: 4 }}>
                {fmt(latestRatio ? latestRatio.free_cash_flow_cr : null, false, true)}
              </div>
            </div>
          </div>

          {/* Charts Tabs Section */}
          <div className="glass-card" style={{ padding: 24, marginBottom: 24 }}>
            <div style={{ display: "flex", gap: 8, borderBottom: "1px solid #e2e8f0", paddingBottom: 12, marginBottom: 20 }}>
              {[
                { id: "revenue", label: "📈 Revenue & Profit" },
                { id: "margins", label: "📊 Margins (10yr)" },
                { id: "balance_sheet", label: "🏦 Balance Sheet Trend" }
              ].map((t) => (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  style={{
                    padding: "8px 16px", borderRadius: 8, fontSize: 13, fontWeight: 600,
                    cursor: "pointer", border: "none", outline: "none",
                    background: activeTab === t.id ? "#0A2342" : "transparent",
                    color: activeTab === t.id ? "white" : "#64748b",
                    transition: "all 0.15s"
                  }}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div style={{ height: 350 }}>
              {activeTab === "revenue" && companyPl.length > 0 && (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={companyPl}>
                    <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v: any) => fmt(Number(v), false, true)} />
                    <Legend />
                    <Bar name="Sales" dataKey="sales" fill="#0A2342" radius={[4, 4, 0, 0]} />
                    <Bar name="Net Profit" dataKey="net_profit" fill="#00C9A7" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}

              {activeTab === "margins" && companyPl.length > 0 && (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={companyPl}>
                    <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v: any) => fmt(Number(v), true)} />
                    <Legend />
                    <Line name="Operating Profit Margin (OPM%)" dataKey="opm_percentage" stroke="#F4A261" strokeWidth={2.5} activeDot={{ r: 6 }} />
                  </LineChart>
                </ResponsiveContainer>
              )}

              {activeTab === "balance_sheet" && companyBs.length > 0 && (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={companyBs}>
                    <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v: any) => fmt(Number(v), false, true)} />
                    <Legend />
                    <Area name="Total Assets" dataKey="total_assets" stroke="#0A2342" fill="#0A2342" fillOpacity={0.15} strokeWidth={2} />
                    <Area name="Borrowings" dataKey="borrowings" stroke="#e74c3c" fill="#e74c3c" fillOpacity={0.1} strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              )}

              {activeTab === "revenue" && companyPl.length === 0 && <div style={{ textAlign: "center", paddingTop: 100, color: "#64748b" }}>No historical profit & loss data available.</div>}
              {activeTab === "margins" && companyPl.length === 0 && <div style={{ textAlign: "center", paddingTop: 100, color: "#64748b" }}>No margins data available.</div>}
              {activeTab === "balance_sheet" && companyBs.length === 0 && <div style={{ textAlign: "center", paddingTop: 100, color: "#64748b" }}>No balance sheet data available.</div>}
            </div>
          </div>

          {/* Historical Data Table */}
          <div className="glass-card" style={{ padding: 24 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: "#0A2342", marginBottom: 16 }}>📊 Historical Performance & Financial Ratio Records</h3>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ background: "#0A2342", color: "white" }}>
                    {["Year", "Sales (Cr)", "Expenses (Cr)", "Operating Profit", "OPM %", "Net Profit", "Interest (Cr)", "Depreciation"].map((h) => (
                      <th key={h} style={{ padding: "10px 12px", textAlign: "left", fontWeight: 600, whiteSpace: "nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {companyPl.map((p, i) => (
                    <tr key={p.year} style={{ background: i % 2 === 0 ? "white" : "#f8fafc", borderBottom: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "10px 12px", fontWeight: 600 }}>{p.year}</td>
                      <td style={{ padding: "10px 12px" }}>{fmt(p.sales, false, true)}</td>
                      <td style={{ padding: "10px 12px" }}>{fmt(p.expenses, false, true)}</td>
                      <td style={{ padding: "10px 12px" }}>{fmt(p.operating_profit, false, true)}</td>
                      <td style={{ padding: "10px 12px" }}>{fmt(p.opm_percentage, true)}</td>
                      <td style={{ padding: "10px 12px", fontWeight: 600, color: p.net_profit >= 0 ? "#16a34a" : "#dc2626" }}>{fmt(p.net_profit, false, true)}</td>
                      <td style={{ padding: "10px 12px" }}>{fmt(p.interest, false, true)}</td>
                      <td style={{ padding: "10px 12px" }}>{fmt(p.depreciation, false, true)}</td>
                    </tr>
                  ))}
                  {companyPl.length === 0 && (
                    <tr>
                      <td colSpan={8} style={{ padding: 20, textAlign: "center", color: "#64748b" }}>No performance records found.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
