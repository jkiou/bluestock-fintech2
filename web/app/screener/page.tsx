"use client";

import { useEffect, useState } from "react";

const fmt = (v: number | null, pct = false, cr = false) => {
  if (v == null || isNaN(v)) return "N/A";
  if (pct) return `${v.toFixed(1)}%`;
  if (cr) return v >= 1e5 ? `₹${(v / 1e5).toFixed(1)}L Cr` : `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })} Cr`;
  return v.toFixed(2);
};

const PRESETS = {
  "Quality Compounder": {
    return_on_equity_pct: [15, 999],
    debt_to_equity: [0, 1.0],
    free_cash_flow_cr: [0, 9999999],
  },
  "Value Pick": {
    pe_ratio: [0, 20],
    pb_ratio: [0, 3],
    dividend_yield_pct: [1, 100],
  },
  "Growth Accelerator": {
    net_profit_margin_pct: [10, 100],
    return_on_equity_pct: [15, 100],
  },
  "Dividend Champion": {
    dividend_yield_pct: [2, 100],
    free_cash_flow_cr: [0, 9999999],
  },
  "Debt-Free Blue Chip": {
    debt_to_equity: [0, 0.01],
    return_on_equity_pct: [12, 100],
  },
  "Turnaround Watch": {
    net_profit_margin_pct: [0, 100],
    return_on_equity_pct: [0, 100],
  },
};

type PresetKey = keyof typeof PRESETS;

export default function InvestmentScreener() {
  const [companies, setCompanies] = useState<any[]>([]);
  const [ratios, setRatios] = useState<any[]>([]);
  const [mode, setMode] = useState<"preset" | "custom">("preset");
  const [selectedPreset, setSelectedPreset] = useState<PresetKey>("Quality Compounder");

  // Custom filters state
  const [minRoe, setMinRoe] = useState<number>(0);
  const [maxDe, setMaxDe] = useState<number>(10);
  const [minNpm, setMinNpm] = useState<number>(0);
  const [minFcf, setMinFcf] = useState<number>(0);
  const [selectedSectors, setSelectedSectors] = useState<string[]>([]);

  useEffect(() => {
    Promise.all([
      fetch("/data/companies.json").then((r) => r.json()),
      fetch("/data/ratios_latest.json").then((r) => r.json()),
    ]).then(([comps, rats]) => {
      setCompanies(comps);
      setRatios(rats);
    });
  }, []);

  const sectors = [...new Set(companies.map((c) => c.sector).filter(Boolean))].sort();

  // Combine companies with latest ratios
  const mergedData = companies.map((c) => {
    const r = ratios.find((ratio) => ratio.company_id === c.id) || {};
    return { ...c, ...r };
  });

  const getFilteredData = () => {
    if (mode === "preset") {
      const filters = PRESETS[selectedPreset] as any;
      return mergedData.filter((item) => {
        for (const [key, range] of Object.entries(filters)) {
          const val = item[key];
          if (val == null || isNaN(val)) return false;
          const [min, max] = range as [number, number];
          if (val < min || val > max) return false;
        }
        return true;
      });
    } else {
      return mergedData.filter((item) => {
        const itemRoe = item.return_on_equity_pct ?? -999999;
        const itemDe = item.debt_to_equity ?? 999999;
        const itemNpm = item.net_profit_margin_pct ?? -999999;
        const itemFcf = item.free_cash_flow_cr ?? -999999;

        if (itemRoe < minRoe) return false;
        if (itemDe > maxDe) return false;
        if (itemNpm < minNpm) return false;
        if (itemFcf < minFcf) return false;

        if (selectedSectors.length > 0 && (!item.sector || !selectedSectors.includes(item.sector))) {
          return false;
        }
        return true;
      });
    }
  };

  const filtered = getFilteredData().sort((a, b) => (b.market_cap_cr ?? 0) - (a.market_cap_cr ?? 0));

  const handleSectorToggle = (sectorName: string) => {
    if (selectedSectors.includes(sectorName)) {
      setSelectedSectors(selectedSectors.filter((s) => s !== sectorName));
    } else {
      setSelectedSectors([...selectedSectors, sectorName]);
    }
  };

  const downloadCSV = () => {
    const headers = ["Ticker", "Company", "Sector", "Market Cap (Cr)", "ROE%", "OPM%", "NPM%", "D/E", "FCF (Cr)", "PE", "Dividend Yield%"];
    const rows = filtered.map((c) => [
      c.id,
      `"${c.company_name}"`,
      `"${c.sector}"`,
      c.market_cap_cr ?? "",
      c.return_on_equity_pct ?? "",
      c.operating_profit_margin_pct ?? "",
      c.net_profit_margin_pct ?? "",
      c.debt_to_equity ?? "",
      c.free_cash_flow_cr ?? "",
      c.pe_ratio ?? "",
      c.dividend_yield_pct ?? "",
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `screener_export_${selectedPreset.toLowerCase().replace(/ /g, "_")}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <h1 style={{ fontSize: 26, fontWeight: 700, color: "#0A2342", marginBottom: 4 }}>🔍 Investment Screener</h1>
      <p style={{ color: "#64748b", marginBottom: 24, fontSize: 14 }}>Filter Nifty 100 companies using institutional-grade metrics.</p>

      <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 24, alignItems: "start" }}>
        {/* Sidebar Controls */}
        <div className="glass-card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: "#0A2342", marginBottom: 16 }}>Screener Mode</h3>
          <div style={{ display: "flex", gap: 10, marginBottom: 20 }}>
            <button
              onClick={() => setMode("preset")}
              style={{
                flex: 1, padding: "8px", borderRadius: 6, fontSize: 12, fontWeight: 600, border: "none", cursor: "pointer",
                background: mode === "preset" ? "#0A2342" : "#f1f5f9",
                color: mode === "preset" ? "white" : "#64748b",
              }}
            >
              Preset Screens
            </button>
            <button
              onClick={() => setMode("custom")}
              style={{
                flex: 1, padding: "8px", borderRadius: 6, fontSize: 12, fontWeight: 600, border: "none", cursor: "pointer",
                background: mode === "custom" ? "#0A2342" : "#f1f5f9",
                color: mode === "custom" ? "white" : "#64748b",
              }}
            >
              Custom Filters
            </button>
          </div>

          {mode === "preset" ? (
            <div>
              <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 6, fontWeight: 600 }}>Select Preset Screen</label>
              <select
                value={selectedPreset}
                onChange={(e) => setSelectedPreset(e.target.value as PresetKey)}
                style={{
                  width: "100%", padding: "10px", borderRadius: 6, border: "1px solid #cbd5e1", background: "white", fontSize: 13,
                  color: "#0A2342", fontWeight: 500, outline: "none", cursor: "pointer"
                }}
              >
                {Object.keys(PRESETS).map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
              <div style={{ marginTop: 16, background: "#f8fafc", padding: 12, borderRadius: 8, fontSize: 11, color: "#64748b", lineHeight: 1.5 }}>
                <strong>Preset criteria:</strong>
                <ul style={{ paddingLeft: 16, marginTop: 6, marginBottom: 0 }}>
                  {Object.entries(PRESETS[selectedPreset]).map(([key, val]) => (
                    <li key={key}>
                      {key.replace(/_pct/g, "").replace(/_cr/g, "").replace(/_/g, " ").toUpperCase()}: {val[0]} to {val[1] === 9999999 ? "∞" : val[1]}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 6, fontWeight: 600 }}>Min ROE: {minRoe}%</label>
                <input
                  type="range" min="-50" max="100" step="1" value={minRoe} onChange={(e) => setMinRoe(Number(e.target.value))}
                  style={{ width: "100%", accentColor: "#00C9A7" }}
                />
              </div>
              <div>
                <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 6, fontWeight: 600 }}>Max Debt-to-Equity: {maxDe.toFixed(1)}x</label>
                <input
                  type="range" min="0" max="10" step="0.1" value={maxDe} onChange={(e) => setMaxDe(Number(e.target.value))}
                  style={{ width: "100%", accentColor: "#00C9A7" }}
                />
              </div>
              <div>
                <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 6, fontWeight: 600 }}>Min Net Margin: {minNpm}%</label>
                <input
                  type="range" min="-50" max="100" step="1" value={minNpm} onChange={(e) => setMinNpm(Number(e.target.value))}
                  style={{ width: "100%", accentColor: "#00C9A7" }}
                />
              </div>
              <div>
                <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 6, fontWeight: 600 }}>Min FCF (Cr): ₹{minFcf} Cr</label>
                <input
                  type="range" min="-1000" max="10000" step="100" value={minFcf} onChange={(e) => setMinFcf(Number(e.target.value))}
                  style={{ width: "100%", accentColor: "#00C9A7" }}
                />
              </div>
              <div>
                <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 6, fontWeight: 600 }}>Filter Sectors</label>
                <div style={{ maxHeight: 150, overflowY: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
                  {sectors.map((sec) => (
                    <label key={sec} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, cursor: "pointer" }}>
                      <input
                        type="checkbox" checked={selectedSectors.includes(sec)} onChange={() => handleSectorToggle(sec)}
                        style={{ accentColor: "#00C9A7" }}
                      />
                      {sec}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Results Section */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "#0A2342" }}>
              ✅ Found <strong>{filtered.length}</strong> matching companies
            </span>
            {filtered.length > 0 && (
              <button
                onClick={downloadCSV}
                style={{
                  padding: "8px 16px", background: "#00C9A7", color: "white", borderRadius: 8, fontSize: 12,
                  fontWeight: 600, border: "none", cursor: "pointer", outline: "none", display: "flex", alignItems: "center", gap: 6
                }}
              >
                ⬇️ Export (CSV)
              </button>
            )}
          </div>

          <div className="glass-card" style={{ overflow: "hidden" }}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ background: "#0A2342", color: "white" }}>
                    {["Ticker", "Company", "Sector", "Market Cap", "ROE%", "OPM%", "NPM%", "D/E", "FCF (Cr)", "PE", "Yield%"].map((h) => (
                      <th key={h} style={{ padding: "10px 12px", textAlign: "left", fontWeight: 600, whiteSpace: "nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((c, i) => (
                    <tr key={c.id} style={{ background: i % 2 === 0 ? "white" : "#f8fafc", borderBottom: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "10px 12px", fontWeight: 600 }}>{c.id}</td>
                      <td style={{ padding: "10px 12px", whiteSpace: "nowrap" }}>{c.company_name?.slice(0, 22)}</td>
                      <td style={{ padding: "10px 12px", color: "#64748b", fontSize: 11 }}>{c.sector}</td>
                      <td style={{ padding: "10px 12px" }}>{fmt(c.market_cap_cr, false, true)}</td>
                      <td style={{ padding: "10px 12px", fontWeight: 600, color: (c.return_on_equity_pct ?? 0) > 15 ? "#16a34a" : "#dc2626" }}>{fmt(c.return_on_equity_pct, true)}</td>
                      <td style={{ padding: "10px 12px" }}>{fmt(c.operating_profit_margin_pct, true)}</td>
                      <td style={{ padding: "10px 12px" }}>{fmt(c.net_profit_margin_pct, true)}</td>
                      <td style={{ padding: "10px 12px" }}>{fmt(c.debt_to_equity)}</td>
                      <td style={{ padding: "10px 12px" }}>{fmt(c.free_cash_flow_cr, false, true)}</td>
                      <td style={{ padding: "10px 12px" }}>{fmt(c.pe_ratio)}</td>
                      <td style={{ padding: "10px 12px" }}>{fmt(c.dividend_yield_pct, true)}</td>
                    </tr>
                  ))}
                  {filtered.length === 0 && (
                    <tr>
                      <td colSpan={11} style={{ padding: 32, textAlign: "center", color: "#64748b" }}>
                        No companies match the current filter criteria. Try adjusting the filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
