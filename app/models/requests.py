from pydantic import BaseModel
from typing import List, Optional, Literal
from typing import Optional, Literal
from fastapi import UploadFile
from fastapi import Form


class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 15
    rerank_top_n: Optional[int] = 5
    filter_files: Optional[List[str]] = None

class FileUploadRequest(BaseModel):
    category: Literal["HR", "Finance", "IT", "Operations"]
    department: Literal["Engineering", "Sales", "Marketing", "Support"]
    document_type: Literal["Policy", "SOP", "Runbook"]
    version: str
    description: Optional[str] = None

    @classmethod
    def as_form(
        cls,
        category: Literal["HR", "Finance", "IT", "Operations"] = Form(...),
        department: Literal["Engineering", "Sales", "Marketing", "Support"] = Form(...),
        document_type: Literal["Policy", "SOP", "Runbook"] = Form(...),
        version: str = Form(...),
        description: Optional[str] = Form(None),
    ):
        return cls(
            category=category,
            department=department,
            document_type=document_type,
            version=version,
            description=description,
        )
