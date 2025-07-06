import docx
import re
import spacy
from typing import List, Dict, Optional, Set, Tuple
import json
import os
from spacy.matcher import PhraseMatcher, Matcher
from datetime import datetime
import dateutil.parser as date_parser
import pandas as pd
import fitz  # pymupdf

COMPANY_INDICATORS = [
    'technologies', 'tech', 'systems', 'solutions', 'services', 'consulting', 'labs', 'corporation',
    'corp', 'inc', 'ltd', 'limited', 'company', 'co', 'enterprise', 'group', 'associates',
    'partners', 'ventures', 'studios', 'digital', 'software', 'pvt', 'private'
]

nlp = spacy.load("en_core_web_sm")

# Load external datasets
NAMES_DF = pd.read_csv('C:/Users/tanay/Desktop/Data/College/Summer25/TalEnd/BackEnd/paired_full_names.csv', nrows=50000)
FIRST_NAMES_SET = set(NAMES_DF['First Name'].dropna().str.lower())
LAST_NAMES_SET = set(NAMES_DF['Last Name'].dropna().str.lower())

with open('C:/Users/tanay/Desktop/Data/College/Summer25/TalEnd/BackEnd/LINKEDIN_SKILLS_ORIGINAL.txt', encoding='utf-8') as f:
    SKILLS_SET = set(line.strip().lower() for line in f if line.strip())

with open('C:/Users/tanay/Desktop/Data/College/Summer25/TalEnd/BackEnd/titles_combined.txt', encoding='utf-8') as f:
    TITLES_SET = set(line.strip().lower() for line in f if line.strip())

COLLEGE_DF = pd.read_csv('C:/Users/tanay/Desktop/Data/College/Summer25/TalEnd/BackEnd/world-universities.csv', header=None, names=['country', 'college', 'url'])
COLLEGE_SET = set(COLLEGE_DF['college'].dropna().str.lower())

FORBIDDEN_NAMES = {"chatgpt", "resume", "cv", "profile", "curriculum vitae", "summary", "objective"}

def load_indian_names_from_file(file_path: str) -> Dict[str, List[str]]:
    """Load Indian names from external file if available"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Could not load names from {file_path}: {e}")
    return {}

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    doc = fitz.open(file_path)
    for page in doc:
        text += page.get_text("text") or ""
    doc.close()
    return text.strip()

def extract_text_from_docx(file_path: str) -> str:
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs]).strip()

def extract_emails(text: str) -> List[str]:
    """Extract all email addresses from text"""
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(pattern, text)
    return list(set(emails)) 

def extract_phone_numbers(text: str) -> List[str]:
    """Extract all phone numbers from text with improved patterns"""
    patterns = [
        r'\+91[-\s]?\d{5}\s?\d{5}',  # +91 12345 67890
        r'\b91[-\s]?\d{10}\b',       # 91 1234567890
        r'\b[789]\d{9}\b',           # 9876543210
        r'\b0\d{2,4}[-\s]?\d{6,8}\b', # Landline
        r'\(\d{2,4}\)\s*\d{6,8}',   # (022) 12345678
        r'\+\d{1,4}[-\s]?\d{8,12}',  # International format
    ]
    
    phones = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        phones.extend(matches)
    
    # Clean and validate phone numbers
    cleaned_phones = []
    for phone in phones:
        digits_only = re.sub(r'[^\d]', '', phone)
        if 10 <= len(digits_only) <= 15:  # Valid phone number length
            cleaned_phones.append(phone.strip())
    
    return list(set(cleaned_phones))

def extract_name_enhanced(text: str, doc=None, file_name: Optional[str] = None) -> Optional[str]:
    """Extract name by checking file name, first line, first two words, first 8 lines, spaCy NER, and email. If a name appears in 2+ sources (allowing for subset matches), return it. Filters out generic/forbidden names."""
    if doc is None:
        doc = nlp(text)
    lines = text.split('\n')
    candidates = []

    # Helper to normalize names
    def norm(name):
        return ' '.join(name.strip().split()).title() if name else None

    # Helper to check forbidden names (robust)
    def is_forbidden(name):
        if not name:
            return True
        name_norm = name.strip().lower().replace(" ", "")
        for forbidden in FORBIDDEN_NAMES:
            forbidden_norm = forbidden.replace(" ", "").lower()
            if name_norm == forbidden_norm:
                return True
        return False

    # 0. File name
    file_name_candidate = None
    if file_name:
        base = os.path.splitext(os.path.basename(file_name))[0]
        file_name_words = re.split(r'[^A-Za-z]+', base)
        file_name_words = [w for w in file_name_words if w]
        if 2 <= len(file_name_words) <= 4:
            first_name_valid = file_name_words[0].lower() in FIRST_NAMES_SET
            last_name_valid = file_name_words[-1].lower() in LAST_NAMES_SET
            if first_name_valid or last_name_valid:
                if all(word.isalpha() and word[0].isupper() for word in file_name_words):
                    file_name_candidate = ' '.join(file_name_words)
                    candidate_norm = norm(file_name_candidate)
                    if not is_forbidden(candidate_norm):
                        candidates.append(candidate_norm)

    # 1. First line
    first_line_candidate = None
    if lines:
        first_line = lines[0].strip()
        first_line_words = first_line.split()
        if 2 <= len(first_line_words) <= 4:
            first_name_valid = first_line_words[0].lower() in FIRST_NAMES_SET
            last_name_valid = first_line_words[-1].lower() in LAST_NAMES_SET
            if first_name_valid or last_name_valid:
                if all(word.isalpha() and word[0].isupper() for word in first_line_words):
                    first_line_candidate = first_line
                    candidate_norm = norm(first_line_candidate)
                    if not is_forbidden(candidate_norm):
                        candidates.append(candidate_norm)

    # 2. First two words
    first_two_candidate = None
    words = text.split()
    if len(words) >= 2:
        first_two = words[:2]
        # More permissive: if both are alphabetic and title-cased, accept as candidate
        if all(word.isalpha() and word.istitle() for word in first_two):
            first_two_candidate = ' '.join(first_two)
            candidate_norm = norm(first_two_candidate)
            if not is_forbidden(candidate_norm):
                candidates.append(candidate_norm)
        # Bonus: if both are in names set, even if not title-cased
        elif first_two[0].lower() in FIRST_NAMES_SET and first_two[1].lower() in LAST_NAMES_SET:
            first_two_candidate = ' '.join(first_two)
            candidate_norm = norm(first_two_candidate)
            if not is_forbidden(candidate_norm):
                candidates.append(candidate_norm)

    # 3. First 8 lines (heuristics)
    heuristics_candidate = None
    for i, line in enumerate(lines[:8]):
        line = line.strip()
        if not line or len(line) < 3:
            continue
        skip_patterns = [
            r'\b(curriculum|vitae|resume|cv|profile|summary|objective|contact|email|phone|linkedin|github)\b',
            r'\b\d+\b',
            r'@',
            r'https?://',
        ]
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in skip_patterns):
            continue
        words = line.split()
        if 2 <= len(words) <= 4:
            if all(word.isalpha() and word.istitle() for word in words):
                if (words[0].lower() in FIRST_NAMES_SET or 
                    words[-1].lower() in LAST_NAMES_SET or
                    i < 3):
                    heuristics_candidate = line
                    candidate_norm = norm(heuristics_candidate)
                    if not is_forbidden(candidate_norm):
                        candidates.append(candidate_norm)
                    break

    # 4. spaCy NER
    ner_candidate = None
    for ent in doc.ents:
        if ent.label_ == "PERSON" and 2 <= len(ent.text.split()) <= 4:
            if not any(word.lower() in ['university', 'college', 'institute', 'company'] 
                      for word in ent.text.split()):
                ner_candidate = ent.text.strip()
                candidate_norm = norm(ner_candidate)
                if not is_forbidden(candidate_norm):
                    candidates.append(candidate_norm)
                break

    # 5. Email
    email_candidate = None
    emails = extract_emails(text)
    if emails:
        name_from_email = extract_name_from_email(emails[0])
        if name_from_email:
            email_candidate = name_from_email
            candidate_norm = norm(email_candidate)
            if not is_forbidden(candidate_norm):
                candidates.append(candidate_norm)

    # Improved consensus: treat names as matching if one is a contiguous subsequence of the other
    from collections import Counter
    def is_subsequence(short, long):
        """Return True if all words in short appear in order in long (contiguous)."""
        short_words = short.split()
        long_words = long.split()
        for i in range(len(long_words) - len(short_words) + 1):
            if long_words[i:i+len(short_words)] == short_words:
                return True
        return False

    filtered_candidates = [c for c in candidates if c and not is_forbidden(c)]
    if not filtered_candidates:
        return None
    # Count matches by subsequence
    match_counts = Counter()
    for i, cand_i in enumerate(filtered_candidates):
        for j, cand_j in enumerate(filtered_candidates):
            if i == j:
                continue
            # If either is a contiguous subsequence of the other, count as a match
            if is_subsequence(cand_i, cand_j) or is_subsequence(cand_j, cand_i):
                match_counts[cand_i] += 1
    # If any candidate matches with at least one other, return the longest such candidate (not forbidden)
    consensus_candidates = [c for c, count in match_counts.items() if count >= 1 and not is_forbidden(c)]
    for name in sorted(consensus_candidates, key=lambda x: len(x.split()), reverse=True):
        if name and not is_forbidden(name):
            return name
    # Otherwise, return the first non-empty candidate that is not forbidden
    for name in filtered_candidates:
        if name and not is_forbidden(name):
            return name
    return None

def extract_name_from_email(email: str) -> Optional[str]:
    """Derive a name from an email address using paired_full_names.csv"""
    if not email:
        return None
    try:
        local_part = email.split('@')[0]
        name_part = re.sub(r'[\._\d\-]', ' ', local_part)
        name_part = re.sub(r'\b(mr|ms|dr|prof|sir|madam)\b', '', name_part, flags=re.IGNORECASE)
        words = [word.capitalize() for word in name_part.split() if len(word) > 1]
        # Try to match first and last names from dataset
        for i in range(len(words)-1):
            if words[i].lower() in FIRST_NAMES_SET and words[i+1].lower() in LAST_NAMES_SET:
                return f"{words[i]} {words[i+1]}"
        if words and words[0].lower() in FIRST_NAMES_SET:
            return words[0]
        if 2 <= len(words) <= 4:
            return ' '.join(words)
    except Exception:
        return None
    return None

def extract_skills_enhanced(text: str) -> List[str]:
    """Extract skills using LINKEDIN_SKILLS_ORIGINAL.txt, matching only whole words."""
    found_skills = set()
    text_lower = text.lower()
    for skill in SKILLS_SET:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.add(skill)
    return list(found_skills)

def extract_work_experience(text: str) -> Dict[str, any]:
    """Extract detailed work experience information"""
    
    # Pattern for experience sections
    experience_section_patterns = [
        r'(?:work\s+)?experience\s*:?\s*(.*?)(?=\n(?:education|skills|projects|certifications|\Z))',
        r'professional\s+experience\s*:?\s*(.*?)(?=\n(?:education|skills|projects|certifications|\Z))',
        r'employment\s+history\s*:?\s*(.*?)(?=\n(?:education|skills|projects|certifications|\Z))',
    ]
    
    experience_text = ""
    for pattern in experience_section_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            experience_text = match.group(1)
            break
    
    if not experience_text:
        experience_text = text  # Use full text if no specific section found
    
    # Extract years of experience from various patterns
    years_patterns = [
        r'(\d+(?:\.\d+)?)\+?\s*years?\s+of\s+experience',
        r'experience\s+of\s+(\d+(?:\.\d+)?)\+?\s*years?',
        r'(\d+(?:\.\d+)?)\+?\s*years?\s+experience',
        r'(\d+(?:\.\d+)?)\+?\s*yrs?\s+experience',
        r'total\s+experience\s*:?\s*(\d+(?:\.\d+)?)\+?\s*years?',
    ]
    
    total_experience = None
    for pattern in years_patterns:
        matches = re.findall(pattern, experience_text, re.IGNORECASE)
        if matches:
            try:
                total_experience = max(float(match) for match in matches)
                break
            except ValueError:
                continue
    
    # Extract individual job entries
    job_entries = extract_job_entries(experience_text)
    
    # Calculate experience from job dates if not explicitly mentioned
    if not total_experience and job_entries:
        calculated_experience = calculate_total_experience_from_jobs(job_entries)
        if calculated_experience:
            total_experience = calculated_experience
    
    return {
        'total_years': total_experience,
        'job_entries': job_entries,
        'current_position': extract_current_position(text),
        'current_company': extract_current_company(text, job_entries)
    }

def extract_job_entries(text: str) -> List[Dict[str, str]]:
    """Extract individual job entries with dates, positions, and companies"""
    
    job_entries = []
    lines = text.split('\n')
    current_job = {}
    date_patterns = [
        r'(\d{4})\s*[-–]\s*(\d{4}|present|current)',
        r'(\w+\s+\d{4})\s*[-–]\s*(\w+\s+\d{4}|present|current)',
        r'(\d{1,2}/\d{4})\s*[-–]\s*(\d{1,2}/\d{4}|present|current)',
    ]
    for line in lines:
        line = line.strip()
        if not line:
            if current_job:
                job_entries.append(current_job)
                current_job = {}
            continue
        
        # Check for date patterns
        date_found = False
        for pattern in date_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                current_job['start_date'] = match.group(1)
                current_job['end_date'] = match.group(2)
                date_found = True
                break
        
        # Look for job titles
        if any(title in line.lower() for title in TITLES_SET):
            current_job['position'] = line
        
        # Look for company names
        if any(indicator.lower() in line.lower() for indicator in COMPANY_INDICATORS):
            current_job['company'] = line
    
    if current_job:
        job_entries.append(current_job)
    
    return job_entries

def calculate_total_experience_from_jobs(job_entries: List[Dict[str, str]]) -> Optional[float]:
    """Calculate total experience from job date ranges"""
    
    total_months = 0
    current_year = datetime.now().year
    
    for job in job_entries:
        if 'start_date' not in job or 'end_date' not in job:
            continue
        
        try:
            # Parse start date
            start_str = job['start_date']
            if start_str.isdigit():
                start_year = int(start_str)
                start_month = 1
            else:
                start_date = date_parser.parse(start_str, fuzzy=True)
                start_year = start_date.year
                start_month = start_date.month
            
            # Parse end date
            end_str = job['end_date'].lower()
            if end_str in ['present', 'current']:
                end_year = current_year
                end_month = 12
            elif end_str.isdigit():
                end_year = int(end_str)
                end_month = 12
            else:
                end_date = date_parser.parse(end_str, fuzzy=True)
                end_year = end_date.year
                end_month = end_date.month
            
            # Calculate months for this job
            job_months = (end_year - start_year) * 12 + (end_month - start_month)
            total_months += max(0, job_months)
            
        except Exception:
            continue
    
    return round(total_months / 12, 1) if total_months > 0 else None

def extract_current_position(text: str) -> Optional[str]:
    """Extract only the present designation using titles_combined.txt"""
    lines = text.split('\n')
    for line in lines:
        for title in TITLES_SET:
            if title in line.lower() and ('present' in line.lower() or 'current' in line.lower()):
                return title.title()
    return None

def extract_current_company(text: str, job_entries: List[Dict[str, str]]) -> Optional[str]:
    """Extract current company"""
    
    # Check job entries for current company
    for job in job_entries:
        if ('end_date' in job and 
            job['end_date'].lower() in ['present', 'current'] and 
            'company' in job):
            return job['company']
    
    # Look for current company indicators in text
    current_company_patterns = [
        r'current(?:ly)?\s+(?:working\s+(?:at|with|for))?\s*:?\s*([^\n]+(?:' + '|'.join(COMPANY_INDICATORS) + r')[^\n]*)',
        r'presently\s+(?:at|with)\s+([^\n]+)',
        r'working\s+(?:at|with|for)\s+([^\n]+(?:' + '|'.join(COMPANY_INDICATORS) + r')[^\n]*)',
    ]
    
    for pattern in current_company_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return None

def extract_education_enhanced(text: str) -> List[Dict[str, str]]:
    """Extract education and check for college using world-universities.csv"""
    education_entries = []
    lines = text.split('\n')
    for line in lines:
        for college in COLLEGE_SET:
            if college in line.lower():
                education_entries.append({'institution': college.title(), 'raw': line.strip()})
    return education_entries

def parse_cv_enhanced(text: str, file_name: Optional[str] = None) -> dict:
    """Enhanced CV parsing function with all improvements"""
    doc = nlp(text)
    # Extract work experience details
    work_experience = extract_work_experience(text)
    parsed_data = {
        "name": extract_name_enhanced(text, doc, file_name=file_name),
        "emails": extract_emails(text),
        "phone_numbers": extract_phone_numbers(text),
        "skills_by_category": extract_skills_enhanced(text),
        "total_experience_years": work_experience['total_years'],
        "job_entries": work_experience['job_entries'],
        "current_position": work_experience['current_position'],
        "current_company": work_experience['current_company'],
        "education": extract_education_enhanced(text),
        "raw_text": text
    }
    # Add flat skills list for backward compatibility
    parsed_data['skills'] = list(set(parsed_data['skills_by_category']))
    # Add primary email and phone for backward compatibility
    parsed_data['email'] = parsed_data['emails'][0] if parsed_data['emails'] else None
    parsed_data['phone'] = parsed_data['phone_numbers'][0] if parsed_data['phone_numbers'] else None
    return parsed_data

def parse_cv(text: str, file_name: Optional[str] = None) -> dict:
    """Main CV parsing function - enhanced version"""
    return parse_cv_enhanced(text, file_name=file_name)

def save_indian_names_dataset(names_dict: Dict[str, List[str]], file_path: str = 'indian_names.json'):
    """Save Indian names dataset to JSON file"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(names_dict, f, ensure_ascii=False, indent=2)
        print(f"Indian names dataset saved to {file_path}")
    except Exception as e:
        print(f"Error saving names dataset: {e}")

def load_large_indian_names_dataset(csv_file_path: str) -> Dict[str, List[str]]:
    """Load your 50K Indian names from CSV/Excel file"""
    import pandas as pd
    try:
        df = pd.read_csv(r"TalEnd/BackEnd/paired_full_names.csv")
        names_dict = {
            'first_names': df['first_name'].dropna().unique().tolist() if 'first_name' in df.columns else [],
            'last_names': df['last_name'].dropna().unique().tolist() if 'last_name' in df.columns else []
        }
        save_indian_names_dataset(names_dict)
        return names_dict
    except Exception as e:
        print(f"Error loading large dataset: {e}")
        return {}

def test_cv_parser(sample_cv_text: str):
    """Test the enhanced CV parser with sample text"""
    print("Testing Enhanced CV Parser...")
    print("=" * 50)
    result = parse_cv_enhanced(sample_cv_text)
    print(f"Name: {result['name']}")
    print(f"Email: {result['email']}")
    print(f"Phone: {result['phone']}")
    print(f"Total Experience: {result['total_experience_years']} years")
    print(f"Current Position: {result['current_position']}")
    print(f"Current Company: {result['current_company']}")
    print("\nSkills by Category:")
    for skill in result['skills_by_category']:
        print(f"  {skill}")
    print(f"\nJob Entries: {len(result['job_entries'])}")
    for i, job in enumerate(result['job_entries']):
        print(f"  Job {i+1}: {job}")
    print(f"\nEducation: {len(result['education'])}")
    for i, edu in enumerate(result['education']):
        print(f"  Education {i+1}: {edu}")
    return result

def profile_parse_cv_enhanced(text: str, file_name: Optional[str] = None) -> dict:
    """Profile each stage of the enhanced CV parsing function and print timings."""
    import time
    timings = {}
    start = time.time()
    doc = nlp(text)
    timings['nlp'] = time.time() - start

    t0 = time.time()
    name = extract_name_enhanced(text, doc, file_name=file_name)
    timings['name'] = time.time() - t0

    t0 = time.time()
    emails = extract_emails(text)
    timings['emails'] = time.time() - t0

    t0 = time.time()
    phones = extract_phone_numbers(text)
    timings['phones'] = time.time() - t0

    t0 = time.time()
    skills_by_category = extract_skills_enhanced(text)
    timings['skills'] = time.time() - t0

    t0 = time.time()
    work_experience = extract_work_experience(text)
    timings['work_experience'] = time.time() - t0

    t0 = time.time()
    education = extract_education_enhanced(text)
    timings['education'] = time.time() - t0

    total = time.time() - start
    timings['total'] = total

    print("\n--- CV Parser Profiling ---")
    for k, v in timings.items():
        print(f"{k:20s}: {v:.4f} seconds")
    print("--------------------------\n")

    parsed_data = {
        "name": name,
        "emails": emails,
        "phone_numbers": phones,
        "skills_by_category": skills_by_category,
        "total_experience_years": work_experience['total_years'],
        "job_entries": work_experience['job_entries'],
        "current_position": work_experience['current_position'],
        "current_company": work_experience['current_company'],
        "education": education,
        "raw_text": text
    }
    parsed_data['skills'] = list(set(parsed_data['skills_by_category']))
    parsed_data['email'] = parsed_data['emails'][0] if parsed_data['emails'] else None
    parsed_data['phone'] = parsed_data['phone_numbers'][0] if parsed_data['phone_numbers'] else None
    return parsed_data


