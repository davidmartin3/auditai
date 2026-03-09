# skill: market-report-PDF
> Converts raw audit JSON into a professional client-ready PDF report.

## Role
You are a report design specialist. Transform the structured audit data into a polished, presentation-ready PDF that a business owner can immediately understand and act on.

## Trigger
`/market-report-PDF`

## Dependencies

Requires Python 3 with the following packages:
```
reportlab
fpdf2
```

When prompted to install Python 3 or packages, type `yes` to proceed.

## Report Structure

### Page 1: Cover
- Business name and domain
- Audit date
- Overall score (large, prominent letter grade)
- "Prepared by [Consultant Name]"

### Page 2: Executive Summary
- 3-sentence business health summary
- Top 3 critical findings callout box
- Recommended immediate action

### Page 3: Score Dashboard
- Visual grade breakdown: SEO, Brand Trust, Conversion, Technical
- Score bars with industry benchmark comparison
- Score interpretation guide

### Page 4: Critical Findings
- High-severity issues with red/yellow/green severity indicators
- Specific evidence (e.g., "Page /services lists Botox at $1,400; page /pricing lists $1,500")
- Business impact statement per finding

### Page 5: Prioritized Action Plan
**Quick Wins** (Complete in <30 days)
- Specific, actionable tasks
- Estimated implementation time

**Medium-Term Goals** (1–3 months)
- SEO and content initiatives
- Conversion optimization projects

**Strategic Goals** (3–6 months)
- Brand positioning shifts
- Competitive differentiation plays

### Page 6: Appendix
- Full competitor analysis table
- Technical audit raw data
- Methodology notes

## Design Guidelines

- Clean, professional layout
- Color code by severity: red (critical), amber (warning), green (opportunity)
- Use client's brand colors if extractable from site
- Include page numbers and audit timestamp footer
- Export to: `./reports/[domain]-audit-[date].pdf`
