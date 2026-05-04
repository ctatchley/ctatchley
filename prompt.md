# Recipe Sharing Platform

# Tech Stack
- Python 3.12
	-Use FastAPI for python, and run with uvicorn
	-Use Pillow to verify and normalize uploaded images
- SQLite

## What is this?
A website that allows visitors to post and browse recipes.

## Features
- Basic Features: Submit/view recipes, category filtering, image uploads.

- Enhanced Features: Rating system, search by recipe text.

## Upload Safety
- Uploaded images are optional.
- Limit image uploads to 5 MB.
- Accept only JPG, PNG, WEBP, and GIF image sources.
- Verify uploaded images with Pillow before saving.
- Normalize saved uploads to generated WEBP files inside `uploads/`.

## Rating Rules
- Identify visitors with a long-lived anonymous browser cookie.
- Store only a hash of the visitor identifier in SQLite.
- Allow one active rating per visitor per recipe; submitting again updates the visitor's previous rating.

## File Architecture
./
	index.html
	submit.html
	style.css
	script.js
	app.py
	uploads/
