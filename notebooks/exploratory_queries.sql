-- Nifty 100 Financial Intelligence Platform - Sprint 1 Exploratory Queries
-- Run these queries on data/nifty100.db to inspect coverage and data quality.

-- Query 1: Total row counts for all 12 tables in the database
SELECT 'companies' AS table_name, COUNT(*) AS row_count FROM companies
UNION ALL
SELECT 'profitandloss', COUNT(*) FROM profitandloss
UNION ALL
SELECT 'balancesheet', COUNT(*) FROM balancesheet
UNION ALL
SELECT 'cashflow', COUNT(*) FROM cashflow
UNION ALL
SELECT 'analysis', COUNT(*) FROM analysis
UNION ALL
SELECT 'documents', COUNT(*) FROM documents
UNION ALL
SELECT 'prosandcons', COUNT(*) FROM prosandcons
UNION ALL
SELECT 'sectors', COUNT(*) FROM sectors
UNION ALL
SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL
SELECT 'market_cap', COUNT(*) FROM market_cap
UNION ALL
SELECT 'financial_ratios', COUNT(*) FROM financial_ratios
UNION ALL
SELECT 'peer_groups', COUNT(*) FROM peer_groups;

-- Query 2: Number of distinct companies in the master reference table
SELECT COUNT(DISTINCT id) AS total_companies FROM companies;

-- Query 3: Early, late, and count of years coverage per company in time-series P&L
SELECT 
    company_id,
    MIN(year) AS earliest_year,
    MAX(year) AS latest_year,
    COUNT(year) AS total_years
FROM profitandloss
GROUP BY company_id
ORDER BY total_years ASC, company_id LIMIT 10;

-- Query 4: Check for missing critical fields (NULL counts) in profit and loss statements
SELECT 
    COUNT(*) AS total_rows,
    SUM(CASE WHEN sales IS NULL THEN 1 ELSE 0 END) AS missing_sales,
    SUM(CASE WHEN expenses IS NULL THEN 1 ELSE 0 END) AS missing_expenses,
    SUM(CASE WHEN operating_profit IS NULL THEN 1 ELSE 0 END) AS missing_operating_profit,
    SUM(CASE WHEN opm_percentage IS NULL THEN 1 ELSE 0 END) AS missing_opm_pct,
    SUM(CASE WHEN net_profit IS NULL THEN 1 ELSE 0 END) AS missing_net_profit,
    SUM(CASE WHEN eps IS NULL THEN 1 ELSE 0 END) AS missing_eps
FROM profitandloss;

-- Query 5: Distribution of companies across broad macro sectors
SELECT 
    broad_sector, 
    COUNT(*) AS company_count,
    ROUND(SUM(index_weight_pct), 2) AS total_index_weight
FROM sectors
GROUP BY broad_sector
ORDER BY company_count DESC;

-- Query 6: Database-level Foreign Key integrity verification (Returns zero rows if clean)
PRAGMA foreign_key_check;

-- Query 7: Distribution of stock price records (date count) per company
SELECT 
    company_id,
    COUNT(date) AS price_records_count,
    MIN(date) AS price_start_date,
    MAX(date) AS price_end_date
FROM stock_prices
GROUP BY company_id
ORDER BY price_records_count ASC LIMIT 5;

-- Query 8: Top 5 companies by sales in the latest available fiscal year (2024-03)
SELECT 
    p.company_id,
    c.company_name,
    p.sales
FROM profitandloss p
JOIN companies c ON p.company_id = c.id
WHERE p.year = '2024-03'
ORDER BY p.sales DESC
LIMIT 5;

-- Query 9: Count of annual reports (documents) available per calendar year
SELECT 
    Year,
    COUNT(*) AS annual_reports_count
FROM documents
GROUP BY Year
ORDER BY Year DESC;

-- Query 10: Identify any companies in the master database that do not have a peer group mapping
SELECT 
    c.id, 
    c.company_name 
FROM companies c
LEFT JOIN peer_groups p ON c.id = p.company_id
WHERE p.peer_group_name IS NULL;
