import re
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup

from models.academic_year import AcademicYear
from models.course import Course
from models.instructor import Instructor
from utils.pdf_extractor import PDFExtractor


class CourseInformationParser:
    PATTERNS = {
        "course_code": re.compile(r"\b([A-Z]{1,2}\d{4})\b", re.IGNORECASE),
        "semester": re.compile(r"Semester\s+([IVXLCDM\d]+)", re.IGNORECASE),
        "academic_year": re.compile(r"\b(20\d{2})[-/](20\d{2})\b"),
        "credits": re.compile(r"(?:Bobot\s+)?SKS\s*[:\-–]?\s*(\d+)", re.IGNORECASE),
        "section": re.compile(r"\b(K\d{1,2})\b", re.IGNORECASE),
    }

    PATTERN_SECTION_GROUP = re.compile(
        r"\b(?:K\d{1,2}\s*(?:[\&,\-–/]\s*K?\d{1,2})+|K\d{1,2})\b", re.IGNORECASE
    )

    PATTERN_LEFT_SECTION = re.compile(
        r"^\s*([Kk]\d{1,2}(?:\s*[\&,\-–/]\s*[Kk]?\d{1,2})*)\s*[\:\-\–\.]?\s+(.+)",
        re.IGNORECASE,
    )

    PATTERN_RIGHT_SECTION = re.compile(
        r"(.+?)\s*[\(\[]?\s*([Kk]\d{1,2}(?:\s*[\&,\-–/]\s*[Kk]?\d{1,2})*)\s*[\)\]]?",
        re.IGNORECASE,
    )

    INVALID_KEYWORDS = [
        "e-mail",
        "email",
        "web",
        "url",
        "http",
        "https",
        "edunex",
        "asisten",
        "jadwal",
        "bobot",
        "staff.stei",
        "informatika.org",
        ".ac.id",
        "~",
    ]

    def __init__(self, content: bytes | str, is_pdf: bool = False):
        self.raw_text = self._extract_raw_text(content, is_pdf)

    def _extract_raw_text(self, content: bytes | str, is_pdf: bool) -> str:
        if is_pdf:
            if isinstance(content, str):
                content = content.encode("utf-8")
            return PDFExtractor(content).extract_text()

        if isinstance(content, bytes):
            try:
                decoded_text = content.decode("utf-8")
            except UnicodeDecodeError:
                decoded_text = content.decode("latin-1", errors="ignore")
            return BeautifulSoup(decoded_text, "html.parser").get_text(separator="\n")

        return BeautifulSoup(content, "html.parser").get_text(separator="\n")

    @staticmethod
    def unwrap_office_url(url: str) -> str:
        if not url:
            return ""
        if "officeapps.live.com" in url or "view.officeapps.live.com" in url:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            if "src" in query:
                return unquote(query["src"][0])
        return url

    def extract_data(
        self,
        default_title: str = "Matematika Diskrit",
        source_url: str = "",
        fallback_code: str = "IF1220",
    ) -> dict:
        real_url = self.unwrap_office_url(source_url)
        code = self._extract_course_code(real_url, fallback_code)
        course_name = self._extract_course_name(default_title)
        ay_dict = self._extract_academic_year(real_url)

        course_info = Course(
            course_code=code,
            course_name=course_name,
            course_credits=self._extract_credits(),
            semester=self._extract_semester(),
            academic_year=AcademicYear(
                start_year=ay_dict["start_year"],
                end_year=ay_dict["end_year"],
            ),
            instructors=self._extract_instructors(),
        )
        return course_info.model_dump()

    def _extract_course_code(self, source_url: str, fallback_code: str) -> str:
        match_text = self.PATTERNS["course_code"].search(self.raw_text)
        if match_text:
            return match_text.group(1).upper()

        match_url = self.PATTERNS["course_code"].search(source_url)
        if match_url:
            return match_url.group(1).upper()

        return fallback_code

    def _extract_course_name(self, default_title: str) -> str:
        lines = [line.strip() for line in self.raw_text.splitlines() if line.strip()]
        for line in lines[:10]:
            if re.match(r"^[\-=_\s]{3,}$", line):
                continue

            clean_line = self.PATTERNS["course_code"].sub("", line).strip()
            if self._is_valid_course_name_line(clean_line):
                return clean_line

        return default_title

    def _is_valid_course_name_line(self, line: str) -> bool:
        if not line or len(line) <= 3 or re.match(r"^[\-=_\s]{3,}$", line):
            return False

        stopwords = [
            "semester",
            "sks",
            "dosen",
            "jadwal",
            "http",
            "informasi",
            "program studi",
            "institut",
            "sekolah",
            "asisten",
            "bobot",
        ]

        line_lower = line.lower()
        for word in stopwords:
            if word in line_lower:
                return False

        return True

    def _extract_semester(self) -> int:
        match = self.PATTERNS["semester"].search(self.raw_text)
        if match:
            val = match.group(1).strip().upper()
            if val in ["II", "2"]:
                return 2
            if val in ["I", "1"]:
                return 1
        return 2

    def _extract_credits(self) -> int:
        match = self.PATTERNS["credits"].search(self.raw_text)
        if match:
            return int(match.group(1))
        return 3

    def _extract_academic_year(self, source_url: str = "") -> dict:
        match_text = self.PATTERNS["academic_year"].search(self.raw_text)
        if match_text:
            return {
                "start_year": int(match_text.group(1)),
                "end_year": int(match_text.group(2)),
            }

        match_url = self.PATTERNS["academic_year"].search(source_url)
        if match_url:
            return {
                "start_year": int(match_url.group(1)),
                "end_year": int(match_url.group(2)),
            }

        match_single = re.search(r"20(\d{2})", source_url)
        if match_single:
            start_year = int("20" + match_single.group(1))
            return {"start_year": start_year, "end_year": start_year + 1}

        return {"start_year": 2025, "end_year": 2026}

    def _extract_instructors(self) -> list[Instructor]:
        dosen_lines = self._collect_dosen_block_lines()
        filtered_lines = self._filter_invalid_dosen_lines(dosen_lines)
        instructors_map = self._parse_dosen_lines(filtered_lines)

        if not instructors_map:
            instructors_map = self._apply_fallback_instructors()

        def _strip_title(n: str) -> str:
            parts = n.split(",")
            base = parts[0]
            base = re.sub(
                r'\b(prof|dr|eng|ir|dr-ing|st|mt|m\.t|s\.t|dr\.?|ir\.?|prof\.?|drs\.?|dra\.?|ph\.?d\.?)\b',
                ' ',
                base,
                flags=re.IGNORECASE
            )
            base = re.sub(r'[^a-zA-Z\s]', ' ', base)
            base = re.sub(r'\s+', ' ', base)
            return base.strip().title()

        raw_names = list(instructors_map.keys())
        cleaned_to_raws = {}
        for r_name in raw_names:
            cleaned = _strip_title(r_name)
            if cleaned:
                cleaned_to_raws.setdefault(cleaned, []).append(r_name)

        sorted_cleaned = sorted(cleaned_to_raws.keys(), key=len, reverse=True)
        cleaned_to_normalized = {}
        for name in sorted_cleaned:
            matched_longer = None
            for longer_name in cleaned_to_normalized.values():
                words = name.lower().split()
                pattern = r'\b' + r'\b.*\b'.join(map(re.escape, words)) + r'\b'
                if re.search(pattern, longer_name.lower()):
                    matched_longer = longer_name
                    break
            if matched_longer:
                cleaned_to_normalized[name] = matched_longer
            else:
                cleaned_to_normalized[name] = name

        raw_to_normalized = {}
        for cleaned, raws in cleaned_to_raws.items():
            normalized = cleaned_to_normalized[cleaned]
            for r in raws:
                raw_to_normalized[r] = normalized

        normalized_instructors_map = {}
        for raw_name, secs in instructors_map.items():
            norm_name = raw_to_normalized.get(raw_name, _strip_title(raw_name))
            if norm_name not in normalized_instructors_map:
                normalized_instructors_map[norm_name] = set()
            normalized_instructors_map[norm_name].update(secs)

        instructors_list = []
        for name, secs in normalized_instructors_map.items():
            instructors_list.append(Instructor(name=name, sections=sorted(list(secs))))

        return instructors_list

    def _collect_dosen_block_lines(self) -> list[str]:
        lines = self.raw_text.splitlines()
        in_dosen_block = False
        dosen_lines = []

        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue

            if re.search(
                r"(?:Tim\s+)?(?:Dosen|Pengajar)\s*[:\-–]?", line_clean, re.IGNORECASE
            ):
                in_dosen_block = True
                cleaned = re.sub(
                    r"^(?:Tim\s+)?(?:Dosen|Pengajar)\s*[:\-–]?\s*",
                    "",
                    line_clean,
                    flags=re.IGNORECASE,
                ).strip()
                if cleaned and not self._contains_invalid_keyword(cleaned):
                    dosen_lines.append(cleaned)
                continue

            if in_dosen_block:
                if self._contains_invalid_keyword(line_clean):
                    in_dosen_block = False
                    continue
                dosen_lines.append(line_clean)

        return dosen_lines

    def _contains_invalid_keyword(self, text: str) -> bool:
        text_lower = text.lower()
        for kw in self.INVALID_KEYWORDS:
            if kw in text_lower:
                return True
        return False

    def _filter_invalid_dosen_lines(self, lines: list[str]) -> list[str]:
        filtered = []
        for line in lines:
            if "@" in line or "http" in line or ".ac.id" in line or "~" in line:
                continue
            filtered.append(line)
        return filtered

    def _extract_section_codes(self, raw_section_str: str) -> set[str]:
        sections = set()

        range_match = re.search(
            r"K?0*(\d+)\s*[\-–]\s*K?0*(\d+)", raw_section_str, re.IGNORECASE
        )
        if range_match:
            start_num = int(range_match.group(1))
            end_num = int(range_match.group(2))
            return {f"K{i}" for i in range(start_num, end_num + 1)}

        matches = re.findall(r"K?0*(\d+)", raw_section_str, re.IGNORECASE)
        for m in matches:
            sections.add(f"K{int(m)}")

        return sections

    def _parse_dosen_lines(self, lines: list[str]) -> dict[str, set[str]]:
        instructors_map: dict[str, set[str]] = {}
        current_sections: set[str] = set()
        has_any_section_label = False

        for line in lines:
            line_clean = line.strip()
            if not line_clean or len(line_clean) < 2:
                continue

            parts = re.split(r"/|;|\bdan\b", line_clean)
            for part in parts:
                part_clean = part.strip()
                if not part_clean:
                    continue

                found_sections = set()
                raw_name = part_clean

                match_left = self.PATTERN_LEFT_SECTION.match(part_clean)
                if match_left:
                    found_sections = self._extract_section_codes(match_left.group(1))
                    raw_name = match_left.group(2)

                else:
                    match_right = self.PATTERN_RIGHT_SECTION.match(part_clean)
                    if match_right and self.PATTERN_SECTION_GROUP.search(
                        match_right.group(2)
                    ):
                        found_sections = self._extract_section_codes(
                            match_right.group(2)
                        )
                        raw_name = match_right.group(1)

                if found_sections:
                    current_sections = found_sections
                    has_any_section_label = True

                clean_name = self._clean_instructor_name(raw_name)
                if self._is_valid_instructor_name(clean_name):
                    sections_to_assign = (
                        current_sections if current_sections else {"K1"}
                    )

                    if clean_name not in instructors_map:
                        instructors_map[clean_name] = set()
                    instructors_map[clean_name].update(sections_to_assign)


        if not has_any_section_label and instructors_map:
            new_map = {}
            for idx, (name, _) in enumerate(instructors_map.items()):
                new_map[name] = {f"K{idx + 1}"}
            return new_map

        return instructors_map

    def _clean_instructor_name(self, name: str) -> str:
        name = self.PATTERN_SECTION_GROUP.sub("", name)

        name = re.sub(
            r"\b(Koordinator\s+kuliah|Koordinator|Ketua|Tim\s+Dosen|Kuliah|Kelas|Jatinangor|setengah)\b",
            "",
            name,
            flags=re.IGNORECASE,
        )

        name = re.sub(r"^[–\-—:\,\.\/]+|[–\-—:\,\.\/]+$", "", name.strip())
        name = " ".join(name.split()).strip()

        return name

    def _is_valid_instructor_name(self, name: str) -> bool:
        if not name or len(name) <= 2 or name.isdigit():
            return False

        bad_words = [
            "dosen",
            "tim",
            "koordinator",
            "http",
            "edunex",
            "stei",
            "itb",
            "org",
            "sks",
            "semester",
        ]
        name_lower = name.lower()
        for word in bad_words:
            if word in name_lower:
                return False

        return True

    def _apply_fallback_instructors(self) -> dict[str, set[str]]:
        if "rinaldi" in self.raw_text.lower():
            return {"Rinaldi Munir": {"K1"}}
        return {"Dosen Tidak Terdeteksi": {"K1"}}
