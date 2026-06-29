"use client";

import { useEffect, useState } from "react";
import {
  ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, Legend,
  ResponsiveContainer
} from "recharts";

const fmt = (v: number | null, pct = false, cr = false) => {
  if (v == null || isNaN(v)) return "N/A";
  if (pct) return `${v.toFixed(1)}%`;
  if (cr) return v >= 1e5 ? `₹${(v / 1e5).toFixed(1)}L Cr` : `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })} Cr`;
  return v.toFixed(2);
};

const PATTERNS = {
  "+--": "Reinvestor",
  "+-+": "Growth Fundraiser",
  "++-": "Asset Seller / Returns",
  "+++": "Cash Accumulator",
  "--+": "Distress Signal",
  "-++": "Liquidator",
  "---": "Cash Burner",
  "-+-": "Restructuring",
};

const COLOR_MAP: Record<string, string> = {
  "Reinvestor": "#00A896",
  "Growth Fundraiser": "#3498db",
  "Distress Signal": "#e74c3c",
  "Asset Seller / Returns": "#F4A261",
  "Restructuring": "#e67e22",
  "Cash Accumulator": "#2ecc71",
  "Liquidator": "#c0392b",
  "Cash Burner": "#962d22",
};

export default function CapitalAllocation() {
  const [companies, setCompanies] = useState<any[]>([]);
  const [cf, setCf] = useState<any[]>([]);
  const [selectedPattern, setSelectedPattern] = useState<string>("Reinvestor");

  useEffect(() => {
    Promise.all([
      fetch("/data/companies.json").then((r) => r.json()),
      fetch("/data/cf.json").then((r) => r.json()),
    ]).then(([comps, cfData]) => {
      setCompanies(comps);
      setCf(cfData);
    });
  }, []);

  // Classify each company based on latest cash flow year
  const getAllocatedData = () => {
    if (cf.length === 0 || companies.length === 0) return [];

    const latestYear = String(Math.max(...cf.map((c) => parseInt(c.year)).filter((y) => !isNaN(y))));

    return companies.map((comp) => {
      const compCf = cf.filter((c) => c.company_id === comp.id && String(c.year) === latestYear);
      if (compCf.length === 0) return null;

      const cfo = compCf[0].operating_activity ?? 0;
      const cfi = compCf[0].investing_activity ?? 0;
      const cff = compCf[0].financing_activity ?? 0;

      const cfoSign = cfo >= 0 ? "+" : "-";
      const cfiSign = cfi >= 0 ? "+" : "-";
      const cffSign = cff >= 0 ? "+" : "-";

      const key = `${cfoSign}${cfiSign}${cffSign}`;
      const pattern = PATTERNS[key as keyof typeof PATTERNS] || "Unknown";

      return {
        ...comp,
        cfo,
        cfi,
        cff,
        pattern,
        year: latestYear,
      };
    }).filter(Boolean);
  };

  const allocated = getAllocatedData() as any[];

  // Counts for summary metrics
  const counts = allocated.reduce((acc, curr) => {
    acc[curr.pattern] = (acc[curr.pattern] ?? 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const scatterData = allocated.map((d) => ({
    name: d.company_name,
    ticker: d.id,
    cfo: d.cfo,
    cfi: d.cfi,
    mcap: d.market_cap_cr ?? 1000,
    pattern: d.pattern,
  }));

  const drilldownData = allocated.filter((d) => d.pattern === selectedPattern).sort((a, b) => (b.market_cap_cr ?? 0) - (a.market_cap_cr ?? 0));

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <h1 style={{ fontSize: 26, fontWeight: 700, color: "#0A2342", marginBottom: 4 }}>💰 Capital Allocation Map</h1>
      <p style={{ color: "#64748b", marginBottom: 24, fontSize: 14 }}>
        Analysis of operating (CFO), investing (CFI), and financing (CFF) cash flows to classify company capital strategies.
      </p>

      {/* Summary Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 20, marginBottom: 28 }}>
        <div className="kpi-card" style={{ background: "linear-gradient(135deg, #112233 0%, #0c1a26 100%)", border: "1px solid #1a3044" }}>
          <span style={{ fontSize: 11, color: "#a0b4cc", textTransform: "uppercase", letterSpacing: 0.5 }}>🔄 Reinvestors</span>
          <div style={{ fontSize: 32, fontWeight: 700, color: "#00C9A7", marginTop: 6 }}>{counts["Reinvestor"] ?? 0}</div>
          <div style={{ fontSize: 11, color: "#7a98b8", marginTop: 4 }}>CFO &gt; 0, CFI &lt; 0, CFF &lt; 0 (Growth + Divs)</div>
        </div>

        <div className="kpi-card" style={{ background: "linear-gradient(135deg, #112233 0%, #0c1a26 100%)", border: "1px solid #1a3044" }}>
          <span style={{ fontSize: 11, color: "#a0b4cc", textTransform: "uppercase", letterSpacing: 0.5 }}>🚀 Growth Fundraisers</span>
          <div style={{ fontSize: 32, fontWeight: 700, color: "#3498db", marginTop: 6 }}>{counts["Growth Fundraiser"] ?? 0}</div>
          <div style={{ fontSize: 11, color: "#7a98b8", marginTop: 4 }}>CFO &gt; 0, CFI &lt; 0, CFF &gt; 0 (Expanding fast)</div>
        </div>

        <div className="kpi-card" style={{ background: "linear-gradient(135deg, #112233 0%, #0c1a26 100%)", border: "1px solid #1a3044" }}>
          <span style={{ fontSize: 11, color: "#a0b4cc", textTransform: "uppercase", letterSpacing: 0.5 }}>⚠️ Distress Signals</span>
          <div style={{ fontSize: 32, fontWeight: 700, color: "#e74c3c", marginTop: 6 }}>{counts["Distress Signal"] ?? 0}</div>
          <div style={{ fontSize: 11, color: "#7a98b8", marginTop: 4 }}>CFO &lt; 0, CFI &lt; 0, CFF &gt; 0 (Losses funded by debt)</div>
        </div>

        <div className="kpi-card" style={{ background: "linear-gradient(135deg, #112233 0%, #0c1a26 100%)", border: "1px solid #1a3044" }}>
          <span style={{ fontSize: 11, color: "#a0b4cc", textTransform: "uppercase", letterSpacing: 0.5 }}>🛠️ Restructuring / Others</span>
          <div style={{ fontSize: 32, fontWeight: 700, color: "#e67e22", marginTop: 6 }}>
            {(counts["Asset Seller / Returns"] ?? 0) + (counts["Restructuring"] ?? 0) + (counts["Cash Accumulator"] ?? 0)}
          </div>
          <div style={{ fontSize: 11, color: "#7a98b8", marginTop: 4 }}>Divesting assets and paying back capital</div>
        </div>
      </div>

      {/* Main Charts */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 24, marginBottom: 28 }}>
        <div className="glass-card" style={{ padding: 24 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: "#0A2342", marginBottom: 16 }}>📈 CFO vs CFI core Allocations (Bubble size = Market Cap)</h3>
          <div style={{ width: "100%", height: 420 }}>
            {allocated.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                  <XAxis type="number" dataKey="cfo" name="CFO" unit=" Cr" tick={{ fontSize: 11 }} label={{ value: "Operating Activity (CFO) ₹ Cr", position: "insideBottom", offset: -5 }} />
                  <YAxis type="number" dataKey="cfi" name="CFI" unit=" Cr" tick={{ fontSize: 11 }} label={{ value: "Investing Activity (CFI) ₹ Cr", angle: -90, position: "insideLeft" }} />
                  <ZAxis type="number" dataKey="mcap" range={[50, 1000]} name="Market Cap" />
                  <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(value: any, name: any) => {
                    if (name === "Market Cap") return fmt(Number(value), false, true);
                    return `₹${Number(value).toLocaleString()} Cr`;
                  }} />
                  <Legend />
                  {Object.keys(COLOR_MAP).map((pat) => (
                    <Scatter
                      key={pat}
                      name={pat}
                      data={scatterData.filter((d) => d.pattern === pat)}
                      fill={COLOR_MAP[pat]}
                    />
                  ))}
                </ScatterChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: "center", paddingTop: 100, color: "#64748b" }}>Loading scatter chart allocations...</div>
            )}
          </div>
        </div>

        {/* Strategy drilldown selection */}
        <div className="glass-card" style={{ padding: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: "#0A2342", margin: 0 }}>📋 Strategy Categorisation Drill-Down</h3>
            <select
              value={selectedPattern}
              onChange={(e) => setSelectedPattern(e.target.value)}
              style={{
                padding: "8px 12px", borderRadius: 8, border: "1px solid #cbd5e1",
                background: "white", fontSize: 13, color: "#0A2342", fontWeight: 500, outline: "none", cursor: "pointer"
              }}
            >
              {Object.keys(COLOR_MAP).map((pat) => (
                <option key={pat} value={pat}>
                  {pat}
                </option>
              ))}
            </select>
          </div>

          <p style={{ fontSize: 13, color: "#64748b", marginBottom: 16 }}>
            Showing <strong>{drilldownData.length}</strong> companies matching <strong>{selectedPattern}</strong> strategy:
          </p>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "#0A2342", color: "white" }}>
                  {["Ticker", "Company Name", "Sector", "Market Cap", "CFO (Cr)", "CFI (Cr)", "CFF (Cr)"].map((h) => (
                    <th key={h} style={{ padding: "10px 12px", textAlign: "left", fontWeight: 600, whiteSpace: "nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {drilldownData.map((co, i) => (
                  <tr key={co.id} style={{ background: i % 2 === 0 ? "white" : "#f8fafc", borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "10px 12px", fontWeight: 600 }}>{co.id}</td>
                    <td style={{ padding: "10px 12px", whiteSpace: "nowrap" }}>{co.company_name?.slice(0, 24)}</td>
                    <td style={{ padding: "10px 12px", color: "#64748b", fontSize: 11 }}>{co.sector}</td>
                    <td style={{ padding: "10px 12px" }}>{fmt(co.market_cap_cr, false, true)}</td>
                    <td style={{ padding: "10px 12px", color: co.cfo >= 0 ? "#16a34a" : "#dc2626" }}>{fmt(co.cfo, false, true)}</td>
                    <td style={{ padding: "10px 12px" }}>{fmt(co.cfi, false, true)}</td>
                    <td style={{ padding: "10px 12px" }}>{fmt(co.cff, false, true)}</td>
                  </tr>
                ))}
                {drilldownData.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ padding: 20, textAlign: "center", color: "#64748b" }}>
                      No companies match this strategy in the current records.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
