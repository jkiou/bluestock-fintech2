import os
import logging
import pandas as pd
from src.etl.normaliser import normalize_ticker, normalize_year

logger = logging.getLogger("etl.loader")

def load_companies(file_path: str) -> pd.DataFrame:
    """
    Loads companies.xlsx.
    header=1: Row 0 is metadata, Row 1 contains actual headers.
    """
    logger.info(f"Loading companies from {file_path}")
    df = pd.read_excel(file_path, header=1)
    
    # Normalize ticker (id)
    df["id"] = df["id"].apply(normalize_ticker)
    
    # Strip whitespace/newlines from company name
    if "company_name" in df.columns:
        df["company_name"] = df["company_name"].astype(str).str.replace(r"\n", " ", regex=True).str.strip()
        
    return df

def load_profit_loss(file_path: str) -> pd.DataFrame:
    """
    Loads profitandloss.xlsx.
    header=1: Row 0 is metadata, Row 1 contains actual headers.
    """
    logger.info(f"Loading profit and loss from {file_path}")
    df = pd.read_excel(file_path, header=1)
    
    # Normalize fields
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    df["year"] = df["year"].apply(normalize_year)
    
    return df

def load_balancesheet(file_path: str) -> pd.DataFrame:
    """
    Loads balancesheet.xlsx.
    header=1: Row 0 is metadata, Row 1 contains actual headers.
    """
    logger.info(f"Loading balance sheet from {file_path}")
    df = pd.read_excel(file_path, header=1)
    
    # Normalize fields
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    df["year"] = df["year"].apply(normalize_year)
    
    return df

def load_cashflow(file_path: str) -> pd.DataFrame:
    """
    Loads cashflow.xlsx.
    header=1: Row 0 is metadata, Row 1 contains actual headers.
    """
    logger.info(f"Loading cash flow from {file_path}")
    df = pd.read_excel(file_path, header=1)
    
    # Normalize fields
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    df["year"] = df["year"].apply(normalize_year)
    
    return df

def load_analysis(file_path: str) -> pd.DataFrame:
    """
    Loads analysis.xlsx.
    header=1: Row 0 is metadata, Row 1 contains actual headers.
    """
    logger.info(f"Loading analysis from {file_path}")
    df = pd.read_excel(file_path, header=1)
    
    # Normalize fields
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    
    return df

def load_documents(file_path: str) -> pd.DataFrame:
    """
    Loads documents.xlsx.
    header=1: Row 0 is metadata, Row 1 contains actual headers.
    """
    logger.info(f"Loading documents from {file_path}")
    df = pd.read_excel(file_path, header=1)
    
    # Normalize fields
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    
    # Year in documents is capitalized 'Year' and should be cast to integer
    if "Year" in df.columns:
        # Fill NA, then convert to int
        df["Year"] = pd.to_numeric(df["Year"], errors='coerce').fillna(0).astype(int)
        
    return df

def load_prosandcons(file_path: str) -> pd.DataFrame:
    """
    Loads prosandcons.xlsx.
    header=1: Row 0 is metadata, Row 1 contains actual headers.
    """
    logger.info(f"Loading pros and cons from {file_path}")
    df = pd.read_excel(file_path, header=1)
    
    # Normalize fields
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    
    return df

def load_all_core(raw_data_dir: str) -> dict:
    """
    Loads all 7 core files from the raw data directory and returns a dictionary of DataFrames.
    """
    return {
        "companies": load_companies(os.path.join(raw_data_dir, "companies.xlsx")),
        "profitandloss": load_profit_loss(os.path.join(raw_data_dir, "profitandloss.xlsx")),
        "balancesheet": load_balancesheet(os.path.join(raw_data_dir, "balancesheet.xlsx")),
        "cashflow": load_cashflow(os.path.join(raw_data_dir, "cashflow.xlsx")),
        "analysis": load_analysis(os.path.join(raw_data_dir, "analysis.xlsx")),
        "documents": load_documents(os.path.join(raw_data_dir, "documents.xlsx")),
        "prosandcons": load_prosandcons(os.path.join(raw_data_dir, "prosandcons.xlsx")),
    }

if __name__ == "__main__":
    # Test script execution
    logging.basicConfig(level=logging.INFO)
    raw_dir = "data/raw"
    try:
        dfs = load_all_core(raw_dir)
        for name, df in dfs.items():
            print(f"Successfully loaded {name}: shape={df.shape}")
    except Exception as e:
        logger.error(f"Error loading core datasets: {e}", exc_info=True)
