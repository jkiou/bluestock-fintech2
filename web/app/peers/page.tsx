"use client";

import { useEffect, useState } from "react";
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  ResponsiveContainer, Tooltip, Legend
} from "recharts";

const fmt = (v: number | null, pct = false, cr = false) => {
  if (v == null || isNaN(v)) return "N/A";
  if (pct) return `${v.toFixed(1)}%`;
  if (cr) return v >= 1e5 ? `₹${(v / 1e5).toFixed(1)}L Cr` : `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })} Cr`;
  return v.toFixed(2);
};

const METRICS = [
  { key: "return_on_equity_pct", label: "ROE%" },
  { key: "operating_profit_margin_pct", label: "OPM%" },
  { key: "net_profit_margin_pct", label: "NPM%" },
  { key: "debt_to_equity", label: "D/E" },
  { key: "interest_coverage", label: "ICR" },
  { key: "asset_turnover", label: "Asset TO" },
  { key: "free_cash_flow_cr", label: "FCF (Cr)" },
  { key: "earnings_per_share", label: "EPS" },
];

const COLORS = ["#0A2342", "#00C9A7", "#F4A261", "#e74c3c", "#9b59b6", "#2ecc71", "#3498db", "#e67e22"];

export default function PeerComparison() {
  const [companies, setCompanies] = useState<any[]>([]);
  const [ratios, setRatios] = useState<any[]>([]);
  const [peerGroups, setPeerGroups] = useState<any[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<string>("");
  const [useSectorFallback, setUseSectorFallback] = useState<boolean>(false);

  useEffect(() => {
    Promise.all([
      fetch("/data/companies.json").then((r) => r.json()),
      fetch("/data/ratios_latest.json").then((r) => r.json()),
      fetch("/data/peer_groups.json").then((r) => r.json()),
    ]).then(([comps, rats, pg]) => {
      setCompanies(comps);
      setRatios(rats);
      setPeerGroups(pg);

      if (pg.length > 0) {
        const groups = [...new Set(pg.map((p: any) => p.peer_group_name).filter(Boolean))].sort() as string[];
        if (groups.length > 0) {
          setSelectedGroup(groups[0]);
        }
      } else {
        setUseSectorFallback(true);
        const sectors = [...new Set(comps.map((c: any) => c.sector).filter(Boolean))].sort() as string[];
        if (sectors.length > 0) {
          setSelectedGroup(sectors[0]);
        }
      }
    });
  }, []);

  const groups = useSectorFallback
    ? [...new Set(companies.map((c) => c.sector).filter(Boolean))].sort()
    : [...new Set(peerGroups.map((p) => p.peer_group_name).filter(Boolean))].sort();

  // Combine companies with latest ratios
  const mergedData = companies.map((c) => {
    const r = ratios.find((ratio) => ratio.company_id === c.id) || {};
    return { ...r, ...c };
  });

  // Get current group member data
  const getGroupMembers = () => {
    if (useSectorFallback) {
      return mergedData.filter((c) => c.sector === selectedGroup);
    } else {
      const memberIds = peerGroups.filter((p) => p.peer_group_name === selectedGroup).map((p) => p.company_id);
      return mergedData.filter((c) => memberIds.includes(c.id));
    }
  };

  const groupData = getGroupMembers().sort((a, b) => (b.market_cap_cr ?? 0) - (a.market_cap_cr ?? 0));

  // Build Radar Data
  const getRadarData = () => {
    if (groupData.length < 2) return [];

    // We normalize each KPI in [0, 100] relative to the min/max of the selected group
    return METRICS.map((m) => {
      const colData = groupData.map((d) => d[m.key]).filter((v) => v != null && !isNaN(v));
      const min = colData.length > 0 ? Math.min(...colData) : 0;
      const max = colData.length > 0 ? Math.max(...colData) : 100;
      const range = max - min || 1;

      const radarPoint: any = { subject: m.label };

      groupData.forEach((row) => {
        const val = row[m.key];
        let normalized = 0;
        if (val != null && !isNaN(val)) {
          normalized = ((val - min) / range) * 100;
        }
        radarPoint[row.id] = Math.round(normalized);
      });

      return radarPoint;
    });
  };

  const radarData = getRadarData();

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1 style={{ fontSize: 26, fontWeight: 700, color: "#0A2342" }}>👥 Peer Comparison Engine</h1>
        <div style={{ minWidth: 250 }}>
          <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 4, fontWeight: 600 }}>
            {useSectorFallback ? "Select Sector" : "Select Peer Group"}
          </label>
          <select
            value={selectedGroup}
            onChange={(e) => setSelectedGroup(e.target.value)}
            style={{
              width: "100%", padding: "10px 12px", borderRadius: 8,
              border: "1px solid #cbd5e1", background: "white", fontSize: 14,
              color: "#0A2342", fontWeight: 500, outline: "none", cursor: "pointer"
            }}
          >
            {groups.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 24 }}>
        <button
          onClick={() => {
            setUseSectorFallback(false);
            const pgGroups = [...new Set(peerGroups.map((p: any) => p.peer_group_name).filter(Boolean))].sort() as string[];
            if (pgGroups.length > 0) setSelectedGroup(pgGroups[0]);
          }}
          disabled={peerGroups.length === 0}
          style={{
            padding: "6px 12px", borderRadius: 20, fontSize: 11, fontWeight: 600, border: "none", cursor: "pointer",
            background: !useSectorFallback ? "#00C9A7" : "#e2e8f0",
            color: !useSectorFallback ? "white" : "#64748b",
            opacity: peerGroups.length === 0 ? 0.5 : 1
          }}
        >
          Use Custom Peer Groups
        </button>
        <button
          onClick={() => {
            setUseSectorFallback(true);
            const secList = [...new Set(companies.map((c: any) => c.sector).filter(Boolean))].sort() as string[];
            if (secList.length > 0) setSelectedGroup(secList[0]);
          }}
          style={{
            padding: "6px 12px", borderRadius: 20, fontSize: 11, fontWeight: 600, border: "none", cursor: "pointer",
            background: useSectorFallback ? "#00C9A7" : "#e2e8f0",
            color: useSectorFallback ? "white" : "#64748b",
          }}
        >
          Group by Sector
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 24 }}>
        {/* Radar Chart Visual */}
        {groupData.length >= 2 ? (
          <div className="glass-card" style={{ padding: 24, display: "flex", flexDirection: "column", alignItems: "center" }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: "#0A2342", alignSelf: "flex-start", marginBottom: 16 }}>
              📡 Radar Chart — Normalised KPI Comparison (0–100 Rank in Group)
            </h3>
            <div style={{ width: "100%", height: 420 }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: "#64748b", fontSize: 12, fontWeight: 500 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 10 }} />
                  <Tooltip />
                  <Legend />
                  {groupData.map((co, idx) => (
                    <Radar
                      key={co.id}
                      name={`${co.company_name?.slice(0, 15)} (${co.id})`}
                      dataKey={co.id}
                      stroke={COLORS[idx % COLORS.length]}
                      fill={COLORS[idx % COLORS.length]}
                      fillOpacity={0.15}
                      strokeWidth={2}
                    />
                  ))}
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : (
          <div className="glass-card" style={{ padding: 40, textAlign: "center", color: "#64748b" }}>
            ⚠️ Not enough companies in this group for normalized radar visualization.
          </div>
        )}

        {/* Side-by-Side Comparison Table */}
        <div className="glass-card" style={{ padding: 24 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: "#0A2342", marginBottom: 16 }}>📊 Side-by-Side KPI Comparison Table</h3>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "#0A2342", color: "white" }}>
                  {["Ticker", "Company Name", "ROE%", "OPM%", "NPM%", "D/E", "Interest Coverage", "Asset TO", "FCF (Cr)", "EPS"].map((h) => (
                    <th key={h} style={{ padding: "10px 12px", textAlign: "left", fontWeight: 600, whiteSpace: "nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {groupData.map((co, i) => (
                  <tr key={co.id} style={{ background: i % 2 === 0 ? "white" : "#f8fafc", borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "10px 12px", fontWeight: 600, color: "#0A2342" }}>{co.id}</td>
                    <td style={{ padding: "10px 12px", fontWeight: 500, whiteSpace: "nowrap" }}>{co.company_name?.slice(0, 24)}</td>
                    <td style={{ padding: "10px 12px" }}>{fmt(co.return_on_equity_pct, true)}</td>
                    <td style={{ padding: "10px 12px" }}>{fmt(co.operating_profit_margin_pct, true)}</td>
                    <td style={{ padding: "10px 12px" }}>{fmt(co.net_profit_margin_pct, true)}</td>
                    <td style={{ padding: "10px 12px" }}>{fmt(co.debt_to_equity)}</td>
                    <td style={{ padding: "10px 12px" }}>{fmt(co.interest_coverage)}</td>
                    <td style={{ padding: "10px 12px" }}>{fmt(co.asset_turnover)}</td>
                    <td style={{ padding: "10px 12px" }}>{fmt(co.free_cash_flow_cr, false, true)}</td>
                    <td style={{ padding: "10px 12px" }}>{fmt(co.earnings_per_share)}</td>
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
