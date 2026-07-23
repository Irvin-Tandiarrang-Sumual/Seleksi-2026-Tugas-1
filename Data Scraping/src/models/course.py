from pydantic import BaseModel, Field
from models.academic_year import AcademicYear
from models.instructor import Instructor


class Course(BaseModel):
    course_code: str
    course_name: str
    course_credits: int
    semester: int
    academic_year: AcademicYear
    instructors: list[Instructor] = Field(default_factory=list)
