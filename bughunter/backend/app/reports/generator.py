"""Report generator — Markdown and PDF."""
from datetime import datetime, timezone


class ReportGenerator:
    def generate_markdown(self, finding, evidence, ai_analysis, program) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        lines = [
            f"# Security Finding Report",
            f"",
            f"**Title:** {finding.name}",
            f"**Program:** {program.name if program else 'Unknown'}",
            f"**Affected Asset:** {finding.scope_result.get('matched_at', 'N/A')}",
            f"**Vulnerability Category:** {finding.category}",
            f"**Severity:** {finding.severity.upper()}",
            f"**Scanner:** {finding.scanner} {finding.scanner_version or ''}",
            f"**Testing Date:** {now}",
            f"**Status:** {finding.status}",
            f"",
            f"---",
            f"",
            f"## Summary",
            f"",
            ai_analysis.output.get("understanding", "_No AI analysis available._") if ai_analysis else "_No AI analysis available._",
            f"",
            f"## Technical Details",
            f"",
            ai_analysis.output.get("why_vulnerable", "_N/A_") if ai_analysis else "_N/A_",
            f"",
            f"## Reproduction Steps",
            f"",
            f"1. Navigate to: `{finding.scope_result.get('matched_at', 'N/A')}`",
            f"2. Observe the vulnerability indicators documented in evidence.",
            f"",
        ]

        if ai_analysis and ai_analysis.output.get("safe_verification_steps"):
            lines += ["## Verification Steps", ""]
            for step in ai_analysis.output["safe_verification_steps"]:
                lines.append(f"- {step}")
            lines.append("")

        lines += [
            f"## Evidence",
            f"",
        ]
        for ev in evidence:
            lines.append(f"- **{ev.kind}** (collected by `{ev.collected_by}` at {ev.collected_at.isoformat()})")
            lines.append(f"  - Reference: `{ev.content_ref}`")
            lines.append(f"  - SHA256: `{ev.sha256}`")

        if ai_analysis:
            sev_rec = ai_analysis.output.get("severity_recommendation", {})
            lines += [
                f"",
                f"## Security Impact",
                f"",
                ai_analysis.output.get("exploitability", "_N/A_"),
                f"",
                f"## Remediation",
                f"",
                "_Please consult your security team for remediation guidance based on the above findings._",
                f"",
                f"## CVSS Estimate",
                f"",
                f"**Level:** {sev_rec.get('level', 'N/A')}",
                f"**Vector:** `{sev_rec.get('cvss_vector', 'N/A')}`",
            ]

        lines += [
            f"",
            f"## Scope Confirmation",
            f"",
            f"This finding was detected within the authorized scope of the **{program.name if program else 'Unknown'}** program.",
            f"Scope validation result: `{finding.scope_result}`",
            f"",
            f"---",
            f"",
            f"> ⚠️ This report is a draft. Review and edit before submission. **Do not submit without human review.**",
            f"> This report was NOT automatically submitted to the program.",
        ]
        return "\n".join(lines)

    def generate_pdf(self, markdown: str, output_path: str) -> str:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import cm

        doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        for line in markdown.split("\n"):
            if line.startswith("# "):
                story.append(Paragraph(line[2:], styles["Title"]))
            elif line.startswith("## "):
                story.append(Paragraph(line[3:], styles["Heading2"]))
            elif line.startswith("**") and line.endswith("**"):
                story.append(Paragraph(line.strip("*"), styles["Heading3"]))
            elif line.strip():
                story.append(Paragraph(line.replace("`", ""), styles["Normal"]))
            else:
                story.append(Spacer(1, 0.3*cm))

        doc.build(story)
        return output_path

