"""
src/reports/tearsheet.py
3-Page PDF Tearsheet — Nifty100 Financial Analysis
===============================================================
Page 1 : Company Profile · KPI Dashboard · Income Statement History
Page 2 : Balance Sheet Trends · Cash Flow Profile · Capital Allocation
Page 3 : Stock Price Summary · CAGR Growth Rates · Peer Comparison · Qualitative Insights
"""
import os
import logging
import sqlite3
from datetime import datetime

import pandas as pd

logger = logging.getLogger("reports.tearsheet")
DB_PATH      = os.getenv("DB_PATH", "data/nifty100.db")
TEARSHEET_DIR = os.path.join("reports", "tearsheets")

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
    logger.warning("reportlab not installed — PDF output disabled")

NAVY  = colors.HexColor("#0A2342") if RL else None
TEAL  = colors.HexColor("#00A896") if RL else None
LIGHT = colors.HexColor("#EEF2F7") if RL else None
GOLD  = colors.HexColor("#F4A261") if RL else None
GREEN = colors.HexColor("#2ECC71") if RL else None
RED   = colors.HexColor("#E74C3C") if RL else None
WHITE = colors.white if RL else None
GREY  = colors.HexColor("#7F8C8D") if RL else None

# ─────────────────────────────────────────────
# DATA LOADER
# ─────────────────────────────────────────────
def _load(ticker: str, db_path: str) -> dict:
    with sqlite3.connect(db_path) as c:
        comp = pd.read_sql("""
            SELECT c.*, c.company_name AS name, c.id AS ticker,
                   s.broad_sector AS sector, s.sub_sector AS industry,
                   s.index_weight_pct, s.market_cap_category,
                   mc.pe_ratio, mc.pb_ratio, mc.dividend_yield_pct,
                   mc.market_cap_crore AS market_cap_cr,
                   mc.enterprise_value_crore AS ev_cr, mc.ev_ebitda
            FROM companies c
            LEFT JOIN sectors   s  ON c.id = s.company_id
            LEFT JOIN market_cap mc ON c.id = mc.company_id
                AND mc.year = (SELECT MAX(year) FROM market_cap)
            WHERE c.id = ?""", c, params=[ticker.upper()])
        if comp.empty:
            raise ValueError(f"Ticker '{ticker}' not found")
        cid = comp.iloc[0]["id"]

        kpi  = pd.read_sql("SELECT * FROM financial_ratios WHERE company_id=? ORDER BY year", c, params=[cid])
        pl   = pd.read_sql("""SELECT year,sales,expenses,operating_profit,opm_percentage,
                               other_income,interest,depreciation,profit_before_tax,
                               tax_percentage,net_profit,eps,dividend_payout
                               FROM profitandloss WHERE company_id=? ORDER BY year""", c, params=[cid])
        bs   = pd.read_sql("""SELECT year,equity_capital,reserves,borrowings,other_liabilities,
                               total_liabilities,fixed_assets,cwip,investments,other_asset,total_assets
                               FROM balancesheet WHERE company_id=? ORDER BY year""", c, params=[cid])
        cf   = pd.read_sql("""SELECT year,operating_activity,investing_activity,
                               financing_activity,net_cash_flow
                               FROM cashflow WHERE company_id=? ORDER BY year""", c, params=[cid])
        mc_h = pd.read_sql("""SELECT year,market_cap_crore,enterprise_value_crore,
                               pe_ratio,pb_ratio,ev_ebitda,dividend_yield_pct
                               FROM market_cap WHERE company_id=? ORDER BY year""", c, params=[cid])
        an   = pd.read_sql("SELECT * FROM analysis WHERE company_id=?", c, params=[cid])
        pc   = pd.read_sql("SELECT pros,cons FROM prosandcons WHERE company_id=?", c, params=[cid])
        sp   = pd.read_sql("""SELECT date,close_price,volume FROM stock_prices
                               WHERE company_id=? ORDER BY date""", c, params=[cid])
        sector = comp.iloc[0].get("sector", "")
        peers = pd.read_sql("""
            SELECT c.id AS ticker, c.company_name AS name,
                   fr.return_on_equity_pct, fr.net_profit_margin_pct,
                   fr.operating_profit_margin_pct, fr.debt_to_equity,
                   fr.interest_coverage, mc.pe_ratio, mc.pb_ratio,
                   mc.market_cap_crore AS market_cap_cr
            FROM companies c
            JOIN financial_ratios fr ON c.id=fr.company_id
            LEFT JOIN sectors s ON c.id=s.company_id
            LEFT JOIN market_cap mc ON c.id=mc.company_id
                AND mc.year=(SELECT MAX(year) FROM market_cap)
            WHERE s.broad_sector=? AND c.id!=?
            ORDER BY mc.market_cap_crore DESC NULLS LAST LIMIT 6""",
            c, params=[sector, ticker.upper()])
        docs = pd.read_sql("SELECT Year,Annual_Report FROM documents WHERE company_id=? ORDER BY Year DESC LIMIT 5",
                           c, params=[cid])

    if "id" in kpi.columns:
        kpi = kpi.drop(columns=["id"])

    return dict(comp=comp.iloc[0].to_dict(), kpi=kpi, pl=pl, bs=bs, cf=cf,
                mc_h=mc_h, an=an, pc=pc, sp=sp, peers=peers, docs=docs,
                ticker=ticker.upper())


def _fmt(v, pct=False, cr=False, x=False, dp=2):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "N/A"
    if pct:  return f"{v:.{dp}f}%"
    if cr:   return f"Rs {v:,.0f} Cr"
    if x:    return f"{v:.{dp}f}x"
    return f"{v:.{dp}f}"

def _chg(old, new):
    """Return coloured YoY change string."""
    try:
        pct = (new - old) / abs(old) * 100
        arrow = "▲" if pct >= 0 else "▼"
        col = "green" if pct >= 0 else "red"
        return f"<font color='{col}'>{arrow} {abs(pct):.1f}%</font>"
    except Exception:
        return "—"


# ─────────────────────────────────────────────
# REPORT BUILDER
# ─────────────────────────────────────────────
def generate_tearsheet(ticker: str, db_path: str = DB_PATH,
                       output_dir: str = TEARSHEET_DIR) -> str:
    if not RL:
        raise RuntimeError("reportlab not installed")
    os.makedirs(output_dir, exist_ok=True)
    d = _load(ticker, db_path)
    comp, kpi, pl, bs, cf, mc_h, an, pc, sp, peers, docs = (
        d["comp"], d["kpi"], d["pl"], d["bs"], d["cf"],
        d["mc_h"], d["an"], d["pc"], d["sp"], d["peers"], d["docs"]
    )
    latest_kpi = kpi.iloc[-1].to_dict() if not kpi.empty else {}
    latest_pl  = pl.iloc[-1].to_dict()  if not pl.empty  else {}
    latest_bs  = bs.iloc[-1].to_dict()  if not bs.empty  else {}
    latest_cf  = cf.iloc[-1].to_dict()  if not cf.empty  else {}

    out = os.path.join(output_dir, f"{ticker.upper()}_tearsheet.pdf")
    doc = SimpleDocTemplate(out, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    S = []

    def h(txt, sz=11, col=NAVY, sp=5, bold=True):
        tag = f"<b>{txt}</b>" if bold else txt
        return Paragraph(tag, ParagraphStyle("_h", fontSize=sz, textColor=col,
                                             spaceAfter=sp, spaceBefore=2))

    def rule(color=NAVY, th=0.8):
        return HRFlowable(width="100%", thickness=th, color=color, spaceAfter=4)

    def label_val(items, cols=4):
        """Render a 2-col label/value grid."""
        per_row = cols // 2
        rows = []
        for i in range(0, len(items), per_row):
            row = []
            for k, v in items[i:i+per_row]:
                row += [
                    Paragraph(f"<b>{k}</b>",
                              ParagraphStyle("_kl", fontSize=7.5, textColor=GREY)),
                    Paragraph(str(v),
                              ParagraphStyle("_kv", fontSize=9, textColor=TEAL, fontName="Helvetica-Bold")),
                ]
            while len(row) < cols:
                row += [Paragraph("", styles["Normal"]), Paragraph("", styles["Normal"])]
            rows.append(row)
        w = [4.5*cm, 3.5*cm] * (cols // 2)
        t = Table(rows, colWidths=w)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), LIGHT),
            ("GRID",          (0,0), (-1,-1), 0.25, colors.HexColor("#CFD8DC")),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ]))
        return t

    def std_table(header, rows, col_widths, hdr_color=NAVY):
        t = Table([header] + rows, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  hdr_color),
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

    # ══════════════════════════════════════════════════
    # PAGE 1 — Company Profile, KPI Dashboard, P&L
    # ══════════════════════════════════════════════════

    # ── Header Banner ──
    banner_left = Paragraph(
        f"<font color='white' size='16'><b>{comp.get('name','')}</b></font><br/>"
        f"<font color='#A8D8EA' size='10'>{ticker}  ·  {comp.get('sector','—')}  ·  {comp.get('market_cap_category','')}</font>",
        ParagraphStyle("_bl", leading=22, leftIndent=4))
    banner_right = Paragraph(
        f"<font color='white' size='9'>"
        f"Industry: {comp.get('industry','—')}<br/>"
        f"Index Weight: {_fmt(comp.get('index_weight_pct'), pct=True)}<br/>"
        f"Market Cap: {_fmt(comp.get('market_cap_cr'), cr=True)}<br/>"
        f"Enterprise Value: {_fmt(comp.get('ev_cr'), cr=True)}"
        f"</font>",
        ParagraphStyle("_br", leading=14, leftIndent=4))
    btbl = Table([[banner_left, banner_right]], colWidths=[11*cm, 7*cm])
    btbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), NAVY),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
    ]))
    S += [btbl, Spacer(1, 0.4*cm)]

    # ── About Company ──
    about = comp.get("about_company", "")
    if about:
        S.append(h("ABOUT THE COMPANY", sz=9, col=TEAL))
        S.append(Paragraph(str(about)[:900],
                           ParagraphStyle("_ab", fontSize=8, leading=12, textColor=colors.HexColor("#2C3E50"))))
        S.append(Spacer(1, 0.3*cm))

    # ── 10-KPI Dashboard ──
    S.append(h("KEY METRICS  —  LATEST YEAR", sz=10))
    kpi_items = [
        ("Return on Equity (ROE)",    _fmt(latest_kpi.get("return_on_equity_pct"), pct=True)),
        ("Net Profit Margin",         _fmt(latest_kpi.get("net_profit_margin_pct"), pct=True)),
        ("Operating Profit Margin",   _fmt(latest_kpi.get("operating_profit_margin_pct"), pct=True)),
        ("Debt / Equity",             _fmt(latest_kpi.get("debt_to_equity"))),
        ("Interest Coverage",         _fmt(latest_kpi.get("interest_coverage"), x=True)),
        ("Free Cash Flow",            _fmt(latest_kpi.get("free_cash_flow_cr"), cr=True)),
        ("Earnings Per Share (EPS)",  _fmt(latest_kpi.get("earnings_per_share"))),
        ("Book Value / Share",        _fmt(latest_kpi.get("book_value_per_share"))),
        ("Asset Turnover",            _fmt(latest_kpi.get("asset_turnover"), x=True)),
        ("Dividend Payout Ratio",     _fmt(latest_kpi.get("dividend_payout_ratio_pct"), pct=True)),
        ("P/E Ratio",                 _fmt(comp.get("pe_ratio"))),
        ("P/B Ratio",                 _fmt(comp.get("pb_ratio"))),
        ("EV/EBITDA",                 _fmt(comp.get("ev_ebitda"), x=True)),
        ("Dividend Yield",            _fmt(comp.get("dividend_yield_pct"), pct=True)),
        ("Book Value (Company ROE)",  _fmt(comp.get("roe_percentage"), pct=True)),
        ("ROCE",                      _fmt(comp.get("roce_percentage"), pct=True)),
    ]
    S += [label_val(kpi_items, cols=4), Spacer(1, 0.4*cm)]

    # ── Income Statement History ──
    S.append(h("INCOME STATEMENT — 10-YEAR TREND  (Rs Crore unless noted)", sz=10))
    if not pl.empty:
        pl_hdr = ["Year", "Revenue", "Expenses", "EBIT (Op.Profit)", "OPM%",
                  "Other Income", "Interest", "Depreciation", "Net Profit", "EPS", "Div Payout%"]
        pl_rows = []
        for _, r in pl.tail(10).iterrows():
            pl_rows.append([
                str(r["year"]),
                _fmt(r["sales"], cr=True),
                _fmt(r["expenses"], cr=True),
                _fmt(r["operating_profit"], cr=True),
                _fmt(r["opm_percentage"], pct=True),
                _fmt(r["other_income"], cr=True),
                _fmt(r["interest"], cr=True),
                _fmt(r["depreciation"], cr=True),
                _fmt(r["net_profit"], cr=True),
                _fmt(r["eps"]),
                _fmt(r["dividend_payout"], pct=True),
            ])
        cw = [2.0*cm, 2.2*cm, 2.2*cm, 2.5*cm, 1.5*cm, 2.0*cm, 1.8*cm, 2.0*cm, 2.2*cm, 1.4*cm, 1.7*cm]
        S.append(std_table(pl_hdr, pl_rows, cw))

    # Page 1 footer
    S += [Spacer(1, 0.3*cm), rule(GREY, 0.5),
          Paragraph(f"<font size='7' color='grey'>Page 1/3  ·  Nifty100 Intelligence Platform  ·  {datetime.now().strftime('%d %b %Y %H:%M')}</font>",
                    styles["Normal"]),
          PageBreak()]

    # ══════════════════════════════════════════════════
    # PAGE 2 — Balance Sheet · Cash Flow · Capital Alloc · Valuation
    # ══════════════════════════════════════════════════
    S += [h(f"{comp.get('name',ticker)}  —  Financial Position & Cash Flows", sz=13),
          rule(), Spacer(1, 0.3*cm)]

    # ── Balance Sheet ──
    S.append(h("BALANCE SHEET — HISTORICAL SUMMARY  (Rs Crore)", sz=10))
    if not bs.empty:
        bs_hdr = ["Year", "Equity Capital", "Reserves", "Borrowings", "Other Liab.",
                  "Total Liab.", "Fixed Assets", "CWIP", "Investments", "Total Assets"]
        bs_rows = []
        for _, r in bs.tail(10).iterrows():
            bs_rows.append([
                str(r["year"]),
                _fmt(r["equity_capital"], cr=True),
                _fmt(r["reserves"], cr=True),
                _fmt(r["borrowings"], cr=True),
                _fmt(r["other_liabilities"], cr=True),
                _fmt(r["total_liabilities"], cr=True),
                _fmt(r["fixed_assets"], cr=True),
                _fmt(r["cwip"], cr=True),
                _fmt(r["investments"], cr=True),
                _fmt(r["total_assets"], cr=True),
            ])
        cw = [1.8*cm, 2.3*cm, 2.3*cm, 2.3*cm, 2.0*cm, 2.0*cm, 2.2*cm, 1.8*cm, 2.1*cm, 2.2*cm]
        S += [std_table(bs_hdr, bs_rows, cw), Spacer(1, 0.4*cm)]

    # ── Balance Sheet Ratios ──
    if not bs.empty and not pl.empty:
        S.append(h("KEY SOLVENCY & EFFICIENCY METRICS  (derived)", sz=10))
        bs_ratio_items = []
        # Debt-to-Asset
        if latest_bs.get("total_assets") and latest_bs.get("borrowings"):
            bs_ratio_items.append(("Debt-to-Asset Ratio",
                                   _fmt(latest_bs["borrowings"] / latest_bs["total_assets"])))
        # Equity ratio
        if latest_bs.get("total_assets") and latest_bs.get("equity_capital") and latest_bs.get("reserves"):
            eq = (latest_bs["equity_capital"] or 0) + (latest_bs["reserves"] or 0)
            bs_ratio_items.append(("Equity Ratio", _fmt(eq / latest_bs["total_assets"])))
        # Capital Employed
        if latest_bs.get("total_assets") and latest_bs.get("other_liabilities"):
            bs_ratio_items.append(("Capital Employed (Rs Cr)",
                                   _fmt((latest_bs["total_assets"] or 0) - (latest_bs["other_liabilities"] or 0), cr=True)))
        if bs_ratio_items:
            S += [label_val(bs_ratio_items, cols=4), Spacer(1, 0.3*cm)]

    # ── Cash Flow Statement ──
    S.append(h("CASH FLOW STATEMENT — HISTORICAL  (Rs Crore)", sz=10))
    if not cf.empty:
        cf_hdr = ["Year", "Operating (CFO)", "Investing (CFI)", "Financing (CFF)", "Net Cash Flow", "CFO/CFI Ratio"]
        cf_rows = []
        for _, r in cf.tail(10).iterrows():
            cfo = r["operating_activity"] or 0
            cfi = r["investing_activity"] or 0
            ratio = _fmt(abs(cfo / cfi)) if cfi and cfi != 0 else "N/A"
            cf_rows.append([
                str(r["year"]),
                _fmt(cfo, cr=True),
                _fmt(cfi, cr=True),
                _fmt(r["financing_activity"], cr=True),
                _fmt(r["net_cash_flow"], cr=True),
                ratio,
            ])
        cw = [2.0*cm, 3.5*cm, 3.5*cm, 3.5*cm, 3.3*cm, 2.2*cm]
        S += [std_table(cf_hdr, cf_rows, cw), Spacer(1, 0.4*cm)]

    # ── Capital Allocation Classification ──
    S.append(h("CAPITAL ALLOCATION PROFILE", sz=10))
    cfo_v = latest_cf.get("operating_activity", 0) or 0
    cfi_v = latest_cf.get("investing_activity", 0) or 0
    cff_v = latest_cf.get("financing_activity", 0) or 0
    sgn = lambda v: "+" if v >= 0 else "-"
    PATTERNS = {
        ("+","-","+"): "Star / Reinvestor — Strong operations, heavy CapEx, but raising external capital",
        ("+","-","-"): "Mature Compounder — Self-funded growth, debt repayment; classic value creator",
        ("+","+","-"): "Divesting Reinvestor — Selling assets AND repaying debt/dividends",
        ("+","+","+"): "Aggressive Expander — Cash inflows from operations AND asset sales AND external funding",
        ("-","-","+"): "Turnaround / Pre-revenue — Burning cash, relying on external capital",
        ("-","+","-"): "Liquidator / Restructuring — Selling assets, reducing liabilities",
        ("-","-","-"): "Cash Destruction — All three negative; severe distress signal",
        ("-","+","+"): "Capital Infused Builder — External + asset sale funded; operations not self-sustaining yet",
    }
    pattern = PATTERNS.get((sgn(cfo_v), sgn(cfi_v), sgn(cff_v)), "Unknown Pattern")
    alloc_text = (
        f"<b>Pattern Classification:</b> {pattern}<br/><br/>"
        f"CFO = {_fmt(cfo_v, cr=True)}  |  CFI = {_fmt(cfi_v, cr=True)}  |  CFF = {_fmt(cff_v, cr=True)}<br/>"
        f"Net Cash Movement = {_fmt(latest_cf.get('net_cash_flow', 0), cr=True)}"
    )
    alloc_tbl = Table([[Paragraph(alloc_text,
                                  ParagraphStyle("_at", fontSize=8.5, leading=13))]], colWidths=[18*cm])
    alloc_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#E8F5E9")),
        ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#A5D6A7")),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ]))
    S += [alloc_tbl, Spacer(1, 0.4*cm)]

    # ── Valuation History ──
    S.append(h("VALUATION MULTIPLES — HISTORICAL", sz=10))
    if not mc_h.empty:
        mc_hdr = ["Year", "Market Cap (Rs Cr)", "Enterprise Value (Rs Cr)", "P/E", "P/B", "EV/EBITDA", "Div Yield %"]
        mc_rows = []
        for _, r in mc_h.tail(8).iterrows():
            mc_rows.append([
                str(r["year"]),
                _fmt(r["market_cap_crore"], cr=True),
                _fmt(r["enterprise_value_crore"], cr=True),
                _fmt(r["pe_ratio"]),
                _fmt(r["pb_ratio"]),
                _fmt(r["ev_ebitda"], x=True),
                _fmt(r["dividend_yield_pct"], pct=True),
            ])
        cw = [2.0*cm, 3.8*cm, 4.0*cm, 2.2*cm, 2.2*cm, 2.5*cm, 2.3*cm]
        S.append(std_table(mc_hdr, mc_rows, cw))

    S += [Spacer(1, 0.3*cm), rule(GREY, 0.5),
          Paragraph(f"<font size='7' color='grey'>Page 2/3  ·  Nifty100 Intelligence Platform  ·  {datetime.now().strftime('%d %b %Y %H:%M')}</font>",
                    styles["Normal"]),
          PageBreak()]

    # ══════════════════════════════════════════════════
    # PAGE 3 — Stock Prices · CAGR · Peer Comparison · Pros/Cons
    # ══════════════════════════════════════════════════
    S += [h(f"{comp.get('name',ticker)}  —  Growth Analytics & Peer Intelligence", sz=13),
          rule(), Spacer(1, 0.3*cm)]

    # ── Stock Price Summary ──
    S.append(h("STOCK PRICE SUMMARY (Historical Trading Data)", sz=10))
    if not sp.empty:
        sp_agg = sp.copy()
        sp_agg["date"] = pd.to_datetime(sp_agg["date"])
        latest_price = sp_agg.iloc[-1]["close_price"]
        high_52w     = sp_agg.tail(252)["close_price"].max() if len(sp_agg) >= 5 else sp_agg["close_price"].max()
        low_52w      = sp_agg.tail(252)["close_price"].min() if len(sp_agg) >= 5 else sp_agg["close_price"].min()
        avg_vol      = sp_agg.tail(60)["volume"].mean()
        price_items  = [
            ("Latest Close Price",   f"Rs {latest_price:,.2f}"),
            ("52-Week High",         f"Rs {high_52w:,.2f}"),
            ("52-Week Low",          f"Rs {low_52w:,.2f}"),
            ("Avg. Daily Volume (60D)", f"{avg_vol:,.0f} shares"),
            ("Price Range (52W)",    f"Rs {low_52w:,.0f} – Rs {high_52w:,.0f}"),
            ("Price vs 52W High",    f"{(latest_price/high_52w - 1)*100:+.1f}%"),
        ]
        S += [label_val(price_items, cols=4), Spacer(1, 0.3*cm)]

        sp_hdr  = ["Date", "Open", "High", "Low", "Close", "Volume"]
        sp_rows = []
        for _, r in sp.tail(10).iterrows():
            sp_rows.append([
                str(r["date"])[:10],
                "N/A", "N/A", "N/A",
                f"Rs {r['close_price']:,.2f}",
                f"{int(r['volume']):,}" if r["volume"] else "N/A",
            ])
        cw = [3.0*cm, 2.8*cm, 2.8*cm, 2.8*cm, 3.0*cm, 3.6*cm]
        S += [std_table(sp_hdr, sp_rows, cw, hdr_color=TEAL), Spacer(1, 0.4*cm)]

    # ── CAGR Growth Rates ──
    S.append(h("COMPOUNDED ANNUAL GROWTH RATES (CAGR)", sz=10))
    if not an.empty:
        an_row = an.iloc[0].to_dict()
        cagr_items = []
        for col, lbl in [
            ("compounded_sales_growth",  "Sales CAGR"),
            ("compounded_profit_growth", "Profit CAGR"),
            ("stock_price_cagr",         "Stock Price CAGR"),
            ("roe",                      "ROE (Analysis)"),
        ]:
            v = an_row.get(col)
            if v is not None and not (isinstance(v, float) and pd.isna(v)):
                cagr_items.append((lbl, _fmt(v, pct=True)))
        if cagr_items:
            S += [label_val(cagr_items, cols=4), Spacer(1, 0.3*cm)]
    else:
        # Derive from P&L
        if len(pl) >= 3:
            def cagr(old, new, yrs):
                try:
                    return ((new/old)**(1/yrs) - 1) * 100
                except Exception:
                    return None
            n = len(pl)
            yrs = min(n-1, 10)
            s_cagr = cagr(pl.iloc[-(yrs+1)]["sales"], pl.iloc[-1]["sales"], yrs)
            p_cagr = cagr(pl.iloc[-(yrs+1)]["net_profit"], pl.iloc[-1]["net_profit"], yrs)
            cagr_items = [
                (f"Sales CAGR ({yrs}Y)", _fmt(s_cagr, pct=True)),
                (f"Profit CAGR ({yrs}Y)", _fmt(p_cagr, pct=True)),
            ]
            S += [label_val(cagr_items, cols=4), Spacer(1, 0.3*cm)]

    # ── Financial Ratios History ──
    S.append(h("FINANCIAL RATIOS — YEAR-ON-YEAR", sz=10))
    if not kpi.empty:
        r_hdr  = ["Year", "ROE%", "NPM%", "OPM%", "D/E", "Int.Cov", "FCF (Cr)", "EPS", "Div Payout%"]
        r_rows = []
        for _, r in kpi.tail(10).iterrows():
            r_rows.append([
                str(r["year"]),
                _fmt(r["return_on_equity_pct"], pct=True),
                _fmt(r["net_profit_margin_pct"], pct=True),
                _fmt(r["operating_profit_margin_pct"], pct=True),
                _fmt(r["debt_to_equity"]),
                _fmt(r["interest_coverage"], x=True),
                _fmt(r["free_cash_flow_cr"], cr=True),
                _fmt(r["earnings_per_share"]),
                _fmt(r["dividend_payout_ratio_pct"], pct=True),
            ])
        cw = [2.2*cm, 2.0*cm, 2.0*cm, 2.0*cm, 1.8*cm, 2.0*cm, 2.5*cm, 2.0*cm, 2.5*cm]
        S += [std_table(r_hdr, r_rows, cw), Spacer(1, 0.4*cm)]

    # ── Peer Comparison ──
    S.append(h(f"PEER COMPARISON  —  {comp.get('sector','').upper()}", sz=10))
    if not peers.empty:
        p_hdr  = ["Ticker", "Company Name", "Mkt Cap (Cr)", "ROE%", "NPM%", "OPM%", "D/E", "Int.Cov", "P/E", "P/B"]
        p_rows = []
        for _, r in peers.iterrows():
            p_rows.append([
                str(r["ticker"]),
                str(r["name"])[:28],
                _fmt(r["market_cap_cr"], cr=True),
                _fmt(r["return_on_equity_pct"], pct=True),
                _fmt(r["net_profit_margin_pct"], pct=True),
                _fmt(r["operating_profit_margin_pct"], pct=True),
                _fmt(r["debt_to_equity"]),
                _fmt(r["interest_coverage"], x=True),
                _fmt(r["pe_ratio"]),
                _fmt(r["pb_ratio"]),
            ])
        cw = [2.2*cm, 4.5*cm, 2.8*cm, 1.6*cm, 1.6*cm, 1.6*cm, 1.5*cm, 1.8*cm, 1.5*cm, 1.5*cm]
        S += [std_table(p_hdr, p_rows, cw, hdr_color=TEAL), Spacer(1, 0.4*cm)]

    # ── Pros & Cons ──
    S.append(h("QUALITATIVE ANALYST INSIGHTS", sz=10))
    pros_list, cons_list = [], []
    if not pc.empty:
        for _, r in pc.iterrows():
            if r["pros"]: pros_list.append(r["pros"])
            if r["cons"]: cons_list.append(r["cons"])

    # Dynamic rule-based fallbacks
    roe  = latest_kpi.get("return_on_equity_pct") or 0
    npm  = latest_kpi.get("net_profit_margin_pct") or 0
    dte  = latest_kpi.get("debt_to_equity") or 0
    icr  = latest_kpi.get("interest_coverage") or 999
    fcf  = latest_kpi.get("free_cash_flow_cr") or 0
    opm  = latest_kpi.get("operating_profit_margin_pct") or 0

    if not pros_list:
        if roe > 20:  pros_list.append(f"Exceptional capital efficiency with ROE of {roe:.1f}%, well above the 15% benchmark.")
        if npm > 15:  pros_list.append(f"Industry-leading profitability with net margins of {npm:.1f}%.")
        if opm > 20:  pros_list.append(f"Strong operating leverage demonstrated by OPM of {opm:.1f}%.")
        if dte < 0.3: pros_list.append("Nearly debt-free balance sheet offering significant financial flexibility.")
        elif dte < 1: pros_list.append(f"Conservative leverage profile with D/E of {dte:.2f}x — well within safe zone.")
        if icr > 10:  pros_list.append(f"Excellent interest coverage of {icr:.1f}x ensures debt servicing comfort.")
        if fcf > 0:   pros_list.append(f"Positive free cash flow of {_fmt(fcf, cr=True)} supports shareholder returns & reinvestment.")
    if not cons_list:
        if dte > 1.5: cons_list.append(f"Elevated leverage at {dte:.2f}x D/E may constrain financial flexibility.")
        if icr < 3:   cons_list.append(f"Low interest coverage of {icr:.1f}x raises solvency concerns in a rising rate environment.")
        if fcf < 0:   cons_list.append(f"Negative FCF of {_fmt(fcf, cr=True)} suggests heavy CapEx cycle or operational inefficiencies.")
        if npm < 5:   cons_list.append(f"Thin net margins of {npm:.1f}% leave limited buffer against input cost shocks.")

    if not pros_list: pros_list.append("Consistent operational track record aligned with sector benchmarks.")
    if not cons_list: cons_list.append("Premium valuation multiples may limit near-term upside potential.")

    max_len = max(len(pros_list), len(cons_list))
    pc_rows_data = []
    for i in range(max_len):
        p = Paragraph(f"<font color='#1B5E20'>✔ {pros_list[i]}</font>",
                      ParagraphStyle("_pr", fontSize=8, leading=11)) if i < len(pros_list) \
            else Paragraph("", styles["Normal"])
        cn = Paragraph(f"<font color='#B71C1C'>✖ {cons_list[i]}</font>",
                       ParagraphStyle("_cn", fontSize=8, leading=11)) if i < len(cons_list) \
            else Paragraph("", styles["Normal"])
        pc_rows_data.append([p, cn])

    pc_tbl = Table(
        [[Paragraph("<b>STRENGTHS / PROS</b>", ParagraphStyle("_ph", fontSize=8.5, textColor=colors.HexColor("#1B5E20"), fontName="Helvetica-Bold")),
          Paragraph("<b>RISKS / CONS</b>", ParagraphStyle("_ch", fontSize=8.5, textColor=colors.HexColor("#B71C1C"), fontName="Helvetica-Bold"))]]
        + pc_rows_data,
        colWidths=[9*cm, 9*cm])
    pc_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,0), colors.HexColor("#E8F5E9")),
        ("BACKGROUND",    (1,0), (1,0), colors.HexColor("#FFEBEE")),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.lightgrey),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    S += [pc_tbl, Spacer(1, 0.4*cm)]

    # ── Annual Reports Directory ──
    if not docs.empty:
        S.append(h("ANNUAL REPORTS DIRECTORY", sz=10))
        doc_hdr  = ["Financial Year", "Annual Report Reference"]
        doc_rows = [[str(r["Year"]), str(r["Annual_Report"])[:80]] for _, r in docs.iterrows()]
        cw = [4*cm, 14*cm]
        S.append(std_table(doc_hdr, doc_rows, cw, hdr_color=GOLD))
        S.append(Spacer(1, 0.3*cm))

    # Page 3 footer
    S += [rule(GREY, 0.5),
          Paragraph(
              f"<font size='7' color='grey'>Page 3/3  ·  Nifty100 Financial Analysis  ·  "
              f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}</font>",
              styles["Normal"])]

    doc.build(S)
    logger.info(f"3-Page tearsheet saved: {out}")
    return out


def generate_all_tearsheets(db_path=DB_PATH, output_dir=TEARSHEET_DIR) -> list:
    with sqlite3.connect(db_path) as conn:
        tickers = pd.read_sql("SELECT id FROM companies", conn)["id"].tolist()
    paths = []
    for t in tickers:
        try:
            paths.append(generate_tearsheet(t, db_path, output_dir))
        except Exception as e:
            logger.error(f"Tearsheet failed for {t}: {e}")
    logger.info(f"Generated {len(paths)}/{len(tickers)} tearsheets.")
    return paths


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
    t = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE"
    out = generate_tearsheet(t)
    print(f"✓ Tearsheet: {out}")
