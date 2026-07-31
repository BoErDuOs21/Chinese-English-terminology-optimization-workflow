"""Upload to object storage node - uploads the generated HTML page and returns a presigned download URL."""
import os
import logging
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk.s3 import S3SyncStorage
from graphs.state import UploadStorageInput, UploadStorageOutput

logger = logging.getLogger(__name__)


def upload_storage_node(state: UploadStorageInput, config: RunnableConfig, runtime: Runtime[Context]) -> UploadStorageOutput:
    """
    title: Upload to Object Storage
    desc: Upload the generated interactive HTML page to object storage and return a presigned download URL
    integrations: 对象存储
    """
    ctx = runtime.context
    local_path = state.local_html_path

    if not local_path:
        raise ValueError("No HTML file path provided for upload.")

    if not os.path.exists(local_path):
        raise FileNotFoundError(f"HTML file not found at: {local_path}")

    # Initialize S3 storage client
    storage = S3SyncStorage(
        endpoint_url=os.getenv("COZE_BUCKET_ENDPOINT_URL"),
        access_key="",
        secret_key="",
        bucket_name=os.getenv("COZE_BUCKET_NAME"),
        region="cn-beijing",
    )

    # Read file content
    with open(local_path, 'rb') as f:
        file_content = f.read()

    # Upload to object storage
    file_key = storage.upload_file(
        file_content=file_content,
        file_name="terminology_comparison.html",
        content_type="text/html; charset=utf-8",
    )

    logger.info(f"HTML file uploaded to storage with key: {file_key}")

    # Generate presigned URL (valid for 24 hours)
    download_url = storage.generate_presigned_url(
        key=file_key,
        expire_time=86400,
    )

    logger.info(f"Presigned URL generated successfully")

    return UploadStorageOutput(download_url=download_url)
