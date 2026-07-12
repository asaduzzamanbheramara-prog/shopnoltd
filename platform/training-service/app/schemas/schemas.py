from pydantic import BaseModel
from typing import Optional
class CourseIn(BaseModel):
    code: str; title: str; description: str = ""
    level: str = "beginner"; price: float = 0; duration_hours: int = 0
class LessonIn(BaseModel):
    course_id: str; title: str; content: str = ""; video_url: str = ""
    duration_min: int = 0
class QuizIn(BaseModel):
    course_id: str; lesson_id: Optional[str] = None; title: str
    questions: list; passing_score: int = 70
class QuizSubmit(BaseModel):
    quiz_id: str; answers: dict
