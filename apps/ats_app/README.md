# ATS — Simple Resume Score Checker

## How to use

1. Open workspace **ATS**
2. Create a **Job Description** (title, description, required skills)
3. Create **ATS Resume Check**
   - Enter candidate name
   - Select the Job Description
   - Upload resume (PDF / DOCX / TXT)
4. Save, then click **Check ATS Score**
5. See score out of 100, matched/missing skills, and breakdown

## Install

```bash
bench --site your-site install-app ats_app
./env/bin/pip install -r apps/ats_app/requirements.txt
bench --site your-site migrate
```

## Scoring (out of 100)

| Part | Points |
|------|-------:|
| Required skills match | 50 |
| Keywords match | 20 |
| Preferred skills | 10 |
| Experience | 10 |
| Education | 10 |
