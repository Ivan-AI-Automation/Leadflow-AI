# LeadFlow AI Sample Data

This folder contains fictional but realistic lead datasets for testing and demonstrating LeadFlow AI.

## Files

### `b2b_service_leads.csv`

Represents leads for B2B service businesses such as marketing agencies, consultants, SaaS companies, legal services, IT providers, and field service companies.

Expected columns:

```text
first_name, last_name, company_name, job_title, email, phone, website, industry, source, location, deal_value, budget_range, interest_level, timeline, notes
```

### `real_estate_leads.csv`

Represents buyer and investor leads for an estate agency or real estate sales team.

Expected columns:

```text
first_name, last_name, email, phone, location, property_type, budget_range, timeline, source, interest_level, notes
```

### `recruitment_leads.xlsx`

Represents hiring leads for a recruitment agency. Each row is a company contact with a hiring need.

Expected columns:

```text
first_name, last_name, company_name, job_title, email, phone, hiring_need, role_type, urgency, source, location, notes
```

## Intentional Data Issues

The datasets intentionally include realistic imperfections:

- missing email values;
- missing phone values;
- missing company names;
- different lead sources such as referrals, inbound forms, webinars, ads, open houses, and LinkedIn;
- different deal values, budgets, urgency levels, and timelines;
- duplicate-looking leads with slightly different contact details or sources;
- notes that contain useful buying intent, context, or follow-up clues.

These issues are included so the project can demonstrate validation, missing contact detection, lead scoring, categorization, and follow-up prioritization.

## How These Files Are Used

Use these files to test the import upload flow:

1. Sign in to LeadFlow AI.
2. Upload one of the files from this folder.
3. Review the detected row count, column count, column names, and data types.
4. Later project steps will use these same files to create leads, calculate Follow-up Priority Scores, generate email drafts, and export approved follow-ups.

## Regenerating The Files

Run the generator from the project root:

```bash
python sample_data/generate_sample_data.py
```

The script recreates:

- `sample_data/b2b_service_leads.csv`
- `sample_data/real_estate_leads.csv`
- `sample_data/recruitment_leads.xlsx`
