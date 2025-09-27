from fastapi import HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select
from modules.config import app, get_session, UPLOAD_FOLDER, THUMBNAILS_FOLDER, templates
from modules.models import AccessoryCategory, AccessoryModel
from typing import Optional
import uuid
from datetime import datetime
from pathlib import Path


# Admin Routes
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin dashboard"""
    return templates.TemplateResponse(
        "admin/dashboard.html", {"request": request, "title": "Admin Dashboard"}
    )


@app.get("/admin/categories", response_class=HTMLResponse)
async def admin_categories(request: Request, session: Session = Depends(get_session)):
    """List categories"""
    categories = session.exec(select(AccessoryCategory)).all()
    return templates.TemplateResponse(
        "admin/categories.html",
        {"request": request, "categories": categories, "title": "Categories"},
    )


@app.get("/admin/categories/{category_id}/edit", response_class=HTMLResponse)
async def admin_edit_category(
    request: Request, category_id: int, session: Session = Depends(get_session)
):
    """Edit category form"""
    category = session.get(AccessoryCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    return templates.TemplateResponse(
        "admin/category_edit.html",
        {
            "request": request,
            "category": category,
            "title": f"Edit {category.name.title()} Category",
            "action": "edit",
        },
    )


@app.post("/admin/categories/{category_id}/edit")
async def admin_edit_category_post(
    request: Request,
    category_id: int,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    anchor_index: int = Form(...),
    session: Session = Depends(get_session),
):
    """Handle category editing"""
    try:
        category = session.get(AccessoryCategory, category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        # Update category fields
        category.name = name.strip().lower()  # Keep names lowercase for consistency
        category.description = description
        category.anchor_index = anchor_index

        session.commit()

        return RedirectResponse(url="/admin/categories", status_code=303)

    except Exception as e:
        return templates.TemplateResponse(
            "admin/category_edit.html",
            {
                "request": request,
                "category": category,
                "title": f"Edit {category.name.title()} Category",
                "action": "edit",
                "error": str(e),
            },
        )


@app.get("/admin/models", response_class=HTMLResponse)
async def admin_models(request: Request, session: Session = Depends(get_session)):
    """List models"""
    query = select(AccessoryModel, AccessoryCategory).join(AccessoryCategory)
    results = session.exec(query).all()
    models = [(model, category) for model, category in results]

    return templates.TemplateResponse(
        "admin/models.html",
        {"request": request, "models": models, "title": "3D Models"},
    )


@app.get("/admin/models/create", response_class=HTMLResponse)
async def admin_create_model(request: Request, session: Session = Depends(get_session)):
    """Create model form"""
    categories = session.exec(select(AccessoryCategory)).all()
    return templates.TemplateResponse(
        "admin/model_form.html",
        {
            "request": request,
            "categories": categories,
            "title": "Create 3D Model",
            "action": "create",
        },
    )


@app.post("/admin/models/create")
async def admin_create_model_post(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    category_id: int = Form(...),
    model_file: Optional[UploadFile] = File(None),
    thumbnail_file: Optional[UploadFile] = File(None),
    position_x: float = Form(0.0),
    position_y: float = Form(0.0),
    position_z: float = Form(0.0),
    rotation_x: float = Form(0.0),
    rotation_y: float = Form(0.0),
    rotation_z: float = Form(0.0),
    scale_x: float = Form(1.0),
    scale_y: float = Form(1.0),
    scale_z: float = Form(1.0),
    anchor_index: str = Form(""),  # Accept as string first
    is_active: Optional[bool] = Form(None),
    session: Session = Depends(get_session),
):
    """Handle model creation"""
    try:
        # Convert anchor_index from string to int or None
        parsed_anchor_index = None
        if anchor_index and anchor_index.strip():
            try:
                parsed_anchor_index = int(anchor_index)
            except ValueError:
                raise ValueError(f"Invalid anchor index: {anchor_index}")
        else:
            # If no override provided, use the category's default anchor_index
            category = session.get(AccessoryCategory, category_id)
            if category:
                parsed_anchor_index = category.anchor_index

        # Create new model
        new_model = AccessoryModel(
            uuid=str(uuid.uuid4()),
            name=name,
            description=description,
            category_id=category_id,
            position_x=position_x,
            position_y=position_y,
            position_z=position_z,
            rotation_x=rotation_x,
            rotation_y=rotation_y,
            rotation_z=rotation_z,
            scale_x=scale_x,
            scale_y=scale_y,
            scale_z=scale_z,
            anchor_index=parsed_anchor_index,
            is_active=is_active if is_active is not None else True,
            filename="",  # Will be set if file uploaded
            original_filename="",
            file_size=0,
            file_type="",
        )

        # Handle model file
        if model_file and model_file.filename:
            ext = Path(model_file.filename).suffix.lower()
            if ext not in [".glb", ".gltf"]:
                raise ValueError("Model file must be .glb or .gltf")

            unique_name = f"{new_model.uuid}{ext}"
            file_path = UPLOAD_FOLDER / unique_name

            content = await model_file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            new_model.filename = unique_name
            new_model.original_filename = model_file.filename
            new_model.file_size = len(content)
            new_model.file_type = ext

        # Handle thumbnail
        if thumbnail_file and thumbnail_file.filename:
            ext = Path(thumbnail_file.filename).suffix.lower()
            if ext in [".jpg", ".jpeg", ".png", ".webp"]:
                unique_name = f"thumb_{new_model.uuid}{ext}"
                thumb_path = THUMBNAILS_FOLDER / unique_name

                content = await thumbnail_file.read()
                with open(thumb_path, "wb") as f:
                    f.write(content)

                new_model.thumbnail_path = f"thumbnails/{unique_name}"

        session.add(new_model)
        session.commit()

        return RedirectResponse(url="/admin/models", status_code=303)

    except Exception as e:
        categories = session.exec(select(AccessoryCategory)).all()
        return templates.TemplateResponse(
            "admin/model_form.html",
            {
                "request": request,
                "categories": categories,
                "title": "Create 3D Model",
                "action": "create",
                "error": str(e),
            },
        )


@app.get("/admin/models/{model_id}/edit", response_class=HTMLResponse)
async def admin_edit_model(
    request: Request, model_id: int, session: Session = Depends(get_session)
):
    """Edit model form"""
    model = session.get(AccessoryModel, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    categories = session.exec(select(AccessoryCategory)).all()
    return templates.TemplateResponse(
        "admin/model_form.html",
        {
            "request": request,
            "model": model,
            "categories": categories,
            "title": f"Edit {model.name}",
            "action": "edit",
        },
    )


@app.post("/admin/models/{model_id}/edit")
async def admin_edit_model_post(
    request: Request,
    model_id: int,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    category_id: int = Form(...),
    model_file: Optional[UploadFile] = File(None),
    thumbnail_file: Optional[UploadFile] = File(None),
    position_x: float = Form(0.0),
    position_y: float = Form(0.0),
    position_z: float = Form(0.0),
    rotation_x: float = Form(0.0),
    rotation_y: float = Form(0.0),
    rotation_z: float = Form(0.0),
    scale_x: float = Form(1.0),
    scale_y: float = Form(1.0),
    scale_z: float = Form(1.0),
    anchor_index: str = Form(""),  # Accept as string first
    is_active: Optional[bool] = Form(None),
    session: Session = Depends(get_session),
):
    """Handle model editing"""
    try:
        model = session.get(AccessoryModel, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        # Convert anchor_index from string to int or None
        parsed_anchor_index = None
        if anchor_index and anchor_index.strip():
            try:
                parsed_anchor_index = int(anchor_index)
            except ValueError:
                raise ValueError(f"Invalid anchor index: {anchor_index}")
        else:
            # If no override provided, use the category's default anchor_index
            category = session.get(AccessoryCategory, category_id)
            if category:
                parsed_anchor_index = category.anchor_index

        # Update basic fields
        model.name = name
        model.description = description
        model.category_id = category_id
        model.position_x = position_x
        model.position_y = position_y
        model.position_z = position_z
        model.rotation_x = rotation_x
        model.rotation_y = rotation_y
        model.rotation_z = rotation_z
        model.scale_x = scale_x
        model.scale_y = scale_y
        model.scale_z = scale_z
        model.anchor_index = parsed_anchor_index
        model.is_active = is_active if is_active is not None else False
        model.updated_at = datetime.utcnow()

        # Handle model file replacement
        if model_file and model_file.filename:
            ext = Path(model_file.filename).suffix.lower()
            if ext not in [".glb", ".gltf"]:
                raise ValueError("Model file must be .glb or .gltf")

            # Delete old file
            if model.filename:
                old_path = UPLOAD_FOLDER / model.filename
                if old_path.exists():
                    old_path.unlink()

            unique_name = f"{model.uuid}{ext}"
            file_path = UPLOAD_FOLDER / unique_name

            content = await model_file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            model.filename = unique_name
            model.original_filename = model_file.filename
            model.file_size = len(content)
            model.file_type = ext

        # Handle thumbnail replacement
        if thumbnail_file and thumbnail_file.filename:
            ext = Path(thumbnail_file.filename).suffix.lower()
            if ext in [".jpg", ".jpeg", ".png", ".webp"]:
                # Delete old thumbnail
                if model.thumbnail_path:
                    old_thumb_path = Path("static") / model.thumbnail_path
                    if old_thumb_path.exists():
                        old_thumb_path.unlink()

                unique_name = f"thumb_{model.uuid}{ext}"
                thumb_path = THUMBNAILS_FOLDER / unique_name

                content = await thumbnail_file.read()
                with open(thumb_path, "wb") as f:
                    f.write(content)

                model.thumbnail_path = f"thumbnails/{unique_name}"

        session.commit()

        return RedirectResponse(url="/admin/models", status_code=303)

    except Exception as e:
        categories = session.exec(select(AccessoryCategory)).all()
        return templates.TemplateResponse(
            "admin/model_form.html",
            {
                "request": request,
                "model": model,
                "categories": categories,
                "title": f"Edit {model.name}",
                "action": "edit",
                "error": str(e),
            },
        )


@app.post("/admin/models/{model_id}/delete")
async def admin_delete_model(model_id: int, session: Session = Depends(get_session)):
    """Delete model"""
    model = session.get(AccessoryModel, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Delete files
    if model.filename:
        file_path = UPLOAD_FOLDER / model.filename
        if file_path.exists():
            file_path.unlink()

    if model.thumbnail_path:
        thumb_path = Path("static") / model.thumbnail_path
        if thumb_path.exists():
            thumb_path.unlink()

    session.delete(model)
    session.commit()

    return RedirectResponse(url="/admin/models", status_code=303)


@app.post("/admin/models/{model_id}/toggle")
async def admin_toggle_model(model_id: int, session: Session = Depends(get_session)):
    """Toggle model active status"""
    model = session.get(AccessoryModel, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    model.is_active = not model.is_active
    model.updated_at = datetime.utcnow()
    session.commit()

    return {"success": True, "is_active": model.is_active}
