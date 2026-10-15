# Vacation Rental – GeoDjango + PostGIS + pgvector

A vacation rental search application built with Django. It combines **spatial search** (PostGIS) and **AI semantic search** (Sentence Transformers + pgvector).

## Features

- Homepage with a debounced autocomplete search box
- Semantic suggestions for **Locations** and **Properties**, clearly labelled by type
- Same-name properties in different locations are kept as separate records and shown with their location
- Property listing page with pagination (search query and type are preserved)
- Property detail page: image gallery, amenities, distance from city centre (km), nearby properties (PostGIS `DWithin`)
- Django Admin with custom filters, inline image upload and image previews
- Bulk data import from CSV / Excel / Parquet with Pandas (including images from public URLs)
- Django REST Framework autocomplete API with serializer validation
- HNSW indexes (cosine distance) on Location and Property embeddings

## Tech Stack

| Area | Technology |
|---|---|
| Backend | Django, GeoDjango, Django REST Framework |
| Database | PostgreSQL 17, PostGIS, pgvector (Docker) |
| AI model | `all-MiniLM-L6-v2` (Sentence Transformers, 384 dimensions) |
| Data import | Pandas |

## Requirements

- Linux (tested on Ubuntu)
- Docker and Docker Compose
- Python 3.10+
- Internet connection on first run (downloads the ~90 MB embedding model and the property images)

## Setup

### 1. System packages (Ubuntu / Debian)

```bash
sudo apt update
sudo apt install -y gdal-bin libgdal-dev libgeos-dev libproj-dev python3-venv python3-dev libpq-dev
```

### 2. Start the database

```bash
git clone https://github.com/mahfujalam77452/vacation_rental
cd vacation_rental
docker compose up -d --build
docker compose ps
```

This starts PostgreSQL 17 with the PostGIS and pgvector extensions.

| Setting | Value |
|---|---|
| Container | `rental_db` |
| Database | `propertydb` |
| User / Password | `postgres` / `postgres` |
| Host / Port | `localhost` / `5432` |

Data is kept in the `pgdata` Docker volume. `init.sql` enables the extensions on first start. If the volume already existed, enable them manually:

```bash
docker exec -it rental_db psql -U postgres -d propertydb -c "CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS vector;"
```

### 3. Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Create tables and the admin user

```bash
python manage.py migrate
DJANGO_SUPERUSER_PASSWORD=admin1234 python manage.py createsuperuser --noinput --username admin --email admin@example.com
```

This creates the admin account used to log in at `/admin/`:

| Username | Password |
|---|---|
| `admin` | `admin1234` |

(These are demo credentials for evaluation only. If the user already exists, the command reports that the username is taken, which is harmless. To choose your own credentials instead, run `python manage.py createsuperuser`.)

### 5. Import the data

```bash
python manage.py import_properties
```

This reads `data/properties.csv` and creates the Locations, Properties and their images. Embeddings are generated automatically while saving (the first run downloads the embedding model). Property photos are public Unsplash images (3–5 per property, 33 distinct files) that are downloaded once and reused, so this takes about a minute.

Expected output:

```
68 valid row found !
End : 8 location, 68 new property, 0 updated, 268 images
```

Running the command again does not create duplicates (records are matched by location + title, and properties that already have images are skipped).

If any record is missing an embedding, generate them with:

```bash
python manage.py generate_embeddings          # only records without an embedding
```

### 6. Run the server

```bash
python manage.py runserver
```

| Page | URL |
|---|---|
| Homepage / search | http://127.0.0.1:8000/ |
| Search results | http://127.0.0.1:8000/search/ |
| Property detail | `http://127.0.0.1:8000/property/<slug>/` |
| Autocomplete API | http://127.0.0.1:8000/api/autocomplete/?q=floral |
| Admin | http://127.0.0.1:8000/admin/ |

## Tests

The test database needs the `vector` extension. Run this once:

```bash
docker exec -it rental_db psql -U postgres -d template1 -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Then:

```bash
python manage.py test property_app
```

The tests cover the autocomplete API (empty, short, too long and unmatched queries, response structure), duplicate property names, slug uniqueness, embedding creation/update, listing and pagination, the detail page, distance fallback and the `DWithin` nearby query.

## Try it out

After the server is running, open http://127.0.0.1:8000/ and try the searches below. Type slowly or pause after typing, because suggestions appear 300 ms after you stop typing. Each suggestion has a **Location** (green) or **Property** (blue) badge.

### Location search

| Type this | What you should see |
|---|---|
| `Destin` | Location *Destin, Florida*. Click it to list its 7 properties. |
| `Florida` | Florida locations: Miami, Orlando, Key West, Destin |
| `Floridiya` (misspelled) | Florida locations, found by semantic similarity rather than exact text |
| `Cox` | Location *Cox's Bazar* (8 properties) |
| `Sylhet` | Location *Sylhet* (9 properties) |
| `Gatlinburg` | Location *Gatlinburg, Tennessee* (10 properties) |

### Property search (same name in several locations)

| Type this | What you should see |
|---|---|
| `Floral` | *Floral Beach House* three times, each with its own location: Orlando, Miami, Sylhet |
| `Sunset` | *Sunset Beach House* in Miami, Cox's Bazar and Gatlinburg |
| `Cozy` | *Cozy Family Retreat* in Miami, Key West and Gatlinburg |
| `Lakeview` | *Lakeview Cottage* in Orlando, Sylhet and Gatlinburg |
| `Palm Breeze` | *Palm Breeze Apartment* in Miami, Key West and Cancun |

Click any one of them: the results page lists **all three** properties with that name, and the one you clicked is shown first.

### Other property names

| Type this | What you should see |
|---|---|
| `King` | *King's Castle Luxury Beach Escape* (Destin), a unique name, so one result |
| `Smoky` | *Smoky Mountain Cabin* (Gatlinburg) |
| `Brickell` | *Brickell Skyline Loft* (Miami) |
| `Laboni` | *Laboni Point Sea View Suite* (Cox's Bazar) |
| `Jaflong` | *Jaflong Hill View Cottage* (Sylhet) |

### Meaning-based (semantic) searches

These words do not have to appear in the name. Results depend on the model, so they should be related but are not guaranteed to be identical to the list.

| Type this | Expect (roughly) |
|---|---|
| `mountain` | Gatlinburg and the Smoky Mountain cabin |
| `cabin` | Cabin and lodge style properties |
| `villa` | Villa properties (e.g. *Playa Delfines Villa*, *Biscayne Bay Villa*) |
| `lake` | Lake-related names such as *Lake Buena Vista Resort Villa* |

### Pagination

Type `beach` and press the **Search** button without choosing a suggestion. There are more than 6 results, so Next/Previous buttons appear. Go to page 2 and check that the search box still contains your query.

### Invalid input

| Type this | What you should see |
|---|---|
| `a` (one character) | No suggestions |
| `!!` then Search | A validation error message, no results |
| `xqzwvk` then Search | A "no properties found" message |

### Detail page

Open any property, for example *Sunset Beach House* in Miami. Check the image gallery (click thumbnails), amenities, the distance from the city centre in km, and the **nearby properties** section at the bottom.

### API check

```bash
curl "http://127.0.0.1:8000/api/autocomplete/?q=Floral"
curl "http://127.0.0.1:8000/api/autocomplete/?q=a"
```

The first returns the three *Floral Beach House* results with locations. The second returns HTTP 400 with a validation message.

## How the search works

1. The user types in the search box. After 300 ms of inactivity, one request goes to the autocomplete API (debouncing; older in-flight requests are cancelled).
2. The API returns Location and Property suggestions. Partial text matches come first, then semantic matches ranked by cosine distance (pgvector).
3. Selecting a suggestion decides the search behaviour:
   - **Location** → all properties in that location
   - **Property** → all properties with that name (any location); the selected one is listed first
   - **No selection** (pressing Search) → text match combined with semantic match

### API example

```
GET /api/autocomplete/?q=Floral
```

```json
{
  "results": [
    {"type": "property", "id": 25, "name": "Floral Beach House", "location": "Miami, Florida"},
    {"type": "property", "id": 31, "name": "Floral Beach House", "location": "Orlando, Florida"}
  ]
}
```

Validation errors (query missing, shorter than 2 characters, longer than 100 characters) return HTTP `400` with an error message. When nothing matches, `results` is an empty list.

## Data model

- **Location**: name, slug, country, state, city, address, `point` (geography), `boundary` (multipolygon), `embedding` (vector 384), is_active, timestamps
- **Property**: location (FK), title, slug (unique), description, property_type, status, price, bedrooms, bathrooms, area_sqft, address, `point`, `footprint`, `embedding` (vector 384), is_featured, is_active, timestamps
- **PropertyImage**: property (FK), image, alt_text, caption, width, height, file_size, is_primary, sort_order, created_at

Notes:

- `title` is not unique. `slug` is unique and is generated from title + location, so identical titles in different locations (or the same location) get different slugs.
- The assignment's model PDF uses 1536 dimensions for Location/Property embeddings, but `all-MiniLM-L6-v2` produces **384**-dimensional vectors, so the fields use 384.
- `PropertyImage.embedding` is intentionally not included, because image similarity search is out of scope.
- HNSW indexes (`vector_cosine_ops`, `m=16`, `ef_construction=64`) exist on both Location and Property embeddings.

## CSV format (`data/properties.csv`)

| Column | Required | Notes |
|---|---|---|
| `location_name`, `country`, `city`, `title`, `property_type`, `price` | Yes | Rows with a missing/invalid price, title or location are skipped |
| `state`, `status`, `description`, `address` | No | Amenities are written inside `description` as `Amenities: a, b, c.` |
| `bedrooms`, `bathrooms`, `area_sqft` | No | |
| `lat`, `lng` | No | Property coordinates |
| `location_lat`, `location_lng` | No | City-centre coordinates |
| `is_featured` | No | `True` / `False` |
| `image_urls` | No | Public image URLs separated by `\|`; the first one becomes the primary image |

## Admin

Log in at http://127.0.0.1:8000/admin/ with **username `admin`** and **password `admin1234`** (created in step 4):

- Location, Property and PropertyImage are registered
- Custom filters on Property: **Price range** and **Image status**, plus built-in filters (type, status, country, location, featured, active)
- Images can be uploaded inline on the Property page, with previews
- Thumbnails are shown in the Property list

## Troubleshooting

| Problem | Fix |
|---|---|
| `connection refused` | Check that the container is running: `docker compose ps` |
| `type "vector" does not exist` | Enable the extension (see step 2) and run `migrate` again |
| `GDAL library not found` | Install the system packages from step 1 |
| Image download failures during import | Check the internet connection and re-run `import_properties`; properties without images are retried |
| Slow first search / HF Hub warning | The embedding model loads on first use; the "unauthenticated request" warning is harmless |

## Project structure

```
vacation_rental/
├── config/                  # Django settings and root URLs
├── property_app/
│   ├── models.py            # Location, Property, PropertyImage
│   ├── admin.py             # Admin configuration
│   ├── forms.py             # Search form with custom validation
│   ├── serializers.py       # DRF serializers
│   ├── views.py             # Pages and autocomplete API
│   ├── search.py            # Semantic (pgvector) search functions
│   ├── embeddings.py        # Sentence Transformers service
│   ├── signals.py           # Automatic embedding on save
│   ├── management/commands/ # import_properties, generate_embeddings
│   ├── templates/
│   └── tests.py
├── data/properties.csv
├── Dockerfile
├── docker-compose.yml
├── init.sql
└── requirements.txt
```