import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper.course_data_collector import CourseDataCollector
from scraper.course_information_parser import CourseInformationParser
from scraper.grades_page_parser import GradePageParser
from scraper.html_fetcher import HTMLFetcher
from scraper.paper_parser import PaperParser


class CourseYearCrawler:
    def __init__(
        self,
        course_code: str,
        course_name: str,
        base_url: str,
        academic_year: Dict[str, Any],
        logger: Optional[Any] = None,
    ) -> None:
        self.course_code = course_code
        self.course_name = course_name
        self.base_url = base_url
        self.academic_year = academic_year
        self.logger = logger

        self.fetcher = HTMLFetcher()
        self.paper_parser = PaperParser()
        self.results_lock = threading.Lock()

        self.results: Dict[str, List[Any]] = {
            "courses_info": [],
            "courses_grades": [],
            "course_materials": [],
            "assignments": [],
            "paper_files": [],
        }

    def _log(self, level: str, msg: str) -> None:
        """Log message tanpa emoji."""
        if self.logger:
            getattr(self.logger, level)(msg, self.course_code)
        else:
            prefix = {
                "info": "[INFO] ",
                "success": "[SUCCESS] ",
                "warning": "[WARNING] ",
                "error": "[ERROR] ",
                "skip": "[SKIP] ",
            }.get(level, "")
            print(f"{prefix}[{self.course_code}] {msg}")

    def crawl(self) -> Dict[str, List[Any]]:
        self._log(
            "info",
            f"Crawling {self.course_name} ({self.academic_year['start_year']}/{self.academic_year['end_year']})",
        )

        html_bytes = self.fetcher.fetch(self.base_url)
        if not html_bytes:
            self._log("error", f"Gagal fetch halaman utama: {self.base_url}")
            return self.results

        html_str = self._decode_html(html_bytes)

        self._detect_and_update_course_code(html_str)

        self._collect_and_process_sections(html_str)

        return self.results

    def _decode_html(self, html_bytes: bytes) -> str:
        try:
            return html_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return str(html_bytes)

    def _detect_and_update_course_code(self, html_str: str) -> None:
        soup = BeautifulSoup(html_str, "html.parser")
        code_pattern = re.compile(r"\b([A-Za-z]{2,3}\d{4})\b", re.IGNORECASE)
        found_code: Optional[str] = None

        target_elements = [soup.find("title")] + soup.find_all(["h2", "h1", "h3", "b"])
        for element in target_elements:
            if element:
                match = code_pattern.search(element.get_text())
                if match:
                    found_code = match.group(1).upper()
                    break

        if not found_code:
            match = code_pattern.search(html_str[:2000])
            if match:
                found_code = match.group(1).upper()

        if found_code:
            self._log(
                "info",
                f"Detected dynamic course code: {found_code} (was {self.course_code})",
            )
            self.course_code = found_code

    def _collect_and_process_sections(self, html_str: str) -> None:
        collector = CourseDataCollector(
            self.base_url,
            self.course_code,
            self.course_name,
        )

        collector.collect_info(html_str)
        collector.collect_materials(html_str)
        collector.collect_assignments(html_str)
        collector.collect_papers(html_str)
        collector.collect_grades(html_str)

        if collector.course_info:
            self._process_course_info(collector.course_info)

        self._process_materials(collector.materials)
        self._process_assignments(collector.assignments)
        self._process_papers(collector.papers)

        if collector.grades:
            self._process_grades(collector.grades)

    def _process_course_info(self, info_link: Dict[str, Any]) -> None:
        try:
            pdf_url = info_link["url"]
            self._log("info", f"Downloading silabus PDF: {pdf_url}")

            pdf_bytes = self.fetcher.fetch(pdf_url)
            if not pdf_bytes:
                self._log("warning", f"Gagal download PDF: {pdf_url}")
                return

            parser = CourseInformationParser(pdf_bytes, is_pdf=True)
            data = parser.extract_data(
                default_title=self.course_name,
                source_url=pdf_url,
                fallback_code=self.course_code,
            )

            if data:
                data = self._to_dict(data)
                data["academic_year"] = self.academic_year
                self.results["courses_info"].append(data)
                self._log(
                    "success",
                    f"Parsed course info: {data.get('course_name', 'N/A')}",
                )

        except Exception as e:
            self._log("error", f"Error processing course info: {str(e)}")

    def _process_materials(self, materials: List[Dict[str, Any]]) -> None:
        for material in materials:
            self.results["course_materials"].append(
                {
                    "course_code": self.course_code,
                    "course_name": self.course_name,
                    "title": material["title"],
                    "url": material["url"],
                    "academic_year": self.academic_year,
                }
            )

        if materials:
            self._log("success", f"Found {len(materials)} course materials")

    def _process_assignments(self, assignments: List[Dict[str, Any]]) -> None:
        for assignment in assignments:
            self.results["assignments"].append(
                {
                    "course_code": self.course_code,
                    "course_name": self.course_name,
                    "title": assignment["title"],
                    "url": assignment["url"],
                    "academic_year": self.academic_year,
                }
            )

        if assignments:
            self._log("success", f"Found {len(assignments)} assignments")

    def _process_papers(self, papers_list: List[Dict[str, Any]]) -> None:
        paper_urls: List[str] = []

        for paper in papers_list:
            if paper["type"] == "paper_list":
                urls_from_list = self._fetch_paper_list_urls(paper["url"])
                paper_urls.extend(urls_from_list)
            elif paper["type"] == "paper":
                paper_urls.append(paper["url"])

        if paper_urls:
            self._log(
                "info",
                f"Processing {len(paper_urls)} papers with 5 workers",
            )
            self._download_papers_parallel(paper_urls)

        if self.results["paper_files"]:
            self._log(
                "success",
                f"Found {len(self.results['paper_files'])} papers",
            )

    def _fetch_paper_list_urls(self, list_url: str) -> List[str]:
        paper_urls: List[str] = []
        try:
            self._log("info", f"Fetching paper list: {list_url}")
            html_bytes = self.fetcher.fetch(list_url)
            if not html_bytes:
                return paper_urls

            html_str = self._decode_html(html_bytes)

            if html_str.startswith("%PDF") or len(html_str) < 50:
                self._log("warning", f"Skipped non-HTML content: {list_url}")
                return paper_urls

            soup = BeautifulSoup(html_str, "html.parser")
            for link in soup.find_all("a", href=True):
                href = link["href"].replace("\\", "/")
                if href.endswith(".pdf"):
                    full_url = urljoin(list_url, href)
                    paper_urls.append(full_url)

            self._log("info", f"Found {len(paper_urls)} PDFs in paper list")

        except Exception as e:
            self._log("warning", f"Error fetching paper list: {str(e)}")

        return paper_urls

    def _download_papers_parallel(
        self, paper_urls: List[str], max_workers: int = 5
    ) -> None:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._download_and_parse_paper, url): url
                for url in paper_urls
            }

            completed = 0
            for future in as_completed(futures):
                completed += 1
                try:
                    future.result()
                except Exception as e:
                    self._log("warning", f"Paper processing error: {str(e)}")

                if completed % 10 == 0:
                    self._log(
                        "info",
                        f"Progress: {completed}/{len(paper_urls)} papers processed",
                    )

    def _download_and_parse_paper(self, paper_url: str) -> None:
        try:
            fetch_res = self.fetcher.fetch(paper_url, return_final_url=True)
            if not fetch_res:
                self._log("warning", f"Gagal download paper: {paper_url}")
                return

            pdf_bytes, final_url = fetch_res

            paper_data = self.paper_parser.parse(
                pdf_bytes=pdf_bytes,
                file_url=final_url,
                course_code=self.course_code,
                academic_year_dict=self.academic_year,
            )

            if paper_data:
                paper_dict = self._to_dict(paper_data)
                paper_dict["course_name"] = self.course_name

                with self.results_lock:
                    self.results["paper_files"].append(paper_dict)

        except Exception as e:
            self._log("warning", f"Error parsing paper: {str(e)}")

    def _process_grades(self, grades_list: List[Dict[str, Any]]) -> None:
        for grades_link in grades_list:
            try:
                grades_url = grades_link["url"]
                self._log("info", f"Fetching grades page: {grades_url}")

                html_bytes = self.fetcher.fetch(grades_url)
                if not html_bytes:
                    self._log("warning", f"Gagal fetch grades page: {grades_url}")
                    continue

                html_bytes = self._resolve_excel_frame_html(html_bytes, grades_url)

                parser = GradePageParser(html_bytes)
                raw_grades_data = parser.parse(grades_url)

                if raw_grades_data:
                    grades_data = self._to_dict(raw_grades_data)
                    grades_data["academic_year"] = self.academic_year
                    self.results["courses_grades"].append(grades_data)

                    self._log(
                        "success",
                        f"Parsed {len(grades_data.get('students', []))} student grades",
                    )

            except Exception as e:
                self._log("error", f"Error processing grades: {str(e)}")

    def _resolve_excel_frame_html(self, html_bytes: bytes, grades_url: str) -> bytes:
        html_str = self._decode_html(html_bytes)
        soup = BeautifulSoup(html_str, "html.parser")

        frame = soup.find(["frame", "iframe"], src=True)
        if not frame:
            link = soup.find("link", id="shLink", href=True)
            if link:
                sub_url = urljoin(grades_url, link["href"])
                self._log("info", f"Following Excel sheet link: {sub_url}")
                sub_html = self.fetcher.fetch(sub_url)
                return sub_html if sub_html else html_bytes
            return html_bytes

        frames = soup.find_all(["frame", "iframe"], src=True)
        target_frame = None
        for f in frames:
            if "sheet001" in f["src"].lower():
                target_frame = f
                break

        if not target_frame and frames:
            target_frame = frames[0]

        if target_frame:
            sub_url = urljoin(grades_url, target_frame["src"])
            self._log("info", f"Following frame src: {sub_url}")
            sub_html = self.fetcher.fetch(sub_url)
            return sub_html if sub_html else html_bytes

        return html_bytes

    @staticmethod
    def _to_dict(data: Any) -> Dict[str, Any]:
        if isinstance(data, dict):
            return data

        if hasattr(data, "model_dump") and callable(getattr(data, "model_dump")):
            return data.model_dump()

        if hasattr(data, "dict") and callable(getattr(data, "dict")):
            return data.dict()

        if hasattr(data, "__dict__"):
            return vars(data)

        raise TypeError(f"Gagal mengonversi objek tipe {type(data)} ke dictionary")
