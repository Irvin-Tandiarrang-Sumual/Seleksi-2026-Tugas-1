from typing import List, Optional

from pydantic import BaseModel, Field


class Student(BaseModel):
    name: Optional[str] = None
    student_number: Optional[str] = None
    emails: List[str] = Field(default_factory=list)
