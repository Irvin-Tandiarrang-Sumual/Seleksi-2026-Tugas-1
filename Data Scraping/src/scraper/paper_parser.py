import re
from typing import Any, Dict, List, Optional, Tuple

from langdetect import detect

from models.academic_year import AcademicYear
from models.paper import Paper
from models.student import Student
from utils.pdf_extractor import PDFExtractor


class PaperParser:
    ALL_EMAILS_PATTERN = re.compile(
        r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", re.IGNORECASE
    )

    ITB_PRODI_PREFIX = r"(?:135|182|165|132|180|181|101|102|[1-3|7|9][0-9]{2})"

    def parse(
        self,
        pdf_bytes: bytes,
        file_url: str,
        course_code: str = "IF2123",
        academic_year_dict: Optional[dict] = None,
        web_metadata_map: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> dict:
        ay_dict = academic_year_dict or {
            "start_year": 2025,
            "end_year": 2026,
            "semester": 1,
        }
        ay_obj = AcademicYear(
            start_year=ay_dict.get("start_year", 2025),
            end_year=ay_dict.get("end_year", 2026),
        )
        sec_sem = ay_dict.get("semester", 1)

        extractor = PDFExtractor(pdf_bytes)
        first_page_text = extractor.extract_first_page() or ""
        full_text = self._get_full_or_last_page_text(extractor, first_page_text)

        if not first_page_text.strip() and not full_text.strip():
            return self._build_empty_response(file_url, course_code, sec_sem, ay_obj)

        lines = [
            line.strip()
            for line in first_page_text.splitlines()
            if line.strip() and not line.strip().isdigit()
        ]

        nim = self._extract_nim(first_page_text, file_url)
        if not nim:
            nim = self._extract_nim(full_text, file_url)

        emails = self._extract_emails(full_text, nim)

        title, author = self._extract_title_and_author(lines, nim)

        if web_metadata_map:
            normalized_pdf_title = self._normalize_string(title)
            matched_data = self._match_web_metadata(
                normalized_pdf_title, author, web_metadata_map
            )
            if matched_data:
                if matched_data.get("name"):
                    author = matched_data["name"]
                if matched_data.get("number"):
                    nim = matched_data["number"]

        if author == "Penulis Tidak Terdeteksi" and emails:
            author_from_email = self._extract_author_from_email_fallback(emails)
            if author_from_email:
                author = author_from_email

        abstract = self._extract_abstract(first_page_text, emails)

        student_obj = Student(
            name=author if author != "Penulis Tidak Terdeteksi" else None,
            student_number=str(nim) if nim else None,
            emails=emails,
        )

        paper = Paper(
            title=title,
            abstract=abstract if abstract else None,
            student=student_obj,
            url=file_url,
            language=self._detect_language(abstract if abstract else title),
            course_code=course_code,
            section_semester=sec_sem,
            academic_year=ay_obj,
        )
        return paper.model_dump()
    
    def _extract_nim(self, text: str, file_url: str = "") -> Optional[str]:
        nim_match = re.search(r"\b(" + self.ITB_PRODI_PREFIX + r"[0-9]{5})\b", text)
        if nim_match:
            return nim_match.group(1)

        bracket_match = re.search(
            r"[\(\[]\s*(" + self.ITB_PRODI_PREFIX + r"[0-9]{5})\s*[\)\]]", text
        )
        if bracket_match:
            return bracket_match.group(1)

        split_match = re.search(
            r"[\,\-–—]\s*(" + self.ITB_PRODI_PREFIX + r"[0-9]{5})", text
        )
        if split_match:
            return split_match.group(1)

        attached_match = re.search(r"(" + self.ITB_PRODI_PREFIX + r"[0-9]{5})", text)
        if attached_match:
            return attached_match.group(1)

        if file_url:
            match_url = re.search(
                r"\b(" + self.ITB_PRODI_PREFIX + r"[0-9]{5})\b", file_url
            )
            if match_url:
                return match_url.group(1)

        return None

    def _extract_title_and_author(
        self, lines: List[str], found_nim: Optional[str]
    ) -> Tuple[str, str]:
        if not lines:
            return "Judul Tidak Terdeteksi", "Penulis Tidak Terdeteksi"

        author_name = "Penulis Tidak Terdeteksi"
        author_line_idx = -1

        for idx, line in enumerate(lines[:12]):
            if found_nim and found_nim in line:
                author_line_idx = idx
                author_name = self._clean_author_name(
                    line.split(found_nim)[0], found_nim
                )
                break

            nim_match = re.search(
                r"^(.*?)(?:\s*[\,\-–—]\s*|\s+(?:and|&)\s+|\s+)("
                + self.ITB_PRODI_PREFIX
                + r"[0-9]{5})",
                line,
                re.IGNORECASE,
            )
            if nim_match:
                author_line_idx = idx
                author_name = self._clean_author_name(nim_match.group(1), found_nim)
                break

            if idx + 1 < len(lines):
                next_line = lines[idx + 1].lower()
                if any(
                    kw in next_line
                    for kw in ["program studi", "sekolah teknik", "institut teknologi"]
                ):
                    if not line.lower().startswith(
                        ("dengan", "pada", "untuk", "menggunakan", "berbasis")
                    ):
                        author_line_idx = idx
                        author_name = self._clean_author_name(line, found_nim)
                        break

        title_lines = []
        limit_idx = author_line_idx if author_line_idx != -1 else min(len(lines), 4)

        for i in range(limit_idx):
            line = lines[i]
            if re.search(
                r"^(makalah|tugas|materi|slide|katalog)\b", line, re.IGNORECASE
            ):
                continue
            title_lines.append(line)

        raw_title = " ".join(title_lines).strip() if title_lines else lines[0]
        cleaned_title = self._clean_title_string(raw_title)

        return (
            cleaned_title if cleaned_title else "Judul Tidak Terdeteksi",
            author_name,
        )

    def _clean_author_name(
        self, raw_author: str, found_nim: Optional[str] = None
    ) -> str:
        if not raw_author:
            return "Penulis Tidak Terdeteksi"

        clean_author = raw_author

        if found_nim:
            clean_author = clean_author.replace(found_nim, "")

        clean_author = re.sub(
            r"\b(1st|2nd|3rd|4th|authors?|oleh|by|disusun|nama)\b",
            "",
            clean_author,
            flags=re.IGNORECASE,
        )
        clean_author = re.sub(r"[\(\[\{].*?[\)\]\}]", "", clean_author)
        clean_author = re.sub(r"[\d,\.\s]+$", "", clean_author)
        clean_author = re.sub(r"[\s,\-–—&]+$", "", clean_author)
        clean_author = re.sub(r"[0-9,\.\{\}\[\]\(\)\-–—_*+=/\\:;]+", " ", clean_author)
        clean_author = re.sub(
            r"\b(nim|program|studi|teknik|informatika|institut|teknologi|sekolah|bandung|email|laboratorium|engineer|dr|prof|m\.t|s\.t|m\.eng|m\.sc|ir|eng)\b",
            "",
            clean_author,
            flags=re.IGNORECASE,
        )

        clean_author = " ".join(clean_author.split()).strip()

        if len(clean_author) >= 3 and not clean_author.isdigit():
            return clean_author.title()

        return "Penulis Tidak Terdeteksi"

    def _extract_emails(self, text: str, nim: Optional[str] = None) -> List[str]:
        raw_emails = self.ALL_EMAILS_PATTERN.findall(text)
        seen = set()
        unique_emails = []

        for email in raw_emails:
            cleaned_email = email.lower().strip()

            if "gmail.com" in cleaned_email:
                cleaned_email = re.sub(r"^\d+", "", cleaned_email)

            if "itb.ac.id" in cleaned_email:
                cleaned_email = re.sub(
                    r"^\d(?=" + self.ITB_PRODI_PREFIX + r"[0-9]{5})", "", cleaned_email
                )

            if cleaned_email and cleaned_email not in seen:
                seen.add(cleaned_email)
                unique_emails.append(cleaned_email)

        return unique_emails

    def _extract_author_from_email_fallback(self, emails: List[str]) -> Optional[str]:
        for email in emails:
            if "gmail.com" in email:
                local_part = email.split("@")[0]
                clean_name = re.sub(r"\d+", "", local_part)
                clean_name = re.sub(r"[._\-]", " ", clean_name).strip()
                if len(clean_name) > 2:
                    return clean_name.title()
        return None

    def _clean_title_string(self, title: str) -> str:
        title = re.sub(
            r"^(makalah|tugas|materi|slide)?\s*(if\d{4})?[^,]*?tahun\s+\d{4}(/\d{4})?[\s,:-]*",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip()
        title = re.sub(r"\s+", " ", title).strip()

        if len(title) > 300:
            title = title[:300] + "..."

        return title

    def _get_full_or_last_page_text(
        self, extractor: PDFExtractor, first_page: str
    ) -> str:
        try:
            if hasattr(extractor, "extract_all_pages"):
                pages = extractor.extract_all_pages()
                if isinstance(pages, list):
                    return "\n".join(pages)
            elif hasattr(extractor, "text"):
                return extractor.text
        except Exception:
            pass
        return first_page

    def _extract_abstract(self, text: str, emails: List[str]) -> str:
        start_pos = self._calculate_abstract_start_offset(text, emails)
        matches = self._find_abstract_start_match(text, start_pos)
        if not matches:
            return ""

        abstract_start = matches[0].end()
        abstract_end = self._find_abstract_end_position(text, abstract_start)

        raw_abstract = text[abstract_start:abstract_end].strip()
        return self._clean_abstract_text(raw_abstract)

    def _calculate_abstract_start_offset(self, text: str, emails: List[str]) -> int:
        start_pos = 0
        if emails:
            for email in emails:
                email_pos = text.lower().find(email.lower())
                if email_pos != -1:
                    start_pos = max(start_pos, email_pos + len(email))
        return start_pos

    def _find_abstract_start_match(self, text: str, start_pos: int) -> List:
        pattern = re.compile(
            r"\b(abstrak|abstract|abstracts|abstrakts)\b\s*(?:—|–|‒|―|-|:|▪|■|\.|\s)",
            re.IGNORECASE,
        )
        matches = list(pattern.finditer(text, pos=start_pos))
        return matches if matches else list(pattern.finditer(text))

    def _find_abstract_end_position(self, text: str, abstract_start: int) -> int:
        end_pattern = re.compile(
            r"\b(?:keywords|kata\s+kunci|index\s+terms|key\s+words|pendahuluan|introduction|i\.\s+introduction|i\.\s+pendahuluan|1\.\s+pendahuluan|1\.\s+introduction)\b",
            re.IGNORECASE,
        )
        end_matches = list(end_pattern.finditer(text, pos=abstract_start))
        return end_matches[0].start() if end_matches else len(text)

    def _clean_abstract_text(self, abstract_text: str) -> str:
        abstract_text = re.sub(r"^(?:—|–|‒|―|-|:|▪|■|\.)\s*", "", abstract_text)
        abstract_text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", abstract_text)
        abstract_text = re.sub(r"\s+", " ", abstract_text)
        return abstract_text.strip()

    def _detect_language(self, abstract: str) -> str:
        try:
            return detect(abstract)
        except Exception:
            return "id"

    def _match_web_metadata(self, norm_title: str, author_name: str, web_map: Dict[str, Dict[str, str]]) -> Optional[Dict[str, str]]:
        if norm_title in web_map:
            return web_map[norm_title]

        for web_title, data in web_map.items():
            if len(norm_title) > 15 and (
                norm_title in web_title or web_title in norm_title
            ):
                return data

        if author_name and author_name != "Penulis Tidak Terdeteksi":
            norm_author = self._normalize_string(author_name)
            for _, data in web_map.items():
                web_author = self._normalize_string(data.get("name", ""))
                if norm_author in web_author or web_author in norm_author:
                    return data
        return None

    def _build_empty_response(
        self, file_url: str, course_code: str, sec_sem: int, ay_obj: AcademicYear
    ) -> dict:
        filename = file_url.split("/")[-1].replace(".pdf", "")
        paper = Paper(
            title=filename,
            abstract=filename,
            student=Student(name=None, student_number=None, emails=[]),
            url=file_url,
            language="id",
            course_code=course_code,
            section_semester=sec_sem,
            academic_year=ay_obj,
        )
        return paper.model_dump()

    @staticmethod
    def _normalize_string(text: str) -> str:
        return re.sub(r"\s+", " ", text).lower().strip()
