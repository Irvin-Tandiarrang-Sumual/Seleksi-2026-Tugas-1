import json
from pathlib import Path
from typing import Any, Dict, List

from utils.logger import Logger


class Writer:
    def __init__(self, output_dir: str = "data") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_all(self, results: Dict[str, List[Any]], logger: Logger) -> None:
        file_mapping = {
            "courses_info.json": results.get("courses_info", []),
            "courses_grades.json": results.get("courses_grades", []),
            "course_materials.json": results.get("course_materials", []),
            "assignments.json": results.get("assignments", []),
            "paper_files.json": results.get("paper_files", []),
        }

        for filename, data in file_mapping.items():
            filepath = self.output_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(
                f"[SUCCESS] Saved (ALL COURSES): {filepath} ({len(data)} items)"
            )
