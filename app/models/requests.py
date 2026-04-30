from pydantic import BaseModel
from typing import List, Optional, Literal, Union
from datetime import datetime
from fastapi import UploadFile, Form
from datetime import date

class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 15
    rerank_top_n: Optional[int] = 5
    category: Optional[Union[str, List[str]]] = None
    department: Optional[Union[str, List[str]]] = None
    doc_type: Optional[Union[str, List[str]]] = None
    region: Optional[Union[str, List[str]]] = None


class FileUploadRequest(BaseModel):
    category: Literal["HR", "Finance", "IT", "Operations", "Resume"]
    department: Literal["Engineering", "Sales", "Marketing", "Support"]
    document_type: Literal["Policy", "SOP", "Runbook", "Resume"]
    region: Literal["United States", "European Union", "Asia-Specific"]
    version: str
    effective_date: date
    description: Optional[str] = None

    @classmethod
    def as_form(
        cls,
        category: Literal["HR", "Finance", "IT", "Operations", "Resume"] = Form(...),
        department: Literal["Engineering", "Sales", "Marketing", "Support"] = Form(...),
        document_type: Literal["Policy", "SOP", "Runbook", "Resume"] = Form(...),
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


class MetadataUpdateRequest(BaseModel):
    category: Optional[Literal["HR", "Finance", "IT", "Operations", "Resume"]] = None
    department: Optional[Literal["Engineering", "Sales", "Marketing", "Support"]] = None
    doc_type: Optional[Literal["Policy", "SOP", "Runbook", "Resume"]] = None
    region: Optional[Literal["United States", "European Union", "Asia-Specific"]] = None
    version: Optional[str] = None
    effective_date: Optional[date] = None
    description: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[List[str]] = None
