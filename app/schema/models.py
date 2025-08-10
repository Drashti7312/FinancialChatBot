from pydantic import BaseModel, Field, GetJsonSchemaHandler
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from pydantic_core import CoreSchema

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, _info):  # added `_info` as second argument
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict:
        schema = handler(core_schema)
        schema.update(type="string")
        return schema

class DocumentUpload(BaseModel):
    session_id: str
    user_id: str
    file_type: str  # csv, excel, pdf, docx
    filename: str

class LinkUpload(BaseModel):
    session_id: str
    user_id: str
    url: str
    title: Optional[str] = None

class ChatMessage(BaseModel):
    session_id: str
    user_id: str
    message: str

class GetChartsRequest(BaseModel):
    session_id: str
    user_id: str

class ChatHistory(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    session_id: str
    user_id: str
    messages: List[Dict[str, Any]] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class SessionDocuments(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    session_id: str
    user_id: str
    excel_ids: List[str] = []
    pdf_ids: List[str] = []
    docx_ids: List[str] = []
    csv_ids: List[str] = []
    link_ids: List[str] = []
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
