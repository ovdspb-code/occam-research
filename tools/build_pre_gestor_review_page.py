#!/usr/bin/env python
"""Build the public static Pre-Gestor review console."""

from __future__ import annotations

import argparse
import html
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


DOMAIN_LABELS = {
    "authority_interactions": "Authority procedures",
    "case_doctrine_watchlist": "Doctrine watchlist",
    "corporate_tax_sl": "Corporate tax",
    "direct_tax_irpf_autonomo": "IRPF autonomo",
    "direct_tax_irpf_personal": "IRPF personal",
    "fiscal_calendar": "Core forms",
    "foreign_assets_international_tax": "IRNR / foreign assets",
    "inbound_immigration_tax": "Inbound / immigration",
    "indirect_tax_iva_igic": "IVA / IGIC",
    "local_municipal_tax": "Local municipal",
    "property_transfer_wealth_inheritance": "Property / wealth",
    "rights_benefits_relief": "Rights / relief",
    "social_security_reta_labor": "Social security",
    "territorial_jurisdiction": "Territory",
}

FOCUS_QUEUE = {
    "corporate.model_202_payment_on_account": {
        "label": "Gestor queue",
        "es": "Confirmar coeficientes de Modelo 202: 18%, 5/7 y 19/20, y la ruta 40.2 vs 40.3.",
        "ru": "Подтвердить коэффициенты Modelo 202: 18%, 5/7 и 19/20, и маршрут 40.2 vs 40.3.",
        "en": "Confirm Modelo 202 coefficients: 18%, 5/7 and 19/20, and the 40.2 vs 40.3 route.",
    },
    "common.corporate.model_200_202_candidate": {
        "label": "Gestor queue",
        "es": "Confirmar si la regla común 200/202 separa correctamente cierre contable, calendario y obligación de pago fraccionado.",
        "ru": "Подтвердить, что общее правило 200/202 корректно разделяет закрытие, календарь и обязанность авансового платежа.",
        "en": "Confirm that the common 200/202 route separates accounting close, calendar visibility and payment-on-account obligation.",
    },
    "procedure.appeals_sanctions_prescription": {
        "label": "Gestor queue",
        "es": "Confirmar LGT art. 188: reducciones 65/30/40 y condiciones de recurso/pago.",
        "ru": "Подтвердить LGT art. 188: reductions 65/30/40 и условия жалобы/оплаты.",
        "en": "Confirm LGT art. 188 reductions 65/30/40 and appeal/payment conditions.",
    },
    "inbound.beckham.art93_candidate": {
        "label": "Gestor queue",
        "es": "Confirmar cuerpos estatutarios Art. 93 LIRPF / Art. 116 RIRPF y plazos Modelos 149/151.",
        "ru": "Подтвердить тела норм Art. 93 LIRPF / Art. 116 RIRPF и сроки Modelos 149/151.",
        "en": "Confirm statutory bodies Art. 93 LIRPF / Art. 116 RIRPF and Modelo 149/151 timing.",
    },
    "doctrine.art93.director.property.escalation": {
        "label": "Gestor queue",
        "es": "Confirmar límites Beckham para administradores, participación y vivienda urbana.",
        "ru": "Подтвердить Beckham-ограничения для администраторов, доли участия и городской недвижимости.",
        "en": "Confirm Beckham limits for directors, shareholding and urban-property facts.",
    },
}


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    return " ".join(str(value).split())


def _short(value: str, limit: int = 260) -> str:
    value = _string(value)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def _load_source_registry(data_dir: Path) -> dict[str, dict[str, Any]]:
    sources: dict[str, dict[str, Any]] = {}
    for path in sorted((data_dir / "source_registry").glob("*.yaml")):
        raw = _load_yaml(path)
        for source_id, source in (raw.get("sources") or {}).items():
            sources[str(source_id)] = dict(source or {})
    return sources


def _source_from_claim(source_id: str, claim: dict[str, Any] | None, registry: dict[str, dict[str, Any]]) -> dict[str, Any]:
    registered = registry.get(source_id, {})
    claim = claim or {}
    return {
        "source_id": source_id,
        "title": _string(registered.get("title") or claim.get("support_anchor") or source_id),
        "url": _string(claim.get("source_url") or registered.get("source_url")),
        "support_anchor": _string(claim.get("support_anchor")),
        "claim": _string(claim.get("claim")),
        "support_state": _string(claim.get("claim_supported_by_source") or "unknown"),
        "last_checked": _string(claim.get("last_checked") or registered.get("last_checked")),
        "review_status": _string(claim.get("review_status") or registered.get("review_status")),
        "jurisdiction": _string(claim.get("jurisdiction") or registered.get("jurisdiction")),
    }


def _git_commit(path: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=path, text=True).strip()
    except Exception:
        return "unknown"


def _build_dataset(data_dir: Path, source_label: str, source_commit: str) -> dict[str, Any]:
    registry = _load_source_registry(data_dir)
    rules: list[dict[str, Any]] = []
    rule_dir = data_dir / "rule_packs"
    for pack_path in sorted(rule_dir.glob("*.yaml")):
        pack = _load_yaml(pack_path)
        domain_id = _string(pack.get("domain_id"))
        for rule in _as_list(pack.get("rules")):
            recommendation = rule.get("recommendation") or {}
            display = recommendation.get("display_text") or {}
            logic = recommendation.get("logic_profile") or {}
            params = recommendation.get("parameters") or {}
            structured_values = params.get("structured_values") or {}
            claims_by_id = {
                _string(claim.get("source_id")): claim
                for claim in _as_list(recommendation.get("source_claims"))
                if isinstance(claim, dict)
            }
            source_ids = [_string(item) for item in _as_list(recommendation.get("source_ids"))]
            sources = [_source_from_claim(source_id, claims_by_id.get(source_id), registry) for source_id in source_ids]
            rule_id = _string(rule.get("rule_id"))
            focus = FOCUS_QUEUE.get(rule_id)
            risk_flags = [
                {
                    "code": _string(item.get("code")),
                    "severity": _string(item.get("severity")),
                    "message": _string(item.get("message")),
                }
                for item in _as_list(recommendation.get("risk_flags"))
                if isinstance(item, dict)
            ]
            tags = []
            if focus:
                tags.append("gestor_queue")
            if logic.get("high_stakes"):
                tags.append("high_stakes")
            if any(source.get("support_state") != "yes" for source in sources):
                tags.append("source_attention")
            if any("unverifiable" in source.get("review_status", "") for source in sources):
                tags.append("unverifiable_by_fetch")
            rules.append(
                {
                    "index": len(rules) + 1,
                    "type": "rule",
                    "rule_id": rule_id,
                    "rule_pack_id": _string(pack.get("rule_pack_id")),
                    "pack_file": pack_path.name,
                    "domain_id": domain_id,
                    "domain_label": DOMAIN_LABELS.get(domain_id, domain_id),
                    "scenario": _string(rule.get("scenario")),
                    "priority": rule.get("priority"),
                    "confidence": rule.get("confidence"),
                    "gestor_review_state": _string(rule.get("gestor_review_state") or "unreviewed"),
                    "high_stakes": bool(logic.get("high_stakes")),
                    "rule_type": _string(logic.get("rule_type")),
                    "valid_from": _string((rule.get("triggers") or {}).get("period_scope", {}).get("valid_from") or pack.get("valid_from")),
                    "valid_until": _string((rule.get("triggers") or {}).get("period_scope", {}).get("valid_until") or pack.get("valid_until")),
                    "texts": {
                        "es": {
                            "title": _short(display.get("es") or recommendation.get("summary")),
                            "summary": _string(display.get("es") or recommendation.get("summary")),
                            "practical": _string(recommendation.get("practical_answer")),
                        },
                        "ru": {
                            "title": _short(display.get("ru") or recommendation.get("summary")),
                            "summary": _string(display.get("ru") or recommendation.get("summary")),
                            "practical": _string(recommendation.get("practical_answer")),
                        },
                        "en": {
                            "title": _short(recommendation.get("summary")),
                            "summary": _string(recommendation.get("summary")),
                            "practical": _string(recommendation.get("practical_answer")),
                        },
                    },
                    "focus_question": focus,
                    "next_actions": [_string(item) for item in _as_list(recommendation.get("next_actions"))],
                    "evidence_needed": [_string(item) for item in _as_list(recommendation.get("evidence_needed"))],
                    "open_questions": [_string(item) for item in _as_list(recommendation.get("open_questions"))],
                    "risk_flags": risk_flags,
                    "structured_values": structured_values,
                    "forms": _as_list(params.get("form_ids")),
                    "sources": sources,
                    "tags": tags,
                    "reward_eur": 1,
                }
            )
    return {
        "schema": "pre_gestor_public_review_console.v2",
        "dataset_id": "pre-gestor-a1-2026-06-19-legal-audit",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": {
            "label": source_label,
            "commit": source_commit,
            "rule_count": len(rules),
            "review_unit_credit_eur": 1,
        },
        "stats": {
            "rules_total": len(rules),
            "gestor_queue": sum(1 for rule in rules if "gestor_queue" in rule["tags"]),
            "source_attention": sum(1 for rule in rules if "source_attention" in rule["tags"]),
            "high_stakes": sum(1 for rule in rules if rule["high_stakes"]),
        },
        "rules": rules,
    }


def _page_template(dataset_json: str, generated_at: str) -> str:
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Pre-Gestor expert review console for Spanish fiscal rules.">
  <link rel="icon" href="../favicon.ico">
  <title>Pre-Gestor Expert Review · Occam</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f6f8;
      --panel: #ffffff;
      --panel-2: #f8fafc;
      --ink: #172033;
      --muted: #667085;
      --faint: #98a2b3;
      --line: #d9e0ea;
      --line-soft: #e8edf3;
      --navy: #142b51;
      --teal: #0f766e;
      --teal-soft: #e7f5f2;
      --burgundy: #9f174f;
      --burgundy-soft: #fde8f1;
      --amber: #b45309;
      --amber-soft: #fff4df;
      --red: #b42318;
      --red-soft: #feeceb;
      --green: #047857;
      --green-soft: #e8f7ee;
      --violet: #5b4bb2;
      --violet-soft: #eeecfb;
      --shadow: 0 18px 48px rgba(20, 43, 81, .10);
      --shadow-sm: 0 6px 20px rgba(20, 43, 81, .07);
      --radius: 8px;
      --font: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --mono: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: var(--font);
      color: var(--ink);
      background:
        linear-gradient(180deg, #eef2f7 0, #f7f9fb 280px, var(--bg) 100%);
      -webkit-font-smoothing: antialiased;
      line-height: 1.5;
    }}
    a {{ color: var(--teal); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    button, input, textarea, select {{ font: inherit; }}
    button {{ cursor: pointer; }}
    .app {{ max-width: 1540px; margin: 0 auto; padding: 20px; }}
    .topbar {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: start;
      margin-bottom: 16px;
    }}
    .brandline {{ display: flex; gap: 12px; align-items: center; min-width: 0; }}
    .mark {{
      width: 42px;
      height: 42px;
      border-radius: var(--radius);
      display: grid;
      place-items: center;
      background: var(--navy);
      color: white;
      font-weight: 800;
      letter-spacing: .02em;
      flex: 0 0 auto;
    }}
    h1 {{ margin: 0; font-size: 24px; line-height: 1.1; letter-spacing: 0; }}
    .subtitle {{ margin: 5px 0 0; color: var(--muted); max-width: 980px; font-size: 14px; }}
    .toolbar {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }}
    .segmented, .compact-group {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow-sm);
    }}
    .segmented button, .btn, .chip, .choice {{
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
      border-radius: 7px;
      min-height: 36px;
      padding: 8px 11px;
      font-weight: 700;
      font-size: 13px;
    }}
    .segmented button.active, .chip.active {{
      background: var(--navy);
      border-color: var(--navy);
      color: #fff;
    }}
    .btn.primary {{ background: var(--teal); border-color: var(--teal); color: #fff; }}
    .btn.subtle {{ background: var(--panel-2); }}
    .btn:disabled {{ opacity: .45; cursor: not-allowed; }}
    .meta-strip {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }}
    .metric {{
      background: rgba(255,255,255,.92);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 12px;
      box-shadow: var(--shadow-sm);
      min-height: 78px;
    }}
    .metric b {{ display: block; font-size: 24px; line-height: 1; margin-bottom: 7px; font-variant-numeric: tabular-nums; }}
    .metric span {{ color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }}
    .layout {{
      display: grid;
      grid-template-columns: 330px minmax(0, 1fr) 360px;
      gap: 14px;
      align-items: start;
    }}
    .panel {{
      background: rgba(255,255,255,.96);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }}
    .panel-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px;
      border-bottom: 1px solid var(--line-soft);
    }}
    .panel-title {{ font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }}
    .pad {{ padding: 14px; }}
    .field {{ display: grid; gap: 6px; margin-bottom: 12px; }}
    label {{ color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: .04em; }}
    input, textarea, select {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: #fff;
      color: var(--ink);
      padding: 10px 11px;
      min-height: 40px;
    }}
    textarea {{ min-height: 112px; resize: vertical; line-height: 1.45; }}
    .filters {{ display: flex; flex-wrap: wrap; gap: 7px; }}
    .chip {{ min-height: 32px; padding: 6px 9px; }}
    .queue-list {{ max-height: calc(100vh - 318px); overflow: auto; border-top: 1px solid var(--line-soft); }}
    .queue-row {{
      width: 100%;
      display: grid;
      grid-template-columns: 28px minmax(0, 1fr) auto;
      gap: 9px;
      align-items: center;
      border: 0;
      border-bottom: 1px solid var(--line-soft);
      background: transparent;
      padding: 10px 12px;
      text-align: left;
      color: var(--ink);
    }}
    .queue-row:hover {{ background: #f3f7fb; }}
    .queue-row.active {{ background: #eaf5f2; }}
    .queue-row strong {{ display: block; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-size: 13px; }}
    .queue-row small {{ display: block; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; color: var(--muted); font-size: 12px; }}
    .index-dot {{
      width: 24px;
      height: 24px;
      border-radius: 999px;
      display: grid;
      place-items: center;
      background: var(--panel-2);
      color: var(--muted);
      font-size: 11px;
      font-weight: 800;
    }}
    .status-dot {{ width: 12px; height: 12px; border-radius: 999px; background: #cbd5e1; }}
    .status-dot.verified {{ background: var(--green); }}
    .status-dot.needs_fix {{ background: var(--amber); }}
    .status-dot.reject {{ background: var(--red); }}
    .status-dot.out_of_scope {{ background: var(--violet); }}
    .workspace-head {{ padding: 18px 20px 14px; border-bottom: 1px solid var(--line-soft); }}
    .rule-kicker {{ color: var(--muted); font: 700 12px var(--mono); overflow-wrap: anywhere; }}
    .rule-title {{ margin: 8px 0 12px; font-size: 24px; line-height: 1.2; letter-spacing: 0; }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 7px; }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      padding: 5px 9px;
      font-size: 12px;
      font-weight: 800;
      background: var(--panel-2);
      color: var(--muted);
      border: 1px solid var(--line-soft);
    }}
    .badge.queue {{ background: var(--burgundy-soft); color: var(--burgundy); border-color: #f7c7dc; }}
    .badge.high {{ background: var(--red-soft); color: var(--red); border-color: #f7c2bf; }}
    .badge.source {{ background: var(--amber-soft); color: var(--amber); border-color: #f4d18f; }}
    .badge.ok {{ background: var(--green-soft); color: var(--green); border-color: #b7e4c8; }}
    .content-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.05fr) minmax(260px, .95fr);
      gap: 14px;
      padding: 16px;
    }}
    .sectionbox {{
      border: 1px solid var(--line-soft);
      background: #fff;
      border-radius: var(--radius);
      padding: 14px;
    }}
    .sectionbox h2, .sectionbox h3 {{
      margin: 0 0 9px;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: .06em;
      color: var(--muted);
    }}
    .sectionbox p {{ margin: 0; color: #303a48; }}
    .list {{ margin: 0; padding-left: 18px; color: #303a48; }}
    .list li {{ margin: 6px 0; }}
    .source-list {{ display: grid; gap: 9px; }}
    .source {{
      border: 1px solid var(--line-soft);
      background: #fff;
      border-radius: var(--radius);
      padding: 11px;
    }}
    .source-top {{ display: flex; gap: 10px; justify-content: space-between; align-items: start; }}
    .source a {{ font-weight: 800; overflow-wrap: anywhere; }}
    .source small {{ display: block; color: var(--muted); margin-top: 4px; overflow-wrap: anywhere; }}
    .claim-text {{ margin-top: 8px; color: #475467; font-size: 13px; }}
    .mini {{ font: 700 11px var(--mono); color: var(--muted); }}
    .decision {{ position: sticky; top: 14px; }}
    .progressbar {{ height: 9px; background: #e5eaf0; overflow: hidden; border-radius: 999px; }}
    .progressbar div {{ height: 100%; width: 0; background: linear-gradient(90deg, var(--teal), var(--burgundy)); transition: width .2s ease; }}
    .credit {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: center;
      margin: 12px 0;
      padding: 12px;
      border: 1px solid #cce4dd;
      border-radius: var(--radius);
      background: var(--teal-soft);
    }}
    .credit b {{ font-size: 26px; font-variant-numeric: tabular-nums; }}
    .choice-group {{ display: grid; gap: 8px; margin-bottom: 14px; }}
    .choice-label {{ font-size: 12px; color: var(--muted); font-weight: 800; text-transform: uppercase; letter-spacing: .04em; }}
    .choice-row {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; }}
    .choice {{ min-height: 42px; text-align: left; }}
    .choice.selected {{ color: #fff; border-color: transparent; }}
    .choice.verified.selected, .choice.yes.selected {{ background: var(--green); }}
    .choice.needs_fix.selected, .choice.partial.selected, .choice.unclear.selected {{ background: var(--amber); }}
    .choice.reject.selected, .choice.no.selected {{ background: var(--red); }}
    .choice.out_of_scope.selected, .choice.na.selected {{ background: var(--violet); }}
    .actions {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
    .actions .wide {{ grid-column: 1 / -1; }}
    .empty {{ padding: 28px; color: var(--muted); text-align: center; }}
    .toast {{
      position: fixed;
      right: 18px;
      bottom: 18px;
      background: var(--navy);
      color: #fff;
      padding: 12px 14px;
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      transform: translateY(12px);
      opacity: 0;
      pointer-events: none;
      transition: .18s ease;
      max-width: 380px;
      z-index: 20;
    }}
    .toast.show {{ opacity: 1; transform: translateY(0); }}
    @media (max-width: 1180px) {{
      .layout {{ grid-template-columns: 300px minmax(0, 1fr); }}
      .decision {{ position: static; grid-column: 1 / -1; }}
      .meta-strip {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    }}
    @media (max-width: 760px) {{
      .app {{ padding: 12px; }}
      .topbar, .layout, .content-grid {{ grid-template-columns: 1fr; }}
      .toolbar {{ justify-content: flex-start; }}
      .meta-strip {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      #workspace {{ order: 1; }}
      .decision {{ order: 2; }}
      .layout > aside.panel:first-child {{ order: 3; }}
      .queue-list {{ max-height: 320px; }}
      .rule-title {{ font-size: 20px; }}
      .choice-row, .actions {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <header class="topbar">
      <div class="brandline">
        <div class="mark">PG</div>
        <div>
          <h1 data-i18n="appTitle">Pre-Gestor Expert Review</h1>
          <p class="subtitle" data-i18n="subtitle">Validate one fiscal question at a time. Each completed question counts as one review credit.</p>
        </div>
      </div>
      <div class="toolbar">
        <div class="segmented" aria-label="Language">
          <button type="button" data-lang="es">ES</button>
          <button type="button" data-lang="ru">RU</button>
          <button type="button" data-lang="en">EN</button>
        </div>
        <button class="btn subtle" id="exportBtn" type="button" data-i18n="exportJson">Export JSON</button>
        <label class="btn subtle" for="importFile" data-i18n="importJson">Import JSON</label>
        <input id="importFile" type="file" accept="application/json,.json" hidden>
      </div>
    </header>

    <section class="meta-strip" aria-label="Review metrics">
      <div class="metric"><b id="metricTotal">0</b><span data-i18n="metricTotal">Questions</span></div>
      <div class="metric"><b id="metricDone">0</b><span data-i18n="metricDone">Completed</span></div>
      <div class="metric"><b id="metricCredit">€0</b><span data-i18n="metricCredit">Review credit</span></div>
      <div class="metric"><b id="metricQueue">0</b><span data-i18n="metricQueue">Priority queue</span></div>
      <div class="metric"><b id="metricAttention">0</b><span data-i18n="metricAttention">Source attention</span></div>
    </section>

    <div class="layout">
      <aside class="panel">
        <div class="panel-head">
          <div class="panel-title" data-i18n="queueTitle">Audit queue</div>
          <span class="mini" id="queueCount">0</span>
        </div>
        <div class="pad">
          <div class="field">
            <label for="reviewerName" data-i18n="reviewerName">Reviewer</label>
            <input id="reviewerName" autocomplete="name">
          </div>
          <div class="field">
            <label for="reviewerOrg" data-i18n="reviewerOrg">Gestoría / role</label>
            <input id="reviewerOrg">
          </div>
          <div class="field">
            <label for="inviteCode" data-i18n="inviteCode">Invite code</label>
            <input id="inviteCode">
          </div>
          <div class="field">
            <label for="searchBox" data-i18n="search">Search</label>
            <input id="searchBox" placeholder="Modelo 202, Beckham, IVA...">
          </div>
          <div class="field">
            <label for="domainSelect" data-i18n="domain">Domain</label>
            <select id="domainSelect"></select>
          </div>
          <div class="filters" id="filters"></div>
        </div>
        <div class="queue-list" id="queueList"></div>
      </aside>

      <main class="panel" id="workspace">
        <div class="workspace-head">
          <div class="rule-kicker" id="ruleKicker"></div>
          <h2 class="rule-title" id="ruleTitle"></h2>
          <div class="badges" id="badges"></div>
        </div>
        <div class="content-grid">
          <section class="sectionbox">
            <h2 data-i18n="questionToVerify">Question to verify</h2>
            <p id="focusQuestion"></p>
          </section>
          <section class="sectionbox">
            <h2 data-i18n="practicalAnswer">Draft answer boundary</h2>
            <p id="practicalText"></p>
          </section>
          <section class="sectionbox">
            <h2 data-i18n="evidenceNeeded">Evidence needed</h2>
            <ul class="list" id="evidenceList"></ul>
          </section>
          <section class="sectionbox">
            <h2 data-i18n="openChecks">Checks before approval</h2>
            <ul class="list" id="checksList"></ul>
          </section>
          <section class="sectionbox" style="grid-column:1 / -1">
            <h2 data-i18n="sources">Sources and claims</h2>
            <div class="source-list" id="sourceList"></div>
          </section>
          <section class="sectionbox" style="grid-column:1 / -1">
            <h2 data-i18n="riskFlags">Risk flags</h2>
            <ul class="list" id="riskList"></ul>
          </section>
        </div>
      </main>

      <aside class="panel decision">
        <div class="panel-head">
          <div class="panel-title" data-i18n="decisionTitle">Decision</div>
          <span class="mini" id="positionText"></span>
        </div>
        <div class="pad">
          <div class="progressbar"><div id="progressFill"></div></div>
          <div class="credit">
            <div>
              <div class="choice-label" data-i18n="creditLabel">Current month credit</div>
              <small id="creditDetail"></small>
            </div>
            <b id="creditAmount">€0</b>
          </div>
          <div class="choice-group">
            <div class="choice-label" data-i18n="verdict">Verdict</div>
            <div class="choice-row" data-choice-group="verdict"></div>
          </div>
          <div class="choice-group">
            <div class="choice-label" data-i18n="sourceSupport">Source support</div>
            <div class="choice-row" data-choice-group="source_support"></div>
          </div>
          <div class="choice-group">
            <div class="choice-label" data-i18n="publicSafety">Safe wording</div>
            <div class="choice-row" data-choice-group="public_safety"></div>
          </div>
          <div class="choice-group">
            <div class="choice-label" data-i18n="territoryTime">Territory / period</div>
            <div class="choice-row" data-choice-group="territory_time"></div>
          </div>
          <div class="field">
            <label for="reviewNotes" data-i18n="notes">Notes</label>
            <textarea id="reviewNotes"></textarea>
          </div>
          <div class="field">
            <label for="requiredFix" data-i18n="requiredFix">Required fix</label>
            <textarea id="requiredFix"></textarea>
          </div>
          <div class="actions">
            <button class="btn subtle" id="prevBtn" type="button" data-i18n="previous">Previous</button>
            <button class="btn subtle" id="nextBtn" type="button" data-i18n="next">Next</button>
            <button class="btn primary wide" id="saveNextBtn" type="button" data-i18n="saveNext">Save and next</button>
            <button class="btn subtle wide" id="copyBtn" type="button" data-i18n="copySummary">Copy review summary</button>
          </div>
        </div>
      </aside>
    </div>
  </div>
  <div class="toast" id="toast"></div>
  <script type="application/json" id="dataset-json">{dataset_json}</script>
  <script>
    const DATASET = JSON.parse(document.getElementById("dataset-json").textContent);
    const STORAGE_KEY = "occam.pre_gestor_review_console.v2." + DATASET.dataset_id;
    const CREDIT_PER_QUESTION = DATASET.source.review_unit_credit_eur || 1;
    const I18N = {{
      es: {{
        appTitle: "Revisión experta Pre-Gestor", subtitle: "Valida una pregunta fiscal por vez. Cada pregunta completada cuenta como un crédito de revisión.",
        exportJson: "Exportar JSON", importJson: "Importar JSON", metricTotal: "Preguntas", metricDone: "Completadas", metricCredit: "Crédito", metricQueue: "Prioridad", metricAttention: "Fuentes a revisar",
        queueTitle: "Cola de auditoría", reviewerName: "Revisor", reviewerOrg: "Gestoría / rol", inviteCode: "Código de invitación", search: "Buscar", domain: "Dominio",
        allDomains: "Todos los dominios", all: "Todas", priority: "Prioridad", pending: "Pendientes", completed: "Completadas", sourceAttention: "Fuentes", highStakes: "Alto riesgo",
        questionToVerify: "Pregunta a verificar", practicalAnswer: "Límite de la respuesta borrador", evidenceNeeded: "Evidencia necesaria", openChecks: "Comprobaciones", sources: "Fuentes y afirmaciones", riskFlags: "Riesgos",
        decisionTitle: "Decisión", creditLabel: "Crédito del mes", verdict: "Veredicto", sourceSupport: "Soporte de fuente", publicSafety: "Redacción segura", territoryTime: "Territorio / periodo",
        notes: "Notas", requiredFix: "Corrección requerida", previous: "Anterior", next: "Siguiente", saveNext: "Guardar y siguiente", copySummary: "Copiar resumen",
        verified: "Verificado", needs_fix: "Corregir", reject: "Rechazar", out_of_scope: "Fuera de alcance", yes: "Sí", partial: "Parcial", no: "No", unclear: "No claro", na: "No aplica",
        saved: "Guardado en este navegador.", exported: "JSON descargado.", imported: "JSON importado.", copied: "Resumen copiado.", noResults: "No hay preguntas con estos filtros.",
        noFocus: "Confirmar si esta regla puede pasar a gestor_verified o qué condición debe bloquearla.", noSources: "No hay fuentes declaradas.", noRisks: "No hay riesgos adicionales declarados.",
        completedDetail: "1 euro por pregunta completada", sourceStatus: "Estado", support: "Soporte"
      }},
      ru: {{
        appTitle: "Экспертная проверка Pre-Gestor", subtitle: "Проверяйте по одному фискальному вопросу. Каждый завершённый вопрос считается как один кредит проверки.",
        exportJson: "Экспорт JSON", importJson: "Импорт JSON", metricTotal: "Вопросы", metricDone: "Завершено", metricCredit: "Кредит", metricQueue: "Приоритет", metricAttention: "Источники",
        queueTitle: "Очередь аудита", reviewerName: "Проверяющий", reviewerOrg: "Хестория / роль", inviteCode: "Код приглашения", search: "Поиск", domain: "Домен",
        allDomains: "Все домены", all: "Все", priority: "Приоритет", pending: "Пустые", completed: "Завершено", sourceAttention: "Источники", highStakes: "Высокий риск",
        questionToVerify: "Что проверить", practicalAnswer: "Граница чернового ответа", evidenceNeeded: "Нужные документы", openChecks: "Проверки до одобрения", sources: "Источники и claims", riskFlags: "Риски",
        decisionTitle: "Решение", creditLabel: "Кредит текущего месяца", verdict: "Вердикт", sourceSupport: "Поддержка источником", publicSafety: "Безопасность текста", territoryTime: "Территория / период",
        notes: "Заметки", requiredFix: "Что исправить", previous: "Назад", next: "Дальше", saveNext: "Сохранить и дальше", copySummary: "Скопировать summary",
        verified: "Подтверждено", needs_fix: "Исправить", reject: "Отклонить", out_of_scope: "Вне scope", yes: "Да", partial: "Частично", no: "Нет", unclear: "Неясно", na: "Не применимо",
        saved: "Сохранено в этом браузере.", exported: "JSON скачан.", imported: "JSON импортирован.", copied: "Summary скопирован.", noResults: "Нет вопросов с такими фильтрами.",
        noFocus: "Подтвердить, можно ли переводить правило в gestor_verified, или указать блокирующее условие.", noSources: "Источники не указаны.", noRisks: "Дополнительные риски не указаны.",
        completedDetail: "1 евро за завершённый вопрос", sourceStatus: "Статус", support: "Поддержка"
      }},
      en: {{
        appTitle: "Pre-Gestor Expert Review", subtitle: "Validate one fiscal question at a time. Each completed question counts as one review credit.",
        exportJson: "Export JSON", importJson: "Import JSON", metricTotal: "Questions", metricDone: "Completed", metricCredit: "Credit", metricQueue: "Priority queue", metricAttention: "Source attention",
        queueTitle: "Audit queue", reviewerName: "Reviewer", reviewerOrg: "Gestoría / role", inviteCode: "Invite code", search: "Search", domain: "Domain",
        allDomains: "All domains", all: "All", priority: "Priority", pending: "Pending", completed: "Completed", sourceAttention: "Sources", highStakes: "High stakes",
        questionToVerify: "Question to verify", practicalAnswer: "Draft answer boundary", evidenceNeeded: "Evidence needed", openChecks: "Checks before approval", sources: "Sources and claims", riskFlags: "Risk flags",
        decisionTitle: "Decision", creditLabel: "Current month credit", verdict: "Verdict", sourceSupport: "Source support", publicSafety: "Safe wording", territoryTime: "Territory / period",
        notes: "Notes", requiredFix: "Required fix", previous: "Previous", next: "Next", saveNext: "Save and next", copySummary: "Copy review summary",
        verified: "Verified", needs_fix: "Needs fix", reject: "Reject", out_of_scope: "Out of scope", yes: "Yes", partial: "Partial", no: "No", unclear: "Unclear", na: "N/A",
        saved: "Saved in this browser.", exported: "JSON downloaded.", imported: "JSON imported.", copied: "Summary copied.", noResults: "No questions match these filters.",
        noFocus: "Confirm whether this rule may move to gestor_verified or state the blocking condition.", noSources: "No sources declared.", noRisks: "No additional risks declared.",
        completedDetail: "1 euro per completed question", sourceStatus: "Status", support: "Support"
      }}
    }};
    const CHOICES = {{
      verdict: ["verified", "needs_fix", "reject", "out_of_scope"],
      source_support: ["yes", "partial", "no", "unclear"],
      public_safety: ["yes", "partial", "no"],
      territory_time: ["yes", "partial", "no", "na"]
    }};
    const state = loadState();
    let lang = state.lang || "es";
    let filter = state.filter || "all";
    let domain = state.domain || "all";
    let current = Number.isInteger(state.current) ? state.current : 0;

    function blankReview() {{
      return {{ verdict: "", source_support: "", public_safety: "", territory_time: "", notes: "", required_fix: "", reviewed_at: "" }};
    }}
    function loadState() {{
      try {{ return {{ reviewer: {{}}, reviews: {{}}, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || "{{}}") }}; }}
      catch {{ return {{ reviewer: {{}}, reviews: {{}} }}; }}
    }}
    function t(key) {{ return (I18N[lang] && I18N[lang][key]) || I18N.en[key] || key; }}
    function review(rule) {{
      state.reviews[rule.rule_id] ||= blankReview();
      return state.reviews[rule.rule_id];
    }}
    function isDone(rule) {{ return Boolean(review(rule).verdict); }}
    function save(showToast = false) {{
      const rule = visibleRules()[current] || DATASET.rules[0];
      if (rule) {{
        const r = review(rule);
        r.notes = document.getElementById("reviewNotes").value.trim();
        r.required_fix = document.getElementById("requiredFix").value.trim();
        if (r.verdict && !r.reviewed_at) r.reviewed_at = new Date().toISOString();
      }}
      state.reviewer = {{
        name: document.getElementById("reviewerName").value.trim(),
        organization: document.getElementById("reviewerOrg").value.trim(),
        invite_code: document.getElementById("inviteCode").value.trim()
      }};
      state.lang = lang; state.filter = filter; state.domain = domain; state.current = current;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      if (showToast) toast(t("saved"));
      renderMetrics(); renderQueue();
    }}
    function visibleRules() {{
      const q = document.getElementById("searchBox").value.trim().toLowerCase();
      return DATASET.rules.filter(rule => {{
        const r = review(rule);
        const text = [rule.rule_id, rule.domain_label, rule.scenario, rule.texts.en.summary, rule.texts.es.summary, rule.texts.ru.summary].join(" ").toLowerCase();
        if (q && !text.includes(q)) return false;
        if (domain !== "all" && rule.domain_id !== domain) return false;
        if (filter === "priority" && !rule.tags.includes("gestor_queue")) return false;
        if (filter === "pending" && isDone(rule)) return false;
        if (filter === "completed" && !isDone(rule)) return false;
        if (filter === "sourceAttention" && !rule.tags.includes("source_attention")) return false;
        if (filter === "highStakes" && !rule.high_stakes) return false;
        return true;
      }});
    }}
    function setLang(next) {{
      lang = next;
      document.documentElement.lang = lang;
      document.querySelectorAll("[data-lang]").forEach(btn => btn.classList.toggle("active", btn.dataset.lang === lang));
      document.querySelectorAll("[data-i18n]").forEach(node => node.textContent = t(node.dataset.i18n));
      renderDomains(); renderFilters(); renderChoices(); renderRule(); renderMetrics(); save(false);
    }}
    function renderDomains() {{
      const selected = domain;
      const domains = [...new Map(DATASET.rules.map(rule => [rule.domain_id, rule.domain_label])).entries()].sort((a, b) => a[1].localeCompare(b[1]));
      document.getElementById("domainSelect").innerHTML = [`<option value="all">${{escapeHtml(t("allDomains"))}}</option>`]
        .concat(domains.map(([id, label]) => `<option value="${{escapeAttr(id)}}">${{escapeHtml(label)}}</option>`)).join("");
      document.getElementById("domainSelect").value = selected;
    }}
    function renderFilters() {{
      const filters = ["all", "priority", "pending", "completed", "sourceAttention", "highStakes"];
      document.getElementById("filters").innerHTML = filters.map(name => `<button class="chip ${{filter === name ? "active" : ""}}" data-filter="${{name}}" type="button">${{escapeHtml(t(name))}}</button>`).join("");
      document.querySelectorAll("[data-filter]").forEach(btn => btn.onclick = () => {{ filter = btn.dataset.filter; current = 0; renderFilters(); renderQueue(); renderRule(); save(false); }});
    }}
    function renderChoices() {{
      Object.entries(CHOICES).forEach(([group, values]) => {{
        const node = document.querySelector(`[data-choice-group="${{group}}"]`);
        node.innerHTML = values.map(value => `<button type="button" class="choice ${{value}}" data-choice-group-name="${{group}}" data-choice-value="${{value}}">${{escapeHtml(t(value))}}</button>`).join("");
      }});
    }}
    function renderQueue() {{
      const visible = visibleRules();
      document.getElementById("queueCount").textContent = String(visible.length);
      if (current >= visible.length) current = Math.max(0, visible.length - 1);
      const list = document.getElementById("queueList");
      if (!visible.length) {{
        list.innerHTML = `<div class="empty">${{escapeHtml(t("noResults"))}}</div>`;
        return;
      }}
      list.innerHTML = visible.map((rule, index) => {{
        const r = review(rule);
        const title = rule.texts[lang]?.title || rule.texts.en.title || rule.rule_id;
        const sub = `${{rule.domain_label}} · ${{rule.scenario}}`;
        return `<button class="queue-row ${{index === current ? "active" : ""}}" type="button" data-row="${{index}}">
          <span class="index-dot">${{rule.index}}</span>
          <span><strong>${{escapeHtml(title)}}</strong><small>${{escapeHtml(sub)}}</small></span>
          <span class="status-dot ${{escapeAttr(r.verdict)}}"></span>
        </button>`;
      }}).join("");
      document.querySelectorAll("[data-row]").forEach(btn => btn.onclick = () => {{ save(false); current = Number(btn.dataset.row); renderRule(); renderQueue(); }});
    }}
    function renderRule() {{
      const visible = visibleRules();
      if (!visible.length) return;
      if (current >= visible.length) current = Math.max(0, visible.length - 1);
      const rule = visible[current];
      const r = review(rule);
      const text = rule.texts[lang] || rule.texts.en;
      document.getElementById("positionText").textContent = `${{current + 1}} / ${{visible.length}}`;
      document.getElementById("ruleKicker").textContent = `${{rule.rule_id}} · ${{rule.domain_label}} · ${{DATASET.source.commit}}`;
      document.getElementById("ruleTitle").textContent = text.title || rule.rule_id;
      document.getElementById("focusQuestion").textContent = (rule.focus_question && (rule.focus_question[lang] || rule.focus_question.en)) || t("noFocus");
      document.getElementById("practicalText").textContent = text.practical || text.summary || "";
      document.getElementById("badges").innerHTML = badges(rule, r).map(item => `<span class="badge ${{item.cls}}">${{escapeHtml(item.text)}}</span>`).join("");
      renderList("evidenceList", rule.evidence_needed);
      renderList("checksList", [...(rule.open_questions || []), ...(rule.next_actions || [])].slice(0, 8));
      renderSources(rule);
      renderRisks(rule);
      Object.entries(CHOICES).forEach(([group]) => {{
        document.querySelectorAll(`[data-choice-group-name="${{group}}"]`).forEach(btn => btn.classList.toggle("selected", btn.dataset.choiceValue === r[group]));
      }});
      document.getElementById("reviewNotes").value = r.notes || "";
      document.getElementById("requiredFix").value = r.required_fix || "";
      document.getElementById("prevBtn").disabled = current <= 0;
      document.getElementById("nextBtn").disabled = current >= visible.length - 1;
    }}
    function badges(rule, r) {{
      const items = [
        {{ text: rule.gestor_review_state, cls: "ok" }},
        {{ text: rule.valid_from + (rule.valid_until ? " → " + rule.valid_until : ""), cls: "" }},
        {{ text: "confidence " + rule.confidence, cls: "" }}
      ];
      if (rule.tags.includes("gestor_queue")) items.push({{ text: "gestor queue", cls: "queue" }});
      if (rule.high_stakes) items.push({{ text: "high stakes", cls: "high" }});
      if (rule.tags.includes("source_attention")) items.push({{ text: "source attention", cls: "source" }});
      if (r.verdict) items.push({{ text: t(r.verdict), cls: "ok" }});
      return items.filter(item => item.text);
    }}
    function renderList(id, items) {{
      document.getElementById(id).innerHTML = (items && items.length)
        ? items.map(item => `<li>${{escapeHtml(item)}}</li>`).join("")
        : `<li>${{escapeHtml(t("noFocus"))}}</li>`;
    }}
    function renderSources(rule) {{
      const node = document.getElementById("sourceList");
      if (!rule.sources.length) {{
        node.innerHTML = `<div class="source"><small>${{escapeHtml(t("noSources"))}}</small></div>`;
        return;
      }}
      node.innerHTML = rule.sources.map(source => {{
        const status = [source.source_id, source.jurisdiction, source.last_checked].filter(Boolean).join(" · ");
        const stateClass = source.support_state === "yes" ? "ok" : "source";
        return `<article class="source">
          <div class="source-top">
            <div><a href="${{escapeAttr(source.url)}}" target="_blank" rel="noopener noreferrer">${{escapeHtml(source.title || source.source_id)}}</a><small>${{escapeHtml(status)}}</small></div>
            <span class="badge ${{stateClass}}">${{escapeHtml(source.support_state || "unknown")}}</span>
          </div>
          <div class="claim-text"><strong>${{escapeHtml(source.support_anchor || source.review_status || "")}}</strong><br>${{escapeHtml(source.claim || "")}}</div>
        </article>`;
      }}).join("");
    }}
    function renderRisks(rule) {{
      const risks = rule.risk_flags || [];
      document.getElementById("riskList").innerHTML = risks.length
        ? risks.map(risk => `<li><strong>${{escapeHtml(risk.severity)}} · ${{escapeHtml(risk.code)}}</strong>: ${{escapeHtml(risk.message)}}</li>`).join("")
        : `<li>${{escapeHtml(t("noRisks"))}}</li>`;
    }}
    function renderMetrics() {{
      const done = DATASET.rules.filter(isDone).length;
      const credit = done * CREDIT_PER_QUESTION;
      const pct = DATASET.rules.length ? Math.round(done / DATASET.rules.length * 100) : 0;
      document.getElementById("metricTotal").textContent = DATASET.rules.length;
      document.getElementById("metricDone").textContent = done;
      document.getElementById("metricCredit").textContent = `€${{credit}}`;
      document.getElementById("metricQueue").textContent = DATASET.stats.gestor_queue;
      document.getElementById("metricAttention").textContent = DATASET.stats.source_attention;
      document.getElementById("creditAmount").textContent = `€${{credit}}`;
      document.getElementById("creditDetail").textContent = `${{done}}/${{DATASET.rules.length}} · ${{t("completedDetail")}}`;
      document.getElementById("progressFill").style.width = pct + "%";
    }}
    function exportJson() {{
      save(false);
      const reviews = DATASET.rules
        .map(rule => ({{ rule_id: rule.rule_id, ...review(rule) }}))
        .filter(item => ["verdict", "source_support", "public_safety", "territory_time", "notes", "required_fix"].some(key => Boolean(item[key])));
      const payload = {{
        schema: "pre_gestor_expert_review_submission.v2",
        exported_at: new Date().toISOString(),
        dataset_id: DATASET.dataset_id,
        dataset_commit: DATASET.source.commit,
        reviewer: state.reviewer,
        credit_eur: DATASET.rules.filter(isDone).length * CREDIT_PER_QUESTION,
        completed_count: DATASET.rules.filter(isDone).length,
        reviews
      }};
      const name = (state.reviewer.name || "reviewer").toLowerCase().replace(/[^a-z0-9а-яё_-]+/giu, "_").slice(0, 40) || "reviewer";
      const blob = new Blob([JSON.stringify(payload, null, 2)], {{ type: "application/json;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `pre-gestor-review-${{name}}-${{new Date().toISOString().slice(0, 10)}}.json`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 500);
      toast(t("exported"));
    }}
    function importJson(file) {{
      const reader = new FileReader();
      reader.onload = () => {{
        const payload = JSON.parse(String(reader.result || "{{}}"));
        if (payload.reviewer) state.reviewer = payload.reviewer;
        (payload.reviews || []).forEach(item => {{
          if (!item.rule_id) return;
          const {{ rule_id, ...body }} = item;
          state.reviews[rule_id] = {{ ...blankReview(), ...body }};
        }});
        hydrateReviewer(); save(false); renderAll(); toast(t("imported"));
      }};
      reader.readAsText(file);
    }}
    async function copySummary() {{
      save(false);
      const rule = visibleRules()[current] || DATASET.rules[0];
      const r = review(rule);
      const text = [
        `Dataset: ${{DATASET.dataset_id}} @ ${{DATASET.source.commit}}`,
        `Rule: ${{rule.rule_id}}`,
        `Reviewer: ${{state.reviewer.name || ""}}`,
        `Verdict: ${{r.verdict || ""}}`,
        `Source support: ${{r.source_support || ""}}`,
        `Notes: ${{r.notes || ""}}`,
        `Required fix: ${{r.required_fix || ""}}`
      ].join("\\n");
      await navigator.clipboard.writeText(text);
      toast(t("copied"));
    }}
    function hydrateReviewer() {{
      document.getElementById("reviewerName").value = state.reviewer.name || "";
      document.getElementById("reviewerOrg").value = state.reviewer.organization || "";
      document.getElementById("inviteCode").value = state.reviewer.invite_code || "";
    }}
    function toast(message) {{
      const node = document.getElementById("toast");
      node.textContent = message;
      node.classList.add("show");
      clearTimeout(toast.timer);
      toast.timer = setTimeout(() => node.classList.remove("show"), 1800);
    }}
    function escapeHtml(value) {{
      return String(value ?? "").replace(/[&<>"']/g, ch => ({{ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }}[ch]));
    }}
    function escapeAttr(value) {{ return escapeHtml(value).replace(/`/g, "&#96;"); }}
    function renderAll() {{ renderDomains(); renderFilters(); renderChoices(); renderQueue(); renderRule(); renderMetrics(); }}

    document.querySelectorAll("[data-lang]").forEach(btn => btn.onclick = () => setLang(btn.dataset.lang));
    document.getElementById("domainSelect").onchange = event => {{ domain = event.target.value; current = 0; renderQueue(); renderRule(); save(false); }};
    document.getElementById("searchBox").oninput = () => {{ current = 0; renderQueue(); renderRule(); save(false); }};
    ["reviewerName", "reviewerOrg", "inviteCode", "reviewNotes", "requiredFix"].forEach(id => document.getElementById(id).addEventListener("input", () => save(false)));
    document.addEventListener("click", event => {{
      const btn = event.target.closest("[data-choice-group-name]");
      if (!btn) return;
      const rule = visibleRules()[current] || DATASET.rules[0];
      const r = review(rule);
      r[btn.dataset.choiceGroupName] = btn.dataset.choiceValue;
      if (btn.dataset.choiceGroupName === "verdict") r.reviewed_at = new Date().toISOString();
      save(false); renderRule(); renderMetrics();
    }});
    document.getElementById("prevBtn").onclick = () => {{ save(false); current = Math.max(0, current - 1); renderRule(); renderQueue(); }};
    document.getElementById("nextBtn").onclick = () => {{ save(false); current = Math.min(visibleRules().length - 1, current + 1); renderRule(); renderQueue(); }};
    document.getElementById("saveNextBtn").onclick = () => {{ save(true); current = Math.min(visibleRules().length - 1, current + 1); renderRule(); renderQueue(); }};
    document.getElementById("exportBtn").onclick = exportJson;
    document.getElementById("copyBtn").onclick = copySummary;
    document.getElementById("importFile").onchange = event => event.target.files?.[0] && importJson(event.target.files[0]);

    hydrateReviewer();
    setLang(lang);
  </script>
  <!-- Generated: {html.escape(generated_at)} -->
</body>
</html>
"""


def build(data_dir: Path, out_path: Path, source_label: str, source_commit: str) -> None:
    dataset = _build_dataset(data_dir, source_label, source_commit)
    generated_at = dataset["generated_at"]
    dataset_json = json.dumps(dataset, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = _page_template(dataset_json, generated_at)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, type=Path, help="Path to pre_gestor_intelligence/data")
    parser.add_argument("--out", default=Path("pre-gestor-a1-review/index.html"), type=Path)
    parser.add_argument("--source-label", default="codex/pre-gestor-core")
    parser.add_argument("--source-commit", default="")
    args = parser.parse_args()
    data_dir = args.data_dir.expanduser().resolve()
    source_commit = args.source_commit or _git_commit(data_dir.parents[2])
    build(data_dir, args.out.expanduser().resolve(), args.source_label, source_commit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
