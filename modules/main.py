from fastapi import HTTPException, Depends, UploadFile, File, Form, Request
from sqlmodel import Session, select
from modules.config import app, get_session, UPLOAD_FOLDER, logger, templates
from modules.models import AccessoryCategory, AccessoryModel
from typing import Optional
import uuid
from datetime import datetime
from pathlib import Path


# Main Routes

@app.get("/")
async def home(request: Request):
    """Serve the main HTML page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "database": "connected"
    }



@app.get("/api/categories")
async def get_categories(session: Session = Depends(get_session)):
    """Get all accessory categories"""
    categories = session.exec(select(AccessoryCategory)).all()
    return {
        "status": "success",
        "data": categories
    }

@app.get("/api/models")
async def get_models(
    category: Optional[str] = None,
    active_only: bool = True,
    session: Session = Depends(get_session)
):
    """Get all models, optionally filtered by category"""
    query = select(AccessoryModel, AccessoryCategory).join(AccessoryCategory)
    
    if category:
        query = query.where(AccessoryCategory.name == category)
    
    if active_only:
        query = query.where(AccessoryModel.is_active == True)
    
    results = session.exec(query).all()
    
    # Group by category
    models_by_category = {}
    for model, category_obj in results:
        category_name = category_obj.name
        if category_name not in models_by_category:
            models_by_category[category_name] = []
        
        model_data = {
            "id": model.uuid,
            "name": model.name,
            "description": model.description,
            "filename": model.filename,
            "thumbnail": f"/static/{model.thumbnail_path}" if model.thumbnail_path else None,
            "position": [model.position_x, model.position_y, model.position_z],
            "rotation": [model.rotation_x, model.rotation_y, model.rotation_z],
            "scale": [model.scale_x, model.scale_y, model.scale_z],
            "anchor_index": model.anchor_index or category_obj.anchor_index,
            "created_at": model.created_at.isoformat()
        }
        models_by_category[category_name].append(model_data)
    
    return {
        "status": "success", 
        "data": models_by_category
    }

@app.post("/api/upload")
async def upload_model(
    file: UploadFile = File(...),
    category_name: str = Form(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    """Upload a new 3D model"""
    
    # Validate file type
    if not file.filename.lower().endswith(('.glb', '.gltf')):
        raise HTTPException(status_code=400, detail="Only .glb and .gltf files are allowed")
    
    # Get category
    category = session.exec(
        select(AccessoryCategory).where(AccessoryCategory.name == category_name)
    ).first()
    
    if not category:
        raise HTTPException(status_code=400, detail=f"Category '{category_name}' not found")
    
    # Generate unique filename
    model_uuid = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix.lower()
    unique_filename = f"{model_uuid}{file_extension}"
    file_path = UPLOAD_FOLDER / unique_filename
    
    try:
        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Create database record
        new_model = AccessoryModel(
            uuid=model_uuid,
            name=name,
            description=description,
            filename=unique_filename,
            original_filename=file.filename,
            file_size=len(content),
            file_type=file_extension,
            category_id=category.id,
            # Default positioning based on category
            position_x=0.0, position_y=0.0, position_z=-1.0,
            rotation_x=0.0, rotation_y=0.0, rotation_z=0.0,
            scale_x=0.2, scale_y=0.2, scale_z=0.2,
            anchor_index=category.anchor_index
        )
        
        session.add(new_model)
        session.commit()
        session.refresh(new_model)
        
        logger.info(f"Successfully uploaded model: {name} ({unique_filename})")
        
        return {
            "status": "success",
            "message": "Model uploaded successfully",
            "data": {
                "id": new_model.uuid,
                "name": new_model.name,
                "filename": new_model.filename
            }
        }
        
    except Exception as e:
        # Clean up file if database operation fails
        if file_path.exists():
            file_path.unlink()
        
        logger.error(f"Error uploading model: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")

@app.delete("/api/models/{model_uuid}")
async def delete_model(model_uuid: str, session: Session = Depends(get_session)):
    """Delete a model"""
    model = session.exec(
        select(AccessoryModel).where(AccessoryModel.uuid == model_uuid)
    ).first()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    try:
        # Delete file
        file_path = UPLOAD_FOLDER / model.filename
        if file_path.exists():
            file_path.unlink()
        
        # Delete thumbnail if exists
        if model.thumbnail_path and Path(model.thumbnail_path).exists():
            Path(model.thumbnail_path).unlink()
        
        # Delete database record
        session.delete(model)
        session.commit()
        
        logger.info(f"Successfully deleted model: {model.name}")
        
        return {
            "status": "success",
            "message": "Model deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error deleting model: {e}")
        raise HTTPException(status_code=500, detail="Delete failed")