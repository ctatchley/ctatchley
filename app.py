from hashlib import sha256
from io import BytesIO
from pathlib import Path
from secrets import token_urlsafe
from sqlite3 import Row, connect
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "recipes.db"
UPLOAD_DIR = BASE_DIR / "uploads"
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_DIMENSION = 2400
VISITOR_COOKIE = "recipe_visitor_id"
VISITOR_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
CATEGORY_OPTIONS = [
    "appetizer",
    "breakfast",
    "brunch",
    "lunch",
    "dinner",
    "dessert",
    "drink",
    "snack",
    "soup",
    "salad",
    "side dish",
    "vegetarian",
]
UPLOAD_DIR.mkdir(exist_ok=True)
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_DIMENSION * MAX_IMAGE_DIMENSION * 2

app = FastAPI(title="Recipe Sharing Platform")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def db():
    connection = connect(DB_PATH)
    connection.row_factory = Row
    return connection


def init_db():
    UPLOAD_DIR.mkdir(exist_ok=True)
    with db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                ingredients TEXT NOT NULL,
                instructions TEXT NOT NULL,
                image_path TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                visitor_hash TEXT,
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
            )
            """
        )
        rating_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(ratings)").fetchall()
        }
        if "visitor_hash" not in rating_columns:
            connection.execute("ALTER TABLE ratings ADD COLUMN visitor_hash TEXT")
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_ratings_recipe_visitor
            ON ratings(recipe_id, visitor_hash)
            """
        )


def recipe_from_row(row: Row):
    rating_count = row["rating_count"] or 0
    rating_average = row["rating_average"]
    return {
        "id": row["id"],
        "title": row["title"],
        "category": row["category"],
        "ingredients": row["ingredients"],
        "instructions": row["instructions"],
        "image_url": f"/{row['image_path']}" if row["image_path"] else None,
        "created_at": row["created_at"],
        "rating_count": rating_count,
        "rating_average": round(rating_average, 1) if rating_average else None,
    }


def visitor_hash_for(request: Request, response: Response):
    visitor_id = request.cookies.get(VISITOR_COOKIE)
    if not visitor_id or len(visitor_id) > 128:
        visitor_id = token_urlsafe(32)
        response.set_cookie(
            VISITOR_COOKIE,
            visitor_id,
            max_age=VISITOR_COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
        )
    return sha256(visitor_id.encode("utf-8")).hexdigest()


async def save_verified_image(image: UploadFile):
    contents = await image.read(MAX_IMAGE_BYTES + 1)
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Image uploads must be 5 MB or smaller.")

    try:
        probe = Image.open(BytesIO(contents))
        probe.verify()

        decoded = Image.open(BytesIO(contents))
        if decoded.format not in ALLOWED_IMAGE_FORMATS:
            raise HTTPException(status_code=400, detail="Please upload a JPG, PNG, WEBP, or GIF image.")

        decoded = ImageOps.exif_transpose(decoded)
        decoded.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
        if decoded.mode not in {"RGB", "RGBA"}:
            decoded = decoded.convert("RGB")

        image_name = f"{uuid4().hex}.webp"
        image_file = UPLOAD_DIR / image_name
        decoded.save(image_file, "WEBP", quality=85, method=6)
    except HTTPException:
        raise
    except (OSError, Image.DecompressionBombError, UnidentifiedImageError):
        raise HTTPException(status_code=400, detail="Uploaded file could not be verified as an image.")

    return f"uploads/{image_name}"


@app.on_event("startup")
def on_startup():
    init_db()


app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/submit")
def submit_page():
    return FileResponse(BASE_DIR / "submit.html")


@app.get("/submit.html")
def submit_html():
    return FileResponse(BASE_DIR / "submit.html")


@app.get("/style.css")
def stylesheet():
    return FileResponse(BASE_DIR / "style.css")


@app.get("/script.js")
def script():
    return FileResponse(BASE_DIR / "script.js")


@app.get("/api/recipes")
def list_recipes(category: str | None = None, search: str | None = None):
    clauses = []
    values = []

    if category:
        clauses.append("LOWER(recipes.category) = LOWER(?)")
        values.append(category)

    if search:
        clauses.append(
            """(
                LOWER(recipes.title) LIKE LOWER(?)
                OR LOWER(recipes.category) LIKE LOWER(?)
                OR LOWER(recipes.ingredients) LIKE LOWER(?)
                OR LOWER(recipes.instructions) LIKE LOWER(?)
            )"""
        )
        term = f"%{search}%"
        values.extend([term, term, term, term])

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT recipes.*,
               COUNT(ratings.id) AS rating_count,
               AVG(ratings.rating) AS rating_average
        FROM recipes
        LEFT JOIN ratings ON ratings.recipe_id = recipes.id
        {where}
        GROUP BY recipes.id
        ORDER BY recipes.created_at DESC
    """

    with db() as connection:
        rows = connection.execute(query, values).fetchall()
    return [recipe_from_row(row) for row in rows]


@app.get("/api/categories")
def list_categories():
    return CATEGORY_OPTIONS


@app.post("/api/recipes")
async def create_recipe(
    title: Annotated[str, Form()],
    category: Annotated[str, Form()],
    ingredients: Annotated[str, Form()],
    instructions: Annotated[str, Form()],
    image: Annotated[UploadFile | None, File()] = None,
):
    cleaned = {
        "title": title.strip(),
        "category": category.strip().lower(),
        "ingredients": ingredients.strip(),
        "instructions": instructions.strip(),
    }

    if not all(cleaned.values()):
        raise HTTPException(status_code=400, detail="All recipe text fields are required.")

    if cleaned["category"] not in CATEGORY_OPTIONS:
        raise HTTPException(status_code=400, detail="Please choose one of the available categories.")

    image_path = None
    if image and image.filename:
        image_path = await save_verified_image(image)

    with db() as connection:
        cursor = connection.execute(
            """
            INSERT INTO recipes (title, category, ingredients, instructions, image_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                cleaned["title"],
                cleaned["category"],
                cleaned["ingredients"],
                cleaned["instructions"],
                image_path,
            ),
        )
        recipe_id = cursor.lastrowid

    return {"id": recipe_id, "message": "Recipe shared."}


@app.post("/api/recipes/{recipe_id}/ratings")
def rate_recipe(recipe_id: int, rating: Annotated[int, Form()], request: Request, response: Response):
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Ratings must be between 1 and 5.")

    visitor_hash = visitor_hash_for(request, response)
    with db() as connection:
        exists = connection.execute("SELECT id FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Recipe not found.")
        connection.execute(
            """
            INSERT INTO ratings (recipe_id, visitor_hash, rating)
            VALUES (?, ?, ?)
            ON CONFLICT(recipe_id, visitor_hash) DO UPDATE SET
                rating = excluded.rating,
                created_at = CURRENT_TIMESTAMP
            """,
            (recipe_id, visitor_hash, rating),
        )

    return {"message": "Rating saved."}
