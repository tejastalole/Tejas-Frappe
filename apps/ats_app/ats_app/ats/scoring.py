# Copyright (c) 2026, Tejas and contributors
# MIT License

"""Extract resume text and calculate a simple explainable ATS score."""

from __future__ import annotations

import os
import re

import frappe


def split_csv(value: str | None) -> list[str]:
	if not value:
		return []
	parts = re.split(r"[,;\n|]+", value)
	return [p.strip() for p in parts if p.strip()]


def normalize(text: str) -> str:
	return re.sub(r"\s+", " ", (text or "")).strip().lower()


def contains_term(text: str, term: str) -> bool:
	if not text or not term:
		return False
	pattern = r"\b" + re.escape(term.lower().strip()) + r"\b"
	return bool(re.search(pattern, text.lower()))


def unique(items: list[str]) -> list[str]:
	seen = set()
	out = []
	for item in items:
		key = item.lower()
		if key in seen:
			continue
		seen.add(key)
		out.append(item)
	return out


def extract_text_from_file(file_path: str) -> str:
	ext = os.path.splitext(file_path)[1].lower()
	if ext == ".pdf":
		return _extract_pdf(file_path)
	if ext in (".docx", ".doc"):
		return _extract_docx(file_path)
	if ext == ".txt":
		with open(file_path, encoding="utf-8", errors="ignore") as handle:
			return handle.read()
	frappe.throw(f"Unsupported file type: {ext}. Use PDF, DOCX, or TXT.")


def _extract_pdf(file_path: str) -> str:
	parts = []
	try:
		import pdfplumber

		with pdfplumber.open(file_path) as pdf:
			for page in pdf.pages:
				page_text = page.extract_text()
				if page_text:
					parts.append(page_text)
	except Exception:
		pass

	if parts:
		return "\n".join(parts)

	try:
		import PyPDF2

		with open(file_path, "rb") as handle:
			reader = PyPDF2.PdfReader(handle)
			if getattr(reader, "is_encrypted", False):
				frappe.throw("Password-protected PDF is not supported.")
			for page in reader.pages:
				page_text = page.extract_text()
				if page_text:
					parts.append(page_text)
	except Exception as exc:
		frappe.throw(f"Failed to read PDF: {exc}")

	if not parts:
		frappe.throw("Could not extract text from PDF.")
	return "\n".join(parts)


def _extract_docx(file_path: str) -> str:
	try:
		import docx
	except ImportError:
		frappe.throw("python-docx is required. Run: pip install python-docx")

	document = docx.Document(file_path)
	text = "\n".join(p.text for p in document.paragraphs if p.text.strip())
	if not text.strip():
		frappe.throw("DOCX file appears empty.")
	return text


MONTHS = {
	"jan": 1,
	"january": 1,
	"feb": 2,
	"february": 2,
	"mar": 3,
	"march": 3,
	"apr": 4,
	"april": 4,
	"may": 5,
	"jun": 6,
	"june": 6,
	"jul": 7,
	"july": 7,
	"aug": 8,
	"august": 8,
	"sep": 9,
	"sept": 9,
	"september": 9,
	"oct": 10,
	"october": 10,
	"nov": 11,
	"november": 11,
	"dec": 12,
	"december": 12,
}

EXPERIENCE_HEADER_RE = re.compile(
	r"(?im)^\s*(?:"
	r"(?:internship\s+)?(?:work\s+)?experience|"
	r"professional\s+experience|employment(?:\s+history)?|"
	r"career\s+(?:history|summary)|internships?"
	r")\b"
)
EDUCATION_OR_OTHER_HEADER_RE = re.compile(
	r"(?im)^\s*(?:education|academic|qualification|skills?|projects?|"
	r"certifications?|achievements?|summary|objective|personal)\b"
)
DATE_RANGE_RE = re.compile(
	r"(?i)\b(?:(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
	r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
	r"\.?\s*)?"
	r"((?:19|20)\d{2})"
	r"\s*[-–—~to]+\s*"
	r"(?:(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
	r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
	r"\.?\s*)?"
	r"((?:19|20)\d{2}|present|current|now|ongoing|till\s+date)\b"
)
EXPLICIT_EXP_RE = re.compile(
	r"(?i)(?:total\s+)?(?:work\s+|professional\s+)?"
	r"(?:experience|exp)\s*[:\-–]?\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)"
	r"|"
	r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?"
	r"(?:professional\s+|work\s+)?(?:experience|exp)\b"
)


def _experience_section(text: str) -> str:
	"""Return only experience/internship text; stop at Education/Skills/etc."""
	match = EXPERIENCE_HEADER_RE.search(text)
	if not match:
		return ""
	start = match.start()
	stop = EDUCATION_OR_OTHER_HEADER_RE.search(text, match.end())
	end = stop.start() if stop else len(text)
	return text[start:end]


def _to_month_index(month: str | None, year: int, *, end: bool = False) -> int:
	if month:
		m = MONTHS.get(month.lower().strip("."), 1 if not end else 12)
	else:
		m = 12 if end else 1
	return year * 12 + (m - 1)


def _parse_end_token(token: str) -> tuple[int, int]:
	from datetime import datetime

	val = token.lower().strip()
	if val in ("present", "current", "now", "ongoing", "till date"):
		now = datetime.now()
		return now.year, now.month
	return int(val), 12


def _merge_months(intervals: list[tuple[int, int]]) -> float:
	if not intervals:
		return 0.0
	intervals = sorted(intervals, key=lambda item: item[0])
	merged: list[tuple[int, int]] = []
	for start, end in intervals:
		if end < start:
			continue
		if merged and start <= merged[-1][1] + 1:
			merged[-1] = (merged[-1][0], max(merged[-1][1], end))
		else:
			merged.append((start, end))
	total_months = sum(end - start + 1 for start, end in merged)
	return round(total_months / 12.0, 1)


def extract_experience_years(text: str) -> float | None:
	"""Estimate work experience years.

	- Prefer explicit "X years of experience"
	- Otherwise parse dates only from Experience/Internship sections
	- Never count Education date ranges
	- Merge overlapping jobs so years are not double-counted
	"""
	if not text:
		return None

	explicit = EXPLICIT_EXP_RE.search(text)
	if explicit:
		value = explicit.group(1) or explicit.group(2)
		return round(float(value), 1)

	section = _experience_section(text)
	source = section if section.strip() else text

	intervals: list[tuple[int, int]] = []
	for match in DATE_RANGE_RE.finditer(source):
		line_start = source.rfind("\n", 0, match.start()) + 1
		line_end = source.find("\n", match.end())
		line = source[line_start : line_end if line_end != -1 else None]
		if re.search(
			r"(?i)\b(college|university|school|diploma|bachelor|master|education|cgpa)\b",
			line,
		):
			continue

		start_month, start_year, end_month, end_year_token = match.groups()
		start_year = int(start_year)
		end_year, end_month_num = _parse_end_token(end_year_token)

		start_idx = _to_month_index(start_month, start_year, end=False)
		if end_year_token.isdigit():
			end_idx = _to_month_index(end_month, end_year, end=True)
		else:
			end_idx = end_year * 12 + (end_month_num - 1)

		if end_idx >= start_idx:
			intervals.append((start_idx, end_idx))

	years = _merge_months(intervals)
	return years if years > 0 else None


def education_match(resume_text: str, required: str | None) -> bool:
	if not required:
		return True
	aliases = {
		"be": ["be", "b.e", "bachelor of engineering", "btech", "b.tech", "bachelor of technology"],
		"btech": ["btech", "b.tech", "bachelor of technology", "be", "b.e"],
		"mca": ["mca", "master of computer applications"],
		"mba": ["mba", "master of business"],
		"bsc": ["bsc", "b.sc", "bachelor of science"],
		"msc": ["msc", "m.sc", "master of science"],
	}
	terms = split_csv(required.replace("/", ","))
	lower = resume_text.lower()
	for term in terms:
		key = re.sub(r"[^a-z0-9]", "", term.lower())
		checks = aliases.get(key, [term.lower()])
		if any(contains_term(lower, c) or c in lower for c in checks):
			return True
	return False


def calculate_score(job, resume_text: str) -> dict:
	required = unique(split_csv(job.required_skills))
	preferred = unique(split_csv(job.preferred_skills))
	keywords = unique(split_csv(job.keywords))

	matched_skills = [s for s in required if contains_term(resume_text, s)]
	missing_skills = [s for s in required if s not in matched_skills]
	matched_preferred = [s for s in preferred if contains_term(resume_text, s)]
	matched_keywords = [k for k in keywords if contains_term(resume_text, k)]
	missing_keywords = [k for k in keywords if k not in matched_keywords]

	# Weights (total 100)
	# Required skills 50, keywords 20, preferred 10, experience 10, education 10
	skill_score = (len(matched_skills) / len(required) * 50) if required else 50
	keyword_score = (len(matched_keywords) / len(keywords) * 20) if keywords else 20
	preferred_score = (len(matched_preferred) / len(preferred) * 10) if preferred else 10

	candidate_years = extract_experience_years(resume_text)
	required_years = float(job.experience_required or 0)
	if not required_years:
		experience_score = 10
		experience_note = "No experience requirement set"
	elif candidate_years is None:
		experience_score = 5
		experience_note = "Could not detect experience from resume"
	elif candidate_years >= required_years:
		experience_score = 10
		experience_note = f"Found ~{candidate_years} years (required {required_years})"
	elif candidate_years >= max(required_years - 1, 0):
		experience_score = 6
		experience_note = f"Found ~{candidate_years} years (required {required_years})"
	else:
		experience_score = 2
		experience_note = f"Found ~{candidate_years} years (required {required_years})"

	edu_ok = education_match(resume_text, job.education)
	education_score = 10 if edu_ok else (5 if not job.education else 0)
	education_note = "Matched" if edu_ok else ("No requirement" if not job.education else "Not found")

	total = round(
		skill_score + keyword_score + preferred_score + experience_score + education_score,
		1,
	)
	total = max(0, min(100, total))

	if total >= 85:
		recommendation = "Strong Match"
	elif total >= 70:
		recommendation = "Good Match"
	elif total >= 55:
		recommendation = "Average Match"
	else:
		recommendation = "Weak Match"

	breakdown = f"""
	<p><b>ATS Score: {total} / 100</b> — {recommendation}</p>
	<ul>
		<li>Required Skills: {round(skill_score, 1)} / 50
			({" , ".join(matched_skills) or "none"} matched)</li>
		<li>Keywords: {round(keyword_score, 1)} / 20</li>
		<li>Preferred Skills: {round(preferred_score, 1)} / 10</li>
		<li>Experience: {round(experience_score, 1)} / 10 — {experience_note}</li>
		<li>Education: {round(education_score, 1)} / 10 — {education_note}</li>
	</ul>
	"""

	return {
		"ats_score": total,
		"recommendation": recommendation,
		"matched_skills": ", ".join(matched_skills),
		"missing_skills": ", ".join(missing_skills),
		"matched_keywords": ", ".join(matched_keywords),
		"missing_keywords": ", ".join(missing_keywords),
		"score_breakdown": breakdown,
	}


@frappe.whitelist()
def check_ats_score(name: str):
	doc = frappe.get_doc("ATS Resume Check", name)
	if not doc.resume:
		frappe.throw("Please upload a resume first.")
	if not doc.job_description:
		frappe.throw("Please select a Job Description.")

	file_doc = frappe.get_doc("File", {"file_url": doc.resume})
	resume_text = extract_text_from_file(file_doc.get_full_path())
	if not resume_text.strip():
		frappe.throw("Could not extract text from the resume.")

	job = frappe.get_doc("Job Description", doc.job_description)
	result = calculate_score(job, resume_text)

	doc.resume_text = resume_text
	doc.ats_score = result["ats_score"]
	doc.recommendation = result["recommendation"]
	doc.matched_skills = result["matched_skills"]
	doc.missing_skills = result["missing_skills"]
	doc.matched_keywords = result["matched_keywords"]
	doc.missing_keywords = result["missing_keywords"]
	doc.score_breakdown = result["score_breakdown"]
	doc.checked_on = frappe.utils.now_datetime()
	doc.save()

	return {
		"ats_score": doc.ats_score,
		"recommendation": doc.recommendation,
	}
