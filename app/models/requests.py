from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime
from fastapi import UploadFile, Form
from datetime import date

class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 15
    rerank_top_n: Optional[int] = 5
    filter_files: Optional[List[str]] = None


class FileUploadRequest(BaseModel):
    category: Literal["HR", "Finance", "IT", "Operations"]
    department: Literal["Engineering", "Sales", "Marketing", "Support"]
    document_type: Literal["Policy", "SOP", "Runbook"]
    region: Literal["United States", "European Union", "Asia-Specific"]
    version: str
    effective_date: date
    description: Optional[str] = None

    @classmethod
    def as_form(
        cls,
        category: Literal["HR", "Finance", "IT", "Operations"] = Form(...),
        department: Literal["Engineering", "Sales", "Marketing", "Support"] = Form(...),
        document_type: Literal["Policy", "SOP", "Runbook"] = Form(...),
        region: Literal["United States", "European Union", "Asia-Specific"] = Form(...),
        version: str = Form(...),
        effective_date: date = Form(...),
        description: Optional[str] = Form(None),
    ):
        return cls(
            category=category,
            department=department,
            document_type=document_type,
            region=region,
            version=version,
            effective_date=effective_date,
            description=description,
        )
