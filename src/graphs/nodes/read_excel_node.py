"""Read Excel node - parses the uploaded Excel file into structured terminology data."""
import os
import logging
import pandas as pd
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from utils.file.file import File, FileOps
from graphs.state import ReadExcelInput, ReadExcelOutput

logger = logging.getLogger(__name__)


def read_excel_node(state: ReadExcelInput, config: RunnableConfig, runtime: Runtime[Context]) -> ReadExcelOutput:
    """
    title: Read Excel File
    desc: Parse the uploaded bilingual terminology Excel file into structured data (Chinese, English, Remark columns)
    """
    ctx = runtime.context
    file_obj = state.file

    if file_obj is None:
        raise ValueError("No file provided. Please upload an Excel file.")

    # Download file to local path for pandas to read
    local_path = FileOps.save_to_local(file_obj, "input_terminology.xlsx")
    logger.info(f"Excel file saved to local path: {local_path}")

    # Read ALL sheets from Excel with pandas
    try:
        if local_path.endswith('.csv'):
            sheets_dict: dict = {"Sheet1": pd.read_csv(local_path)}
        else:
            # sheet_name=None reads ALL sheets, returns {sheet_name: DataFrame}
            sheets_dict = pd.read_excel(local_path, sheet_name=None)
    except Exception as e:
        raise ValueError(f"Failed to read Excel file: {e}")

    if not sheets_dict:
        raise ValueError("The Excel file has no sheets. Please provide a valid file.")

    logger.info(f"Detected {len(sheets_dict)} sheet(s): {list(sheets_dict.keys())}")

    # Helper: normalize column names for a single DataFrame
    def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        col_mapping: dict = {}
        for col in df.columns:
            col_stripped = str(col).strip()
            col_lower = col_stripped.lower()
            if col_stripped in ['中文', 'chinese', 'Chinese']:
                col_mapping[col] = 'chinese'
            elif col_lower in ['english', '英文']:
                col_mapping[col] = 'english'
            elif col_stripped in ['备注', 'remark', 'Remark', '备注说明']:
                col_mapping[col] = 'remark'
        return df.rename(columns=col_mapping)

    # Process each sheet and collect all terms
    terms_data: list = []
    valid_sheet_count = 0

    for sheet_name, df in sheets_dict.items():
        sheet_name_str = str(sheet_name).strip()

        if df.empty:
            logger.info(f"Sheet '{sheet_name_str}' is empty, skipping")
            continue

        df = _normalize_columns(df)

        # Validate required columns exist in this sheet
        if 'chinese' not in df.columns or 'english' not in df.columns:
            logger.warning(
                f"Sheet '{sheet_name_str}' missing required columns "
                f"(found: {list(df.columns)}), skipping"
            )
            continue

        # Ensure 'remark' column exists
        if 'remark' not in df.columns:
            df['remark'] = ''

        valid_sheet_count += 1
        sheet_row_count = 0

        for _, row in df.iterrows():
            chinese_val = str(row.get('chinese', '')).strip()
            english_val = str(row.get('english', '')).strip()
            remark_val = str(row.get('remark', '')).strip()

            # Skip completely empty rows
            if not chinese_val and not english_val:
                continue

            terms_data.append({
                "chinese": chinese_val if chinese_val != 'nan' else '',
                "english": english_val if english_val != 'nan' else '',
                "remark": remark_val if remark_val != 'nan' else '',
                "sheet": sheet_name_str
            })
            sheet_row_count += 1

        logger.info(f"Sheet '{sheet_name_str}': extracted {sheet_row_count} terms")

    if valid_sheet_count == 0:
        raise ValueError(
            "No sheet in the Excel file contains the required columns "
            "('中文'/'Chinese' and 'English'). Please check the file format."
        )

    logger.info(
        f"Parsed {len(terms_data)} terminology records "
        f"from {valid_sheet_count} sheet(s)"
    )

    return ReadExcelOutput(terms_data=terms_data)
