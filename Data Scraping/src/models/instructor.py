from pydantic import BaseModel, Field

class Instructor(BaseModel):
    name: str
    sections: list[str] = Field(default_factory=list)
