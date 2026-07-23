from typing import Any, Dict, List
from urllib.parse import urljoin

from scraper.config import (
    COURSES,
    DATA_OUTPUT_DIR,
    LOG_OUTPUT_DIR,
    MAX_YEAR,
    MIN_YEAR,
    CourseConfig,
)
from scraper.course_year_crawler import CourseYearCrawler
from scraper.html_fetcher import HTMLFetcher
from scraper.year_extractor import YearExtractor
from utils.logger import Logger
from utils.writer import Writer


class Pipeline:
    def __init__(self, logger: Logger) -> None:
        self.logger = logger
        self.fetcher = HTMLFetcher()
        self.writer = Writer(output_dir=DATA_OUTPUT_DIR)

    def _create_empty_result_container(self) -> Dict[str, List[Any]]:
        return {
            "courses_info": [],
            "courses_grades": [],
            "course_materials": [],
            "assignments": [],
            "paper_files": [],
        }

    def _decode_html(self, html_bytes: bytes) -> str:
        try:
            return html_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return str(html_bytes)

    def _merge_results(self, target: Dict[str, List[Any]], source: Dict[str, List[Any]]) -> None:
        for key in target:
            target[key].extend(source.get(key, []))

    def _fetch_course_html(self, course: CourseConfig) -> str | None:
        html_bytes = self.fetcher.fetch(course.base_url)
        if not html_bytes:
            self.logger.error(f"Gagal fetch halaman base: {course.base_url}")
            return None
        return self._decode_html(html_bytes)

    def _get_valid_years(self, html_str: str, course_code: str) -> List[Dict[str, Any]]:
        all_years = YearExtractor.extract_years(html_str)
        valid_years = YearExtractor.filter_valid_years(all_years, MIN_YEAR, MAX_YEAR)

        self.logger.info(f"Found {len(valid_years)} valid years for {course_code}")
        if not valid_years:
            self.logger.warning(f"No valid years found for {course_code}")

        return valid_years

    def _crawl_single_year(self, course: CourseConfig, year_data: Dict[str, Any]) -> Dict[str, List[Any]]:

        year_range = f"{year_data['start_year']}/{year_data['end_year']}"
        year_url = year_data["url"]

        if not year_url.startswith("http"):
            year_url = urljoin(course.base_url, year_url)

        self.logger.info(f"Crawling {course.code} year {year_range}")

        academic_year = {
            "start_year": year_data["start_year"],
            "end_year": year_data["end_year"],
        }

        crawler = CourseYearCrawler(
            course_code=course.code,
            course_name=course.name,
            base_url=year_url,
            academic_year=academic_year,
            logger=self.logger,
        )

        return crawler.crawl()

    def process_course(self, course: CourseConfig) -> Dict[str, List[Any]]:
        self.logger.info(f"Processing: {course.name} ({course.code})")
        course_results = self._create_empty_result_container()

        html_str = self._fetch_course_html(course)
        if not html_str:
            return course_results

        valid_years = self._get_valid_years(html_str, course.code)
        if not valid_years:
            return course_results

        for year_data in valid_years:
            year_results = self._crawl_single_year(course, year_data)
            self._merge_results(course_results, year_results)

        return course_results

    def run(self, courses: List[CourseConfig]) -> None:
        self._log_header(len(courses))
        global_results = self._create_empty_result_container()

        for course in courses:
            try:
                course_res = self.process_course(course)
                self._merge_results(global_results, course_res)
            except Exception as e:
                self.logger.error(f"Fatal error processing {course.code}: {str(e)}")

        self._save_and_finalize(global_results)

    def _log_header(self, total_courses: int) -> None:
        self.logger.info("=" * 80)
        self.logger.info("SCRAPING DATA PERKULIAHAN ITB")
        self.logger.info("=" * 80)
        self.logger.info(f"Total Courses : {total_courses}")
        self.logger.info(f"Year Range    : {MIN_YEAR} - {MAX_YEAR}")

    def _save_and_finalize(self, global_results: Dict[str, List[Any]]) -> None:
        self.logger.info("=" * 80)
        self.logger.info("SAVING ALL COMBINED RESULTS...")
        self.writer.save_all(global_results, self.logger)

        self.logger.info("=" * 80)
        self.logger.info("SCRAPING COMPLETED")
        self.logger.info("=" * 80)
