#!/usr/bin/env python3
"""
report_html.py — Gera relatório HTML no Claude Design System
Integrado ao repo-validation-system
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def render_report(
    repo: str,
    commit: str,
    verdict: str,
    metrics: dict,
    stack: dict,
    strengths: list,
    weaknesses: list,
    ab_results: Optional[dict] = None,
    history: Optional[list] = None,
) -> str:
    verdict_class = {
        "RECOMMENDED": "pill-ok",
        "CONDITIONAL": "pill-warn",
        "NOT RECOMMENDED": "pill-fail",
        "UNABLE TO VALIDATE": "pill-muted",
    }.get(verdict, "pill-muted")

    verdict_icon = {
        "RECOMMENDED": "ti-circle-check-filled",
        "CONDITIONAL": "ti-alert-circle",
        "NOT RECOMMENDED": "ti-circle-x",
        "UNABLE TO VALIDATE": "ti-ban",
    }.get(verdict, "ti-question-mark")

    verdict_bg = {
        "RECOMMENDED": "var(--bg-success)",
        "CONDITIONAL": "var(--bg-warning)",
        "NOT RECOMMENDED": "var(--bg-danger)",
        "UNABLE TO VALIDATE": "var(--surface-1)",
    }.get(verdict, "var(--surface-1)")

    verdict_color = {
        "RECOMMENDED": "var(--text-success)",
        "CONDITIONAL": "var(--text-warning)",
        "NOT RECOMMENDED": "var(--text-danger)",
        "UNABLE TO VALIDATE": "var(--text-muted)",
    }.get(verdict, "var(--text-muted)")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tests_pass = metrics.get("tests_pass", 0)
    tests_total = metrics.get("tests_total", 0)
    pass_rate = metrics.get("tests_pass_rate", 0)
    coverage = metrics.get("coverage")
    build = metrics.get("build_success", False)
    lint = metrics.get("lint_errors", 0)
    vulns_crit = metrics.get("vulns_critical", 0)
    vulns = metrics.get("vulns", 0)
    test_time = metrics.get("test_time_seconds")
    code_files = metrics.get("code_files", 0)
    loc = metrics.get("loc_approx")
    size_mb = metrics.get("repo_size_mb")

    lang = stack.get("language", "?")
    pm = stack.get("package_manager", "?")
    tf = stack.get("test_framework", "?")
    has_docker = stack.get("has_docker", False)
    has_ci = stack.get("has_ci", False)

    ab_section = ""
    if ab_results:
        rows = ""
        for t in ab_results.get("tasks", []):
            delta_ctrl = t.get("delta_vs_control", "—")
            delta_base = t.get("delta_vs_baseline", "—")
            cls_ctrl = "delta-good" if isinstance(delta_ctrl, (int, float)) and delta_ctrl < 0 else "delta-bad"
            cls_base = "delta-good" if isinstance(delta_base, (int, float)) and delta_base < 0 else "delta-bad"
            rows += f"""<tr>
              <td>{t.get('name','')}</td>
              <td>{t.get('baseline_loc','—')}</td>
              <td>{t.get('control_loc','—')}</td>
              <td>{t.get('treatment_loc','—')}</td>
              <td class="{cls_ctrl}">{delta_ctrl if isinstance(delta_ctrl, str) else f"{delta_ctrl:+.0f}%"}</td>
              <td class="{cls_base}">{delta_base if isinstance(delta_base, str) else f"{delta_base:+.0f}%"}</td>
            </tr>"""
        mean_ctrl = ab_results.get("mean_delta_vs_control", "—")
        mean_base = ab_results.get("mean_delta_vs_baseline", "—")
        ab_section = f"""
        <div id="panel-benchmark" class="rvs-panel">
          <div class="rvs-section-label">Resultados por tarefa (LOC)</div>
          <div class="rvs-card" style="padding:0;overflow:hidden">
            <table class="rvs-ab-table">
              <thead><tr>
                <th>Tarefa</th><th>Agente solto</th><th>Só "breve"</th>
                <th>Com a skill</th><th>Ganho skill</th><th>vs solto</th>
              </tr></thead>
              <tbody>
                {rows}
                <tr>
                  <td><strong>média</strong></td><td>—</td><td>—</td><td>—</td>
                  <td class="delta-good"><strong>{mean_ctrl if isinstance(mean_ctrl, str) else f"{mean_ctrl:+.0f}%"}</strong></td>
                  <td class="delta-good"><strong>{mean_base if isinstance(mean_base, str) else f"{mean_base:+.0f}%"}</strong></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>"""

    strengths_html = "".join(
        f'<li><i class="ti ti-circle-check" style="color:var(--text-success)"></i> {s}</li>'
        for s in strengths
    ) or "<li>Nenhum identificado</li>"

    weaknesses_html = "".join(
        f'<li><i class="ti ti-alert-circle" style="color:var(--text-warning)"></i> {w}</li>'
        for w in weaknesses
    ) or "<li>Nenhum identificado</li>"

    stack_pills = "".join(
        f'<span class="rvs-pill pill-muted">{s}</span>'
        for s in [lang, pm, tf,
                  "Docker" if has_docker else None,
                  "CI/CD" if has_ci else None]
        if s
    )

    history_rows = ""
    if history:
        for ev in history:
            vc = {"RECOMMENDED": "pill-ok", "CONDITIONAL": "pill-warn",
                  "NOT RECOMMENDED": "pill-fail"}.get(ev.get("verdict", ""), "pill-muted")
            pr = ev.get("metrics", {}).get("tests_pass_rate")
            cov = ev.get("metrics", {}).get("coverage")
            history_rows += f"""<tr>
              <td>{ev.get('repo','')}</td>
              <td>{ev.get('date','')[:10]}</td>
              <td><span class="rvs-pill {vc}">{ev.get('verdict','')}</span></td>
              <td>{f"{pr:.0f}%" if pr is not None else "—"}</td>
              <td>{f"{cov:.0f}%" if cov is not None else "—"}</td>
            </tr>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Repo Validation — {repo}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&family=Source+Serif+4:ital,opsz,wght@0,8..60,200..900;1,8..60,200..900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.19.0/dist/tabler-icons.min.css">
<style>
:root{{
  --surface-0:#f5f4f0;--surface-1:#f0efeb;--surface-2:#ffffff;
  --text-primary:#0b0b0b;--text-secondary:#52514e;--text-muted:#898781;
  --border:rgba(11,11,11,0.10);--border-strong:rgba(11,11,11,0.18);
  --bg-success:#eaf3de;--text-success:#3b6d11;--border-success:#97c459;
  --bg-warning:#faeeda;--text-warning:#854f0b;--border-warning:#eda100;
  --bg-danger:#fcebeb;--text-danger:#a32d2d;--border-danger:#e24b4a;
  --bg-accent:#e6f1fb;--text-accent:#185fa5;--border-accent:#378add;--fill-accent:#378add;
  --bg-neutral:#f1efe8;--font-sans:"Inter",system-ui,sans-serif;
  --font-mono:ui-monospace,Menlo,Consolas,monospace;
  --font-voice:"Source Serif 4",Georgia,serif;
  --radius:8px;
}}
@media(prefers-color-scheme:dark){{
  :root{{
    --surface-0:#141413;--surface-1:#1a1a19;--surface-2:#242422;
    --text-primary:#ffffff;--text-secondary:#c3c2b7;--text-muted:#898781;
    --border:rgba(255,255,255,0.10);--border-strong:rgba(255,255,255,0.18);
    --bg-success:#173404;--text-success:#c0dd97;--border-success:#3b6d11;
    --bg-warning:#412402;--text-warning:#fac775;--border-warning:#854f0b;
    --bg-danger:#501313;--text-danger:#f7c1c1;--border-danger:#a32d2d;
    --bg-accent:#042c53;--text-accent:#b5d4f4;--border-accent:#185fa5;--fill-accent:#185fa5;
  }}
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--surface-0);color:var(--text-primary);font-family:var(--font-sans);
  line-height:1.6;padding:2.5rem 1.25rem;max-width:760px;margin:0 auto;font-size:15px}}
.sr-only{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}}
.rvs-badge{{display:inline-flex;align-items:center;gap:6px;background:var(--bg-accent);
  color:var(--text-accent);border:0.5px solid var(--border-accent);border-radius:var(--radius);
  padding:4px 12px;font-size:12px;margin-bottom:1.5rem;font-family:var(--font-mono)}}
h1{{font-size:22px;font-weight:500;color:var(--text-primary);margin:0 0 4px}}
.rvs-meta{{font-size:13px;color:var(--text-muted);margin:0;font-family:var(--font-mono)}}
.rvs-section-label{{font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:.09em;
  color:var(--text-muted);margin-bottom:.65rem}}
.rvs-kpi-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin:1rem 0}}
.rvs-kpi{{background:var(--surface-1);border:0.5px solid var(--border);border-radius:var(--radius);padding:.9rem 1.1rem}}
.rvs-kpi-num{{font-size:26px;font-weight:500;color:var(--text-primary);line-height:1;margin-bottom:3px;font-family:var(--font-mono)}}
.rvs-kpi-num.success{{color:var(--text-success)}}
.rvs-kpi-num.accent{{color:var(--text-accent)}}
.rvs-kpi-num.warning{{color:var(--text-warning)}}
.rvs-kpi-label{{font-size:11px;color:var(--text-muted)}}
.rvs-verdict{{display:flex;align-items:center;gap:12px;background:{verdict_bg};
  border:0.5px solid {verdict_color};border-radius:var(--radius);padding:1rem 1.25rem;margin:1rem 0}}
.rvs-verdict i{{font-size:22px;color:{verdict_color}}}
.rvs-verdict-text{{font-size:15px;font-weight:500;color:{verdict_color}}}
.rvs-verdict-sub{{font-size:12px;color:var(--text-muted);margin-top:2px}}
.rvs-card{{background:var(--surface-2);border:0.5px solid var(--border);border-radius:12px;padding:.9rem 1.1rem;margin-bottom:.85rem}}
.rvs-card h3{{font-size:13px;font-weight:500;color:var(--text-primary);margin:0 0 .65rem}}
.rvs-metric-row{{display:flex;justify-content:space-between;align-items:center;
  padding:5px 0;border-bottom:0.5px solid var(--border)}}
.rvs-metric-row:last-child{{border-bottom:none}}
.rvs-metric-name{{font-size:13px;color:var(--text-secondary);display:flex;align-items:center;gap:6px}}
.rvs-metric-name i{{font-size:14px;color:var(--text-muted)}}
.rvs-metric-val{{font-size:12px;font-weight:500;color:var(--text-primary);font-family:var(--font-mono);display:flex;align-items:center;gap:6px}}
.rvs-pill{{display:inline-flex;align-items:center;gap:3px;border-radius:20px;
  padding:2px 9px;font-size:11px;font-weight:500;font-family:var(--font-mono)}}
.pill-ok{{background:var(--bg-success);color:var(--text-success)}}
.pill-warn{{background:var(--bg-warning);color:var(--text-warning)}}
.pill-fail{{background:var(--bg-danger);color:var(--text-danger)}}
.pill-muted{{background:var(--surface-1);color:var(--text-muted);border:0.5px solid var(--border)}}
.rvs-tab-row{{display:flex;gap:4px;margin:1.5rem 0 .75rem;flex-wrap:wrap}}
.rvs-tab{{background:transparent;border:0.5px solid var(--border);border-radius:var(--radius);
  padding:5px 14px;font-size:13px;color:var(--text-secondary);cursor:pointer;font-family:var(--font-sans)}}
.rvs-tab.active{{background:var(--bg-accent);color:var(--text-accent);border-color:var(--border-accent)}}
.rvs-panel{{display:none}}.rvs-panel.active{{display:block}}
.rvs-stack-row{{display:flex;flex-wrap:wrap;gap:5px;margin-top:.5rem}}
.rvs-check-list{{list-style:none;padding:0;margin:0}}
.rvs-check-list li{{display:flex;align-items:center;gap:8px;padding:6px 0;
  border-bottom:0.5px solid var(--border);font-size:13px;color:var(--text-secondary)}}
.rvs-check-list li:last-child{{border-bottom:none}}
.rvs-check-list i{{font-size:14px;flex-shrink:0}}
.rvs-callout{{background:var(--bg-accent);border:0.5px solid var(--border-accent);
  border-left:3px solid var(--fill-accent);border-radius:var(--radius);padding:.9rem 1.1rem;margin:.9rem 0;
  font-size:13px;color:var(--text-primary)}}
.rvs-callout strong{{color:var(--text-accent)}}
.rvs-ab-table{{width:100%;border-collapse:collapse;font-size:12px}}
.rvs-ab-table th{{text-align:left;padding:7px 10px;font-size:11px;font-weight:500;color:var(--text-muted);
  text-transform:uppercase;letter-spacing:.06em;border-bottom:0.5px solid var(--border)}}
.rvs-ab-table th:not(:first-child){{text-align:right}}
.rvs-ab-table td{{padding:8px 10px;border-bottom:0.5px solid var(--border);
  color:var(--text-secondary);font-family:var(--font-mono)}}
.rvs-ab-table td:first-child{{color:var(--text-primary);font-family:var(--font-sans);font-size:13px;font-weight:500}}
.rvs-ab-table td:not(:first-child){{text-align:right}}
.rvs-ab-table tr:last-child td{{border-bottom:none;font-weight:500}}
.delta-good{{color:var(--text-success)}}.delta-bad{{color:var(--text-danger)}}
.rvs-arms{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:1rem}}
.rvs-arm{{background:var(--surface-1);border:0.5px solid var(--border);border-radius:var(--radius);padding:10px}}
.rvs-arm.featured{{background:var(--bg-accent);border-color:var(--border-accent)}}
.rvs-arm-label{{font-size:10px;text-transform:uppercase;letter-spacing:.09em;color:var(--text-muted);margin-bottom:3px}}
.rvs-arm-name{{font-size:12px;font-weight:500;font-family:var(--font-mono);color:var(--text-primary);margin-bottom:3px}}
.rvs-arm.featured .rvs-arm-name{{color:var(--text-accent)}}
.rvs-arm-desc{{font-size:11px;color:var(--text-muted)}}
.chart-wrap{{position:relative;width:100%;height:220px;margin:.75rem 0}}
hr{{border:none;border-top:0.5px solid var(--border);margin:2rem 0}}
.rvs-footer{{display:flex;justify-content:space-between;align-items:center;
  font-size:11px;color:var(--text-muted);font-family:var(--font-mono)}}
</style>
</head>
<body>
<h2 class="sr-only">Repo Validation System — relatório de validação de {repo}</h2>

<div class="rvs-badge">
  <i class="ti ti-shield-check" aria-hidden="true"></i>
  repo-validation-system · v1.0.0
</div>

<h1>{repo}</h1>
<p class="rvs-meta">commit {commit} · {now}</p>

<div class="rvs-tab-row" role="tablist">
  <button class="rvs-tab active" onclick="switchTab('validator')" role="tab" aria-selected="true">
    <i class="ti ti-shield-check" aria-hidden="true"></i> Validação
  </button>
  <button class="rvs-tab" onclick="switchTab('benchmark')" role="tab" aria-selected="false">
    <i class="ti ti-test-pipe" aria-hidden="true"></i> Benchmark A/B
  </button>
  {"" if not history else '<button class="rvs-tab" onclick="switchTab(\'history\')" role="tab" aria-selected="false"><i class="ti ti-history" aria-hidden="true"></i> Histórico</button>'}
</div>

<div id="panel-validator" class="rvs-panel active">

  <div class="rvs-verdict" role="status">
    <i class="ti {verdict_icon}" aria-hidden="true"></i>
    <div>
      <div class="rvs-verdict-text">{verdict}</div>
      <div class="rvs-verdict-sub">Testes {pass_rate:.0f}% · Coverage {"N/A" if coverage is None else f"{coverage:.0f}%"} · {vulns_crit} vulns críticas · Build {"✓" if build else "✗"}</div>
    </div>
  </div>

  <div class="rvs-kpi-row">
    <div class="rvs-kpi"><div class="rvs-kpi-num {"success" if pass_rate >= 90 else "warning" if pass_rate >= 70 else "danger"}">{pass_rate:.0f}%</div><div class="rvs-kpi-label">taxa de aprovação</div></div>
    <div class="rvs-kpi"><div class="rvs-kpi-num accent">{"N/A" if coverage is None else f"{coverage:.0f}%"}</div><div class="rvs-kpi-label">cobertura</div></div>
    {"" if test_time is None else f'<div class="rvs-kpi"><div class="rvs-kpi-num">{test_time:.1f}s</div><div class="rvs-kpi-label">tempo de testes</div></div>'}
    <div class="rvs-kpi"><div class="rvs-kpi-num {"success" if vulns_crit == 0 else "danger"}">{vulns_crit}</div><div class="rvs-kpi-label">vulns críticas</div></div>
  </div>

  <div class="chart-wrap">
    <canvas id="metricsChart" role="img" aria-label="Métricas: aprovação {pass_rate:.0f}%, cobertura {"N/A" if coverage is None else f"{coverage:.0f}%"}, build {"ok" if build else "falhou"}">Aprovação {pass_rate:.0f}%, cobertura {"N/A" if coverage is None else f"{coverage:.0f}%"}.</canvas>
  </div>

  <div class="rvs-section-label">Métricas detalhadas</div>
  <div class="rvs-card">
    <h3>Qualidade de testes</h3>
    <div class="rvs-metric-row"><span class="rvs-metric-name"><i class="ti ti-check" aria-hidden="true"></i>Testes aprovados</span><span class="rvs-metric-val">{tests_pass} / {tests_total} <span class="rvs-pill {"pill-ok" if pass_rate >= 90 else "pill-warn"}">{pass_rate:.0f}%</span></span></div>
    <div class="rvs-metric-row"><span class="rvs-metric-name"><i class="ti ti-percentage" aria-hidden="true"></i>Cobertura</span><span class="rvs-metric-val">{"N/A" if coverage is None else f"{coverage:.1f}%"} <span class="rvs-pill {"pill-ok" if coverage is not None and coverage >= 70 else "pill-warn" if coverage is not None else "pill-muted"}">{"✓" if coverage is not None and coverage >= 70 else "⚠" if coverage is not None else "—"}</span></span></div>
    {"" if test_time is None else f'<div class="rvs-metric-row"><span class="rvs-metric-name"><i class="ti ti-clock" aria-hidden="true"></i>Tempo</span><span class="rvs-metric-val">{test_time:.1f}s</span></div>'}
  </div>

  <div class="rvs-card">
    <h3>Build e segurança</h3>
    <div class="rvs-metric-row"><span class="rvs-metric-name"><i class="ti ti-package" aria-hidden="true"></i>Build</span><span class="rvs-metric-val"><span class="rvs-pill {"pill-ok" if build else "pill-fail"}">{"sucesso" if build else "falhou"}</span></span></div>
    <div class="rvs-metric-row"><span class="rvs-metric-name"><i class="ti ti-alert-triangle" aria-hidden="true"></i>Lint</span><span class="rvs-metric-val">{lint} erros <span class="rvs-pill {"pill-ok" if lint == 0 else "pill-warn"}">{"limpo" if lint == 0 else "revisar"}</span></span></div>
    <div class="rvs-metric-row"><span class="rvs-metric-name"><i class="ti ti-shield" aria-hidden="true"></i>Vulns</span><span class="rvs-metric-val">{vulns} total · {vulns_crit} críticas <span class="rvs-pill {"pill-ok" if vulns_crit == 0 else "pill-fail"}">{"ok" if vulns_crit == 0 else "bloquear"}</span></span></div>
  </div>

  <div class="rvs-card">
    <h3>Stack detectada</h3>
    <div class="rvs-stack-row">{stack_pills}</div>
    <div class="rvs-metric-row" style="margin-top:.65rem"><span class="rvs-metric-name"><i class="ti ti-files" aria-hidden="true"></i>Arquivos de código</span><span class="rvs-metric-val">{code_files}</span></div>
    {"" if loc is None else f'<div class="rvs-metric-row"><span class="rvs-metric-name"><i class="ti ti-file-code" aria-hidden="true"></i>Linhas (aprox.)</span><span class="rvs-metric-val">{loc:,}</span></div>'}
    {"" if size_mb is None else f'<div class="rvs-metric-row"><span class="rvs-metric-name"><i class="ti ti-database" aria-hidden="true"></i>Tamanho</span><span class="rvs-metric-val">{size_mb:.1f} MB</span></div>'}
  </div>

  {"<div class='rvs-section-label'>Pontos fortes</div><div class='rvs-card'><ul class='rvs-check-list'>" + strengths_html + "</ul></div>" if strengths else ""}
  {"<div class='rvs-section-label'>Pontos fracos</div><div class='rvs-card'><ul class='rvs-check-list'>" + weaknesses_html + "</ul></div>" if weaknesses else ""}

</div>

{ab_section}

{"" if not history else f'''<div id="panel-history" class="rvs-panel">
  <div class="rvs-section-label">Avaliações anteriores</div>
  <div class="rvs-card" style="padding:0;overflow:hidden">
    <table class="rvs-ab-table">
      <thead><tr><th>Repo</th><th>Data</th><th>Veredito</th><th>Aprovação</th><th>Coverage</th></tr></thead>
      <tbody>{history_rows}</tbody>
    </table>
  </div>
</div>'''}

<hr>
<div class="rvs-footer">
  <span>repo-validation-system · github.com/juliopessan/repo-validation-system</span>
  <span>{now}</span>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
function switchTab(id){{
  const ids=['validator','benchmark','history'];
  document.querySelectorAll('.rvs-tab').forEach((t,i)=>{{
    t.classList.toggle('active',ids[i]===id);
    t.setAttribute('aria-selected',ids[i]===id);
  }});
  document.querySelectorAll('.rvs-panel').forEach(p=>{{
    p.classList.toggle('active',p.id==='panel-'+id);
  }});
}}
const isDark=matchMedia('(prefers-color-scheme:dark)').matches;
const gc=isDark?'rgba(255,255,255,0.07)':'rgba(0,0,0,0.07)';
const tc=isDark?'#898781':'#898781';
const f={{family:'"Inter",system-ui,sans-serif',size:12}};
const passRate={pass_rate:.1f};
const coverage={coverage if coverage is not None else 0};
const build={1 if build else 0};
const lint={lint};
new Chart(document.getElementById('metricsChart'),{{
  type:'bar',
  data:{{
    labels:['Aprovação','Coverage','Lint ok','Build ok'],
    datasets:[{{
      label:'Resultado',
      data:[passRate,coverage,lint===0?100:0,build*100],
      backgroundColor:[
        passRate>=90?'rgba(10,163,12,0.8)':passRate>=70?'rgba(237,161,0,0.8)':'rgba(208,59,59,0.8)',
        coverage>=70?'rgba(42,120,214,0.8)':coverage>=40?'rgba(237,161,0,0.8)':'rgba(208,59,59,0.8)',
        lint===0?'rgba(10,163,12,0.8)':'rgba(237,161,0,0.8)',
        build===1?'rgba(10,163,12,0.8)':'rgba(208,59,59,0.8)'
      ],
      borderRadius:4,borderSkipped:false
    }},{{
      label:'Threshold RECOMMENDED',data:[90,70,null,null],type:'line',
      borderColor:'rgba(237,161,0,0.6)',borderDash:[4,3],borderWidth:1.5,
      pointRadius:0,fill:false
    }}]
  }},
  options:{{
    responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{display:false}}}},
    scales:{{
      x:{{ticks:{{color:tc,font:f}},grid:{{display:false}}}},
      y:{{min:0,max:110,ticks:{{color:tc,font:f,callback:v=>v+'%'}},grid:{{color:gc,lineWidth:0.5}}}}
    }}
  }}
}});
</script>
</body>
</html>"""


def save_report(
    output_path: Path,
    repo: str,
    commit: str = "unknown",
    verdict: str = "UNABLE TO VALIDATE",
    metrics: Optional[dict] = None,
    stack: Optional[dict] = None,
    strengths: Optional[list] = None,
    weaknesses: Optional[list] = None,
    ab_results: Optional[dict] = None,
    history: Optional[list] = None,
) -> Path:
    html = render_report(
        repo=repo,
        commit=commit,
        verdict=verdict,
        metrics=metrics or {},
        stack=stack or {},
        strengths=strengths or [],
        weaknesses=weaknesses or [],
        ab_results=ab_results,
        history=history,
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    p = save_report(
        output_path="/tmp/sample-report.html",
        repo="juliopessan/arch-review-assistant",
        commit="a3f9c21",
        verdict="RECOMMENDED",
        metrics={
            "tests_pass": 119, "tests_total": 128, "tests_pass_rate": 93.0,
            "coverage": 78.3, "build_success": True,
            "lint_errors": 0, "vulns": 1, "vulns_critical": 0,
            "test_time_seconds": 3.2, "repo_size_mb": 12.5, "code_files": 38, "loc_approx": 4915,
        },
        stack={"language": "Python", "package_manager": "pip", "test_framework": "pytest",
               "has_docker": True, "has_ci": True},
        strengths=["Containerização com Docker", "Pipeline CI/CD configurado", "128 testes cobrindo todos os módulos"],
        weaknesses=["1 dependência high severity (dev only)", "Coverage de 78% — espaço para crescer"],
        history=[
            {"repo": "arch-review-assistant", "date": "2026-06-25", "verdict": "RECOMMENDED",
             "metrics": {"tests_pass_rate": 93, "coverage": 78}},
            {"repo": "ai-cost-optimizer", "date": "2026-06-18", "verdict": "CONDITIONAL",
             "metrics": {"tests_pass_rate": 74, "coverage": 43}},
        ],
    )
    print(f"Report saved to: {p}")
