"""박람회 리드 후속 이메일 자동화 - 대시보드 생성 스크립트

data/leads_sample.csv + output/email_drafts.csv (Basic 제출물)와
data/leads_dummy_100_test.csv + output/email_drafts_test.csv (재현성 테스트)를 읽어
output/dashboard.html 정적 대시보드를 생성한다.

사용법: .venv/Scripts/python.exe scripts/build_dashboard.py
"""

import html
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"

TITLE_ORDER = ["원장", "팀장", "사업개발"]
PRIORITY_ORDER = ["상", "중", "하"]


def load_dataset(leads_path: Path, drafts_path: Path) -> pd.DataFrame:
    leads = pd.read_csv(leads_path, encoding="utf-8-sig")
    drafts = pd.read_csv(drafts_path, encoding="utf-8-sig")
    merged = leads.merge(drafts, on="lead_id", how="left")
    merged["email_missing"] = merged["email"].isna() | (merged["email"].astype(str).str.strip() == "")
    merged["review_flag"] = merged["review_flag"].fillna("N")
    return merged


def fig_to_div(fig, include_js=False) -> str:
    fig.update_layout(
        margin=dict(l=30, r=20, t=50, b=30),
        font=dict(family="Pretendard, 'Malgun Gothic', sans-serif", size=13),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        autosize=True,
        height=380,
    )
    return pio.to_html(
        fig,
        include_plotlyjs="cdn" if include_js else False,
        full_html=False,
        config={"displayModeBar": False, "responsive": True},
        default_width="100%",
        default_height="380px",
    )


def build_charts(df: pd.DataFrame, first: bool = False) -> dict:
    charts = {}

    title_counts = df["title"].value_counts().reindex(
        [t for t in TITLE_ORDER if t in df["title"].unique()] +
        [t for t in df["title"].unique() if t not in TITLE_ORDER]
    ).dropna().astype(int)
    fig = px.bar(
        x=title_counts.index, y=title_counts.values,
        labels={"x": "직책", "y": "리드 수"}, title="직책별 리드 분포",
        color=title_counts.index, color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(showlegend=False)
    charts["title"] = fig_to_div(fig, include_js=first)

    feature_counts = df["interest_feature"].value_counts()
    fig = px.pie(
        names=feature_counts.index, values=feature_counts.values,
        title="관심 제품(interest_feature) 분포", hole=0.45,
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    charts["feature"] = fig_to_div(fig)

    priority_counts = df["follow_up_priority"].value_counts().reindex(PRIORITY_ORDER).dropna().astype(int)
    fig = px.bar(
        x=priority_counts.index, y=priority_counts.values,
        labels={"x": "우선순위", "y": "리드 수"}, title="follow_up_priority 분포",
        color=priority_counts.index,
        color_discrete_map={"상": "#e74c3c", "중": "#f39c12", "하": "#95a5a6"},
    )
    fig.update_layout(showlegend=False)
    charts["priority"] = fig_to_div(fig)

    matrix = pd.crosstab(df["title"], df["follow_up_priority"])
    matrix = matrix.reindex(index=[t for t in TITLE_ORDER if t in matrix.index], columns=[p for p in PRIORITY_ORDER if p in matrix.columns])
    fig = px.imshow(
        matrix, text_auto=True, aspect="auto",
        labels=dict(x="우선순위", y="직책", color="리드 수"),
        title="직책 × 우선순위 매트릭스", color_continuous_scale="Blues",
    )
    charts["matrix"] = fig_to_div(fig)

    return charts


def summary_cards(df: pd.DataFrame) -> dict:
    return {
        "total": len(df),
        "review_flag_y": int((df["review_flag"] == "Y").sum()),
        "email_missing": int(df["email_missing"].sum()),
        "titles": df["title"].nunique(),
    }


def esc(v) -> str:
    return html.escape(str(v)) if pd.notna(v) else ""


def build_table(df: pd.DataFrame, limit: int | None = None) -> str:
    rows = df if limit is None else df.head(limit)
    trs = []
    for _, r in rows.iterrows():
        flag = r.get("review_flag", "N")
        flag_class = "flag-y" if flag == "Y" else "flag-n"
        missing_badge = '<span class="badge badge-warn">이메일 없음</span>' if r["email_missing"] else ""
        subject = esc(r.get("subject", ""))
        body = esc(r.get("body", ""))
        trs.append(f"""
        <tr data-title="{esc(r['title'])}" data-priority="{esc(r['follow_up_priority'])}" data-flag="{esc(flag)}">
          <td>{esc(r['lead_id'])}</td>
          <td>{esc(r['name'])}</td>
          <td>{esc(r['organization'])}</td>
          <td>{esc(r['title'])}</td>
          <td>{esc(r['follow_up_priority'])}</td>
          <td class="subject-cell">{subject} {missing_badge}</td>
          <td class="body-cell">{body}</td>
          <td class="{flag_class}">{esc(flag)}</td>
        </tr>""")
    return "\n".join(trs)


def render(basic: pd.DataFrame, test: pd.DataFrame) -> str:
    basic_charts = build_charts(basic, first=True)
    test_charts = build_charts(test)
    basic_summary = summary_cards(basic)
    test_summary = summary_cards(test)
    basic_table = build_table(basic)
    test_table = build_table(test, limit=100)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>키즐링 박람회 리드 후속 이메일 대시보드</title>
<style>
  :root {{
    --bg: #f6f7fb; --card: #ffffff; --border: #e5e7eb; --text: #1f2937;
    --muted: #6b7280; --accent: #6366f1;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; font-family: Pretendard, 'Malgun Gothic', 'Segoe UI', sans-serif;
    background: var(--bg); color: var(--text);
  }}
  header {{
    background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #fff;
    padding: 28px 32px;
  }}
  header h1 {{ margin: 0 0 6px; font-size: 22px; }}
  header p {{ margin: 0; opacity: 0.9; font-size: 13px; }}
  main {{ max-width: 1200px; margin: 0 auto; padding: 24px 20px 60px; }}
  section {{ margin-bottom: 40px; }}
  section h2 {{
    font-size: 17px; border-left: 4px solid var(--accent); padding-left: 10px;
    margin-bottom: 16px;
  }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin-bottom: 20px; }}
  .card {{
    background: var(--card); border: 1px solid var(--border); border-radius: 12px;
    padding: 18px; text-align: center;
  }}
  .card .num {{ font-size: 28px; font-weight: 700; color: var(--accent); }}
  .card .label {{ font-size: 12px; color: var(--muted); margin-top: 4px; }}
  .chart-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 16px; }}
  .chart-box {{
    background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 8px;
    overflow: hidden; min-width: 0;
  }}
  .chart-box .plotly-graph-div {{ width: 100% !important; }}
  .filters {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }}
  .filters select, .filters input {{
    padding: 8px 10px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;
  }}
  table {{
    width: 100%; border-collapse: collapse; background: var(--card);
    border: 1px solid var(--border); border-radius: 12px; overflow: hidden; font-size: 12.5px;
  }}
  thead th {{
    background: #f1f2f9; text-align: left; padding: 10px 8px; position: sticky; top: 0;
    border-bottom: 1px solid var(--border);
  }}
  tbody td {{ padding: 9px 8px; border-bottom: 1px solid #f0f0f2; vertical-align: top; }}
  .subject-cell {{ max-width: 260px; }}
  .body-cell {{ max-width: 380px; color: var(--muted); }}
  .flag-y {{ color: #dc2626; font-weight: 700; }}
  .flag-n {{ color: #9ca3af; }}
  .badge {{ display: inline-block; font-size: 10px; padding: 2px 6px; border-radius: 999px; margin-left: 4px; }}
  .badge-warn {{ background: #fef3c7; color: #92400e; }}
  .table-wrap {{ max-height: 640px; overflow: auto; border-radius: 12px; }}
  footer {{ text-align: center; color: var(--muted); font-size: 12px; padding: 20px; }}
  .tabs {{ display: flex; gap: 6px; margin-bottom: 18px; }}
  .tab-btn {{
    padding: 8px 16px; border-radius: 999px; border: 1px solid var(--border); background: #fff;
    cursor: pointer; font-size: 13px;
  }}
  .tab-btn.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}
</style>
</head>
<body>
<header>
  <h1>키즐링 박람회 리드 후속 이메일 대시보드</h1>
  <p>data/leads_sample.csv · output/email_drafts.csv 기반 자동 생성 — scripts/build_dashboard.py</p>
</header>
<main>
  <div class="tabs">
    <button class="tab-btn active" data-tab="basic">Basic 제출물 (50건)</button>
    <button class="tab-btn" data-tab="test">재현성 테스트 (100건)</button>
  </div>

  <div class="tab-panel active" id="tab-basic">
    <section>
      <h2>요약</h2>
      <div class="cards">
        <div class="card"><div class="num">{basic_summary['total']}</div><div class="label">총 리드 수</div></div>
        <div class="card"><div class="num">{basic_summary['review_flag_y']}</div><div class="label">review_flag = Y</div></div>
        <div class="card"><div class="num">{basic_summary['email_missing']}</div><div class="label">이메일 결측</div></div>
        <div class="card"><div class="num">{basic_summary['titles']}</div><div class="label">직책 종류</div></div>
      </div>
    </section>
    <section>
      <h2>분포 차트</h2>
      <div class="chart-grid">
        <div class="chart-box">{basic_charts['title']}</div>
        <div class="chart-box">{basic_charts['feature']}</div>
        <div class="chart-box">{basic_charts['priority']}</div>
        <div class="chart-box">{basic_charts['matrix']}</div>
      </div>
    </section>
    <section>
      <h2>리드별 이메일 초안</h2>
      <div class="filters">
        <select id="basic-title-filter"><option value="">전체 직책</option></select>
        <select id="basic-priority-filter"><option value="">전체 우선순위</option></select>
        <select id="basic-flag-filter">
          <option value="">전체 review_flag</option>
          <option value="Y">Y만</option>
          <option value="N">N만</option>
        </select>
        <input type="text" id="basic-search" placeholder="이름/기관 검색">
      </div>
      <div class="table-wrap">
        <table id="basic-table">
          <thead><tr>
            <th>lead_id</th><th>name</th><th>organization</th><th>title</th>
            <th>priority</th><th>subject</th><th>body</th><th>review_flag</th>
          </tr></thead>
          <tbody>{basic_table}</tbody>
        </table>
      </div>
    </section>
  </div>

  <div class="tab-panel" id="tab-test">
    <section>
      <h2>요약</h2>
      <div class="cards">
        <div class="card"><div class="num">{test_summary['total']}</div><div class="label">총 리드 수</div></div>
        <div class="card"><div class="num">{test_summary['review_flag_y']}</div><div class="label">review_flag = Y</div></div>
        <div class="card"><div class="num">{test_summary['email_missing']}</div><div class="label">이메일 결측</div></div>
        <div class="card"><div class="num">{test_summary['titles']}</div><div class="label">직책 종류</div></div>
      </div>
    </section>
    <section>
      <h2>분포 차트</h2>
      <div class="chart-grid">
        <div class="chart-box">{test_charts['title']}</div>
        <div class="chart-box">{test_charts['feature']}</div>
        <div class="chart-box">{test_charts['priority']}</div>
        <div class="chart-box">{test_charts['matrix']}</div>
      </div>
    </section>
    <section>
      <h2>리드별 이메일 초안 (재현성 테스트, data/leads_dummy_100_test.csv)</h2>
      <div class="filters">
        <select id="test-title-filter"><option value="">전체 직책</option></select>
        <select id="test-priority-filter"><option value="">전체 우선순위</option></select>
        <select id="test-flag-filter">
          <option value="">전체 review_flag</option>
          <option value="Y">Y만</option>
          <option value="N">N만</option>
        </select>
        <input type="text" id="test-search" placeholder="이름/기관 검색">
      </div>
      <div class="table-wrap">
        <table id="test-table">
          <thead><tr>
            <th>lead_id</th><th>name</th><th>organization</th><th>title</th>
            <th>priority</th><th>subject</th><th>body</th><th>review_flag</th>
          </tr></thead>
          <tbody>{test_table}</tbody>
        </table>
      </div>
    </section>
  </div>
</main>
<footer>Generated by scripts/build_dashboard.py — [05] 키즐링 박람회 리드 맞춤 후속 이메일 자동화</footer>

<script>
  document.querySelectorAll('.tab-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
      window.dispatchEvent(new Event('resize'));
    }});
  }});

  function setupFilters(prefix) {{
    const table = document.getElementById(prefix + '-table');
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    const titleSel = document.getElementById(prefix + '-title-filter');
    const prioritySel = document.getElementById(prefix + '-priority-filter');
    const flagSel = document.getElementById(prefix + '-flag-filter');
    const search = document.getElementById(prefix + '-search');

    const titles = [...new Set(rows.map(r => r.dataset.title))].sort();
    titles.forEach(t => {{
      const opt = document.createElement('option');
      opt.value = t; opt.textContent = t;
      titleSel.appendChild(opt);
    }});
    const priorities = [...new Set(rows.map(r => r.dataset.priority))].sort();
    priorities.forEach(p => {{
      const opt = document.createElement('option');
      opt.value = p; opt.textContent = p;
      prioritySel.appendChild(opt);
    }});

    function applyFilter() {{
      const t = titleSel.value, p = prioritySel.value, f = flagSel.value;
      const q = search.value.trim().toLowerCase();
      rows.forEach(r => {{
        const matchesT = !t || r.dataset.title === t;
        const matchesP = !p || r.dataset.priority === p;
        const matchesF = !f || r.dataset.flag === f;
        const matchesQ = !q || r.textContent.toLowerCase().includes(q);
        r.style.display = (matchesT && matchesP && matchesF && matchesQ) ? '' : 'none';
      }});
    }}
    [titleSel, prioritySel, flagSel].forEach(el => el.addEventListener('change', applyFilter));
    search.addEventListener('input', applyFilter);
  }}
  setupFilters('basic');
  setupFilters('test');
</script>
</body>
</html>
"""


def main():
    basic = load_dataset(DATA_DIR / "leads_sample.csv", OUTPUT_DIR / "email_drafts.csv")
    test = load_dataset(DATA_DIR / "leads_dummy_100_test.csv", OUTPUT_DIR / "email_drafts_test.csv")
    html_out = render(basic, test)
    out_path = OUTPUT_DIR / "dashboard.html"
    out_path.write_text(html_out, encoding="utf-8")
    print(f"dashboard written to {out_path}")


if __name__ == "__main__":
    main()
