from scraper.html_fetcher import HTMLFetcher
from scraper.section_extractor import SectionExtractor


class CourseDataCollector:
    def __init__(self, base_url: str, course_code: str, course_name: str):
        self.base_url = base_url
        self.course_code = course_code
        self.course_name = course_name
        self.fetcher = HTMLFetcher()

        self.course_info = {}
        self.materials = []
        self.assignments = []
        self.papers = []
        self.grades = []

    def collect_info(self, html: str):
        section = SectionExtractor.extract_section_content(html, "info")
        links = SectionExtractor.extract_links_from_section(section, self.base_url)

        for link in links:
            text_lower = link["text"].lower()
            url_lower = link["url"].lower()
            if any(kw in text_lower or kw in url_lower for kw in ["silabus", "info"]):
                self.course_info = {
                    "title": link["text"],
                    "url": link["url"],
                    "type": "syllabus_pdf",
                }
                break

    def collect_materials(self, html: str):
        section = SectionExtractor.extract_section_content(html, "materials")
        links = SectionExtractor.extract_links_from_section(section, self.base_url)

        seen_urls = set()
        unwanted_keywords = [
            "soal",
            "solusi",
            "jawab",
            "ujian",
            "uts",
            "uas",
            "kuis",
            "tugas",
        ]

        for link in links:
            url = link["url"]
            if url in seen_urls or not url.endswith(".pdf"):
                continue

            if any(kw in url.lower() for kw in unwanted_keywords):
                continue

            self.materials.append(
                {
                    "title": link["text"],
                    "url": url,
                    "type": "slide",
                }
            )
            seen_urls.add(url)

    def collect_assignments(self, html: str):
        section = SectionExtractor.extract_section_content(html, "assignments")
        links = SectionExtractor.extract_links_from_section(section, self.base_url)

        exams_section = SectionExtractor.extract_section_content(html, "exams")
        exam_links = SectionExtractor.extract_links_from_section(
            exams_section, self.base_url
        )

        seen_urls = set()
        for link in links + exam_links:
            url = link["url"]
            if url in seen_urls or "solusi" in link["text"].lower():
                continue

            if url.endswith(".pdf"):
                self.assignments.append(
                    {
                        "title": link["text"],
                        "url": url,
                        "type": "assignment",
                    }
                )
                seen_urls.add(url)

    def collect_papers(self, html: str):
        section = SectionExtractor.extract_section_content(html, "papers")
        links = SectionExtractor.extract_links_from_section(section, self.base_url)

        seen_urls = set()
        for link in links:
            url = link["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)

            text_lower = link["text"].lower()
            is_html_paper = url.endswith((".html", ".htm")) and (
                "daftar" in text_lower or "makalah" in text_lower
            )
            is_pdf_paper = url.endswith(".pdf") and ("daftar" in text_lower)

            if is_html_paper or is_pdf_paper:
                self.papers.append(
                    {
                        "title": link["text"],
                        "url": url,
                        "type": "paper_list",
                    }
                )

    def collect_grades(self, html: str):
        section = SectionExtractor.extract_section_content(html, "grades")

        html_to_search = section if section.strip() else html
        links = SectionExtractor.extract_links_from_section(
            html_to_search, self.base_url
        )

        seen_urls = set()
        for link in links:
            url = link["url"]
            text_lower = link["text"].lower()
            url_lower = url.lower()

            if url in seen_urls:
                continue

            is_grade = (
                "nilai" in text_lower
                or "nilai" in url_lower
                or "grade" in text_lower
                or "grade" in url_lower
            )

            if is_grade:
                self.grades.append(
                    {
                        "title": link["text"] if link["text"] else "Nilai Perkuliahan",
                        "url": url,
                        "type": (
                            "grade_file"
                            if url.endswith((".pdf", ".xlsx", ".xls"))
                            else "grade_page"
                        ),
                    }
                )
                seen_urls.add(url)
