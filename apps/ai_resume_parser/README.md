# AI Resume Parser

Simple two-doctype resume parser for Frappe.

1. **Resume Upload** — upload resume, enter applicant name, click **Parse Resume**
2. **Parsed Resume Data** — all extracted fields stored here

## Install

```bash
cd /home/frappe/tejas
./env/bin/pip install -e apps/ai_resume_parser
./env/bin/pip install PyPDF2 pdfplumber python-docx

# Add to sites/apps.txt: ai_resume_parser
bench --site site1.local install-app ai_resume_parser
bench build --app ai_resume_parser
bench --site site1.local clear-cache
```
