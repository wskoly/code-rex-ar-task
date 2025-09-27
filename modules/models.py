from sqlmodel import SQLModel, Field
from typing import Optional
import uuid
from datetime import datetime


# Database Models
class AccessoryCategory(SQLModel, table=True):
    """Category for accessories (hats, glasses, etc.)"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=50, unique=True, index=True)
    description: Optional[str] = Field(default=None, max_length=200)
    anchor_index: int = Field(description="Default face anchor point for this category")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
class AccessoryModel(SQLModel, table=True):
    """3D Model for virtual try-on accessories"""
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: str = Field(unique=True, index=True, default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(max_length=100, index=True)
    description: Optional[str] = Field(default=None, max_length=500)
    filename: str = Field(max_length=255)
    original_filename: str = Field(max_length=255)
    file_size: int = Field(description="File size in bytes")
    file_type: str = Field(max_length=10, description="File extension (.glb or .gltf)")
    thumbnail_path: Optional[str] = Field(default=None, max_length=255)
    
    # Category relationship
    category_id: int = Field(foreign_key="accessorycategory.id")
    
    # 3D positioning data
    position_x: float = Field(default=0.0)
    position_y: float = Field(default=0.0) 
    position_z: float = Field(default=0.0)
    rotation_x: float = Field(default=0.0)
    rotation_y: float = Field(default=0.0)
    rotation_z: float = Field(default=0.0)
    scale_x: float = Field(default=1.0)
    scale_y: float = Field(default=1.0)
    scale_z: float = Field(default=1.0)
    anchor_index: Optional[int] = Field(default=None, description="Override category anchor")
    
    # Metadata
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
