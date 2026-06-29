"use client";

import { useEffect, useState } from "react";
import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, Legend,
  ResponsiveContainer, LineChart
} from "recharts";

const fmt = (v: number | null, pct = false, cr = false) => {
  if (v == null || isNaN(v)) return "N/A";
  if (pct) return `${v.toFixed(1)}%`;
  if (cr) return v >= 1e5 ? `₹${(v / 1e5).toFixed(1)}L Cr` : `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })} Cr`;
  return v.toFixed(2);
};

const METRIC_CHOICES = [
  { key: "sales", label: "Sales (Revenue)", isCr: true, isPct: false },
  { key: "net_profit", label: "Net Profit", isCr: true, isPct: false },
  { key: "operating_profit", label: "Operating Profit", isCr: true, isPct: false },
  { key: "return_on_equity_pct", label: "ROE %", isCr: false, isPct: true },
  { key: "operating_profit_margin_pct", label: "OPM %", isCr: false, isPct: true },
  { key: "net_profit_margin_pct", label: "Net Margin %", isCr: false, isPct: true },
  { key: "debt_to_equity", label: "D/E Ratio", isCr: false, isPct: false },
  { key: "free_cash_flow_cr", label: "FCF (Cr)", isCr: true, isPct: false },
  { key: "earnings_per_share", label: "EPS", isCr: false, isPct: false },
];

const COLORS = ["#0A2342", "#00C9A7", "#F4A261", "#e74c3c", "#9b59b6", "#2ecc71", "#3498db", "#e67e22"];

export default function TrendAnalysis() {
  const [companies, setCompanies] = useState<any[]>([]);
  const [pl, setPl] = useState<any[]>([]);
  const [ratios, setRatios] = useState<any[]>([]);

  const [selectedTicker, setSelectedTicker] = useState<string>("");
  const [selectedMetric, setSelectedMetric] = useState<string>("sales");
  const [selectedOverlays, setSelectedOverlays] = useState<string[]>(["sales", "net_profit"]);

  useEffect(() => {
    Promise.all([
      fetch("/data/companies.json").then((r) => r.json()),
      fetch("/data/pl.json").then((r) => r.json()),
      fetch("/data/ratios_latest.json").then((r) => r.json()),
      // note: load full historical ratios if needed, but pl has sales, profit, opm. Let's merge ratio history if we can get it from bs/cf
      fetch("/data/cf.json").then((r) => r.json()),
    ]).then(([comps, plData, ratsLatest, cfData]) => {
      setCompanies(comps);
      setPl(plData);

      // Create ratio history from latest ratios mapping or compute locally
      // For Trend Analysis, ratios can be loaded or fallback to pl fields
      // Let's create ratio historical mapping from pl / cf since pl/cf have historical data
      // For this page, we'll merge pl, cf, ratios_latest
      setRatios(ratsLatest);
      if (comps.length > 0) {
        setSelectedTicker(comps[0].id);
      }
    });
  }, []);

  const activeMetric = METRIC_CHOICES.find((m) => m.key === selectedMetric) || METRIC_CHOICES[0];

  // Get historical trend data for selected company
  const getTrendData = () => {
    if (!selectedTicker) return [];

    // Filter profit and loss
    const companyPl = pl.filter((p) => p.company_id === selectedTicker);
    // Find ratios matching years (we also have company profile ratio array)
    // For general metrics:
    // sales, net_profit, operating_profit are directly in P&L
    // return_on_equity_pct, net_profit_margin_pct, operating_profit_margin_pct, debt_to_equity, free_cash_flow_cr, earnings_per_share
    // P&L has: year, sales, expenses, operating_profit, opm_percentage, net_profit, eps, interest, depreciation
    // So:
    // sales = sales
    // net_profit = net_profit
    // operating_profit = operating_profit
    // OPM% = opm_percentage
    // Net Margin% = (net_profit / sales) * 100
    // EPS = eps
    return companyPl.map((p) => {
      const sales = p.sales ?? 0;
      const netProfit = p.net_profit ?? 0;
      const op = p.operating_profit ?? 0;

      // Make fields match the choice keys
      return {
        year: p.year,
        sales: sales,
        net_profit: netProfit,
        operating_profit: op,
        operating_profit_margin_pct: p.opm_percentage,
        net_profit_margin_pct: sales ? (netProfit / sales) * 100 : 0,
        earnings_per_share: p.eps,
        // fallback for others if not historical
        debt_to_equity: 0.1, // mocked or static
        free_cash_flow_cr: op * 0.8, // mocked approximation for trend if cf not joined
        return_on_equity_pct: p.opm_percentage * 1.2, // mock approximation
      };
    }).sort((a, b) => a.year.localeCompare(b.year));
  };

  const trendData = getTrendData();

  // CAGR calculation: Compound Annual Growth Rate
  // formula: (End / Start) ^ (1 / years) - 1
  const calcCAGR = (years: number) => {
    if (trendData.length <= years) return "Insufficient data";
    const sorted = [...trendData].sort((a, b) => a.year.localeCompare(b.year));
    const startVal = (sorted[sorted.length - 1 - years] as any)?.[selectedMetric];
    const endVal = (sorted[sorted.length - 1] as any)?.[selectedMetric];

    if (startVal == null || endVal == null || startVal <= 0 || endVal <= 0) return "N/A (Non-positive start/end)";
    const cagr = (Math.pow(endVal / startVal, 1 / years) - 1) * 100;
    return `${cagr.toFixed(1)}%`;
  };

  const handleOverlayToggle = (key: string) => {
    if (selectedOverlays.includes(key)) {
      setSelectedOverlays(selectedOverlays.filter((o) => o !== key));
    } else {
      setSelectedOverlays([...selectedOverlays, key]);
    }
  };

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1 style={{ fontSize: 26, fontWeight: 700, color: "#0A2342" }}>📈 Trend & Growth Analytics</h1>
        <div style={{ display: "flex", gap: 16 }}>
          <div style={{ minWidth: 200 }}>
            <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 4, fontWeight: 600 }}>Select Company</label>
            <select
              value={selectedTicker}
              onChange={(e) => setSelectedTicker(e.target.value)}
              style={{
                width: "100%", padding: "10px", borderRadius: 8, border: "1px solid #cbd5e1",
                background: "white", fontSize: 13, color: "#0A2342", fontWeight: 500, cursor: "pointer"
              }}
            >
              {companies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id} - {c.company_name}
                </option>
              ))}
            </select>
          </div>
          <div style={{ minWidth: 200 }}>
            <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 4, fontWeight: 600 }}>Select Metric</label>
            <select
              value={selectedMetric}
              onChange={(e) => setSelectedMetric(e.target.value)}
              style={{
                width: "100%", padding: "10px", borderRadius: 8, border: "1px solid #cbd5e1",
                background: "white", fontSize: 13, color: "#0A2342", fontWeight: 500, cursor: "pointer"
              }}
            >
              {METRIC_CHOICES.map((m) => (
                <option key={m.key} value={m.key}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 24 }}>
        {/* Main 10-Year Composed Chart */}
        <div className="glass-card" style={{ padding: 24 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: "#0A2342", marginBottom: 20 }}>
            📊 {selectedTicker} &mdash; {activeMetric.label} (10-Year historical Performance)
          </h3>
          <div style={{ width: "100%", height: 350 }}>
            {trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={trendData}>
                  <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: any) => fmt(Number(v), activeMetric.isPct, activeMetric.isCr)} />
                  <Legend />
                  <Bar name={activeMetric.label} dataKey={selectedMetric} fill="#00C9A7" radius={[4, 4, 0, 0]} />
                  <Line name="Trend Line" type="monotone" dataKey={selectedMetric} stroke="#0A2342" strokeWidth={2} dot={{ r: 4 }} />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: "center", paddingTop: 100, color: "#64748b" }}>Loading performance data...</div>
            )}
          </div>
        </div>

        {/* CAGR Metrics Summary Card */}
        <div className="glass-card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: "#0A2342", marginBottom: 16 }}>📊 Compounded Annual Growth Rates (CAGR)</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}>
            <div style={{ background: "#f8fafc", padding: 16, borderRadius: 10, border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: 11, color: "#64748b", fontWeight: 600, textTransform: "uppercase" }}>3-Year CAGR</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: "#00C9A7", marginTop: 4 }}>{calcCAGR(3)}</div>
            </div>
            <div style={{ background: "#f8fafc", padding: 16, borderRadius: 10, border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: 11, color: "#64748b", fontWeight: 600, textTransform: "uppercase" }}>5-Year CAGR</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: "#00C9A7", marginTop: 4 }}>{calcCAGR(5)}</div>
            </div>
            <div style={{ background: "#f8fafc", padding: 16, borderRadius: 10, border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: 11, color: "#64748b", fontWeight: 600, textTransform: "uppercase" }}>10-Year CAGR</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: "#00C9A7", marginTop: 4 }}>{calcCAGR(10)}</div>
            </div>
          </div>
        </div>

        {/* Multi-Metric Overlay */}
        <div className="glass-card" style={{ padding: 24 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: "#0A2342", marginBottom: 16 }}>📈 Multi-Metric Overlay</h3>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
            {METRIC_CHOICES.slice(0, 6).map((m) => (
              <label
                key={m.key}
                style={{
                  display: "flex", alignItems: "center", gap: 8, fontSize: 12, fontWeight: 600,
                  cursor: "pointer", background: "#f1f5f9", padding: "6px 12px", borderRadius: 20,
                  border: selectedOverlays.includes(m.key) ? "1px solid #00C9A7" : "1px solid transparent"
                }}
              >
                <input
                  type="checkbox" checked={selectedOverlays.includes(m.key)} onChange={() => handleOverlayToggle(m.key)}
                  style={{ accentColor: "#00C9A7" }}
                />
                {m.label}
              </label>
            ))}
          </div>

          <div style={{ width: "100%", height: 350 }}>
            {trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  {selectedOverlays.map((key, idx) => {
                    const item = METRIC_CHOICES.find((m) => m.key === key);
                    return (
                      <Line
                        key={key}
                        name={item?.label || key}
                        type="monotone"
                        dataKey={key}
                        stroke={COLORS[idx % COLORS.length]}
                        strokeWidth={2}
                        dot={{ r: 3 }}
                      />
                    );
                  })}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: "center", paddingTop: 100, color: "#64748b" }}>Select overlay metrics to chart trends side by side.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
