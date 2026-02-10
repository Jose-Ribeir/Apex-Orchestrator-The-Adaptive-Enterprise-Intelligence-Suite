# Seed data for RAG

To have RAG data ready for the seeded **Financial Analyst Agent** and **Field Service Assistant** after startup, place the following files in this directory:

| File | Used by |
|------|--------|
| `industry_standards_review.pdf` | Financial Analyst Agent |
| `company_policy_memo.pdf` | Financial Analyst Agent |
| `q3_financial_report.pdf` | Financial Analyst Agent |
| `parts_catalog.csv` | Field Service Assistant |

If a file is missing, seed will log a warning and skip it; startup continues. The agents are still created; only document ingest is skipped for missing files.

Do not commit large or sensitive PDFs/CSV to version control unless intended. Copy your files here (e.g. from Downloads) before or after deployment.
