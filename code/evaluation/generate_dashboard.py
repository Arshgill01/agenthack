from __future__ import annotations
import json
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parent.parent

def generate_html():
    results_json = EVAL_DIR / "eval_results.json"
    if not results_json.exists():
        print(f"Error: eval_results.json not found at {results_json}")
        sys.exit(1)

    with open(results_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    accuracies = data.get("accuracies", {})
    usage = data.get("actual_token_usage", {})
    results = data.get("results", [])
    failures = data.get("failures", [])
    confusion_matrix = data.get("confusion_matrix", {})
    object_breakdown = data.get("object_breakdown", {})
    risk_stats = data.get("risk_flags_agreement", {})

    total_claims = data.get("total_claims", len(results))
    failures_count = len(failures)

    # Compute cost
    tot_vlm_in = usage.get("vlm_input_tokens", 0)
    tot_vlm_out = usage.get("vlm_output_tokens", 0)
    tot_text_in = usage.get("text_input_tokens", 0)
    tot_text_out = usage.get("text_output_tokens", 0)
    vlm_calls = usage.get("vlm_calls", 0)
    text_calls = usage.get("text_calls", 0)
    
    actual_cost = (tot_vlm_in / 1000000.0) * 0.075 + (tot_vlm_out / 1000000.0) * 0.30 + \
                  (tot_text_in / 1000000.0) * 0.075 + (tot_text_out / 1000000.0) * 0.30

    # Build claims JSON for JS browser search
    claims_js = json.dumps(results or failures)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EGDCA Claims Audit Dashboard - Japanese Retro Edition</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400;1,700&family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-paper: #f5f2eb;
            --bg-grid: #e2ded5;
            --ink-dark: #1d2436;
            --ink-muted: #5e6b84;
            --stamp-red: #c83838;
            --stamp-red-glow: rgba(200, 56, 56, 0.15);
            --retro-green: #3b6046;
            --retro-mustard: #b58d22;
            --border-solid: 2px solid #1d2436;
            --border-thin: 1px solid #1d2436;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            background-color: var(--bg-paper);
            color: var(--ink-dark);
            font-family: 'Inter', sans-serif;
            background-image: 
                radial-gradient(var(--bg-grid) 1.5px, transparent 1.5px);
            background-size: 24px 24px;
            background-attachment: fixed;
            min-height: 100vh;
            padding: 2.5rem;
            line-height: 1.6;
        }}

        header {{
            max-width: 1280px;
            margin: 0 auto 2.5rem auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: var(--border-solid);
            padding-bottom: 1.5rem;
        }}

        h1, h2, h3 {{
            font-family: 'Playfair Display', serif;
            font-weight: 900;
        }}

        .brand-title {{
            font-size: 2.4rem;
            letter-spacing: -0.02em;
            color: var(--ink-dark);
            position: relative;
        }}

        .subtitle {{
            color: var(--ink-muted);
            font-size: 0.95rem;
            margin-top: 0.25rem;
            font-family: 'Space Mono', monospace;
            text-transform: uppercase;
        }}

        .hanko-stamp {{
            border: 3px double var(--stamp-red);
            color: var(--stamp-red);
            padding: 0.5rem 0.75rem;
            font-family: 'Playfair Display', serif;
            font-weight: 900;
            font-size: 1.3rem;
            letter-spacing: 0.1em;
            line-height: 1.1;
            text-align: center;
            border-radius: 4px;
            transform: rotate(-6deg);
            display: inline-block;
            background-color: transparent;
            user-select: none;
            box-shadow: 2px 2px 0px var(--stamp-red-glow);
        }}

        .dashboard-container {{
            max-width: 1280px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr;
            gap: 2.5rem;
        }}

        /* Key Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: 1.5rem;
        }}

        .stat-card {{
            background: #ffffff;
            border: var(--border-solid);
            padding: 1.5rem;
            box-shadow: 4px 4px 0px var(--ink-dark);
            transition: transform 0.2s, box-shadow 0.2s;
            position: relative;
        }}

        .stat-card:hover {{
            transform: translate(-2px, -2px);
            box-shadow: 6px 6px 0px var(--ink-dark);
        }}

        .stat-label {{
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--ink-muted);
            font-weight: 700;
            font-family: 'Space Mono', monospace;
        }}

        .stat-value {{
            font-size: 2.4rem;
            font-weight: 900;
            font-family: 'Space Mono', monospace;
            margin: 0.5rem 0;
            color: var(--ink-dark);
        }}

        .stat-details {{
            font-size: 0.75rem;
            color: var(--ink-muted);
        }}

        /* Mid-Section: Breakdown and System Health */
        .mid-grid {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 2.5rem;
        }}

        @media (max-width: 1024px) {{
            .mid-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .section-card {{
            background: #ffffff;
            border: var(--border-solid);
            padding: 2rem;
            box-shadow: 5px 5px 0px var(--ink-dark);
        }}

        .section-title {{
            font-size: 1.5rem;
            margin-bottom: 1.5rem;
            border-bottom: var(--border-solid);
            padding-bottom: 0.75rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        /* Table Design */
        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            margin-bottom: 1rem;
        }}

        th, td {{
            padding: 0.75rem 1rem;
            border-bottom: var(--border-thin);
            font-size: 0.9rem;
        }}

        th {{
            color: var(--ink-muted);
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
            font-family: 'Space Mono', monospace;
        }}

        .badge {{
            display: inline-block;
            padding: 0.35rem 0.75rem;
            border: var(--border-solid);
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 700;
            font-family: 'Space Mono', monospace;
            text-transform: uppercase;
        }}

        .badge-success {{ background: #e6f4eb; color: var(--retro-green); border-color: var(--retro-green); }}
        .badge-warning {{ background: #fffcf0; color: var(--retro-mustard); border-color: var(--retro-mustard); }}
        .badge-danger {{ background: #fdf2f2; color: var(--stamp-red); border-color: var(--stamp-red); }}

        /* Filter Controls */
        .filter-bar {{
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            margin-bottom: 1.5rem;
        }}

        .search-input {{
            flex: 1;
            min-width: 250px;
            background: #ffffff;
            border: var(--border-solid);
            padding: 0.75rem 1.25rem;
            border-radius: 4px;
            color: var(--ink-dark);
            font-family: inherit;
            outline: none;
            box-shadow: 3px 3px 0px var(--ink-dark);
            transition: all 0.2s;
        }}

        .search-input:focus {{
            transform: translate(-1px, -1px);
            box-shadow: 4px 4px 0px var(--ink-dark);
        }}

        .search-input:focus-visible,
        .filter-select:focus-visible,
        .claim-summary-header:focus-visible {{
            outline: 2px solid var(--stamp-red);
            outline-offset: 2px;
        }}

        .filter-select {{
            background: #ffffff;
            border: var(--border-solid);
            padding: 0.75rem 1.25rem;
            border-radius: 4px;
            color: var(--ink-dark);
            font-family: inherit;
            outline: none;
            cursor: pointer;
            box-shadow: 3px 3px 0px var(--ink-dark);
            transition: all 0.2s;
        }}

        .filter-select:focus {{
            transform: translate(-1px, -1px);
            box-shadow: 4px 4px 0px var(--ink-dark);
        }}

        /* Interactive Claims List */
        .claims-list {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}

        .claim-row {{
            background: #ffffff;
            border: var(--border-solid);
            border-radius: 4px;
            overflow: hidden;
            box-shadow: 4px 4px 0px var(--ink-dark);
            transition: all 0.2s;
        }}

        .claim-row.failed-match {{
            border-left: 8px solid var(--stamp-red);
        }}

        .claim-row.passed-match {{
            border-left: 8px solid var(--retro-green);
        }}

        .claim-row:hover {{
            transform: translate(-1px, -1px);
            box-shadow: 5px 5px 0px var(--ink-dark);
        }}

        .claim-summary-header {{
            padding: 1.25rem 1.5rem;
            display: grid;
            grid-template-columns: 0.8fr 1.2fr 1fr 1fr 1fr 0.2fr;
            align-items: center;
            cursor: pointer;
            gap: 1rem;
            outline: none;
        }}

        @media (max-width: 768px) {{
            .claim-summary-header {{
                display: flex;
                flex-direction: column;
                align-items: flex-start;
                gap: 0.5rem;
                padding: 1rem;
            }}
            .hide-mobile {{
                display: block;
            }}
        }}

        .claim-detail-drawer {{
            padding: 0;
            max-height: 0;
            overflow: hidden;
            background: #faf9f6;
            transition: all 0.3s ease-out;
        }}

        .claim-detail-drawer.open {{
            padding: 2rem;
            max-height: 2500px;
            border-top: var(--border-thin);
        }}

        .drawer-grid {{
            display: grid;
            grid-template-columns: 1.2fr 2fr;
            gap: 2rem;
        }}

        @media (max-width: 900px) {{
            .drawer-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .drawer-column {{
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }}

        .drawer-section-title {{
            font-size: 1.05rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--ink-muted);
            margin-bottom: 0.75rem;
            font-weight: 700;
            border-bottom: var(--border-solid);
            padding-bottom: 0.5rem;
            font-family: 'Space Mono', monospace;
        }}

        .data-label {{
            font-size: 0.75rem;
            color: var(--ink-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.25rem;
            font-family: 'Space Mono', monospace;
        }}

        .data-value {{
            font-size: 0.95rem;
            font-weight: 600;
        }}

        .data-grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }}

        .justification-box {{
            background: #ffffff;
            border: var(--border-solid);
            box-shadow: 2px 2px 0px var(--ink-dark);
            border-radius: 4px;
            padding: 1.25rem;
            font-size: 0.92rem;
            line-height: 1.6;
        }}

        .trace-box {{
            background: #1d2436;
            color: #f5f2eb;
            border: var(--border-solid);
            border-radius: 4px;
            padding: 1.25rem;
            font-family: 'Space Mono', monospace;
            font-size: 0.85rem;
            overflow-x: auto;
            max-height: 350px;
            overflow-y: auto;
        }}

        .trace-item {{
            margin-bottom: 0.75rem;
            color: #cdd6e2;
            border-left: 2px solid var(--retro-mustard);
            padding-left: 0.75rem;
        }}

        .trace-item:last-child {{
            margin-bottom: 0;
        }}

        .indicator-icon {{
            font-size: 1.25rem;
            transition: transform 0.3s;
            font-family: 'Space Mono', monospace;
        }}

        .open .indicator-icon {{
            transform: rotate(90deg);
        }}

        .cost-list {{
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }}

        .cost-list li {{
            display: flex;
            justify-content: space-between;
            font-size: 0.9rem;
            border-bottom: 1px dashed var(--ink-muted);
            padding-bottom: 0.5rem;
        }}

        .cost-list li span:last-child {{
            font-weight: 700;
            color: var(--ink-dark);
            font-family: 'Space Mono', monospace;
        }}

        .cost-total {{
            font-size: 1.15rem;
            font-weight: 900;
            color: var(--stamp-red) !important;
            border-bottom: none !important;
            padding-top: 0.5rem;
        }}
    </style>
</head>
<body>

    <header>
        <div>
            <h1 class="brand-title">EGDCA Claims Audit Dashboard</h1>
            <p class="subtitle">Evidence-Grounded Damage Claims Agent — Verification Metrics</p>
        </div>
        <div class="hanko-stamp">
            検 査 済<br>
            VERIFIED
        </div>
    </header>

    <div class="dashboard-container">
        
        <!-- Key Accuracy Metrics -->
        <section class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Claim Status Acc</div>
                <div class="stat-value">{accuracies.get("claim_status", 0.0)*100:.1f}%</div>
                <div class="stat-details">Supported / Contradicted correctness</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Object Part Acc</div>
                <div class="stat-value">{accuracies.get("object_part", 0.0)*100:.1f}%</div>
                <div class="stat-details">Coarse/fine visible part localization</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Issue Type Acc</div>
                <div class="stat-value">{accuracies.get("issue_type", 0.0)*100:.1f}%</div>
                <div class="stat-details">Damage classification accuracy</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Severity Acc</div>
                <div class="stat-value">{accuracies.get("severity", 0.0)*100:.1f}%</div>
                <div class="stat-details">Evaluated physical severity rating</div>
            </div>
        </section>

        <!-- Mid Breakdown Section -->
        <div class="mid-grid">
            
            <div class="section-card">
                <h2 class="section-title">Object Breakdown</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Object Domain</th>
                            <th>Total Claims</th>
                            <th>Status Acc</th>
                            <th>Part Acc</th>
                            <th>Issue Acc</th>
                            <th>Severity Acc</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    obj_types = ["car", "laptop", "package"]
    for obj in obj_types:
        m_obj = object_breakdown.get(obj, {})
        if m_obj.get("total", 0) > 0:
            html_content += f"""
                        <tr>
                            <td style="font-weight: 700; text-transform: capitalize;">{obj}</td>
                            <td style="font-family: 'Space Mono', monospace;">{m_obj['total']}</td>
                            <td style="font-family: 'Space Mono', monospace; font-weight: 700; color: var(--retro-green);">{m_obj['claim_status_accuracy']*100:.1f}%</td>
                            <td style="font-family: 'Space Mono', monospace;">{m_obj['object_part_accuracy']*100:.1f}%</td>
                            <td style="font-family: 'Space Mono', monospace;">{m_obj['issue_type_accuracy']*100:.1f}%</td>
                            <td style="font-family: 'Space Mono', monospace;">{m_obj['severity_accuracy']*100:.1f}%</td>
                        </tr>
            """
        else:
            html_content += f"""
                        <tr>
                            <td style="font-weight: 700; text-transform: capitalize;">{obj}</td>
                            <td style="font-family: 'Space Mono', monospace;">0</td>
                            <td>-</td>
                            <td>-</td>
                            <td>-</td>
                            <td>-</td>
                        </tr>
            """

    html_content += f"""
                    </tbody>
                </table>
                
                <div style="margin-top: 1.5rem; display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; border-top: var(--border-thin); padding-top: 1.5rem;">
                    <div>
                        <div class="data-label">Exact Risk Flags Match</div>
                        <div class="data-value" style="font-family: 'Space Mono', monospace; font-size: 1.25rem;">{risk_stats.get("exact_match_accuracy", 0.0)*100:.1f}%</div>
                    </div>
                    <div>
                        <div class="data-label">Average Risk Flags Jaccard Similarity</div>
                        <div class="data-value" style="font-family: 'Space Mono', monospace; font-size: 1.25rem;">{risk_stats.get("average_jaccard_similarity", 0.0):.4f}</div>
                    </div>
                </div>
            </div>

            <div class="section-card">
                <h2 class="section-title">Token Usage & Cost</h2>
                <ul class="cost-list">
                    <li><span>VLM Calls (Pass 1-3)</span> <span>{vlm_calls} calls</span></li>
                    <li><span>VLM Input Tokens</span> <span>{tot_vlm_in:,}</span></li>
                    <li><span>VLM Output Tokens</span> <span>{tot_vlm_out:,}</span></li>
                    <li><span>Text Calls (Pass 0 Extractor)</span> <span>{text_calls} calls</span></li>
                    <li><span>Text Input Tokens</span> <span>{tot_text_in:,}</span></li>
                    <li><span>Text Output Tokens</span> <span>{tot_text_out:,}</span></li>
                    <li class="cost-total"><span>Total GCP Cost</span> <span>${actual_cost:.4f}</span></li>
                </ul>
            </div>

        </div>

        <!-- Claims Explorer Bar -->
        <section class="section-card">
            <h2 class="section-title">
                <span>Claims Explorer</span>
                <span style="font-size: 0.95rem; color: var(--ink-muted); font-weight: normal; font-family: 'Space Mono', monospace;">
                    SHOWING <span id="visible-count">{total_claims}</span> OF {total_claims} CLAIMS
                </span>
            </h2>

            <div class="filter-bar">
                <input type="text" id="search-box" class="search-input" placeholder="Search by User ID, claimed part, or words inside user claims..." aria-label="Search claims by user ID, part, or damage type">
                <select id="filter-object" class="filter-select" aria-label="Filter claims by object domain">
                    <option value="all">All Objects</option>
                    <option value="car">Cars</option>
                    <option value="laptop">Laptops</option>
                    <option value="package">Packages</option>
                </select>
                <select id="filter-status" class="filter-select" aria-label="Filter claims by expected decision status">
                    <option value="all">All Decisions</option>
                    <option value="supported">Supported</option>
                    <option value="contradicted">Contradicted</option>
                    <option value="not_enough_information">Not Enough Info</option>
                </select>
                <select id="filter-match" class="filter-select" aria-label="Filter claims by test suite match status">
                    <option value="all">All Test Matches</option>
                    <option value="passed">PASS Matches</option>
                    <option value="failed">FAIL Matches</option>
                </select>
            </div>

            <div class="claims-list" id="claims-container">
                <!-- Javascript will insert claim items here -->
            </div>
        </section>

    </div>

    <script>
        const claims = {claims_js};

        function getMatchClass(claim) {{
            const isMatch = claim.status.match && claim.object_part.match && claim.issue_type.match;
            return isMatch ? 'passed-match' : 'failed-match';
        }}

        function getBadgeClass(status) {{
            if (status === 'supported') return 'badge-success';
            if (status === 'contradicted') return 'badge-danger';
            return 'badge-warning';
        }}

        function renderClaims() {{
            const query = document.getElementById('search-box').value.toLowerCase();
            const objectFilter = document.getElementById('filter-object').value;
            const statusFilter = document.getElementById('filter-status').value;
            const matchFilter = document.getElementById('filter-match').value;
            const container = document.getElementById('claims-container');
            
            container.innerHTML = '';
            let count = 0;

            claims.forEach(c => {{
                // Matching criteria
                const matchesSearch = c.user_id.toLowerCase().includes(query) || 
                                      c.object_part.expected.toLowerCase().includes(query) ||
                                      c.issue_type.expected.toLowerCase().includes(query);
                
                const matchesObject = objectFilter === 'all' || c.object === objectFilter;
                const matchesStatus = statusFilter === 'all' || c.status.expected === statusFilter;
                
                const isMatchPass = c.status.match && c.object_part.match && c.issue_type.match;
                const matchesMatch = matchFilter === 'all' || 
                                    (matchFilter === 'passed' && isMatchPass) || 
                                    (matchFilter === 'failed' && !isMatchPass);

                if (matchesSearch && matchesObject && matchesStatus && matchesMatch) {{
                    count++;
                    const matchClass = getMatchClass(c);
                    const statusBadgeClass = getBadgeClass(c.status.predicted);
                    const agreementClass = c.blind_aware_agreement.includes('escalated') ? 'badge-danger' : 
                                           c.blind_aware_agreement.includes('resolved') ? 'badge-success' : 'badge-warning';
                    
                    const risks_str = c.risk_flags.predicted && c.risk_flags.predicted.length > 0 ? c.risk_flags.predicted.join('; ') : 'none';

                    const rowHtml = `
                        <div class="claim-row ${{matchClass}}" id="claim-block-${{c.row_index}}">
                            <div class="claim-summary-header" onclick="toggleDrawer(${{c.row_index}})" role="button" tabindex="0" aria-expanded="false" onkeydown="if(event.key==='Enter'||event.key===' '){{ event.preventDefault(); toggleDrawer(${{c.row_index}}); }}" aria-label="Toggle details for claim ${{c.user_id}}">
                                <span style="font-weight: 700; font-family: 'Space Mono', monospace;">${{c.user_id}}</span>
                                <span class="hide-mobile" style="color: var(--ink-muted); text-transform: uppercase; font-family: 'Space Mono', monospace; font-size: 0.85rem;">
                                    ${{c.object}}
                                </span>
                                <span><span class="badge ${{statusBadgeClass}}">${{c.status.predicted}}</span></span>
                                <span class="hide-mobile" style="font-size: 0.85rem;">Part: <strong style="color: var(--retro-green);">${{c.object_part.predicted}}</strong></span>
                                <span class="hide-mobile" style="font-size: 0.85rem;">Issue: <strong style="color: var(--retro-mustard);">${{c.issue_type.predicted}}</strong></span>
                                <span class="indicator-icon">▸</span>
                            </div>
                            
                            <div class="claim-detail-drawer" id="drawer-${{c.row_index}}">
                                <div class="drawer-grid">
                                    <div class="drawer-column">
                                        <div>
                                            <div class="drawer-section-title">Claim Information</div>
                                            <div class="data-grid-2">
                                                <div>
                                                    <div class="data-label">Claim Object</div>
                                                    <div class="data-value" style="text-transform: capitalize;">${{c.object}}</div>
                                                </div>
                                                <div>
                                                    <div class="data-label">Agreement Mode</div>
                                                    <div class="data-value"><span class="badge ${{agreementClass}}">${{c.blind_aware_agreement}}</span></div>
                                                </div>
                                            </div>
                                            <div style="margin-top: 1rem;">
                                                <div class="data-label">Stated Claim Details</div>
                                                <div class="data-value" style="font-size: 0.9rem; font-style: italic; background: rgba(31, 41, 55, 0.05); padding: 0.75rem; border-radius: 4px; border: var(--border-thin);">
                                                    Claimed Part: <strong>${{c.object_part.expected}}</strong><br>
                                                    Claimed Damage: <strong>${{c.issue_type.expected}}</strong>
                                                </div>
                                            </div>
                                        </div>
                                        
                                        <div>
                                            <div class="drawer-section-title">Decision Match Results</div>
                                            <div class="cost-list">
                                                <li><span>Claim Status Match</span> <span style="color: ${{c.status.match ? 'var(--retro-green)':'var(--stamp-red)'}}">${{c.status.match ? 'PASS' : 'FAIL'}} (Expected: ${{c.status.expected}})</span></li>
                                                <li><span>Object Part Match</span> <span style="color: ${{c.object_part.match ? 'var(--retro-green)':'var(--stamp-red)'}}">${{c.object_part.match ? 'PASS' : 'FAIL'}} (Expected: ${{c.object_part.expected}})</span></li>
                                                <li><span>Issue Type Match</span> <span style="color: ${{c.issue_type.match ? 'var(--retro-green)':'var(--stamp-red)'}}">${{c.issue_type.match ? 'PASS' : 'FAIL'}} (Expected: ${{c.issue_type.expected}})</span></li>
                                                <li><span>Severity Match</span> <span style="color: ${{c.severity.match ? 'var(--retro-green)':'var(--stamp-red)'}}">${{c.severity.match ? 'PASS' : 'FAIL'}} (Expected: ${{c.severity.expected}})</span></li>
                                                <li><span>Evidence Standard Match</span> <span style="color: ${{c.evidence_standard_met.match ? 'var(--retro-green)':'var(--stamp-red)'}}">${{c.evidence_standard_met.match ? 'PASS' : 'FAIL'}} (Expected: ${{c.evidence_standard_met.expected}})</span></li>
                                                <li><span>Valid Image Match</span> <span style="color: ${{c.valid_image.match ? 'var(--retro-green)':'var(--stamp-red)'}}">${{c.valid_image.match ? 'PASS' : 'FAIL'}} (Expected: ${{c.valid_image.expected}})</span></li>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div class="drawer-column">
                                        <div>
                                            <div class="drawer-section-title">Calibrated Visual Justification</div>
                                            <div class="justification-box">
                                                ${{c.status.predicted === 'not_enough_information' ? 'Not Enough Info: ' : ''}} 
                                                <strong>Decided Status: ${{c.status.predicted.toUpperCase()}}</strong><br>
                                                <p style="margin-top: 0.5rem; color: var(--ink-dark); font-size: 0.95rem;">
                                                    ${{c.status.predicted === 'supported' || c.status.predicted === 'contradicted' ? 'Justification: ' : 'Reason: '}}
                                                    ${{c.status.expected === 'supported' || c.status.expected === 'contradicted' ? 'Visual observations support the final decision.' : 'Visual context was insufficient.'}}
                                                </p>
                                            </div>
                                        </div>
                                        
                                        <div>
                                            <div class="drawer-section-title">Consensus Details</div>
                                            <div class="justification-box">
                                                <div class="data-label">Active Risk Flags</div>
                                                <div class="data-value" style="font-weight: 700; color: ${{risks_str !== 'none' ? 'var(--stamp-red)':'var(--ink-dark)'}}">${{risks_str}}</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                    container.innerHTML += rowHtml;
                }}
            }});

            document.getElementById('visible-count').innerText = count;
        }}

        function toggleDrawer(index) {{
            const drawer = document.getElementById('drawer-' + index);
            const header = document.getElementById('claim-block-' + index);
            const summaryHeader = header.querySelector('.claim-summary-header');
            
            if (drawer.classList.contains('open')) {{
                drawer.classList.remove('open');
                header.classList.remove('open');
                summaryHeader.setAttribute('aria-expanded', 'false');
            }} else {{
                drawer.classList.add('open');
                header.classList.add('open');
                summaryHeader.setAttribute('aria-expanded', 'true');
            }}
        }}

        // Listen for filters
        document.getElementById('search-box').addEventListener('input', renderClaims);
        document.getElementById('filter-object').addEventListener('change', renderClaims);
        document.getElementById('filter-status').addEventListener('change', renderClaims);
        document.getElementById('filter-match').addEventListener('change', renderClaims);

        // Initial render
        renderClaims();
    </script>
</body>
</html>
"""

    output_html = REPO_ROOT / "audit_dashboard.html"
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Interactive Audit Dashboard generated successfully at: {output_html}")

if __name__ == "__main__":
    generate_html()
