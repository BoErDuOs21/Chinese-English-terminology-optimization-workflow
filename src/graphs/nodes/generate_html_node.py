"""Generate interactive HTML node - creates a presentation-ready interactive comparison web page."""
import html
import logging
from typing import List, Dict, Any
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import GenerateHtmlInput, GenerateHtmlOutput

logger = logging.getLogger(__name__)


def _escape(text: str) -> str:
    """Safely escape HTML special characters."""
    return html.escape(str(text), quote=True)


def generate_html_node(state: GenerateHtmlInput, config: RunnableConfig, runtime: Runtime[Context]) -> GenerateHtmlOutput:
    """
    title: Generate Interactive HTML Page
    desc: Create an interactive comparison web page with click-to-zoom feature for presenting terminology changes to the audience
    """
    ctx = runtime.context
    simplified_data = state.simplified_data
    statistics = state.statistics

    if not simplified_data:
        raise ValueError("No simplified data to generate HTML from.")

    total_terms = int(statistics.get("total_terms", 0))
    modified_count = int(statistics.get("modified_count", 0))
    unchanged_count = int(statistics.get("unchanged_count", 0))

    # Sort: modified terms first, then unchanged
    sorted_data = sorted(simplified_data, key=lambda x: (not x.get("is_modified", False), x.get("sheet", ""), x.get("chinese", "")))

    # Build table rows HTML
    rows_html_parts: List[str] = []
    for idx, item in enumerate(sorted_data):
        chinese_val = _escape(item.get("chinese", ""))
        original_en = _escape(item.get("original_english", ""))
        simplified_en = _escape(item.get("simplified_english", ""))
        reason = _escape(item.get("reason", ""))
        remark_en = _escape(item.get("remark_en", item.get("remark", "")))
        sheet = _escape(item.get("sheet", ""))
        is_modified = item.get("is_modified", False)

        row_class = "row-modified" if is_modified else "row-unchanged"
        badge_html = '<span class="badge badge-changed">Modified</span>' if is_modified else '<span class="badge badge-kept">Kept</span>'

        # Data attributes for JS modal
        row_data = (
            f'data-chinese="{chinese_val}" '
            f'data-original="{original_en}" '
            f'data-simplified="{simplified_en}" '
            f'data-reason="{reason}" '
            f'data-remark="{remark_en}" '
            f'data-sheet="{sheet}" '
            f'data-modified="{str(is_modified).lower()}"'
        )

        row_html = f'''<tr class="{row_class}" {row_data} onclick="openModal(this)">
  <td class="col-num">{idx + 1}</td>
  <td class="col-sheet">{sheet}</td>
  <td class="col-chinese">{chinese_val}</td>
  <td class="col-original">{original_en}</td>
  <td class="col-simplified">{simplified_en}</td>
  <td class="col-status">{badge_html}</td>
  <td class="col-remark">{remark_en}</td>
</tr>'''
        rows_html_parts.append(row_html)

    rows_html = "\n".join(rows_html_parts)

    # Build the full HTML page
    html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Terminology Comparison - Before vs After</title>
<style>
  :root {{
    --primary: #4361ee;
    --primary-light: #e8edff;
    --success: #2ec4b6;
    --success-light: #e6f9f7;
    --warning: #ff9f1c;
    --warning-light: #fff5e6;
    --danger: #e63946;
    --bg: #f8f9fc;
    --card-bg: #ffffff;
    --text: #2b2d42;
    --text-light: #6c757d;
    --border: #e2e8f0;
    --shadow: 0 4px 24px rgba(0,0,0,0.08);
    --radius: 12px;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    min-height: 100vh;
  }}

  .container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 40px 24px;
  }}

  /* Header */
  .header {{
    text-align: center;
    margin-bottom: 40px;
  }}
  .header h1 {{
    font-size: 2.2rem;
    font-weight: 700;
    color: var(--primary);
    margin-bottom: 12px;
  }}
  .header p {{
    font-size: 1.05rem;
    color: var(--text-light);
    max-width: 700px;
    margin: 0 auto;
  }}

  /* Stats Cards */
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 36px;
  }}
  .stat-card {{
    background: var(--card-bg);
    border-radius: var(--radius);
    padding: 24px;
    text-align: center;
    box-shadow: var(--shadow);
    border-top: 4px solid var(--primary);
    transition: transform 0.2s;
  }}
  .stat-card:hover {{ transform: translateY(-3px); }}
  .stat-card.total {{ border-top-color: var(--primary); }}
  .stat-card.modified {{ border-top-color: var(--success); }}
  .stat-card.unchanged {{ border-top-color: var(--warning); }}
  .stat-number {{
    font-size: 2.8rem;
    font-weight: 800;
    line-height: 1.1;
  }}
  .stat-card.total .stat-number {{ color: var(--primary); }}
  .stat-card.modified .stat-number {{ color: var(--success); }}
  .stat-card.unchanged .stat-number {{ color: var(--warning); }}
  .stat-label {{
    font-size: 0.95rem;
    color: var(--text-light);
    margin-top: 6px;
    font-weight: 500;
  }}

  /* Search */
  .search-bar {{
    margin-bottom: 24px;
    display: flex;
    justify-content: center;
  }}
  .search-bar input {{
    width: 100%;
    max-width: 500px;
    padding: 12px 20px;
    border: 2px solid var(--border);
    border-radius: 50px;
    font-size: 1rem;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
    background: var(--card-bg);
  }}
  .search-bar input:focus {{
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(67,97,238,0.15);
  }}

  /* Table */
  .table-wrapper {{
    background: var(--card-bg);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    overflow: hidden;
  }}
  .table-hint {{
    padding: 14px 24px;
    background: var(--primary-light);
    color: var(--primary);
    font-size: 0.9rem;
    font-weight: 500;
    text-align: center;
    border-bottom: 1px solid var(--border);
  }}
  .table-hint span {{ font-size: 1.1em; }}

  table {{
    width: 100%;
    border-collapse: collapse;
  }}
  thead th {{
    background: #f1f3f9;
    padding: 14px 16px;
    text-align: left;
    font-weight: 600;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-light);
    border-bottom: 2px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 1;
  }}
  tbody tr {{
    cursor: pointer;
    transition: background 0.15s, box-shadow 0.15s;
    border-bottom: 1px solid var(--border);
  }}
  tbody tr:hover {{
    background: #f0f4ff;
    box-shadow: inset 0 0 0 2px var(--primary);
  }}
  tbody tr:last-child {{ border-bottom: none; }}

  /* Modified row highlight - eye-catching */
  tbody tr.row-modified {{
    background: linear-gradient(90deg, rgba(46,204,113,0.08) 0%, transparent 60%);
    border-left: 4px solid var(--success);
  }}
  tbody tr.row-modified:hover {{
    background: linear-gradient(90deg, rgba(46,204,113,0.15) 0%, rgba(67,97,238,0.05) 100%);
    box-shadow: inset 0 0 0 2px var(--success);
  }}
  tbody tr.row-modified td {{
    font-weight: 500;
  }}
  tbody tr.row-modified .col-chinese {{
    color: var(--primary);
  }}
  td {{
    padding: 14px 16px;
    font-size: 0.95rem;
    vertical-align: middle;
  }}
  .col-num {{ width: 50px; color: var(--text-light); font-weight: 500; }}
  .col-sheet {{ font-size: 0.85rem; color: var(--primary); font-weight: 500; }}
  .col-chinese {{ font-weight: 600; }}
  .col-original {{ color: var(--danger); font-weight: 500; }}
  .col-simplified {{ color: var(--success); font-weight: 600; }}

  /* Badges */
  .badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.3px;
  }}
  .badge-changed {{
    background: var(--success-light);
    color: #1a7a6e;
  }}
  .badge-kept {{
    background: var(--warning-light);
    color: #b37200;
  }}

  /* Modal Overlay - optimized for performance (no backdrop-filter) */
  .modal-overlay {{
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.6);
    z-index: 1000;
    display: flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
    opacity: 0;
    visibility: hidden;
    transition: opacity 0.2s ease, visibility 0.2s ease;
    will-change: opacity;
  }}
  .modal-overlay.active {{
    opacity: 1;
    visibility: visible;
  }}

  .modal-card {{
    background: var(--card-bg);
    border-radius: 20px;
    padding: 48px;
    max-width: 680px;
    width: 90%;
    box-shadow: 0 20px 60px rgba(0,0,0,0.25);
    cursor: default;
    position: relative;
    transform: translateY(20px) scale(0.97);
    transition: transform 0.2s ease;
    will-change: transform;
  }}
  .modal-overlay.active .modal-card {{
    transform: translateY(0) scale(1);
  }}

  .modal-close {{
    position: absolute;
    top: 16px;
    right: 20px;
    width: 36px;
    height: 36px;
    border: none;
    background: #f1f3f9;
    border-radius: 50%;
    font-size: 1.2rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s;
    color: var(--text-light);
  }}
  .modal-close:hover {{ background: #e2e8f0; }}

  .modal-chinese {{
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 8px;
    padding-bottom: 12px;
    border-bottom: 2px solid var(--border);
  }}
  .modal-sheet {{
    font-size: 0.85rem;
    color: var(--primary);
    font-weight: 500;
    margin-bottom: 20px;
    padding-bottom: 12px;
  }}
  .modal-sheet::before {{
    content: "\\1F4C4  Sheet: ";
    font-weight: 600;
  }}

  .comparison-box {{
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 20px;
    align-items: center;
    margin-bottom: 28px;
  }}
  .comparison-item {{
    text-align: center;
    padding: 20px;
    border-radius: var(--radius);
  }}
  .comparison-item.before {{
    background: #fef2f2;
    border: 2px solid #fecaca;
  }}
  .comparison-item.after {{
    background: #f0fdf4;
    border: 2px solid #bbf7d0;
  }}
  .comparison-label {{
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
    margin-bottom: 8px;
  }}
  .comparison-item.before .comparison-label {{ color: var(--danger); }}
  .comparison-item.after .comparison-label {{ color: #16a34a; }}
  .comparison-word {{
    font-size: 1.5rem;
    font-weight: 700;
  }}
  .comparison-item.before .comparison-word {{ color: var(--danger); }}
  .comparison-item.after .comparison-word {{ color: #16a34a; }}
  .comparison-arrow {{
    font-size: 2rem;
    color: var(--primary);
    font-weight: bold;
  }}

  .modal-reason {{
    background: #f8f9fc;
    border-radius: var(--radius);
    padding: 20px;
    margin-bottom: 20px;
  }}
  .modal-reason-label {{
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--primary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
  }}
  .modal-reason-text {{
    font-size: 1.05rem;
    color: var(--text);
    line-height: 1.7;
  }}

  .modal-remark {{
    font-size: 0.9rem;
    color: var(--text-light);
    padding-top: 12px;
    border-top: 1px solid var(--border);
  }}
  .modal-remark strong {{ color: var(--text); }}

  .modal-status {{
    display: inline-block;
    margin-top: 16px;
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
  }}
  .modal-status.changed {{
    background: var(--success-light);
    color: #1a7a6e;
  }}
  .modal-status.kept {{
    background: var(--warning-light);
    color: #b37200;
  }}

  /* No results */
  .no-results {{
    text-align: center;
    padding: 40px;
    color: var(--text-light);
    font-size: 1.1rem;
    display: none;
  }}

  /* Footer */
  .footer {{
    text-align: center;
    margin-top: 40px;
    color: var(--text-light);
    font-size: 0.85rem;
  }}

  /* Responsive */
  @media (max-width: 768px) {{
    .header h1 {{ font-size: 1.6rem; }}
    .modal-card {{ padding: 28px; }}
    .comparison-box {{ grid-template-columns: 1fr; gap: 12px; }}
    .comparison-arrow {{ transform: rotate(90deg); }}
    .comparison-word {{ font-size: 1.2rem; }}
    td, th {{ padding: 10px 8px; font-size: 0.85rem; }}
  }}
</style>
</head>
<body>

<div class="container">
  <!-- Header -->
  <div class="header">
    <h1>Terminology Comparison Report</h1>
    <p>Bilingual terminology readability optimization - replacing obscure English words with simpler alternatives for Southeast Asian team members</p>
  </div>

  <!-- Statistics -->
  <div class="stats-grid">
    <div class="stat-card total">
      <div class="stat-number">{total_terms}</div>
      <div class="stat-label">Total Terms</div>
    </div>
    <div class="stat-card modified">
      <div class="stat-number">{modified_count}</div>
      <div class="stat-label">Modified</div>
    </div>
    <div class="stat-card unchanged">
      <div class="stat-number">{unchanged_count}</div>
      <div class="stat-label">Unchanged</div>
    </div>
  </div>

  <!-- Search -->
  <div class="search-bar">
    <input type="text" id="searchInput" placeholder="Search terms (Chinese / English)..." oninput="filterTable()">
  </div>

  <!-- Table -->
  <div class="table-wrapper">
    <div class="table-hint">
      <span>&#128073;</span> Click any row to zoom in for presentation
    </div>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Sheet</th>
          <th>Chinese</th>
          <th>Before</th>
          <th>After</th>
          <th>Status</th>
          <th>Remark</th>
        </tr>
      </thead>
      <tbody id="termsTable">
{rows_html}
      </tbody>
    </table>
    <div class="no-results" id="noResults">No matching terms found.</div>
  </div>

  <div class="footer">
    Terminology Readability Optimization &bull; Generated for presentation use
  </div>
</div>

<!-- Modal -->
<div class="modal-overlay" id="modalOverlay" onclick="closeModal(event)">
  <div class="modal-card" onclick="event.stopPropagation()">
    <button class="modal-close" onclick="closeModal()">&times;</button>
    <div class="modal-chinese" id="modalChinese"></div>
    <div class="modal-sheet" id="modalSheet"></div>
    <div class="comparison-box">
      <div class="comparison-item before">
        <div class="comparison-label">Before</div>
        <div class="comparison-word" id="modalOriginal"></div>
      </div>
      <div class="comparison-arrow">&rarr;</div>
      <div class="comparison-item after">
        <div class="comparison-label">After</div>
        <div class="comparison-word" id="modalSimplified"></div>
      </div>
    </div>
    <div class="modal-reason">
      <div class="modal-reason-label">Modification Reason</div>
      <div class="modal-reason-text" id="modalReason"></div>
    </div>
    <div class="modal-remark" id="modalRemark"></div>
    <div id="modalStatus"></div>
  </div>
</div>

<script>
function openModal(row) {{
  var overlay = document.getElementById('modalOverlay');
  document.getElementById('modalChinese').textContent = row.dataset.chinese;
  document.getElementById('modalOriginal').textContent = row.dataset.original;
  document.getElementById('modalSimplified').textContent = row.dataset.simplified;
  document.getElementById('modalReason').textContent = row.dataset.reason;

  var sheetEl = document.getElementById('modalSheet');
  var sheet = row.dataset.sheet || '';
  if (sheet) {{
    sheetEl.textContent = sheet;
    sheetEl.style.display = 'block';
  }} else {{
    sheetEl.style.display = 'none';
  }}

  var remark = row.dataset.remark;
  var remarkEl = document.getElementById('modalRemark');
  if (remark) {{
    remarkEl.innerHTML = '<strong>Remark:</strong> ' + remark;
    remarkEl.style.display = 'block';
  }} else {{
    remarkEl.style.display = 'none';
  }}

  var statusEl = document.getElementById('modalStatus');
  if (row.dataset.modified === 'true') {{
    statusEl.innerHTML = '<span class="modal-status changed">Term was simplified</span>';
  }} else {{
    statusEl.innerHTML = '<span class="modal-status kept">Term kept unchanged</span>';
  }}

  overlay.classList.add('active');
  document.body.style.overflow = 'hidden';
}}

function closeModal(e) {{
  if (e && e.target && e.target !== document.getElementById('modalOverlay')) return;
  document.getElementById('modalOverlay').classList.remove('active');
  document.body.style.overflow = '';
}}

document.addEventListener('keydown', function(e) {{
  if (e.key === 'Escape') {{
    document.getElementById('modalOverlay').classList.remove('active');
    document.body.style.overflow = '';
  }}
}});

function filterTable() {{
  var query = document.getElementById('searchInput').value.toLowerCase();
  var rows = document.querySelectorAll('#termsTable tr');
  var visibleCount = 0;
  rows.forEach(function(row) {{
    var chinese = (row.dataset.chinese || '').toLowerCase();
    var original = (row.dataset.original || '').toLowerCase();
    var simplified = (row.dataset.simplified || '').toLowerCase();
    var remark = (row.dataset.remark || '').toLowerCase();
    var sheet = (row.dataset.sheet || '').toLowerCase();
    var match = chinese.includes(query) || original.includes(query) || simplified.includes(query) || remark.includes(query) || sheet.includes(query);
    row.style.display = match ? '' : 'none';
    if (match) visibleCount++;
  }});
  document.getElementById('noResults').style.display = visibleCount === 0 ? 'block' : 'none';
}}
</script>

</body>
</html>'''

    # Save to /tmp
    output_path = "/tmp/terminology_comparison.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    logger.info(f"Interactive HTML page saved to: {output_path}")

    return GenerateHtmlOutput(local_html_path=output_path)
