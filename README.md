# Recipe Sharing Platform

A small FastAPI and SQLite recipe sharing website. Visitors can browse recipes, search by recipe text, filter by category, submit new recipes, upload optional recipe photos, and rate recipes.

## Requirements

- Python 3.12 or newer
- A terminal or command prompt

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Install the Python dependencies:

```bash
python -m pip install fastapi uvicorn python-multipart Pillow
```

## Run the Website

Start the FastAPI server:

```bash
python -m uvicorn app:app --reload
```

Open the site in a browser:

```text
http://127.0.0.1:8000/
```

The submit page is available at:

```text
http://127.0.0.1:8000/submit
```

## Generated Files

The app creates runtime files as needed:

- `recipes.db` stores recipes and ratings in SQLite.
- `uploads/` stores uploaded recipe images.

Uploaded images are optional. When an image is uploaded, the app limits it to 5 MB, verifies it with Pillow, accepts JPG/PNG/WEBP/GIF sources, and saves a normalized generated image file in `uploads/`.

## Rating Behavior

The app uses an anonymous browser cookie to identify visitors for ratings. SQLite stores only a hash of that visitor ID. Each visitor can have one active rating per recipe; rating again updates the previous rating.

## Project Files

- `app.py` - FastAPI backend, SQLite setup, upload validation, and API routes
- `index.html` - recipe browse page
- `submit.html` - recipe submission page
- `style.css` - shared styling
- `script.js` - browser-side form, search, filter, and rating behavior
- `prompt.md` - project specification
