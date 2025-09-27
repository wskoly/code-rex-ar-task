from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, create_engine, Session, select
from modules.models import AccessoryCategory, AccessoryModel
import shutil
from pathlib import Path
import logging
from contextlib import asynccontextmanager


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = "sqlite:///./virtual_tryon.db"
UPLOAD_FOLDER = Path("models")
STATIC_FOLDER = Path("static")
TEMPLATES_FOLDER = Path("templates")
THUMBNAILS_FOLDER = Path("static/thumbnails")
DATA_FOLDER = Path("data/models")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Ensure directories exist
for folder in [UPLOAD_FOLDER, STATIC_FOLDER, TEMPLATES_FOLDER, THUMBNAILS_FOLDER]:
    folder.mkdir(exist_ok=True)

# Database setup
engine = create_engine(DATABASE_URL, echo=True)


def get_session():
    """Dependency to get database session"""
    with Session(engine) as session:
        yield session


def get_file_size(file_path: Path) -> int:
    """Get file size in bytes, return 0 if file doesn't exist"""
    try:
        return file_path.stat().st_size if file_path.exists() else 0
    except Exception:
        return 0


async def copy_default_assets():
    """Copy default model files and thumbnails from data folder"""
    if not DATA_FOLDER.exists():
        logger.warning(f"Data folder {DATA_FOLDER} not found, skipping asset copy")
        return

    logger.info("Copying default assets...")

    # List of expected files
    model_files = [
        "hat.glb",
        "cowboy_hat_free.glb",
        "eyewear_specs.glb",
        "wooden_sunglasses.glb",
    ]
    thumbnail_files = [
        "hat.png",
        "cowboy_hat_free.png",
        "eyewear_specs.png",
        "wooden_sunglasses.png",
    ]

    # Copy model files to models directory
    for model_file in model_files:
        source_path = DATA_FOLDER / model_file
        dest_path = UPLOAD_FOLDER / model_file

        if source_path.exists():
            try:
                shutil.copy2(source_path, dest_path)
                logger.info(f"Copied model: {model_file}")
            except Exception as e:
                logger.error(f"Failed to copy {model_file}: {e}")
        else:
            logger.warning(f"Model file not found: {source_path}")

    # Copy thumbnail files to static/thumbnails directory
    for thumbnail_file in thumbnail_files:
        source_path = DATA_FOLDER / thumbnail_file
        dest_path = THUMBNAILS_FOLDER / thumbnail_file

        if source_path.exists():
            try:
                shutil.copy2(source_path, dest_path)
                logger.info(f"Copied thumbnail: {thumbnail_file}")
            except Exception as e:
                logger.error(f"Failed to copy {thumbnail_file}: {e}")
        else:
            logger.warning(f"Thumbnail file not found: {source_path}")


async def init_db():
    """Initialize database with tables and default data"""
    SQLModel.metadata.create_all(engine)

    # Add default categories if they don't exist
    with Session(engine) as session:
        # Check if categories exist
        existing_categories = session.exec(select(AccessoryCategory)).all()
        if not existing_categories:
            logger.info("Initializing default categories...")

            categories = [
                AccessoryCategory(
                    name="hats",
                    description="Head accessories like hats, caps, and headwear",
                    anchor_index=10,
                ),
                AccessoryCategory(
                    name="glasses",
                    description="Eye accessories like glasses, sunglasses, and eyewear",
                    anchor_index=168,
                ),
            ]

            for category in categories:
                session.add(category)

            session.commit()
            logger.info(f"Added {len(categories)} default categories")

        # Add default models if they don't exist
        existing_models = session.exec(select(AccessoryModel)).all()
        if not existing_models:
            logger.info("Initializing default models...")

            # Get categories
            hats_category = session.exec(
                select(AccessoryCategory).where(AccessoryCategory.name == "hats")
            ).first()
            glasses_category = session.exec(
                select(AccessoryCategory).where(AccessoryCategory.name == "glasses")
            ).first()

            # Copy default models and thumbnails from data folder
            await copy_default_assets()

            default_models = [
                AccessoryModel(
                    uuid="hat1-default",
                    name="Wizard Hat",
                    description="A magical wizard hat perfect for spellcasting",
                    filename="hat.glb",
                    original_filename="hat.glb",
                    file_size=get_file_size(UPLOAD_FOLDER / "hat.glb"),
                    file_type=".glb",
                    thumbnail_path="thumbnails/hat.png",
                    category_id=hats_category.id,
                    position_x=0.0,
                    position_y=-0.2,
                    position_z=-0.7,
                    rotation_x=0.0,
                    rotation_y=-90.0,
                    rotation_z=0.0,
                    scale_x=0.27,
                    scale_y=0.27,
                    scale_z=0.27,
                    anchor_index=10,
                ),
                AccessoryModel(
                    uuid="hat2-default",
                    name="Cowboy Hat",
                    description="Western style cowboy hat with authentic design",
                    filename="cowboy_hat_free.glb",
                    original_filename="cowboy_hat_free.glb",
                    file_size=get_file_size(UPLOAD_FOLDER / "cowboy_hat_free.glb"),
                    file_type=".glb",
                    thumbnail_path="thumbnails/cowboy_hat_free.png",
                    category_id=hats_category.id,
                    position_x=0.0,
                    position_y=0.0,
                    position_z=-0.75,
                    rotation_x=0.0,
                    rotation_y=0.0,
                    rotation_z=0.0,
                    scale_x=0.07,
                    scale_y=0.07,
                    scale_z=0.07,
                    anchor_index=10,
                ),
                AccessoryModel(
                    uuid="glasses1-default",
                    name="Eyewear Specs",
                    description="Professional eyewear with modern frame design",
                    filename="eyewear_specs.glb",
                    original_filename="eyewear_specs.glb",
                    file_size=get_file_size(UPLOAD_FOLDER / "eyewear_specs.glb"),
                    file_type=".glb",
                    thumbnail_path="thumbnails/eyewear_specs.png",
                    category_id=glasses_category.id,
                    position_x=-0.52,
                    position_y=-0.25,
                    position_z=-1.25,
                    rotation_x=0.0,
                    rotation_y=90.0,
                    rotation_z=0.0,
                    scale_x=0.35,
                    scale_y=0.35,
                    scale_z=0.35,
                    anchor_index=168,
                ),
                AccessoryModel(
                    uuid="glasses2-default",
                    name="Wooden Sunglasses",
                    description="Eco-friendly wooden sunglasses with UV protection",
                    filename="wooden_sunglasses.glb",
                    original_filename="wooden_sunglasses.glb",
                    file_size=get_file_size(UPLOAD_FOLDER / "wooden_sunglasses.glb"),
                    file_type=".glb",
                    thumbnail_path="thumbnails/wooden_sunglasses.png",
                    category_id=glasses_category.id,
                    position_x=0.0,
                    position_y=-0.05,
                    position_z=0.0,
                    rotation_x=5.0,
                    rotation_y=0.0,
                    rotation_z=0.0,
                    scale_x=0.23,
                    scale_y=0.23,
                    scale_z=0.23,
                    anchor_index=168,
                ),
            ]

            for model in default_models:
                session.add(model)

            session.commit()
            logger.info(f"Added {len(default_models)} default models")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Virtual Try-On AR Application...")
    await init_db()
    yield
    # Shutdown
    logger.info("Shutting down...")


# FastAPI app
app = FastAPI(
    title="Code rex Virtual Try-On AR API",
    description="Advanced AR face tracking API with 3D model management",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory=STATIC_FOLDER), name="static")
app.mount("/models", StaticFiles(directory=UPLOAD_FOLDER), name="models")
templates = Jinja2Templates(directory=TEMPLATES_FOLDER)
