import re

from bs4 import BeautifulSoup


class YearExtractor:
    YEAR_PATTERN = re.compile(r"(\d{4})\s*[-/]\s*(\d{4})")

    @staticmethod
    def extract_years(html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        years = []

        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            href = link["href"]

            match = YearExtractor.YEAR_PATTERN.search(text) or YearExtractor.YEAR_PATTERN.search(href)
            if not match:
                continue

            start_year = int(match.group(1))
            end_year = int(match.group(2))

            semester_match = re.search(r"Semester\s+([I|V]+|[1-2])", text)
            semester = (
                "II"
                if semester_match and semester_match.group(1) in ["II", "2"]
                else "I"
            )

            years.append(
                {
                    "start_year": start_year,
                    "end_year": end_year,
                    "semester": semester,
                    "url": href,
                    "text": text,
                }
            )

        return years

    @staticmethod
    def filter_valid_years(years: list[dict], min_year: int = 2015, max_year: int = 2026) -> list[dict]:
        return [y for y in years if min_year <= y["start_year"] <= max_year]
