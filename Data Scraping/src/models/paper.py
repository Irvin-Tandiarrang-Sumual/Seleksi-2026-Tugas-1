from typing import Optional
from pydantic import BaseModel
from models.academic_year import AcademicYear
from models.student import Student


class Paper(BaseModel):
    title: str
    abstract: Optional[str] = None
    url: str
    language: str = "id"
    student: Student
    course_code: str
    section_semester: int = 1
    academic_year: AcademicYear

    def model_post_init(self, __context):
        if not self.abstract:
            self.abstract = self.title
