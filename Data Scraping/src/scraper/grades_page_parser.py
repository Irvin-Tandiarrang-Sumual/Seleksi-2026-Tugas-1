import re
from typing import List, Optional, Union

from bs4 import BeautifulSoup, Tag

from models.academic_year import AcademicYear
from models.grade_page_result import GradePageResult
from models.student_grade import StudentGrade


class GradePageParser:
    NIM_PATTERN_ITB = re.compile(r"\b(135\d{5})\b")
    NIM_PATTERN_GENERAL = re.compile(r"\b([1-9]\d{7})\b")
    GRADE_INDEXES = {"A", "AB", "B", "BC", "C", "D", "E"}
    INVALID_ASSISTANT_KEYWORDS = [
        "belum",
        "tidak",
        "none",
        "tbd",
        "ditentukan",
        "tentukan",
    ]

    def __init__(self, html_bytes_or_str: Union[bytes, str]):
        if isinstance(html_bytes_or_str, bytes):
            try:
                text = html_bytes_or_str.decode("utf-8")
            except UnicodeDecodeError:
                text = html_bytes_or_str.decode("latin-1", errors="ignore")
        else:
            text = html_bytes_or_str

        self.soup = BeautifulSoup(text, "html.parser")

    @staticmethod
    def _clean_cell(cell_text: str) -> str:
        cleaned = re.sub(r"<[^>]+>", "", cell_text)
        cleaned = cleaned.replace("\xa0", " ").strip()
        return re.sub(r"\s+", " ", cleaned)

    @staticmethod
    def _parse_value(val_str: str) -> Union[int, float, str]:
        val_clean = val_str.replace(",", ".").strip()
        try:
            val_float = float(val_clean)
            return int(val_float) if val_float.is_integer() else val_float
        except ValueError:
            return val_str

    def _clean_assistant_name(self, raw_name: str) -> Optional[str]:
        cleaned = re.sub(r"\b\d{1,2}\)\s*", " ", raw_name)
        cleaned = re.sub(r"[A-Za-z0-9]+(?:\d{5,}\)?)", "", cleaned)
        cleaned = re.sub(r"\b135\d{5}\b", " ", cleaned)
        cleaned = re.sub(r"\b\d{8,}\b", " ", cleaned)
        cleaned = re.sub(r"[()\[\]:]", "", cleaned)
        cleaned = re.sub(r"[^a-zA-Z\s]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        if (
            not cleaned
            or len(cleaned) < 2
            or any(kw in cleaned.lower() for kw in self.INVALID_ASSISTANT_KEYWORDS)
        ):
            return None

        return cleaned.title()

    def _expand_row_cells(self, row: Tag) -> List[str]:
        expanded = []
        for td in row.find_all(["td", "th"]):
            text = self._clean_cell(td.get_text())
            colspan = int(td.get("colspan", 1))
            expanded.extend([text] * colspan)
        return expanded

    def _extract_metadata(self, source_url: str = "") -> tuple[str, str, int, AcademicYear, Optional[List[str]]]:
        page_text = self.soup.get_text()

        course_code, course_title = self._extract_course_info(page_text, source_url)
        section_semester = self._extract_semester(page_text)
        academic_year = self._extract_academic_year(page_text)
        assistant = self._extract_assistants(page_text)

        return course_code, course_title, section_semester, academic_year, assistant

    def _extract_course_info(self, page_text: str, source_url: str) -> tuple[str, str]:
        course_code = "IF0000"
        course_title = "Mata Kuliah Tidak Terdeteksi"
        code_match = re.search(r"\b(IF\d{4})\b\s*[-–:]?\s*(.*)", page_text)

        if code_match:
            course_code = code_match.group(1).upper()
            raw_title = code_match.group(2).split("\n")[0].strip()
            if raw_title:
                course_title = raw_title
        elif source_url:
            code_match_url = re.search(r"\b(IF\d{4})\b", source_url, re.IGNORECASE)
            if code_match_url:
                course_code = code_match_url.group(1).upper()

        return course_code, course_title

    def _extract_semester(self, page_text: str) -> int:
        sem_match = re.search(r"Semester\s*([I|1|2]+)", page_text, re.IGNORECASE)
        if sem_match and sem_match.group(1).upper() in ["2", "II"]:
            return 2
        return 1

    def _extract_academic_year(self, page_text: str) -> AcademicYear:
        year_match = re.search(r"(20\d{2})\s*[/–-]\s*(20\d{2})", page_text)
        if year_match:
            return AcademicYear(
                start_year=int(year_match.group(1)), end_year=int(year_match.group(2))
            )
        return AcademicYear(start_year=2024, end_year=2025)

    def _extract_assistants(self, page_text: str) -> Optional[List[str]]:
        ast_pattern = re.compile(
            r"(?:Tim\s+)?Asisten(?:\s*\([^)]+\))?\s*[:\-–]\s*(.*?)(?=\n\s*\n|\bJadwal\b|\bDosen\b|\bPeserta\b|\bNIM\b|\bMata\s+Kuliah\b|\bSemester\b|$)",
            re.IGNORECASE | re.DOTALL,
        )
        ast_match = ast_pattern.search(page_text)
        if not ast_match:
            return None

        raw_ast_text = re.sub(r"\s+", " ", ast_match.group(1)).strip()
        raw_tokens = re.split(r"[,;]|\bdan\b|\b\d{1,2}\)", raw_ast_text)

        clean_assistants = [
            name for token in raw_tokens if (name := self._clean_assistant_name(token))
        ]
        return clean_assistants if clean_assistants else None

    def _find_header_and_data_indices(self, rows: List[Tag]) -> tuple[int, int]:
        header_start_idx = -1
        for idx, row in enumerate(rows[:40]):
            cleaned_cells = [
                self._clean_cell(td.get_text()).upper()
                for td in row.find_all(["td", "th"])
            ]
            if "NIM" in cleaned_cells and any(
                name in cleaned_cells for name in ["NAMA", "NAME"]
            ):
                header_start_idx = idx
                break

        if header_start_idx == -1:
            return -1, -1

        data_start_idx = -1
        for idx in range(header_start_idx + 1, len(rows)):
            col_texts = self._expand_row_cells(rows[idx])
            if any(self.NIM_PATTERN_GENERAL.search(cell) for cell in col_texts):
                data_start_idx = idx
                break

        return header_start_idx, data_start_idx

    def _resolve_headers(self, header_rows: List[Tag]) -> List[str]:
        max_cols = max(
            sum(int(td.get("colspan", 1)) for td in r.find_all(["td", "th"]))
            for r in header_rows
        )

        grid = [[None for _ in range(max_cols)] for _ in range(len(header_rows))]
        for r_idx, row in enumerate(header_rows):
            c_idx = 0
            for td in row.find_all(["td", "th"]):
                while c_idx < max_cols and grid[r_idx][c_idx] is not None:
                    c_idx += 1
                if c_idx >= max_cols:
                    break

                text = self._clean_cell(td.get_text())
                colspan = int(td.get("colspan", 1))
                rowspan = int(td.get("rowspan", 1))

                for dr in range(rowspan):
                    for dc in range(colspan):
                        if r_idx + dr < len(header_rows) and c_idx + dc < max_cols:
                            grid[r_idx + dr][c_idx + dc] = text
                c_idx += colspan

        resolved_headers = []
        for col in range(max_cols):
            col_texts = []
            for row in range(len(header_rows)):
                cell_text = grid[row][col]
                if cell_text and (
                    not col_texts or cell_text.upper() != col_texts[-1].upper()
                ):
                    col_texts.append(cell_text)

            combined = " ".join(col_texts).strip()

            words = combined.split()
            if len(words) > 1 and len(set(w.upper() for w in words)) == 1:
                combined = words[0]

            resolved_headers.append(combined)

        seen_headers = {}
        final_headers = []
        for h in resolved_headers:
            if h in seen_headers:
                seen_headers[h] += 1
                final_headers.append(f"{h}_{seen_headers[h]}")
            else:
                seen_headers[h] = 1
                final_headers.append(h)

        return final_headers

    def _parse_student_row(
        self, row_cells: List[str], headers: List[str]
    ) -> Optional[StudentGrade]:
        nim_col_idx = -1
        nim_val = ""
        for idx, text in enumerate(row_cells):
            match = self.NIM_PATTERN_GENERAL.search(text)
            if match:
                nim_col_idx = idx
                nim_val = match.group(1)
                break

        if nim_col_idx == -1:
            return None

        name_val = "Tanpa Nama"
        if nim_col_idx + 1 < len(row_cells):
            candidate = row_cells[nim_col_idx + 1]
            if candidate and not candidate.isdigit():
                name_val = candidate

        section_code = "K1"
        for idx, h_name in enumerate(headers):
            if "KELAS" in h_name.upper() or "CLASS" in h_name.upper():
                if idx < len(row_cells) and row_cells[idx]:
                    section_code = row_cells[idx]
                    break

        final_grade = None
        components = {}

        if len(headers) == len(row_cells):
            for h_idx, h_name in enumerate(headers):
                h_upper = h_name.strip().upper()
                if "KENYATAAN" in h_upper:
                    val = row_cells[h_idx].strip().upper()
                    if val in self.GRADE_INDEXES:
                        final_grade = val
                        break

            ignore_keywords = {"NO", "NIM", "NAMA", "NAME", "KELAS", "CLASS", "SECTION"}

            for h_idx, h_name in enumerate(headers):
                h_clean = h_name.strip()
                if not h_clean:
                    continue

                base_h = re.sub(r"_\d+$", "", h_clean).strip().upper()

                words = base_h.split()
                if len(words) > 1 and len(set(words)) == 1:
                    base_h = words[0]

                if base_h in ignore_keywords:
                    continue

                val = row_cells[h_idx].strip()
                if not val:
                    continue

                if "KENYATAAN" in base_h:
                    continue

                if not final_grade and any(
                    k in base_h for k in ["INDEKS", "NILAI AKHIR", "GRADE"]
                ):
                    if val.upper() in self.GRADE_INDEXES:
                        final_grade = val.upper()
                        continue

                if h_clean not in components:
                    components[h_clean] = self._parse_value(val)

        else:
            for text in reversed(row_cells):
                text_upper = text.upper().strip()
                if text_upper in self.GRADE_INDEXES:
                    final_grade = text_upper
                    break

        cleaned_student_name = re.sub(r"[^a-zA-Z\s]", " ", name_val)
        cleaned_student_name = re.sub(r"\s+", " ", cleaned_student_name).strip().title()
        if not cleaned_student_name:
            cleaned_student_name = "Tanpa Nama"

        return StudentGrade(
            student_number=nim_val,
            name=cleaned_student_name,
            section_code=section_code,
            final_grade=final_grade,
            components=components,
        )

    def parse(self, source_url: str = "") -> Optional[GradePageResult]:
        tables = self.soup.find_all("table")
        if not tables:
            return None

        course_code, course_title, section_semester, academic_year, assistant = (
            self._extract_metadata(source_url)
        )
        students: List[StudentGrade] = []

        for table in tables:
            rows = table.find_all("tr")
            if not rows:
                continue

            header_start_idx, data_start_idx = self._find_header_and_data_indices(rows)
            if header_start_idx == -1 or data_start_idx == -1:
                continue

            headers = self._resolve_headers(rows[header_start_idx:data_start_idx])

            for row in rows[data_start_idx:]:
                row_cells = self._expand_row_cells(row)
                student = self._parse_student_row(row_cells, headers)
                if student:
                    students.append(student)

        if not students:
            return None

        return GradePageResult(
            course_code=course_code,
            course_title=course_title,
            section_semester=section_semester,
            academic_year=academic_year,
            assistant=assistant,
            students=students,
        )
