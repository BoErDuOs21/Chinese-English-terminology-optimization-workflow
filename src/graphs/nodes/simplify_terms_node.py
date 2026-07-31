"""Simplify terms node - uses LLM to replace obscure English words with simpler alternatives.
Supports batch processing for large datasets to avoid token limits."""
import os
import re
import json
import logging
import math
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from langchain_core.messages import SystemMessage, HumanMessage
from graphs.state import SimplifyTermsInput, SimplifyTermsOutput

logger = logging.getLogger(__name__)

# Max terms per LLM batch to avoid token truncation
BATCH_SIZE = 30


def _get_text_content(content: Any) -> str:
    """Safely extract text content from LLM response."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        if content and isinstance(content[0], str):
            return " ".join(content)
        else:
            text_parts: List[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return " ".join(text_parts)
    return str(content)


def _extract_json_array(text: str) -> List[Dict]:
    """Extract and parse JSON array from LLM response text.
    Handles markdown code blocks, extra text, etc."""
    # Strategy 1: Try direct parse first (fastest)
    stripped = text.strip()
    if stripped.startswith('['):
        try:
            result = json.loads(stripped)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 2: Strip markdown code blocks
    code_block_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', stripped)
    if code_block_match:
        try:
            result = json.loads(code_block_match.group(1).strip())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 3: Regex find JSON array
    json_match = re.search(r'\[[\s\S]*\]', stripped)
    if json_match:
        try:
            result = json.loads(json_match.group())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 4: Try to fix truncated JSON (common with large responses)
    # Find the last complete object in the array
    if '[' in stripped:
        start_idx = stripped.index('[')
        truncated = stripped[start_idx:]
        # Try progressively shorter substrings ending at last '}'
        while '}' in truncated:
            last_brace = truncated.rfind('}')
            candidate = truncated[:last_brace + 1] + ']'
            try:
                result = json.loads(candidate)
                if isinstance(result, list):
                    logger.info(f"Recovered {len(result)} items from truncated JSON")
                    return result
            except json.JSONDecodeError:
                pass
            truncated = truncated[:last_brace]

    return []


def _process_batch(
    client: LLMClient,
    sp: str,
    up_tpl_str: str,
    llm_config: Dict[str, Any],
    batch: List[Dict],
    batch_idx: int,
    total_batches: int
) -> List[Dict]:
    """Process a single batch of terms through the LLM with retry on parse failure."""
    logger.info(f"Processing batch {batch_idx + 1}/{total_batches} ({len(batch)} terms)")

    terms_json_str = json.dumps(batch, ensure_ascii=False)
    up_tpl = Template(up_tpl_str)
    up_rendered = up_tpl.render(terms_data=terms_json_str)

    messages = [
        SystemMessage(content=sp),
        HumanMessage(content=up_rendered)
    ]

    max_retries = 2
    content_str = ""

    for attempt in range(max_retries):
        # Use stream() and collect chunks to satisfy WorkflowStreamRunner's streaming expectation
        chunks = []
        for chunk in client.stream(
            messages=messages,
            model=llm_config.get("model", "doubao-seed-2-0-lite-260215"),
            temperature=llm_config.get("temperature", 0.0),
            top_p=llm_config.get("top_p", 0.7),
            max_completion_tokens=llm_config.get("max_completion_tokens", 16384),
            thinking=llm_config.get("thinking", "disabled")
        ):
            if hasattr(chunk, 'content') and chunk.content:
                chunks.append(chunk.content)
        
        # Combine all chunks
        content_str = "".join(chunks)
        logger.info(f"Batch {batch_idx + 1} (attempt {attempt + 1}) response length: {len(content_str)} chars")

        results = _extract_json_array(content_str)
        if results:
            break

        if attempt < max_retries - 1:
            logger.warning(f"Batch {batch_idx + 1} attempt {attempt + 1} failed to parse JSON, retrying...")

    if not results:
        logger.warning(f"Batch {batch_idx + 1}: All {max_retries} attempts failed. First 300 chars: {content_str[:300]}")
        # Return fallback results for this batch
        fallback: List[Dict] = []
        for term in batch:
            fallback.append({
                "chinese": term.get("chinese", ""),
                "original_english": term.get("english", ""),
                "simplified_english": term.get("english", ""),
                "is_modified": False,
                "reason": "LLM response parsing failed, kept original",
                "remark": term.get("remark", ""),
                "remark_en": term.get("remark", ""),
                "sheet": term.get("sheet", "")
            })
        return fallback

    # Map LLM results back with original data using chinese field matching
    # Build lookup from input batch by chinese term
    batch_lookup: Dict[str, Dict] = {}
    for term in batch:
        key = term.get("chinese", "").strip()
        if key:
            batch_lookup[key] = term
    
    # Track which input terms were processed by LLM
    processed_chinese: set = set()
    
    batch_results: List[Dict] = []
    for item in results:
        if not isinstance(item, dict):
            continue

        item_chinese = str(item.get("chinese", "")).strip()
        original_english = str(item.get("original_english", "")).strip()
        simplified_english = str(item.get("simplified_english", "")).strip()
        is_modified = bool(item.get("is_modified", False))
        reason = str(item.get("reason", "")).strip()
        remark_en = str(item.get("remark_en", "")).strip()

        # Match by chinese field
        matched = batch_lookup.get(item_chinese)
        if matched:
            chinese = matched.get("chinese", "")
            remark = matched.get("remark", "")
            sheet = matched.get("sheet", "")
            processed_chinese.add(chinese)
        else:
            # LLM returned a term not in our batch - use what we can
            chinese = item_chinese
            remark = ""
            sheet = ""

        if not simplified_english:
            simplified_english = original_english
            is_modified = False

        if not remark_en:
            remark_en = remark

        batch_results.append({
            "chinese": chinese,
            "original_english": original_english,
            "simplified_english": simplified_english,
            "is_modified": is_modified,
            "reason": reason,
            "remark": remark,
            "remark_en": remark_en,
            "sheet": sheet
        })

    # Add any input terms that LLM did not process
    for key, term in batch_lookup.items():
        if key not in processed_chinese:
            batch_results.append({
                "chinese": term.get("chinese", ""),
                "original_english": term.get("english", ""),
                "simplified_english": term.get("english", ""),
                "is_modified": False,
                "reason": "LLM did not return this term, kept original",
                "remark": term.get("remark", ""),
                "remark_en": term.get("remark", ""),
                "sheet": term.get("sheet", "")
            })

    return batch_results


def simplify_terms_node(state: SimplifyTermsInput, config: RunnableConfig, runtime: Runtime[Context]) -> SimplifyTermsOutput:
    """
    title: Simplify English Terms
    desc: Use LLM to analyze each English term and replace obscure words with simpler, high-frequency alternatives for Southeast Asian non-native English speakers. Supports batch processing for large datasets.
    integrations: 大语言模型
    """
    ctx = runtime.context
    terms_data = state.terms_data

    if not terms_data:
        return SimplifyTermsOutput(
            simplified_data=[],
            statistics={"total_terms": 0, "modified_count": 0, "unchanged_count": 0}
        )

    # Load LLM configurations from metadata
    cfg_file = os.path.join(
        os.getenv("COZE_WORKSPACE_PATH", ""),
        config['metadata']['llm_cfg']
    )
    with open(cfg_file, 'r', encoding='utf-8') as f:
        llm_cfg = json.load(f)

    llm_config = llm_cfg.get("config", {})
    sp = llm_cfg.get("sp", "")
    up_tpl_str = llm_cfg.get("up", "")

    # Initialize LLM client
    client = LLMClient(ctx=ctx)

    # Split into batches to avoid token limit issues
    total_terms = len(terms_data)
    total_batches = math.ceil(total_terms / BATCH_SIZE)
    logger.info(f"Total terms: {total_terms}, processing in {total_batches} batch(es) of {BATCH_SIZE}")

    all_results: List[Dict] = []

    # Prepare all batches
    batches: List[List[Dict]] = []
    for batch_idx in range(total_batches):
        start_idx = batch_idx * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, total_terms)
        batches.append(terms_data[start_idx:end_idx])

    # Process batches in parallel (up to 3 concurrent LLM calls)
    max_workers = min(3, total_batches)
    logger.info(f"Processing {total_batches} batch(es) with {max_workers} parallel workers")

    # Use dict to preserve batch order: {batch_idx: results}
    batch_results_map: Dict[int, List[Dict]] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {}
        for batch_idx, batch in enumerate(batches):
            future = executor.submit(
                _process_batch,
                client=client,
                sp=sp,
                up_tpl_str=up_tpl_str,
                llm_config=llm_config,
                batch=batch,
                batch_idx=batch_idx,
                total_batches=total_batches
            )
            future_to_idx[future] = batch_idx

        for future in as_completed(future_to_idx):
            batch_idx = future_to_idx[future]
            try:
                batch_results_map[batch_idx] = future.result()
            except Exception as e:
                logger.error(f"Batch {batch_idx + 1} failed with error: {e}")
                # Fallback: keep originals for this batch
                fallback: List[Dict] = []
                for term in batches[batch_idx]:
                    fallback.append({
                        "chinese": term.get("chinese", ""),
                        "original_english": term.get("english", ""),
                        "simplified_english": term.get("english", ""),
                        "is_modified": False,
                        "reason": f"Batch processing error: {str(e)[:100]}",
                        "remark": term.get("remark", ""),
                        "remark_en": term.get("remark", ""),
                        "sheet": term.get("sheet", "")
                    })
                batch_results_map[batch_idx] = fallback

    # Merge results in original batch order
    for batch_idx in range(total_batches):
        all_results.extend(batch_results_map.get(batch_idx, []))

    # Calculate statistics
    modified_count = sum(1 for d in all_results if d.get("is_modified", False))
    unchanged_count = len(all_results) - modified_count

    statistics = {
        "total_terms": len(all_results),
        "modified_count": modified_count,
        "unchanged_count": unchanged_count
    }

    logger.info(f"Terminology simplification complete: {statistics}")

    return SimplifyTermsOutput(
        simplified_data=all_results,
        statistics=statistics
    )
