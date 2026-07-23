from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class CourseConfig:
    code: str
    name: str
    base_url: str
    folder_names: List[str]


MIN_YEAR: int = 2020
MAX_YEAR: int = 2026

DATA_OUTPUT_DIR: str = "data"
LOG_OUTPUT_DIR: str = "logs"

COURSES: List[CourseConfig] = [
    CourseConfig(
        code="IF2211",
        name="Strategi Algoritma",
        base_url="https://informatika.stei.itb.ac.id/~rinaldi.munir/Stmik/stmik.htm",
        folder_names=["Stmik", "stmik"],
    ),
    CourseConfig(
        code="IF2120",
        name="Matematika Diskrit",
        base_url="https://informatika.stei.itb.ac.id/~rinaldi.munir/Matdis/matdis.htm",
        folder_names=["Matdis", "matdis"],
    ),
    CourseConfig(
        code="IF2123",
        name="Aljabar Linier dan Geometri",
        base_url="https://informatika.stei.itb.ac.id/~rinaldi.munir/AljabarGeometri/algeo.htm",
        folder_names=["AljabarGeometri", "algeo"],
    ),
]
