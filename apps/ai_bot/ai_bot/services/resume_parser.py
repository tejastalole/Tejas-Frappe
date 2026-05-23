# Copyright (c) 2026, Tejas and contributors
# MIT License

"""Extract Job Applicant fields from resume text."""

import re

GENDER_PATTERNS = [
	(r"(?:gender|sex)\s*[:\-]\s*(male|female|other|m|f)\b", re.I),
	(r"\b(male|female)\b", re.I),
]


def parse_resume_text(text: str) -> dict:
	"""Parse plain-text resume into Job Applicant field dict."""
	text = text or ""
	data = {}

	email = re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", text)
	if email:
		data["email_id"] = email.group(0)

	phone = re.search(r"(?:\+?\d{1,3}[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}", text)
	if phone:
		data["phone_number"] = phone.group(0).strip()

	for pattern, flags in GENDER_PATTERNS:
		m = re.search(pattern, text, flags)
		if m:
			g = m.group(1).lower()
			if g in ("m", "male"):
				data["gender"] = "Male"
			elif g in ("f", "female"):
				data["gender"] = "Female"
			else:
				data["gender"] = g.title()
			break

	# Name: first non-empty line or "Name:" label
	name_m = re.search(r"(?:name|candidate)\s*[:\-]\s*(.+)", text, re.I)
	if name_m:
		data["applicant_name"] = name_m.group(1).strip()[:140]
	else:
		for line in text.splitlines():
			line = line.strip()
			if line and len(line) < 80 and not re.search(r"@|http|phone|email", line, re.I):
				data["applicant_name"] = line
				break

	skills = []
	skills_m = re.search(
		r"(?:skills?|technical skills?)\s*[:\-]?\s*(.+?)(?:\n\n|education|experience|$)",
		text,
		re.I | re.S,
	)
	if skills_m:
		skills = [s.strip() for s in re.split(r"[,;•\n]", skills_m.group(1)) if s.strip()][:15]
	if skills:
		data["skills"] = ", ".join(skills)

	if re.search(r"\b(b\.?tech|b\.?e\.?|m\.?tech|mba|b\.?com|degree)\b", text, re.I):
		data["education"] = _("See resume — education section detected.")

	if re.search(r"\b(experience|work history|employment)\b", text, re.I):
		data["experience"] = _("See resume — experience section detected.")

	return data
