"""
src/reports/portfolio_report.py
2-Page Portfolio Report — Nifty100 Financial Analysis
==================================================================
Page 1 : Executive Summary · Weighted KPI Dashboard · Sector Allocation · Holdings Detail
Page 2 : Individual Holding Deep-Dives · Risk Analysis · Analyst Commentary · Diversification Score
"""
import os
import logging
import sqlite3
from datetime import datetime

import pandas as pd

logger = logging.getLogger("reports.portfolio_report")
DB_PATH       = os.getenv("DB_PATH", "data/nifty100.db")
PORTFOLIO_DIR = os.path.join("reports", "portfolio")

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak,
    )
    RL = True
except ImportError:
    RL = False

NAVY   = colors.HexColor("#0A2342") if RL else None
TEAL   = colors.HexColor("#00A896") if RL else None
LIGHT  = colors.HexColor("#EEF2F7") if RL else None
WHITE  = colors.white if RL else None
GOLD   = colors.HexColor("#F4A261") if RL else None
GREEN  = colors.HexColor("#27AE60") if RL else None
GREY   = colors.HexColor("#7F8C8D") if RL else None
YELLOW = colors.HexColor("#FFFDE7") if RL else None


def _fmt(v, pct=False, cr=False, x=False, dp=2):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "N/A"
    if pct:  return f"{v:.{dp}f}%"
    if cr:   return f"Rs {v:,.0f} Cr"
    if x:    return f"{v:.{dp}f}x"
    return f"{v:.{dp}f}"


def _load(tickers: list, weights: list, db_path: str) -> pd.DataFrame:
    ph = ",".join(["?" for _ in tickers])
    with sqlite3.connect(db_path) as conn:
        companies = pd.read_sql(f"""
            SELECT c.id, c.company_name AS name, c.about_company,
                   c.roce_percentage, c.roe_percentage,
                   s.broad_sector AS sector, s.sub_sector AS industry,
                   s.market_cap_category,
                   mc.pe_ratio, mc.pb_ratio, mc.dividend_yield_pct,
                   mc.market_cap_crore AS market_cap_cr,
                   mc.enterprise_value_crore AS ev_cr, mc.ev_ebitda
            FROM companies c
            LEFT JOIN sectors s ON c.id=s.company_id
            LEFT JOIN market_cap mc ON c.id=mc.company_id
                AND mc.year=(SELECT MAX(year) FROM market_cap)
            WHERE c.id IN ({ph})""", conn, params=tickers)

        ratios = pd.read_sql(f"""
            SELECT fr.* FROM financial_ratios fr
            WHERE fr.company_id IN ({ph})""", conn, params=tickers)

        pl_latest = pd.read_sql(f"""
            SELECT pl.company_id, pl.year, pl.sales, pl.net_profit,
                   pl.operating_profit, pl.opm_percentage, pl.eps, pl.dividend_payout
            FROM profitandloss pl
            WHERE pl.company_id IN ({ph})
              AND pl.year=(SELECT MAX(year) FROM profitandloss WHERE company_id=pl.company_id)
            """, conn, params=tickers)

        cf_latest = pd.read_sql(f"""
            SELECT cf.company_id, cf.year, cf.operating_activity,
                   cf.investing_activity, cf.financing_activity, cf.net_cash_flow
            FROM cashflow cf
            WHERE cf.company_id IN ({ph})
              AND cf.year=(SELECT MAX(year) FROM cashflow WHERE company_id=cf.company_id)
            """, conn, params=tickers)

    latest_ratios = ratios.loc[ratios.groupby("company_id")["year"].idxmax()].copy()
    if "id" in latest_ratios.columns:
        latest_ratios = latest_ratios.drop(columns=["id"])

    merged = companies.merge(latest_ratios, left_on="id", right_on="company_id", how="left")
    merged = merged.merge(pl_latest.rename(columns={"year": "pl_year"}),
                          left_on="id", right_on="company_id", how="left")
    merged = merged.merge(cf_latest.rename(columns={"year": "cf_year"}),
                          left_on="id", right_on="company_id", how="left", suffixes=("", "_cf"))
    merged["ticker"] = merged["id"]
    wmap = dict(zip(tickers, weights))
    merged["weight_pct"] = merged["ticker"].map(wmap).fillna(0.0)
    return merged


def _wavg(df, col, wcol="weight_pct"):
    v = df[[col, wcol]].dropna()
    tw = v[wcol].sum()
    return (v[col] * v[wcol]).sum() / tw if tw else None


def generate_portfolio_report(
    tickers: list, weights: list,
    portfolio_name: str = "My Portfolio",
    db_path: str = DB_PATH,
    output_dir: str = PORTFOLIO_DIR,
) -> str:
    if not RL:
        raise RuntimeError("reportlab not installed")
    if len(tickers) != len(weights):
        raise ValueError("tickers and weights length mismatch")
    os.makedirs(output_dir, exist_ok=True)

    upper_tickers = [t.upper() for t in tickers]
    df = _load(upper_tickers, weights, db_path)

    safe = portfolio_name.replace(" ", "_")
    out  = os.path.join(output_dir, f"{safe}_{datetime.now().strftime('%Y%m%d')}.pdf")
    doc  = SimpleDocTemplate(out, pagesize=A4,
                             leftMargin=1.5*cm, rightMargin=1.5*cm,
                             topMargin=1.5*cm, bottomMargin=1.5*cm)
    stl  = getSampleStyleSheet()
    S    = []

    def h(txt, sz=11, col=NAVY, sp=5):
        return Paragraph(f"<b>{txt}</b>",
                         ParagraphStyle("_h", fontSize=sz, textColor=col,
                                        spaceAfter=sp, fontName="Helvetica-Bold"))

    def rule(col=NAVY, th=0.8):
        return HRFlowable(width="100%", thickness=th, color=col, spaceAfter=4)

    def label_val(items, cols=4):
        per = cols // 2
        rows = []
        for i in range(0, len(items), per):
            row = []
            for k, v in items[i:i+per]:
                row += [
                    Paragraph(f"<b>{k}</b>", ParagraphStyle("_kl", fontSize=7.5, textColor=GREY)),
                    Paragraph(str(v), ParagraphStyle("_kv", fontSize=9.5, textColor=TEAL, fontName="Helvetica-Bold")),
                ]
            while len(row) < cols:
                row += [Paragraph("", stl["Normal"]), Paragraph("", stl["Normal"])]
            rows.append(row)
        t = Table(rows, colWidths=[4.5*cm, 3.5*cm] * per)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), LIGHT),
            ("GRID",          (0,0), (-1,-1), 0.25, colors.HexColor("#CFD8DC")),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ]))
        return t

    def std_table(header, rows, cw, hc=NAVY):
        t = Table([header] + rows, colWidths=cw)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  hc),
            ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
            ("FONTSIZE",      (0,0), (-1,-1), 8),
            ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
            ("GRID",          (0,0), (-1,-1), 0.25, colors.HexColor("#CFD8DC")),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT]),
            ("ALIGN",         (1,0), (-1,-1), "RIGHT"),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ]))
        return t

    # ════════════════════════════════════════
    # PAGE 1 — Executive Summary
    # ════════════════════════════════════════

    # Banner
    banner = Table([[
        Paragraph(
            f"<font color='white' size='16'><b>{portfolio_name}</b></font><br/>"
            f"<font color='#A8D8EA' size='9'>Nifty100 Portfolio Intelligence Report</font>",
            ParagraphStyle("_bl", leading=22, leftIndent=6)),
        Paragraph(
            f"<font color='white' size='9'>"
            f"Report Date: {datetime.now().strftime('%d %B %Y')}<br/>"
            f"Holdings: {len(df)}  ·  Sectors: {df['sector'].nunique()}<br/>"
            f"Total Allocation: {sum(weights):.1f}%"
            f"</font>",
            ParagraphStyle("_br", leading=14, leftIndent=4)),
    ]], colWidths=[11*cm, 7*cm])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), NAVY),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
    ]))
    S += [banner, Spacer(1, 0.4*cm)]

    # Weighted KPIs
    S.append(h("PORTFOLIO WEIGHTED KPI DASHBOARD", sz=10))
    w_roe = _wavg(df, "return_on_equity_pct")
    w_opm = _wavg(df, "operating_profit_margin_pct")
    w_npm = _wavg(df, "net_profit_margin_pct")
    w_dte = _wavg(df, "debt_to_equity")
    w_eps = _wavg(df, "earnings_per_share")
    w_pe  = _wavg(df, "pe_ratio")
    w_pb  = _wavg(df, "pb_ratio")
    w_icr = _wavg(df, "interest_coverage")
    w_fcf = _wavg(df, "free_cash_flow_cr")
    w_dy  = _wavg(df, "dividend_yield_pct")
    total_mcap = df["market_cap_cr"].sum()

    kpi_items = [
        ("Wtd. Return on Equity",   _fmt(w_roe, pct=True)),
        ("Wtd. Oper. Profit Margin",_fmt(w_opm, pct=True)),
        ("Wtd. Net Profit Margin",  _fmt(w_npm, pct=True)),
        ("Wtd. Debt / Equity",      _fmt(w_dte)),
        ("Wtd. EPS",                _fmt(w_eps)),
        ("Wtd. P/E Ratio",          _fmt(w_pe)),
        ("Wtd. P/B Ratio",          _fmt(w_pb)),
        ("Wtd. Interest Coverage",  _fmt(w_icr, x=True)),
        ("Wtd. Free Cash Flow",     _fmt(w_fcf, cr=True)),
        ("Wtd. Dividend Yield",     _fmt(w_dy, pct=True)),
        ("Portfolio Market Cap",    _fmt(total_mcap, cr=True)),
        ("# Holdings",              str(len(df))),
        ("# Sectors",               str(df["sector"].nunique())),
        ("# Industries",            str(df["industry"].nunique())),
    ]
    S += [label_val(kpi_items, cols=4), Spacer(1, 0.4*cm)]

    # Sector Allocation
    S.append(h("SECTOR CONCENTRATION & ALLOCATION", sz=10))
    sec_w = df.groupby("sector").agg(
        Weight=("weight_pct", "sum"),
        Holdings=("id", "count"),
        Avg_MCap=("market_cap_cr", "mean"),
        Avg_ROE=("return_on_equity_pct", "mean"),
    ).reset_index().sort_values("Weight", ascending=False)
    sec_hdr  = ["Sector", "Portfolio Weight", "Holdings", "Avg Mkt Cap (Cr)", "Avg ROE%"]
    sec_rows = []
    for _, r in sec_w.iterrows():
        sec_rows.append([
            str(r["sector"] or "N/A"),
            _fmt(r["Weight"], pct=True),
            str(int(r["Holdings"])),
            _fmt(r["Avg_MCap"], cr=True),
            _fmt(r["Avg_ROE"], pct=True),
        ])
    cw = [6.5*cm, 3.5*cm, 2.5*cm, 4.0*cm, 3.5*cm]
    S += [std_table(sec_hdr, sec_rows, cw, hc=TEAL), Spacer(1, 0.4*cm)]

    # Holdings Detail Table
    S.append(h("FULL HOLDINGS TABLE", sz=10))
    h_hdr  = ["Ticker", "Company Name", "Sector", "Wt%", "Mkt Cap", "ROE%", "NPM%", "OPM%", "D/E", "P/E", "P/B", "EPS"]
    h_rows = []
    for _, r in df.sort_values("weight_pct", ascending=False).iterrows():
        h_rows.append([
            str(r["ticker"]),
            str(r.get("name", ""))[:18],
            str(r.get("sector", ""))[:12],
            _fmt(r["weight_pct"], pct=True),
            _fmt(r.get("market_cap_cr"), cr=True),
            _fmt(r.get("return_on_equity_pct"), pct=True),
            _fmt(r.get("net_profit_margin_pct"), pct=True),
            _fmt(r.get("operating_profit_margin_pct"), pct=True),
            _fmt(r.get("debt_to_equity")),
            _fmt(r.get("pe_ratio")),
            _fmt(r.get("pb_ratio")),
            _fmt(r.get("earnings_per_share")),
        ])
    cw = [2.0*cm, 3.0*cm, 2.2*cm, 1.4*cm, 2.2*cm, 1.4*cm, 1.4*cm, 1.4*cm, 1.2*cm, 1.2*cm, 1.2*cm, 1.4*cm]
    S += [std_table(h_hdr, h_rows, cw)]

    # Page 1 footer
    S += [Spacer(1, 0.3*cm), rule(GREY, 0.5),
          Paragraph(f"<font size='7' color='grey'>Page 1/2  ·  Nifty100 Portfolio Report  ·  {datetime.now().strftime('%d %b %Y %H:%M')}</font>",
                    stl["Normal"]),
          PageBreak()]

    # ════════════════════════════════════════
    # PAGE 2 — Deep Dives · Risk · Commentary
    # ════════════════════════════════════════
    S += [h(f"{portfolio_name}  —  Holding Deep-Dives & Risk Assessment", sz=13),
          rule(), Spacer(1, 0.3*cm)]

    # Individual Holding Summaries
    S.append(h("INDIVIDUAL HOLDING PROFILES", sz=10))
    for _, r in df.sort_values("weight_pct", ascending=False).iterrows():
        name  = r.get("name", r["ticker"])
        about = r.get("about_company", "")
        items = [
            ("Ticker",          str(r["ticker"])),
            ("Sector",          str(r.get("sector","—"))),
            ("Industry",        str(r.get("industry","—"))[:30]),
            ("Portfolio Weight", _fmt(r["weight_pct"], pct=True)),
            ("Market Cap",      _fmt(r.get("market_cap_cr"), cr=True)),
            ("Market Category", str(r.get("market_cap_category","—"))),
            ("Revenue (Latest)", _fmt(r.get("sales"), cr=True)),
            ("Net Profit",      _fmt(r.get("net_profit"), cr=True)),
            ("ROE",             _fmt(r.get("return_on_equity_pct"), pct=True)),
            ("Net Margin",      _fmt(r.get("net_profit_margin_pct"), pct=True)),
            ("OPM",             _fmt(r.get("opm_percentage"), pct=True)),
            ("D/E Ratio",       _fmt(r.get("debt_to_equity"))),
            ("P/E",             _fmt(r.get("pe_ratio"))),
            ("P/B",             _fmt(r.get("pb_ratio"))),
            ("Div Yield",       _fmt(r.get("dividend_yield_pct"), pct=True)),
            ("Free Cash Flow",  _fmt(r.get("free_cash_flow_cr"), cr=True)),
        ]
        S.append(h(f"  {name}  [{r['ticker']}]  —  {_fmt(r['weight_pct'], pct=True)} of Portfolio",
                   sz=9, col=TEAL))
        if about:
            S.append(Paragraph(str(about)[:300],
                               ParagraphStyle("_ab", fontSize=7.5, leading=11,
                                              textColor=colors.HexColor("#34495E"))))
            S.append(Spacer(1, 0.15*cm))
        S += [label_val(items, cols=4), Spacer(1, 0.3*cm)]

    # Risk & Health Analysis
    S.append(h("PORTFOLIO RISK & HEALTH ANALYSIS", sz=10))
    remarks = []

    # Profitability
    if w_roe and w_roe > 20:
        remarks.append(("🟢 HIGH PROFITABILITY",
                        f"Weighted ROE of {w_roe:.1f}% is well above the 15% benchmark. "
                        "Portfolio companies demonstrate exceptional capital efficiency and competitive moats."))
    elif w_roe and w_roe > 12:
        remarks.append(("🟡 ADEQUATE PROFITABILITY",
                        f"Weighted ROE of {w_roe:.1f}% is in an acceptable range. "
                        "Monitor for margin compression in cyclical downturns."))
    else:
        remarks.append(("🔴 LOW PROFITABILITY",
                        f"Weighted ROE of {_fmt(w_roe, pct=True)} is below threshold. "
                        "Consider reviewing low-return holdings for strategic fit."))

    # Leverage
    if w_dte and w_dte < 0.5:
        remarks.append(("🟢 LOW LEVERAGE",
                        f"Aggregate D/E of {w_dte:.2f}x indicates a highly conservative balance sheet. "
                        "Holdings are well-positioned to absorb interest rate shocks."))
    elif w_dte and w_dte > 1.5:
        remarks.append(("🔴 ELEVATED LEVERAGE",
                        f"Weighted D/E of {w_dte:.2f}x may pose refinancing risk. "
                        "Ensure levered holdings are in structurally capital-intensive sectors."))

    # Valuation
    if w_pe and w_pe > 40:
        remarks.append(("🟡 PREMIUM VALUATION",
                        f"Portfolio P/E of {w_pe:.1f}x reflects growth premium pricing. "
                        "High-multiple portfolios can underperform significantly during market rotations or rate hikes."))
    elif w_pe and w_pe < 15:
        remarks.append(("🟢 VALUE TILTED",
                        f"Portfolio P/E of {w_pe:.1f}x suggests value-oriented positioning. "
                        "Look for catalysts that could re-rate these holdings to fair value."))

    # Concentration
    top_wt = df["weight_pct"].max()
    if top_wt > 30:
        top_co = df.loc[df["weight_pct"].idxmax(), "name"]
        remarks.append(("🔴 CONCENTRATION RISK",
                        f"{top_co} has a {top_wt:.1f}% allocation — single-stock concentration above 30% "
                        "significantly increases idiosyncratic risk."))

    # Diversification score
    num_sectors = df["sector"].nunique()
    if num_sectors >= 4:
        remarks.append(("🟢 WELL DIVERSIFIED",
                        f"Portfolio spans {num_sectors} GICS sectors, providing meaningful diversification "
                        "against sector-specific shocks."))
    elif num_sectors <= 2:
        remarks.append(("🔴 SECTOR CONCENTRATED",
                        f"Only {num_sectors} sector(s) represented. Consider adding holdings from "
                        "defensive or counter-cyclical sectors to improve resilience."))

    risk_rows = []
    for badge, comment in remarks:
        risk_rows.append([
            Paragraph(f"<b>{badge}</b>",
                      ParagraphStyle("_rb", fontSize=8, textColor=NAVY, fontName="Helvetica-Bold")),
            Paragraph(comment, ParagraphStyle("_rc", fontSize=8, leading=11)),
        ])
    risk_tbl = Table(risk_rows, colWidths=[4.5*cm, 13.5*cm])
    risk_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,-1), LIGHT),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#CFD8DC")),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    S += [risk_tbl, Spacer(1, 0.4*cm)]

    # Portfolio Income Statement Rollup
    S.append(h("AGGREGATE PORTFOLIO INCOME METRICS (Latest Year, Proportional)", sz=10))
    agg_rev = (df["sales"] * df["weight_pct"] / 100).sum()
    agg_np  = (df["net_profit"] * df["weight_pct"] / 100).sum()
    agg_op  = (df["operating_profit"] * df["weight_pct"] / 100).sum()
    agg_items = [
        ("Proportional Revenue",       _fmt(agg_rev, cr=True)),
        ("Proportional Net Profit",    _fmt(agg_np, cr=True)),
        ("Proportional Op. Profit",    _fmt(agg_op, cr=True)),
        ("Wtd. Avg EPS",               _fmt(w_eps)),
    ]
    S += [label_val(agg_items, cols=4), Spacer(1, 0.3*cm)]

    # Footer
    S += [rule(GREY, 0.5),
          Paragraph(
              f"<font size='7' color='grey'>Page 2/2  ·  Nifty100 Portfolio Report  ·  "
              f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}</font>",
              stl["Normal"])]

    doc.build(S)
    logger.info(f"Portfolio report saved: {out}")
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
    sample_tickers = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]
    sample_weights = [25.0, 20.0, 20.0, 20.0, 15.0]
    out = generate_portfolio_report(sample_tickers, sample_weights, portfolio_name="Sample Portfolio")
    print(f"✓ Portfolio report: {out}")
