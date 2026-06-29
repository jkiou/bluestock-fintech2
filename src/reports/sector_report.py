"""
src/reports/sector_report.py
Sector Analysis Report — Nifty100
====================================================================
Page 1 : Executive Overview · Market Cap Distribution · Nifty100 Universe Summary
Page 2 : GICS Sector Aggregate Medians — Full Statistics Table
Pages 3+ : Per-Sector Deep-Dives with all company details, leaders, and sub-sector analysis
"""
import os
import logging
import sqlite3
from datetime import datetime

import pandas as pd

logger = logging.getLogger("reports.sector_report")
DB_PATH    = os.getenv("DB_PATH", "data/nifty100.db")
SECTOR_DIR = os.path.join("reports", "sector")

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable,
    )
    RL = True
except ImportError:
    RL = False
    logger.warning("reportlab not installed")

NAVY  = colors.HexColor("#0A2342") if RL else None
TEAL  = colors.HexColor("#00A896") if RL else None
LIGHT = colors.HexColor("#EEF2F7") if RL else None
WHITE = colors.white if RL else None
GOLD  = colors.HexColor("#F4A261") if RL else None
GREEN = colors.HexColor("#27AE60") if RL else None
GREY  = colors.HexColor("#7F8C8D") if RL else None

SECTOR_COLORS = [
    colors.HexColor("#1565C0"), colors.HexColor("#2E7D32"),
    colors.HexColor("#6A1B9A"), colors.HexColor("#E65100"),
    colors.HexColor("#00838F"), colors.HexColor("#AD1457"),
    colors.HexColor("#4527A0"), colors.HexColor("#00695C"),
    colors.HexColor("#558B2F"), colors.HexColor("#4E342E"),
]


def _load(db_path: str):
    with sqlite3.connect(db_path) as c:
        companies = pd.read_sql("""
            SELECT c.id, c.company_name AS name,
                   c.about_company, c.roce_percentage, c.roe_percentage,
                   c.book_value, c.face_value,
                   s.broad_sector AS sector, s.sub_sector AS industry,
                   s.index_weight_pct, s.market_cap_category,
                   mc.market_cap_crore AS market_cap_cr,
                   mc.enterprise_value_crore AS ev_cr,
                   mc.pe_ratio, mc.pb_ratio, mc.ev_ebitda,
                   mc.dividend_yield_pct
            FROM companies c
            LEFT JOIN sectors s    ON c.id = s.company_id
            LEFT JOIN market_cap mc ON c.id = mc.company_id
                AND mc.year = (SELECT MAX(year) FROM market_cap)
            ORDER BY s.broad_sector, mc.market_cap_crore DESC NULLS LAST
            """, c)

        ratios = pd.read_sql("SELECT * FROM financial_ratios", c)
        pl_all = pd.read_sql("""
            SELECT company_id, year, sales, net_profit, operating_profit,
                   opm_percentage, eps, dividend_payout
            FROM profitandloss""", c)
        cf_all = pd.read_sql("""
            SELECT company_id, year, operating_activity, investing_activity,
                   financing_activity, net_cash_flow
            FROM cashflow""", c)
        bs_all = pd.read_sql("""
            SELECT company_id, year, total_assets, borrowings, equity_capital, reserves
            FROM balancesheet""", c)

    # Latest ratios
    lr = ratios.loc[ratios.groupby("company_id")["year"].idxmax()].copy()
    if "id" in lr.columns: lr = lr.drop(columns=["id"])

    # Latest P&L
    lp = pl_all.loc[pl_all.groupby("company_id")["year"].idxmax()].copy()
    # Latest CF
    lcf = cf_all.loc[cf_all.groupby("company_id")["year"].idxmax()].copy()
    # Latest BS
    lbs = bs_all.loc[bs_all.groupby("company_id")["year"].idxmax()].copy()

    merged = companies.merge(lr,  left_on="id", right_on="company_id", how="left")
    merged = merged.merge(lp.rename(columns={"year":"pl_year"}),
                          left_on="id", right_on="company_id", how="left", suffixes=("","_pl"))
    merged = merged.merge(lcf.rename(columns={"year":"cf_year"}),
                          left_on="id", right_on="company_id", how="left", suffixes=("","_cf"))
    merged = merged.merge(lbs.rename(columns={"year":"bs_year"}),
                          left_on="id", right_on="company_id", how="left", suffixes=("","_bs"))
    return merged, pl_all, ratios


def _fmt(v, pct=False, cr=False, x=False, dp=1):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "N/A"
    if pct: return f"{v:.{dp}f}%"
    if cr:  return f"Rs {v:,.0f}Cr"
    if x:   return f"{v:.{dp}f}x"
    return f"{v:.{dp}f}"


def generate_sector_report(db_path: str = DB_PATH, output_dir: str = SECTOR_DIR) -> str:
    if not RL:
        raise RuntimeError("reportlab not installed")
    os.makedirs(output_dir, exist_ok=True)
    merged, pl_all, ratios = _load(db_path)

    date_str = datetime.now().strftime("%Y%m%d")
    out = os.path.join(output_dir, f"sector_report_{date_str}.pdf")
    doc = SimpleDocTemplate(out, pagesize=landscape(A4),
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    stl = getSampleStyleSheet()
    S   = []

    def h(txt, sz=12, col=NAVY, sp=5):
        return Paragraph(f"<b>{txt}</b>",
                         ParagraphStyle("_h", fontSize=sz, textColor=col,
                                        spaceAfter=sp, fontName="Helvetica-Bold"))
    def rule(col=NAVY, th=0.8):
        return HRFlowable(width="100%", thickness=th, color=col, spaceAfter=4)

    def std_table(header, rows, cw, hc=NAVY):
        t = Table([header] + rows, colWidths=cw)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  hc),
            ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
            ("FONTSIZE",      (0,0), (-1,-1), 7.5),
            ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
            ("GRID",          (0,0), (-1,-1), 0.25, colors.HexColor("#CFD8DC")),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT]),
            ("ALIGN",         (1,0), (-1,-1), "RIGHT"),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ]))
        return t

    # ═══════════════════════════════════════════════════════
    # PAGE 1 — Executive Overview
    # ═══════════════════════════════════════════════════════
    # Title banner (landscape)
    banner = Table([[
        Paragraph(
            "<font color='white' size='18'><b>NIFTY 100 — SECTOR INTELLIGENCE REPORT</b></font><br/>"
            "<font color='#A8D8EA' size='10'>Comprehensive GICS Sector Analysis · All 92 Companies</font>",
            ParagraphStyle("_bl", leading=26, leftIndent=8)),
        Paragraph(
            f"<font color='white' size='9'>"
            f"Generated: {datetime.now().strftime('%d %B %Y %H:%M')}<br/>"
            f"Universe: {len(merged)} Companies<br/>"
            f"Sectors: {merged['sector'].nunique()}<br/>"
            f"Sub-Sectors: {merged['industry'].nunique()}"
            f"</font>",
            ParagraphStyle("_br", leading=15, leftIndent=4)),
    ]], colWidths=[20*cm, 7*cm])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), NAVY),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
    ]))
    S += [banner, Spacer(1, 0.5*cm)]

    # Universe-level KPI summary
    S.append(h("NIFTY 100 UNIVERSE — TOP-LINE METRICS", sz=11))
    univ_items = [
        ("Total Companies",         str(len(merged))),
        ("Total Market Cap",        _fmt(merged["market_cap_cr"].sum(), cr=True)),
        ("Total Enterprise Value",  _fmt(merged["ev_cr"].sum(), cr=True)),
        ("Median P/E",              _fmt(merged["pe_ratio"].median())),
        ("Median P/B",              _fmt(merged["pb_ratio"].median())),
        ("Median ROE",              _fmt(merged["return_on_equity_pct"].median(), pct=True)),
        ("Median Net Margin",       _fmt(merged["net_profit_margin_pct"].median(), pct=True)),
        ("Median OPM",              _fmt(merged["operating_profit_margin_pct"].median(), pct=True)),
        ("Median D/E",              _fmt(merged["debt_to_equity"].median())),
        ("Median Div Yield",        _fmt(merged["dividend_yield_pct"].median(), pct=True)),
        ("Large Cap Companies",     str(len(merged[merged["market_cap_category"]=="Large Cap"]))),
        ("Mid Cap Companies",       str(len(merged[merged["market_cap_category"]=="Mid Cap"]))),
    ]
    rows = []
    per = 3
    for i in range(0, len(univ_items), per):
        row = []
        for k, v in univ_items[i:i+per]:
            row += [
                Paragraph(f"<b>{k}</b>", ParagraphStyle("_kl", fontSize=7.5, textColor=GREY)),
                Paragraph(str(v), ParagraphStyle("_kv", fontSize=9.5, textColor=TEAL, fontName="Helvetica-Bold")),
            ]
        while len(row) < per * 2:
            row += [Paragraph("", stl["Normal"]), Paragraph("", stl["Normal"])]
        rows.append(row)
    lt = Table(rows, colWidths=[5.5*cm, 3.5*cm] * per)
    lt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), LIGHT),
        ("GRID",          (0,0), (-1,-1), 0.25, colors.HexColor("#CFD8DC")),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    S += [lt, Spacer(1, 0.5*cm)]

    # Sector-level high-level overview table
    S.append(h("SECTOR OVERVIEW — MARKET CAP & COMPANY COUNT", sz=11))
    sec_agg = merged.groupby("sector").agg(
        Companies=("id", "count"),
        Total_MCap=("market_cap_cr", "sum"),
        Largest_Co=("market_cap_cr", "idxmax"),
    ).reset_index().sort_values("Total_MCap", ascending=False)

    ov_hdr  = ["#", "Sector", "Companies", "Total Market Cap (Rs Cr)", "% of Nifty100 MCap", "Largest Company"]
    total_mc = merged["market_cap_cr"].sum()
    ov_rows = []
    for i, (_, r) in enumerate(sec_agg.iterrows()):
        pct = r["Total_MCap"] / total_mc * 100 if total_mc else 0
        try:
            largest = merged.loc[r["Largest_Co"], "name"]
        except Exception:
            largest = "—"
        ov_rows.append([
            str(i+1),
            str(r["sector"] or "N/A"),
            str(int(r["Companies"])),
            _fmt(r["Total_MCap"], cr=True),
            f"{pct:.1f}%",
            str(largest)[:30],
        ])
    cw = [1.0*cm, 7.0*cm, 2.8*cm, 5.5*cm, 4.5*cm, 7.2*cm]
    S += [std_table(ov_hdr, ov_rows, cw)]

    S += [Spacer(1, 0.3*cm), rule(GREY, 0.5),
          Paragraph(f"<font size='7' color='grey'>Page 1 · Nifty100 Sector Intelligence Report · {datetime.now().strftime('%d %b %Y %H:%M')}</font>",
                    stl["Normal"]),
          PageBreak()]

    # ═══════════════════════════════════════════════════════
    # PAGE 2 — Full GICS Aggregated Statistics
    # ═══════════════════════════════════════════════════════
    S += [h("GICS SECTOR — AGGREGATE FINANCIAL STATISTICS", sz=14),
          rule(), Spacer(1, 0.4*cm)]

    S.append(Paragraph(
        "The table below presents median, mean, minimum, and maximum values for key financial metrics "
        "across each GICS broad sector, computed from the latest available financial data for all companies "
        "in the Nifty100 universe. Median values are preferred over mean to reduce the influence of outliers.",
        ParagraphStyle("_desc", fontSize=8.5, leading=12, textColor=colors.HexColor("#2C3E50"))))
    S.append(Spacer(1, 0.4*cm))

    stats_hdr = ["Sector", "Cos", "Med ROE%", "Med NPM%", "Med OPM%", "Med D/E",
                 "Med ICR", "Med FCF(Cr)", "Med P/E", "Med P/B", "Total MCap(Cr)", "Avg Div Yld%"]
    stats_rows = []
    for _, r in sec_agg.sort_values("Total_MCap", ascending=False).iterrows():
        sdf = merged[merged["sector"] == r["sector"]]
        def med(col): return sdf[col].median() if col in sdf.columns else None
        stats_rows.append([
            str(r["sector"] or "N/A"),
            str(int(r["Companies"])),
            _fmt(med("return_on_equity_pct"), pct=True),
            _fmt(med("net_profit_margin_pct"), pct=True),
            _fmt(med("operating_profit_margin_pct"), pct=True),
            _fmt(med("debt_to_equity")),
            _fmt(med("interest_coverage"), x=True),
            _fmt(med("free_cash_flow_cr"), cr=True),
            _fmt(med("pe_ratio")),
            _fmt(med("pb_ratio")),
            _fmt(sdf["market_cap_cr"].sum(), cr=True),
            _fmt(sdf["dividend_yield_pct"].mean(), pct=True),
        ])
    cw = [6.5*cm, 1.5*cm, 2.3*cm, 2.3*cm, 2.3*cm, 1.8*cm, 1.8*cm, 3.0*cm, 1.8*cm, 1.8*cm, 3.5*cm, 2.5*cm]
    S += [std_table(stats_hdr, stats_rows, cw), Spacer(1, 0.5*cm)]

    # Sector Leaders Table
    S.append(h("SECTOR LEADERS — HIGHEST ROE PER GICS SECTOR", sz=11))
    leaders = []
    for sect in sec_agg["sector"].dropna():
        sdf = merged[merged["sector"] == sect]
        if not sdf.empty and sdf["return_on_equity_pct"].notna().any():
            best_idx = sdf["return_on_equity_pct"].idxmax()
            r = sdf.loc[best_idx]
            leaders.append([
                str(sect),
                str(r["name"])[:30],
                str(r["id"]),
                _fmt(r["return_on_equity_pct"], pct=True),
                _fmt(r["net_profit_margin_pct"], pct=True),
                _fmt(r["market_cap_cr"], cr=True),
                _fmt(r["pe_ratio"]),
            ])
    l_hdr = ["Sector", "ROE Leader Company", "Ticker", "ROE%", "NPM%", "Market Cap", "P/E"]
    cw = [6*cm, 7.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 4.0*cm, 2.5*cm]
    S += [std_table(l_hdr, leaders, cw, hc=TEAL)]

    S += [Spacer(1, 0.3*cm), rule(GREY, 0.5),
          Paragraph(f"<font size='7' color='grey'>Page 2 · Nifty100 Sector Intelligence Report · {datetime.now().strftime('%d %b %Y %H:%M')}</font>",
                    stl["Normal"]),
          PageBreak()]

    # ═══════════════════════════════════════════════════════
    # PAGES 3+ — Per-Sector Deep-Dives
    # ═══════════════════════════════════════════════════════
    sectors_sorted = (
        merged.groupby("sector")["market_cap_cr"]
        .sum().sort_values(ascending=False).index.tolist()
    )

    for pg_num, sect in enumerate(sectors_sorted, start=3):
        sdf = merged[merged["sector"] == sect].sort_values("market_cap_cr", ascending=False)
        col_idx = pg_num % len(SECTOR_COLORS)
        sect_color = SECTOR_COLORS[col_idx]

        # Sector banner
        sb = Table([[
            Paragraph(
                f"<font color='white' size='14'><b>{sect.upper()}</b></font><br/>"
                f"<font color='white' size='9'>{len(sdf)} Companies  ·  "
                f"Total MCap: {_fmt(sdf['market_cap_cr'].sum(), cr=True)}  ·  "
                f"Median ROE: {_fmt(sdf['return_on_equity_pct'].median(), pct=True)}</font>",
                ParagraphStyle("_sb", leading=22, leftIndent=8)),
            Paragraph(
                f"<font color='white' size='8'>"
                f"Median NPM: {_fmt(sdf['net_profit_margin_pct'].median(), pct=True)}<br/>"
                f"Median OPM: {_fmt(sdf['operating_profit_margin_pct'].median(), pct=True)}<br/>"
                f"Median D/E: {_fmt(sdf['debt_to_equity'].median())}<br/>"
                f"Median P/E: {_fmt(sdf['pe_ratio'].median())}"
                f"</font>",
                ParagraphStyle("_sb2", leading=14, leftIndent=4)),
        ]], colWidths=[17*cm, 10*cm])
        sb.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), sect_color),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ]))
        S += [sb, Spacer(1, 0.4*cm)]

        # Sub-sector breakdown
        sub_agg = sdf.groupby("industry").agg(
            Cos=("id", "count"),
            MCap=("market_cap_cr", "sum"),
            Med_ROE=("return_on_equity_pct", "median"),
        ).reset_index().sort_values("MCap", ascending=False)
        if not sub_agg.empty and len(sub_agg) > 1:
            S.append(h("SUB-SECTOR BREAKDOWN", sz=9, col=sect_color))
            sub_hdr  = ["Sub-Sector / Industry", "Companies", "Total MCap (Rs Cr)", "Median ROE%"]
            sub_rows = [
                [str(r["industry"] or "—")[:40], str(int(r["Cos"])),
                 _fmt(r["MCap"], cr=True), _fmt(r["Med_ROE"], pct=True)]
                for _, r in sub_agg.iterrows()
            ]
            cw = [10*cm, 3*cm, 6*cm, 4*cm]
            S += [std_table(sub_hdr, sub_rows, cw, hc=sect_color), Spacer(1, 0.3*cm)]

        # All companies in sector
        S.append(h(f"ALL COMPANIES — {sect.upper()}", sz=9, col=sect_color))
        co_hdr = ["Company Name", "Ticker", "Sub-Sector", "MCap Cat.",
                  "Mkt Cap (Cr)", "ROE%", "NPM%", "OPM%", "D/E",
                  "ICR", "FCF (Cr)", "P/E", "P/B", "Div Yld%", "EPS"]
        co_rows = []
        for _, r in sdf.iterrows():
            co_rows.append([
                str(r["name"])[:28],
                str(r["id"]),
                str(r["industry"] or "—")[:18],
                str(r["market_cap_category"] or "—"),
                _fmt(r["market_cap_cr"], cr=True),
                _fmt(r["return_on_equity_pct"], pct=True),
                _fmt(r["net_profit_margin_pct"], pct=True),
                _fmt(r["operating_profit_margin_pct"], pct=True),
                _fmt(r["debt_to_equity"]),
                _fmt(r["interest_coverage"], x=True),
                _fmt(r["free_cash_flow_cr"], cr=True),
                _fmt(r["pe_ratio"]),
                _fmt(r["pb_ratio"]),
                _fmt(r["dividend_yield_pct"], pct=True),
                _fmt(r["earnings_per_share"]),
            ])
        cw = [5.5*cm, 2.0*cm, 3.8*cm, 2.5*cm, 3.0*cm, 1.8*cm, 1.8*cm, 1.8*cm,
              1.5*cm, 1.5*cm, 2.5*cm, 1.5*cm, 1.5*cm, 2.0*cm, 1.8*cm]
        S += [std_table(co_hdr, co_rows, cw, hc=sect_color), Spacer(1, 0.4*cm)]

        # Income statement rollup for sector
        if "sales" in sdf.columns:
            S.append(h("SECTOR INCOME AGGREGATES (Latest Year, Rs Crore)", sz=9, col=sect_color))
            agg_items_data = [
                ("Aggregate Revenue",       _fmt(sdf["sales"].sum(), cr=True)),
                ("Aggregate Net Profit",    _fmt(sdf["net_profit"].sum(), cr=True)),
                ("Aggregate Op. Profit",    _fmt(sdf["operating_profit"].sum(), cr=True)),
                ("Median EPS",              _fmt(sdf["eps"].median())),
            ]
            r2 = []
            for k, v in agg_items_data:
                r2.append([
                    Paragraph(f"<b>{k}</b>", ParagraphStyle("_kl", fontSize=7.5, textColor=GREY)),
                    Paragraph(str(v), ParagraphStyle("_kv", fontSize=9, textColor=sect_color, fontName="Helvetica-Bold")),
                ])
            agg_t = Table([[r2[0][0], r2[0][1], r2[1][0], r2[1][1]],
                           [r2[2][0], r2[2][1], r2[3][0], r2[3][1]]],
                          colWidths=[6*cm, 5*cm, 6*cm, 5*cm])
            agg_t.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,-1), LIGHT),
                ("GRID",          (0,0), (-1,-1), 0.25, colors.HexColor("#CFD8DC")),
                ("TOPPADDING",    (0,0), (-1,-1), 5),
                ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                ("LEFTPADDING",   (0,0), (-1,-1), 8),
            ]))
            S += [agg_t, Spacer(1, 0.3*cm)]

        # Page footer
        S += [rule(GREY, 0.5),
              Paragraph(
                  f"<font size='7' color='grey'>Page {pg_num} · Sector: {sect} · "
                  f"Nifty100 Sector Intelligence Report · {datetime.now().strftime('%d %b %Y %H:%M')}</font>",
                  stl["Normal"])]
        if pg_num < len(sectors_sorted) + 2:
            S.append(PageBreak())

    doc.build(S)
    logger.info(f"Rich sector report saved: {out}")
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
    out = generate_sector_report()
    print(f"✓ Sector report: {out}")
