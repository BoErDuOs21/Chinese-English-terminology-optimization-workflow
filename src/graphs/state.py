"""State definitions for the terminology simplification workflow."""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from utils.file.file import File


class GlobalState(BaseModel):
    """Global state for the terminology simplification workflow."""
    file: Optional[File] = Field(default=None, description="Uploaded Excel file")
    terms_data: List[Dict] = Field(default=[], description="Parsed terminology data from Excel")
    simplified_data: List[Dict] = Field(default=[], description="Simplified terminology comparison data")
    local_html_path: str = Field(default="", description="Local path of the generated interactive HTML page")
    statistics: Dict = Field(default={}, description="Statistics: total, modified, unchanged counts")
    download_url: str = Field(default="", description="Presigned download URL for the HTML page")


class GraphInput(BaseModel):
    """Workflow input definition."""
    file: File = Field(..., description="Uploaded bilingual terminology Excel file (Chinese, English, Remark)")


class GraphOutput(BaseModel):
    """Workflow output definition."""
    download_url: str = Field(..., description="Download URL for the interactive comparison HTML page")
    statistics: Dict = Field(..., description="Summary statistics: total_terms, modified_count, unchanged_count")


# --- Node Input/Output Definitions ---

class ReadExcelInput(BaseModel):
    """Input for the read Excel node."""
    file: File = Field(..., description="Uploaded Excel file to parse")


class ReadExcelOutput(BaseModel):
    """Output for the read Excel node."""
    terms_data: List[Dict] = Field(..., description="List of parsed terminology records with chinese, english, remark fields")


class SimplifyTermsInput(BaseModel):
    """Input for the LLM terminology simplification node."""
    terms_data: List[Dict] = Field(..., description="List of terminology records to simplify")


class SimplifyTermsOutput(BaseModel):
    """Output for the LLM terminology simplification node."""
    simplified_data: List[Dict] = Field(..., description="List of comparison records with original/simplified English and reasons")
    statistics: Dict = Field(..., description="Statistics: total_terms, modified_count, unchanged_count")


class GenerateHtmlInput(BaseModel):
    """Input for the generate interactive HTML page node."""
    simplified_data: List[Dict] = Field(..., description="Simplified terminology comparison data")
    statistics: Dict = Field(..., description="Summary statistics for the report header")


class GenerateHtmlOutput(BaseModel):
    """Output for the generate interactive HTML page node."""
    local_html_path: str = Field(..., description="Local file path of the generated interactive HTML page")


class UploadStorageInput(BaseModel):
    """Input for the upload to object storage node."""
    local_html_path: str = Field(..., description="Local file path of the HTML page to upload")


class UploadStorageOutput(BaseModel):
    """Output for the upload to object storage node."""
    download_url: str = Field(..., description="Presigned download URL for the uploaded HTML page")
