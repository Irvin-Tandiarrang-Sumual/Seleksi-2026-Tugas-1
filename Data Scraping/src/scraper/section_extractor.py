import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag


class SectionExtractor:

    SECTION_MAPPINGS = {
        "info": {"names": ["InfoKuliah"], "texts": ["Informasi Perkuliahan"]},
        "materials": {
            "names": ["SlideKuliah"],
            "texts": ["Slide Bahan Kuliah", "Bahan Kuliah", "Slide Bahan kuliah"],
        },
        "assignments": {
            "names": ["PRdanTugas", "Tugas", "KuisUjian"],
            "texts": ["Tugas", "PR dan Tugas", "Kuis"],
        },
        "papers": {"names": ["Makalah"], "texts": ["Makalah mahasiswa", "Makalah"]},
        "grades": {"names": ["NilaiAkhir"], "texts": ["Nilai Akhir", "Nilai"]},
        "exams": {
            "names": ["Ujian", "KuisUjian"],
            "texts": ["UTS dan UAS", "Ujian", "Kuis dan Ujian"],
        },
    }

    SECTION_KEYWORDS = [
        "Informasi Perkuliahan",
        "Slide Bahan",
        "Tugas",
        "PR dan Tugas",
        "Makalah",
        "Nilai Akhir",
        "Ujian",
        "Kuis",
        "Asisten",
        "Referensi",
        "Jadwal",
        "E-mail",
        "Web",
        "Rencana",
        "Foto",
    ]

    @classmethod
    def _find_anchor(cls, soup: BeautifulSoup, html: str, anchor_name: str) -> Tag | None:
        """Mencari tag anchor berdasarkan nama atribut name."""
        anchor = soup.find("a", attrs={"name": anchor_name})
        if anchor:
            return anchor

        pattern = rf'<a\s+name\s*=\s*["\']?{re.escape(anchor_name)}["\']?'
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            remaining_html = html[match.start() :]
            temp_soup = BeautifulSoup(remaining_html, "html.parser")
            return temp_soup.find("a")

        return None

    @classmethod
    def _is_next_heading(cls, current: Tag, anchor: Tag, mapping: dict) -> bool:
        """Mengecek apakah elemen saat ini merupakan heading dari section selanjutnya."""
        is_heading_tag = current.name in [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "b",
            "strong",
        ]
        is_nested_in_content = any(
            p.name in ["a", "p", "li", "td", "ol", "ul"] for p in current.parents
        )

        if not (is_heading_tag and not is_nested_in_content):
            return False

        text_content = current.get_text(strip=True)
        has_keyword = any(
            kw.lower() in text_content.lower() for kw in cls.SECTION_KEYWORDS
        )

        if (
            has_keyword
            and len(text_content) < 100
            and not text_content.startswith("1.")
        ):
            if current != anchor and anchor not in current.parents:
                is_own_heading = any(
                    own_text.lower() in text_content.lower()
                    for own_text in mapping.get("texts", [])
                )
                return not is_own_heading

        return False

    @classmethod
    def _collect_nodes_until_delimiter(cls, anchor: Tag, mapping: dict) -> str:
        """Mengumpulkan HTML string sampai bertemu pemisah section (<hr> atau heading baru)."""
        content_html = ""
        current = anchor.find_next()

        while current:
            if current.name == "hr":
                break

            if current.name == "a" and current.get("name"):
                break

            if cls._is_next_heading(current, anchor, mapping):
                break

            content_html += str(current) + "\n"
            current = current.find_next()

            if len(content_html) > 150000:  # Prevent infinite loop
                break

        return content_html

    @classmethod
    def extract_section_content(cls, html: str, section_name: str) -> str:
        """Extract content dari section tertentu berdasarkan heading text atau anchor name."""
        soup = BeautifulSoup(html, "html.parser")
        mapping = cls.SECTION_MAPPINGS.get(section_name, {})
        anchor_names = mapping.get("names", [])

        for anchor_name in anchor_names:
            anchor = cls._find_anchor(soup, html, anchor_name)
            if anchor:
                content_html = cls._collect_nodes_until_delimiter(anchor, mapping)
                if content_html.strip() and len(content_html) > 20:
                    return str(anchor) + "\n" + content_html

        return ""

    @staticmethod
    def extract_links_from_section(section_html: str, base_url: str = "") -> list[dict]:
        """Extract semua links dari section HTML."""
        soup = BeautifulSoup(section_html, "html.parser")
        links = []

        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            href = link["href"].replace("\\", "/")

            if base_url:
                href = urljoin(base_url, href)

            links.append(
                {
                    "text": text,
                    "url": href,
                    "title": link.get("title", ""),
                }
            )

        return links
