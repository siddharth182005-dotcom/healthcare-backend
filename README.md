# Healthcare Backend (Django + DRF + PostgreSQL + JWT)

A secure REST API for a healthcare application, built for the **Whatbytes Full-Stack Developer Internship** assignment. Users register and log in, manage their own **patients**, maintain a shared **doctor** directory, and **assign doctors to patients**.

## Features

- Email-based custom user model, passwords hashed with Django's PBKDF2-SHA256
- JWT authentication (`djangorestframework-simplejwt`): access + refresh tokens
- Patient CRUD, strictly scoped to the user who created each patient
- Doctor CRUD (any authenticated user can read; only the creator can edit/delete)
- Patient-doctor mappings with a database-level uniqueness constraint
- Validation and consistent JSON errors (400 / 401 / 403 / 404 / 409)
- Secrets and DB credentials in environment variables
- 70 automated tests, Postman collection, optional Swagger UI

## Technology stack

Python 3.12 · Django 5.2 · Django REST Framework 3.16 · djangorestframework-simplejwt 5.5 · PostgreSQL · psycopg2 · python-dotenv · drf-spectacular (OpenAPI docs)

## Architecture and design decisions

| App | Responsibility |
|---|---|
| `config/` | Settings, root URLs, JSON error handler |
| `accounts/` | Custom `User` model, register, login (JWT), token refresh |
| `patients/` | `Patient` model + CRUD, owner-only access |
| `doctors/` | `Doctor` model + CRUD, creator-only writes |
| `mappings/` | `PatientDoctorMapping` model + assignment endpoints |
| `tests/` | All automated tests |

**Authorization policy**

| Resource | Read | Create | Update / Delete |
|---|---|---|---|
| Patient | Owner only | Any authenticated user (becomes owner) | Owner only |
| Doctor | Any authenticated user | Any authenticated user (becomes creator) | Creator only (others get `403`) |
| Mapping | Owner of the patient only | Owner of the patient only | Owner of the patient only |

- Other users' patients and mappings return **404** (their existence is never revealed). Doctors are a shared directory, so a non-creator editing one gets **403**.
- Ownership is enforced in the **queryset** (`filter(owner=request.user)`) and again with an **object-level permission** (`IsOwner`).
- A doctor who is still assigned to patients cannot be deleted (`409`); remove the mappings first. Deleting a patient removes its mappings.
- Doctor emails are unique case-insensitively (database index on `lower(email)`). The `(patient, doctor)` pair is unique at the database level and is also validated in the serializer.
- Mapping responses contain only the patient's **id** and the doctor's details, never patient data.

## Project structure

```
healthcare-backend/
├── config/            settings.py, urls.py, exceptions.py, views.py, wsgi/asgi
├── accounts/          models, serializers, views, urls, admin, migrations
├── patients/          models, serializers, views, permissions, urls, migrations
├── doctors/           models, serializers, views, permissions, urls, migrations
├── mappings/          models, serializers, views, urls, migrations
├── tests/             base.py, test_auth.py, test_patients.py, test_doctors.py, test_mappings.py
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── postman_collection.json
└── README.md
```

## Prerequisites

1. **Python 3.11+** (https://www.python.org/downloads/). During install tick **"Add python.exe to PATH"**.
2. **PostgreSQL 14+** (https://www.postgresql.org/download/windows/). Remember the password you set for the `postgres` superuser.
3. **Git** (https://git-scm.com/download/win)
4. **VS Code** and **Postman**

Check in PowerShell:

```powershell
python --version
git --version
```

## Installation (Windows PowerShell)

```powershell
# 1. Go to the project folder
cd path\to\healthcare-backend

# 2. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If activation fails with "running scripts is disabled", run this once and retry:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

```powershell
# 3. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Create the PostgreSQL database

Open PowerShell and start `psql` as the `postgres` superuser (adjust `16` to your installed version):

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres
```

Enter the superuser password, then run (choose **your own** password; never reuse a real one from elsewhere):

```sql
CREATE USER healthcare_user WITH PASSWORD 'choose-a-strong-password' CREATEDB;
CREATE DATABASE healthcare_db OWNER healthcare_user;
\q
```

`CREATEDB` lets Django create a temporary `test_healthcare_db` when you run the tests, so tests never touch your real data.

## Configure environment variables

```powershell
Copy-Item .env.example .env
```

Generate a secret key and paste it into `.env`:

```powershell
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

Edit `.env` in VS Code:

```ini
DJANGO_SECRET_KEY=<the generated key>
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=healthcare_db
DB_USER=healthcare_user
DB_PASSWORD=<the password you chose above>
DB_HOST=localhost
DB_PORT=5432
```

`.env` is git-ignored and must never be committed. For any real deployment set `DJANGO_DEBUG=False`, a strong key, the real hostnames, and `DJANGO_HTTPS=True` behind HTTPS.

## Run migrations and start the server

```powershell
python manage.py migrate
python manage.py runserver
```

The API is now at `http://127.0.0.1:8000/`. Swagger UI: `http://127.0.0.1:8000/api/docs/` (schema at `/api/schema/`).

Optional admin user: `python manage.py createsuperuser` (then visit `/admin/`).

## API reference

All request/response bodies are JSON. Protected endpoints need the header `Authorization: Bearer <access_token>`.

| Method | Endpoint | Auth | Success | Description |
|---|---|---|---|---|
| POST | `/api/auth/register/` | No | 201 | Register (name, email, password) |
| POST | `/api/auth/login/` | No | 200 | Returns `access` and `refresh` JWT |
| POST | `/api/auth/token/refresh/` | No | 200 | New access token from refresh token (extra) |
| POST | `/api/patients/` | Yes | 201 | Create patient (owned by you) |
| GET | `/api/patients/` | Yes | 200 | List **your** patients |
| GET | `/api/patients/<id>/` | Yes | 200 | Patient details |
| PUT | `/api/patients/<id>/` | Yes | 200 | Update patient (full body) |
| DELETE | `/api/patients/<id>/` | Yes | 204 | Delete patient |
| POST | `/api/doctors/` | Yes | 201 | Create doctor |
| GET | `/api/doctors/` | Yes | 200 | List all doctors |
| GET | `/api/doctors/<id>/` | Yes | 200 | Doctor details |
| PUT | `/api/doctors/<id>/` | Yes | 200 | Update doctor (creator only) |
| DELETE | `/api/doctors/<id>/` | Yes | 204 | Delete doctor (creator only; 409 if still assigned) |
| POST | `/api/mappings/` | Yes | 201 | Assign a doctor to one of your patients |
| GET | `/api/mappings/` | Yes | 200 | All mappings for your patients |
| GET | `/api/mappings/<patient_id>/` | Yes | 200 | Doctors assigned to that patient |
| DELETE | `/api/mappings/<id>/` | Yes | 204 | Remove an assignment (`<id>` = **mapping** id) |

Note: `GET /api/mappings/<n>/` treats `n` as a **patient id**, while `DELETE /api/mappings/<n>/` treats `n` as a **mapping id**, exactly as the assignment specifies. `PATCH` also works on patient/doctor detail URLs.

### Example requests (PowerShell)

Use `curl.exe` (not the `curl` alias):

```powershell
# Register
curl.exe -X POST http://127.0.0.1:8000/api/auth/register/ -H "Content-Type: application/json" -d '{\"name\":\"Alice\",\"email\":\"alice@example.com\",\"password\":\"Str0ng-Pass!word42\"}'

# Login (copy the "access" value)
curl.exe -X POST http://127.0.0.1:8000/api/auth/login/ -H "Content-Type: application/json" -d '{\"email\":\"alice@example.com\",\"password\":\"Str0ng-Pass!word42\"}'

# Create a patient
curl.exe -X POST http://127.0.0.1:8000/api/patients/ -H "Authorization: Bearer <access>" -H "Content-Type: application/json" -d '{\"name\":\"John Doe\",\"age\":35,\"gender\":\"M\"}'
```

Request bodies:

```jsonc
// POST /api/patients/  (name, age, gender required; gender is M, F or O)
{ "name": "John Doe", "age": 35, "gender": "M", "phone": "+1 555 123 4567",
  "address": "12 Main Street", "medical_history": "Seasonal asthma" }

// POST /api/doctors/  (name, specialization, email required)
{ "name": "Meredith Grey", "specialization": "Surgery", "email": "grey@example.com",
  "phone": "+1 555 000 1111", "address": "Seattle Grace Hospital" }

// POST /api/mappings/
{ "patient": 1, "doctor": 1 }
```

Error responses:

| Case | Status | Example body |
|---|---|---|
| Invalid / missing fields | 400 | `{"email": ["Enter a valid email address."]}` |
| Weak password | 400 | `{"password": ["This password is too short..."]}` |
| Duplicate assignment | 400 | `{"non_field_errors": ["This doctor is already assigned to this patient."]}` |
| Wrong credentials | 401 | `{"detail": "No active account found with the given credentials"}` |
| Missing/expired token | 401 | `{"detail": "Authentication credentials were not provided."}` |
| Editing someone else's doctor | 403 | `{"detail": "Only the user who added this doctor can modify or delete it."}` |
| Missing record / not yours | 404 | `{"detail": "No Patient matches the given query."}` |
| Deleting a doctor that is assigned | 409 | `{"detail": "This doctor is assigned to one or more patients. ..."}` |

JWT lifetimes: access 30 minutes, refresh 1 day (configurable via `JWT_ACCESS_MINUTES`, `JWT_REFRESH_DAYS`).

## Testing with Postman

1. Start the server (`python manage.py runserver`).
2. In Postman: **Import** → select `postman_collection.json`.
3. Open the collection → **Run** (Collection Runner) and run everything top to bottom, or send requests one by one in order.

How it works: the collection uses variables (`base_url`, `access_token`, `refresh_token`, `patient_id`, `doctor_id`, `mapping_id`, `user_email`, `user_password`). Test scripts save values automatically: **Login** stores the tokens, **Create patient/doctor/mapping** store their ids. The collection-level Bearer auth uses `{{access_token}}`, so protected requests work without any manual copying. **Register** generates a fresh email each run so the collection can be re-run. Folder 5 contains deliberately invalid requests with their expected status codes. Change `base_url` if you use a different host or port.

## Automated tests

```powershell
python manage.py test
```

Django creates and destroys a separate `test_healthcare_db` database; your real data is never touched. Run one file with `python manage.py test tests.test_auth`.

The tests cover registration (including hashing and duplicates), login, JWT protection (missing, invalid, expired, refresh-as-access), patient CRUD and cross-user isolation, doctor CRUD and ownership, mapping creation, duplicates, listing, removal, invalid references, and status codes.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ImproperlyConfigured: Missing required environment variable` | `.env` is missing or incomplete. Re-run `Copy-Item .env.example .env` and fill in every value. |
| `connection refused` / `could not connect to server` | PostgreSQL is not running. Open **Services**, start `postgresql-x64-16`. Check `DB_HOST`/`DB_PORT`. |
| `password authentication failed for user` | `DB_USER`/`DB_PASSWORD` in `.env` don't match the user you created. |
| `database "healthcare_db" does not exist` | Run the `CREATE DATABASE` command above. |
| `permission denied to create database` (when testing) | Run `ALTER USER healthcare_user CREATEDB;` in psql as `postgres`. |
| `psql` is not recognized | Use the full path shown above or add PostgreSQL's `bin` folder to PATH. |
| `Activate.ps1 cannot be loaded` | Run the `Set-ExecutionPolicy` command in Installation. |
| `ModuleNotFoundError` | The virtual environment is not active, or run `pip install -r requirements.txt`. |
| `401 ... token not valid` | Access token expired (30 min). Log in again or use `/api/auth/token/refresh/`. |
| `Invalid host header` (400) | Add your host to `DJANGO_ALLOWED_HOSTS`. |

## Submitting to GitHub

1. Create an empty repository on https://github.com/new (no README, no .gitignore). Copy its URL.
2. In PowerShell, from the project folder:

```powershell
git init
git branch -M main
git add .
git status
```

3. **Check that `.env` is NOT listed** in `git status` (only `.env.example` should appear). Then:

```powershell
git commit -m "Healthcare backend: Django, DRF, PostgreSQL, JWT"
git remote add origin https://github.com/<your-username>/healthcare-backend.git
git push -u origin main
```

If asked to sign in, use your GitHub login or a Personal Access Token. If git says "Please tell me who you are", run:

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Finally, make the repository public or add the reviewer as a collaborator, then submit the link.
