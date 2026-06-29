// web/scripts/export-data.js
// Run locally: node scripts/export-data.js
// Exports all SQLite data to /public/data/*.json for static Vercel deployment

const Database = require('better-sqlite3');
const fs = require('fs');
const path = require('path');

const DB_PATH = path.resolve(__dirname, '../../data/nifty100.db');
const OUT_DIR  = path.resolve(__dirname, '../public/data');

fs.mkdirSync(OUT_DIR, { recursive: true });

const db = new Database(DB_PATH, { readonly: true });

function save(name, data) {
  const file = path.join(OUT_DIR, `${name}.json`);
  fs.writeFileSync(file, JSON.stringify(data));
  console.log(`✓ ${name}.json — ${data.length ?? Object.keys(data).length} records`);
}

// 1. Companies + sectors + latest market_cap joined
const companies = db.prepare(`
  SELECT c.id, c.company_name, c.about_company,
         c.face_value, c.book_value, c.roce_percentage, c.roe_percentage,
         c.website, c.nse_profile, c.bse_profile,
         s.broad_sector AS sector, s.sub_sector AS industry,
         s.index_weight_pct, s.market_cap_category,
         mc.pe_ratio, mc.pb_ratio, mc.dividend_yield_pct,
         mc.market_cap_crore AS market_cap_cr,
         mc.enterprise_value_crore AS ev_cr, mc.ev_ebitda
  FROM companies c
  LEFT JOIN sectors s ON c.id = s.company_id
  LEFT JOIN market_cap mc ON c.id = mc.company_id
    AND mc.year = (SELECT MAX(year) FROM market_cap)
  ORDER BY mc.market_cap_crore DESC NULLS LAST
`).all();
save('companies', companies);

// 2. Financial ratios — latest per company
const ratios = db.prepare(`
  SELECT fr.*
  FROM financial_ratios fr
  WHERE fr.year = (SELECT MAX(year) FROM financial_ratios WHERE company_id = fr.company_id)
`).all();
save('ratios_latest', ratios);

// 3. P&L — all years
const pl = db.prepare(`SELECT * FROM profitandloss ORDER BY company_id, year`).all();
save('pl', pl);

// 4. Balance sheet — all years
const bs = db.prepare(`SELECT * FROM balancesheet ORDER BY company_id, year`).all();
save('bs', bs);

// 5. Cash flow — all years
const cf = db.prepare(`SELECT * FROM cashflow ORDER BY company_id, year`).all();
save('cf', cf);

// 6. Market cap history
const mc = db.prepare(`SELECT * FROM market_cap ORDER BY company_id, year`).all();
save('market_cap', mc);

// 7. Stock prices — latest 60 per company
const sp = db.prepare(`
  SELECT sp.* FROM stock_prices sp
  WHERE sp.date >= (
    SELECT date(MAX(date), '-90 days') FROM stock_prices WHERE company_id = sp.company_id
  )
  ORDER BY sp.company_id, sp.date
`).all();
save('stock_prices', sp);

// 8. Analysis / CAGR
const analysis = db.prepare(`SELECT * FROM analysis`).all();
save('analysis', analysis);

// 9. Pros and cons
const proscons = db.prepare(`SELECT * FROM prosandcons`).all();
save('proscons', proscons);

// 10. Annual report documents
const docs = db.prepare(`SELECT * FROM documents ORDER BY company_id, Year DESC`).all();
save('documents', docs);

// 11. Peer groups
const peers = db.prepare(`SELECT * FROM peer_groups`).all();
save('peer_groups', peers);

db.close();
console.log('\n✅ All data exported to public/data/');
