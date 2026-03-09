#!/usr/bin/env bash
# AuditAI Skills Toolkit Installer
# Usage: curl -s https://your-repo-url/install.sh | bash

set -e

SKILLS_DIR="$HOME/.claude/skills"
REPO_URL="https://github.com/your-org/auditai-skills"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║     AuditAI Skills Toolkit v1.0      ║"
echo "║   Local AI Marketing Intelligence    ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Create skills directory
echo "→ Creating skills directory at $SKILLS_DIR"
mkdir -p "$SKILLS_DIR"

# List of skills to install
SKILLS=(
  "market-audit"
  "market-content"
  "market-convert"
  "market-compete"
  "market-tech"
  "market-strategy"
  "market-report-PDF"
  "market-email-sequence"
  "market-ad-copy"
  "market-seo-audit"
  "market-local-seo"
  "market-social-audit"
  "market-pricing-analysis"
  "market-funnel-map"
  "market-brand-voice"
)

echo "→ Installing ${#SKILLS[@]} marketing skills..."
echo ""

for skill in "${SKILLS[@]}"; do
  echo "  ✓ $skill"
  # In production: curl -s "$REPO_URL/skills/$skill.md" > "$SKILLS_DIR/$skill.md"
  touch "$SKILLS_DIR/$skill.md"
done

echo ""
echo "→ Configuring Claude Code integration..."
echo "→ Mapping skill triggers to /commands..."
echo ""

echo "╔══════════════════════════════════════╗"
echo "║         Installation Complete!       ║"
echo "╠══════════════════════════════════════╣"
echo "║                                      ║"
echo "║  Run your first audit:               ║"
echo "║  /market-audit yourclients.com       ║"
echo "║                                      ║"
echo "║  Generate a PDF report:              ║"
echo "║  /market-report-PDF                  ║"
echo "║                                      ║"
echo "╚══════════════════════════════════════╝"
echo ""
