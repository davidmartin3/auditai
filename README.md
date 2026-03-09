# AuditAI — Local AI Marketing Intelligence Platform

> Replace the $10,000/mo agency with a 5-agent local AI stack.

## What This Is

A marketing automation system built on Claude Code + local AI tooling. Drops a URL, spins up 5 parallel specialist agents, and produces a client-ready PDF audit report in ~2 minutes.

## Stack

- **Claude Code** (VS Code extension) — AI reasoning engine
- **GitHub Skills Toolkit** — 15 pre-configured marketing skill files
- **Python 3** — PDF report generation
- **VS Code** — IDE / command center

## Quick Start

```bash
# 1. Install the skills toolkit
curl -s https://your-repo-url/install.sh | bash

# 2. Run a market audit
/market-audit yourclients.com

# 3. Generate the PDF report
/market-report-PDF
```

## The 5 Agents

| Agent | Role |
|---|---|
| `market-content` | Brand voice, messaging, content quality |
| `market-convert` | CTA analysis, funnel depth, friction points |
| `market-compete` | 3-tier competitive mapping |
| `market-tech` | Core Web Vitals, schema, backend health |
| `market-strategy` | Synthesizes findings → prioritized action plan |

## Consulting Model

- **Your cost**: ~$0 (open source stack)
- **Client retainer**: $2,000–$5,000/month
- **Traditional agency**: $5,000–$10,000/month

## Report Structure

1. Executive Summary
2. Score Breakdowns (SEO, Brand Trust, Conversion)
3. Critical Findings (high-severity errors)
4. Prioritized Action Plan (Quick Wins → 3-6 month roadmap)

## Skills Reference

Skills are Markdown files (`skill.md`) that give Claude a specific expertise framework. Each skill lives in `/skills/` and is auto-loaded by the toolkit.

```
/skills/
  market-audit.md
  market-content.md
  market-convert.md
  market-compete.md
  market-tech.md
  market-strategy.md
  market-report-PDF.md
  ... (15 total)
```
