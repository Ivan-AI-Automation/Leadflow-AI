# Business Case Study: LeadFlow AI

## Scenario

A small B2B service agency receives leads from several channels:

- Website forms
- LinkedIn outreach
- Referrals
- Local business events
- Occasional cold outreach lists

The team stores those leads in spreadsheets. Each spreadsheet has slightly different columns,
different formatting, and a mix of good and incomplete contact details.

The agency has a simple problem: lead follow-up is too inconsistent.

Some leads get a reply within an hour. Others sit in a spreadsheet until someone has time to sort
the file manually. High-value leads are not always obvious, and writing follow-up emails from
scratch takes time that the team would rather spend on sales calls and client work.

LeadFlow AI is designed as an internal tool for this exact workflow.

## Before LeadFlow AI

The agency's workflow looked like this:

1. Download leads from website forms, LinkedIn, event lists, and referral notes.
2. Combine them manually in a spreadsheet.
3. Scan rows to find missing emails or phone numbers.
4. Guess which leads are most urgent.
5. Manually label leads as good, maybe, or low priority.
6. Write follow-up emails one by one.
7. Copy email drafts into another system.
8. Lose track of which leads were contacted, followed up, closed, or lost.

The problem was not that the team lacked leads. The problem was that the lead queue had no reliable operating system.

## After LeadFlow AI

With LeadFlow AI, the workflow becomes:

1. Upload the spreadsheet.
2. Review import metadata and obvious data quality issues.
3. Process the file into normalized leads.
4. Detect missing emails, phone numbers, and company names.
5. Score leads using deterministic Follow-up Priority Score rules.
6. Categorize leads into Hot, Warm, Nurture, and Low Priority.
7. Generate editable follow-up drafts for selected leads.
8. Approve drafts after human review.
9. Export ready-to-send drafts as CSV or Excel.
10. Track lead status as New, Contacted, Follow-up, Closed, or Lost.

The team still makes the business decisions. The tool removes the repetitive sorting and drafting work around those decisions.

## What LeadFlow AI Helps With

LeadFlow AI helps the agency:

- Upload lead spreadsheets from different sources.
- Detect missing contact data before wasting time on unusable rows.
- Prioritize high-value and urgent leads.
- Categorize leads into Hot, Warm, Nurture, and Low Priority.
- Generate personalized email drafts that a human can edit.
- Approve and export ready-to-send email drafts.
- See simple pipeline metrics in one dashboard.

## Measurable Business Value

These are realistic ways the agency could measure the value of the tool:

| Metric | Before | After using LeadFlow AI |
| --- | --- | --- |
| Time to inspect a new spreadsheet | Manual review row by row | Import report and missing contact counts |
| Lead prioritization | Based on whoever opens the file first | Deterministic score and category |
| Follow-up consistency | Varies by person | Draft workflow and status tracking |
| Draft writing time | Written from scratch | AI-assisted draft, edited by a human |
| Export process | Manual copy and paste | CSV or Excel export |

I would not claim exact revenue uplift without real production data. The clearer claim is
operational: fewer leads are ignored, better leads are surfaced earlier, and the team spends less
time preparing follow-up messages.

## Example Lead Scoring Results

LeadFlow AI uses a deterministic Follow-up Priority Score. The score is explainable and does not depend on AI.

Example 1:

```json
{
  "lead": "Maya Patel, Northstar Homes",
  "source": "Referral",
  "deal_value": 32000,
  "timeline": "Immediate",
  "interest_level": "High",
  "score": 88,
  "category": "Hot",
  "recommendation": "Prioritize this lead within 24 hours."
}
```

Why this lead scores well:

- Email and phone are present.
- Company data is present.
- Deal value is high.
- Timeline is urgent.
- Referral source is strong.
- Notes give useful context.

Example 2:

```json
{
  "lead": "Jordan Lee, BrightPath Marketing",
  "source": "Inbound form",
  "deal_value": 9200,
  "timeline": "30-60 days",
  "interest_level": "Medium",
  "score": 67,
  "category": "Warm",
  "recommendation": "Follow up soon and keep the conversation moving."
}
```

Why this lead is Warm:

- Email is present.
- Phone is missing.
- Source is still useful.
- Timeline is not urgent.
- Deal value is moderate.

Example 3:

```json
{
  "lead": "Casey Moore",
  "source": "Unknown",
  "deal_value": null,
  "timeline": null,
  "interest_level": null,
  "score": 22,
  "category": "Low Priority",
  "recommendation": "Do not prioritize until more context is available."
}
```

Why this lead is Low Priority:

- Email is missing.
- Phone is missing.
- Company is missing.
- There is no clear buying intent or timeline.

## Example Email Draft

Input context:

```text
Lead: Maya Patel
Company: Northstar Homes
Industry: Property Management
Source: Referral
Interest level: High
Timeline: Immediate
Priority score: 88
Tone: Professional
Sender company: LeadFlow AI Demo Agency
```

Generated draft:

```text
Subject: Following up on Northstar Homes' lead follow-up process

Hi Maya,

Thanks for your interest. I saw that Northstar Homes is looking at improving lead follow-up soon, so I wanted to suggest a practical next step.

LeadFlow AI Demo Agency helps small teams organize incoming leads, spot missing contact details, and prepare follow-up drafts faster without losing the human review step.

Would it be useful to schedule a short call this week to see whether this fits your current workflow?

Best,
LeadFlow AI Demo Agency
```

The draft is intentionally not sent automatically. A human reviews, edits, approves, and exports it.

## Why This Internal Tool Saves Time

The time savings come from removing repeated small decisions:

- Which rows are missing contact details?
- Which leads look urgent?
- Which leads have enough context for a follow-up?
- Which leads should be contacted first?
- Which drafts are approved and ready to export?

None of those tasks is difficult once. They become expensive when repeated across every spreadsheet.

LeadFlow AI gives the team a consistent way to handle those decisions.

## Honest Trade-offs

This project makes a few deliberate trade-offs:

- The app does not send emails. Exporting drafts is safer and easier to inspect in a portfolio project.
- Imports are processed synchronously. That keeps the code easier to understand, but background jobs would be better for large files.
- Scoring rules are deterministic. This is less flexible than an AI ranking model, but it is easier to explain and debug.
- Streamlit is used for speed and clarity. It is a good fit for an internal tool, but a React frontend would offer more control for a larger product.
- The AI provider is used only for writing drafts. It does not make final sales decisions.
- The Docker Compose setup is development-oriented. A real production deployment would need stronger secret management, backups, monitoring, and HTTPS.

## Why I Built It This Way

I built LeadFlow AI as a middle-level Python portfolio project, not as a toy CRUD app.

The goal was to show practical backend judgment:

- Separate API schemas from database models.
- Keep scoring deterministic and explainable.
- Use repositories for database access without burying simple queries under too much abstraction.
- Put business workflows in services.
- Use Alembic from the start.
- Support PostgreSQL through Docker and SQLite for local fallback.
- Add tests around business-critical behavior instead of testing every line.
- Treat AI as an optional provider, not as the center of the system.

I also wanted the project to feel like an actual internal tool. The business user should care about
priority, missing contact details, draft approval, and export files. They should not need to
understand the database schema or AI prompt details.

## What I Would Improve Next

If I continued building this project, I would add:

- Background jobs for import processing and bulk draft generation.
- A visual import column mapping screen.
- Duplicate merge suggestions.
- Team accounts and role-based permissions.
- More detailed activity history in the frontend.
- Export templates for specific CRMs or email tools.
- Email sending integrations behind explicit approval steps.
- Production monitoring, structured logs, and backup guidance.
- Better frontend visual QA with browser screenshots.
- A small seed script for demo users and demo imports.

## Conclusion

LeadFlow AI is a practical workflow tool for teams that already have leads but do not have a consistent process for handling them.

It does not try to replace sales judgment. It makes the lead queue easier to inspect, prioritize, draft for, and export from.

That is the business value: faster follow-up, fewer missed high-value leads, and less manual spreadsheet work.
