"""Country education systems (DESIGN §8).

MVP ships RUSystem (curated fields of study / exams / deadlines). For any other
country we return an honest "no verified data" with a pointer to official
sources — never an LLM-generated admission path (a design decision, P5).
"""

from app.education.service import get_education

__all__ = ["get_education"]
