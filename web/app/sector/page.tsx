"use client";

import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  ScatterChart, Scatter, ZAxis, Legend
} from "recharts";

const fmt = (v: number | null, pct = false, cr = false) => {
  if (v == null || isNaN(v)) return "N/A";
  if (pct) return `${v.toFixed(1)}%`;
  if (cr) return v >= 1e5 ? `₹${(v / 1e5).toFixed(1)}L Cr` : `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })} Cr`;
  return v.toFixed(2);
};

const KPI_CHOICES = [
  { key: "return_on_equity_pct", label: "Return on Equity %", isPct: true, isCr: false },
  { key: "net_profit_margin_pct", label: "Net Profit Margin %", isPct: true, isCr: false },
  { key: "operating_profit_margin_pct", label: "Operating Profit Margin %", isPct: true, isCr: false },
  { key: "debt_to_equity", label: "Debt-to-Equity", isPct: false, isCr: false },
  { key: "asset_turnover", label: "Asset Turnover", isPct: false, isCr: false },
];

const SECTOR_COLORS = [
  "#00C9A7", "#3498db", "#F4A261", "#9b59b6", "#e74c3c",
  "#2ecc71", "#f39c12", "#1abc9c", "#e67e22", "#27ae60"
];

export default function SectorAnalysis() {
  const [companies, setCompanies] = useState<any[]>([]);
  const [ratios, setRatios] = useState<any[]>([]);
  const [pl, setPl] = useState<any[]>([]);
  const [selectedKpi, setSelectedKpi] = useState<string>("return_on_equity_pct");
  const [selectedSector, setSelectedSector] = useState<string>("");

  useEffect(() => {
    Promise.all([
      fetch("/data/companies.json").then((r) => r.json()),
      fetch("/data/ratios_latest.json").then((r) => r.json()),
      fetch("/data/pl.json").then((r) => r.json()),
    ]).then(([comps, rats, plData]) => {
      setCompanies(comps);
      setRatios(rats);
      setPl(plData);

      const sectorList = [...new Set(comps.map((c: any) => c.sector).filter(Boolean))].sort() as string[];
      if (sectorList.length > 0) {
        setSelectedSector(sectorList[0]);
      }
    });
  }, []);

  const sectors = [...new Set(companies.map((c) => c.sector).filter(Boolean))].sort();

  // Combine companies with latest ratios and sales from pl
  const mergedData = companies.map((c) => {
    const r = ratios.find((ratio) => ratio.company_id === c.id) || {};
    const companyPl = pl.filter((p) => p.company_id === c.id).sort((a, b) => b.year.localeCompare(a.year));
    const latestSales = companyPl.length > 0 ? companyPl[0].sales : 0;
    return { ...r, ...c, sales: latestSales };
  });

  const activeKpi = KPI_CHOICES.find((k) => k.key === selectedKpi) || KPI_CHOICES[0];

  // Calculate sector medians
  const getSectorMedians = () => {
    return sectors.map((sec) => {
      const secCos = mergedData.filter((c) => c.sector === sec);
      const vals = secCos.map((c) => c[selectedKpi]).filter((v) => v != null && !isNaN(v)).sort((a, b) => a - b);
      let median = 0;
      if (vals.length > 0) {
        const mid = Math.floor(vals.length / 2);
        median = vals.length % 2 !== 0 ? vals[mid] : (vals[mid - 1] + vals[mid]) / 2;
      }
      return { sector: sec, value: median };
    }).sort((a, b) => b.value - a.value);
  };

  const sectorMedians = getSectorMedians();

  // Drill-down data
  const drilledCompanies = mergedData.filter((c) => c.sector === selectedSector).sort((a, b) => (b.market_cap_cr ?? 0) - (a.market_cap_cr ?? 0));

  // Build Bubble Chart Data
  // X: Sales (Revenue)
  // Y: ROE%
  // Z: Market Cap
  const getBubbleData = () => {
    return mergedData
      .filter((c) => c.sales > 0 && c.return_on_equity_pct != null && c.market_cap_cr > 0)
      .map((c) => ({
        name: c.company_name,
        ticker: c.id,
        sales: c.sales,
        roe: c.return_on_equity_pct,
        mcap: c.market_cap_cr,
        sector: c.sector,
      }));
  };

  const bubbleData = getBubbleData();

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <h1 style={{ fontSize: 26, fontWeight: 700, color: "#0A2342", marginBottom: 24 }}>🏭 Sector Analytics</h1>

      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 24 }}>
        {/* Sector Medians Chart */}
        <div className="glass-card" style={{ padding: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: "#0A2342", margin: 0 }}>📊 Sector Median KPI Comparison</h3>
            <select
              value={selectedKpi}
              onChange={(e) => setSelectedKpi(e.target.value)}
              style={{
                padding: "8px 12px", borderRadius: 8, border: "1px solid #cbd5e1",
                background: "white", fontSize: 13, color: "#0A2342", fontWeight: 500, outline: "none", cursor: "pointer"
              }}
            >
              {KPI_CHOICES.map((k) => (
                <option key={k.key} value={k.key}>
                  {k.label}
                </option>
              ))}
            </select>
          </div>

          <div style={{ width: "100%", height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sectorMedians}>
                <XAxis dataKey="sector" tick={{ fontSize: 10 }} interval={0} angle={-15} dx={-10} dy={5} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: any) => fmt(Number(v), activeKpi.isPct, activeKpi.isCr)} />
                <Bar dataKey="value" fill="#1a5276" radius={[4, 4, 0, 0]} name="Median Value">
                  {sectorMedians.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={SECTOR_COLORS[index % SECTOR_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Bubble Chart */}
        <div className="glass-card" style={{ padding: 24 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: "#0A2342", marginBottom: 16 }}>🔵 Bubble Chart &mdash; Revenue vs ROE (Size = Market Cap)</h3>
          <div style={{ width: "100%", height: 420 }}>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                <XAxis type="number" dataKey="sales" name="Revenue" unit=" Cr" tick={{ fontSize: 11 }} label={{ value: "Latest Revenue (₹ Cr)", position: "insideBottom", offset: -5 }} />
                <YAxis type="number" dataKey="roe" name="ROE" unit="%" tick={{ fontSize: 11 }} label={{ value: "Return on Equity %", angle: -90, position: "insideLeft" }} />
                <ZAxis type="number" dataKey="mcap" range={[50, 1000]} name="Market Cap" />
                <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(value: any, name: any) => {
                  if (name === "Market Cap") return fmt(Number(value), false, true);
                  if (name === "ROE") return `${Number(value).toFixed(1)}%`;
                  return `₹${value.toLocaleString()} Cr`;
                }} />
                <Legend />
                {sectors.map((sec, idx) => (
                  <Scatter
                    key={sec}
                    name={sec}
                    data={bubbleData.filter((d) => d.sector === sec)}
                    fill={SECTOR_COLORS[idx % SECTOR_COLORS.length]}
                  />
                ))}
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Sector Drill-down */}
        <div className="glass-card" style={{ padding: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: "#0A2342", margin: 0 }}>🔍 Sector Deep Dive</h3>
            <select
              value={selectedSector}
              onChange={(e) => setSelectedSector(e.target.value)}
              style={{
                padding: "8px 12px", borderRadius: 8, border: "1px solid #cbd5e1",
                background: "white", fontSize: 13, color: "#0A2342", fontWeight: 500, outline: "none", cursor: "pointer"
              }}
            >
              {sectors.map((sec) => (
                <option key={sec} value={sec}>
                  {sec}
                </option>
              ))}
            </select>
          </div>

          <p style={{ fontSize: 13, color: "#64748b", marginBottom: 16 }}>
            Showing <strong>{drilledCompanies.length}</strong> companies in <strong>{selectedSector}</strong> sector:
          </p>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "#0A2342", color: "white" }}>
                  {["Ticker", "Company", "MCap (Cr)", "ROE%", "NPM%", "OPM%", "D/E", "FCF (Cr)", "PE"].map((h) => (
                    <th key={h} style={{ padding: "10px 12px", textAlign: "left", fontWeight: 600, whiteSpace: "nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {drilledCompanies.map((co, i) => (
                  <tr key={co.id} style={{ background: i % 2 === 0 ? "white" : "#f8fafc", borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "10px 12px", fontWeight: 600 }}>{co.id}</td>
                    <td style={{ padding: "10px 12px", whiteSpace: "nowrap" }}>{co.company_name?.slice(0, 24)}</td>
                    <td style={{ padding: "10px 12px" }}>{fmt(co.market_cap_cr, false, true)}</td>
                    <td style={{ padding: "10px 12px", fontWeight: 600, color: (co.return_on_equity_pct ?? 0) > 15 ? "#16a34a" : "#dc2626" }}>{fmt(co.return_on_equity_pct, true)}</td>
                    <td style={{ padding: "10px 12px" }}>{fmt(co.net_profit_margin_pct, true)}</td>
                    <td style={{ padding: "10px 12px" }}>{fmt(co.operating_profit_margin_pct, true)}</td>
                    <td style={{ padding: "10px 12px" }}>{fmt(co.debt_to_equity)}</td>
                    <td style={{ padding: "10px 12px" }}>{fmt(co.free_cash_flow_cr, false, true)}</td>
                    <td style={{ padding: "10px 12px" }}>{fmt(co.pe_ratio)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
