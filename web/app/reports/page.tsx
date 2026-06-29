"use client";

import { useEffect, useState } from "react";

export default function AnnualReports() {
  const [companies, setCompanies] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string>("");

  useEffect(() => {
    Promise.all([
      fetch("/data/companies.json").then((r) => r.json()),
      fetch("/data/documents.json").then((r) => r.json()),
    ]).then(([comps, docs]) => {
      setCompanies(comps);
      setDocuments(docs);
      if (comps.length > 0) {
        setSelectedTicker(comps[0].id);
      }
    });
  }, []);

  const selectedCompany = companies.find((c) => c.id === selectedTicker) || null;
  const companyDocs = documents.filter((d) => d.company_id === selectedTicker).sort((a, b) => b.Year - a.Year);

  // Group to find total document counts per company for the global coverage summary table
  const docCounts = documents.reduce((acc, curr) => {
    acc[curr.company_id] = (acc[curr.company_id] ?? 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const coverageSummary = companies.map((c) => ({
    ticker: c.id,
    name: c.company_name,
    sector: c.sector,
    count: docCounts[c.id] ?? 0,
  })).sort((a, b) => b.count - a.count);

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1 style={{ fontSize: 26, fontWeight: 700, color: "#0A2342" }}>📄 Annual Report Repository</h1>
        <div style={{ minWidth: 250 }}>
          <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 4, fontWeight: 600 }}>Select Company</label>
          <select
            value={selectedTicker}
            onChange={(e) => setSelectedTicker(e.target.value)}
            style={{
              width: "100%", padding: "10px 12px", borderRadius: 8,
              border: "1px solid #cbd5e1", background: "white", fontSize: 14,
              color: "#0A2342", fontWeight: 500, outline: "none", cursor: "pointer"
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

      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 24 }}>
        {/* Company specific documents list */}
        <div className="glass-card" style={{ padding: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: "#0A2342", marginBottom: 16 }}>
            Filings for {selectedCompany?.company_name} ({selectedTicker})
          </h3>

          {companyDocs.length > 0 ? (
            <ul style={{ display: "flex", flexDirection: "column", gap: 12, paddingLeft: 0, margin: 0, listStyle: "none" }}>
              {companyDocs.map((doc, idx) => (
                <li
                  key={idx}
                  style={{
                    background: "#f8fafc", padding: "12px 18px", borderRadius: 8, border: "1px solid #e2e8f0",
                    display: "flex", justifyContent: "space-between", alignItems: "center"
                  }}
                >
                  <span style={{ fontSize: 13, fontWeight: 600, color: "#0A2342" }}>
                    📁 FY {doc.Year} Annual Report
                  </span>
                  {doc.Annual_Report ? (
                    <a
                      href={doc.Annual_Report}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        padding: "6px 12px", background: "#00C9A7", color: "white", textDecoration: "none",
                        borderRadius: 6, fontSize: 11, fontWeight: 600
                      }}
                    >
                      Download / View PDF File
                    </a>
                  ) : (
                    <span style={{ fontSize: 11, color: "#94a3b8" }}>Link unavailable</span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <div style={{ padding: 24, textAlign: "center", color: "#64748b", background: "#f8fafc", borderRadius: 8 }}>
              No annual reports found for this company.
            </div>
          )}
        </div>

        {/* Global Document Coverage Summary Table */}
        <div className="glass-card" style={{ padding: 24 }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, color: "#0A2342", marginBottom: 16 }}>📑 Global Document Coverage Summary</h3>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "#0A2342", color: "white" }}>
                  {["Ticker", "Company Name", "Sector", "Available Reports"].map((h) => (
                    <th key={h} style={{ padding: "10px 12px", textAlign: "left", fontWeight: 600, whiteSpace: "nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {coverageSummary.map((co, i) => (
                  <tr key={co.ticker} style={{ background: i % 2 === 0 ? "white" : "#f8fafc", borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "10px 12px", fontWeight: 600, color: "#0A2342" }}>{co.ticker}</td>
                    <td style={{ padding: "10px 12px", fontWeight: 500 }}>{co.name}</td>
                    <td style={{ padding: "10px 12px", color: "#64748b", fontSize: 11 }}>{co.sector}</td>
                    <td style={{ padding: "10px 12px", fontWeight: 700, color: co.count > 0 ? "#16a34a" : "#dc2626" }}>{co.count}</td>
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
