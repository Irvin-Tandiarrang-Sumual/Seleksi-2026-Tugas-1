from pydantic import BaseModel

class AcademicYear(BaseModel):
    start_year: int
    end_year: int
