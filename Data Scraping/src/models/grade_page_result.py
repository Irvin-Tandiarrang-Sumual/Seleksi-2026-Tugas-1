from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from models.academic_year import AcademicYear
from models.student_grade import StudentGrade


class GradePageResult(BaseModel):
    course_code: str
    course_title: str
    section_semester: int
    academic_year: AcademicYear
    assistant: Optional[List[str]] = None
    students: List[StudentGrade]

    def to_dict(self) -> Dict[str, Any]:
        res = self.model_dump(exclude={"students"})
        res["students"] = [s.model_dump_json_ready() for s in self.students]
        return res
