from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field

class StudentGrade(BaseModel):
    student_number: str
    name: str = "Tanpa Nama"
    section_code: str = "K1"
    final_grade: Optional[str] = None
    components: Dict[str, Union[int, float, str]] = Field(default_factory=dict)

    def model_dump_json_ready(self) -> Dict[str, Any]:
        data = {
            "student_number": self.student_number,
            "name": self.name,
            "section_code": self.section_code,
        }
        if self.final_grade:
            data["final_grade"] = self.final_grade
        data.update(self.components)
        return data
