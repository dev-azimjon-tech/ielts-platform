# IELTS Platform

An affordable IELTS preparation platform for students from our hometown and other learners who cannot afford expensive test-preparation services.

The platform will provide realistic practice tests for all four IELTS skills, track each learner's progress, and offer a low-cost premium plan after the free practice allowance has been used.

## Current status

The first working slice is now available:

- Registration and login pages
- SQLite user database
- Secure password hashing
- Logout and protected dashboard route
- Basic student dashboard showing the planned free allowance
- 10 original full Reading mocks with automatic scoring
- 10 original full Listening mocks with browser-based demo audio and automatic scoring
- Separate passage/section screens with Previous and Next navigation
- A 20-second Listening reading countdown before each section's audio starts

## Project goals

- Make structured IELTS practice accessible at a much lower price than existing platforms.
- Give students one place to practice Reading, Listening, Speaking, and Writing.
- Track completed mocks and prevent users from exceeding the free usage limits.
- Keep the first version simple to run, maintain, and deploy.

## Planned features

### Free practice allowance

Each registered user can complete:

- 10 Reading mock tests
- 10 Listening mock tests
- 5 Speaking mock tests
- 5 Writing mock tests

The platform should show the user's remaining attempts and stop new attempts when a limit is reached.

### Premium plan

After reaching the free limits, users can purchase premium access for **$5**. Premium access is intended to unlock additional or unlimited practice, depending on the final product rules.

Payment processing is not implemented yet. A payment provider such as Stripe can be added after the core practice and account features are working.

### Other planned functionality

- User registration, login, and logout
- Personal dashboard with progress and remaining attempts
- Reading questions with automatic scoring
- Listening audio, questions, and automatic scoring
- Speaking prompts with a place to submit answers or recordings
- Writing prompts with a place to submit essays
- Admin tools for adding and managing mock tests
- Basic results history and score tracking

## Technology stack

- **Backend:** Python and Flask
- **Frontend:** HTML, CSS, and Jinja templates
- **Database:** SQLite for development and the first release
- **Database access:** Python's built-in `sqlite3` module
- **Authentication:** Flask-Login and Werkzeug password hashing
- **Configuration:** Environment variables loaded with `python-dotenv`

SQLite is the initial database because it requires no separate database server and is easy to use locally. When the platform grows, the application can move to PostgreSQL with a database URL change and migrations.

## Requirements

- Python 3.10 or newer
- `pip`
- `venv` (included with standard Python installations)
- Git

## Installation

The commands below run the current Flask application locally.

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/ielts-platform.git
cd ielts-platform
```

Replace `YOUR_USERNAME` with the GitHub account or organization that owns the repository.

### 2. Create and activate a virtual environment

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

Install the project dependencies with:

```bash
pip install -r requirements.txt
```

The current dependency file contains:

```text
Flask
Flask-Login
python-dotenv
pytest
```

### 4. Configure environment variables

Create a local `.env` file in the project root. Do not commit this file or put real secrets in the repository.

```dotenv
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=replace-this-with-a-long-random-value
DATABASE_URL=sqlite:///ielts_platform.db
```

For production, use a strong secret key and a production database URL. If payments are added, payment-provider keys must also be stored in environment variables.

### 5. Initialize the database

Create the SQLite database and users table with:

```bash
flask --app run.py init-db
```

The database file is created at `instance/ielts_platform.sqlite3` by default. It is ignored by Git. To use another location, set `DATABASE_PATH` in `.env`.

Database migrations can be added later if the schema becomes more complex.

### 6. Load the demo mocks

Seed 10 original full Reading mocks and 10 original full Listening mocks:

```bash
flask --app run.py seed-content
```

The seed command is safe to run again; it will not create duplicate demo mocks.

The Listening mock currently uses the browser's built-in speech synthesis so the feature works without an audio file. Replace it with a professionally recorded MP3 before production.

### 7. Run the development server

```bash
flask --app run.py run --debug
```

Open <http://127.0.0.1:5000> in a browser.

The equivalent command, if `run.py` is provided, is:

```bash
python run.py
```

## Suggested project structure

```text
ielts-platform/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models.py            # Users, tests, questions, attempts, payments
│   ├── auth/                # Registration and login routes
│   ├── main/                # Dashboard and public pages
│   ├── tests/               # Reading, Listening, Speaking, and Writing routes
│   ├── templates/           # Jinja HTML templates
│   └── static/
│       ├── css/
│       └── js/
├── migrations/              # Database migrations
├── tests/                   # Automated tests
├── .env.example
├── requirements.txt
├── run.py
└── README.md
```

## Core data model

The first version will likely need these entities:

- **User:** account information, password hash, and premium status
- **MockTest:** skill type, title, instructions, and published status
- **Question:** question content, answer options, correct answer, and score value
- **Attempt:** user, mock test, submitted answers, score, and completion time
- **Payment:** user, amount, provider reference, status, and purchase time

Usage limits should be calculated from completed attempts for each skill. Premium status should be checked before enforcing free limits.

## Development workflow

1. Create a feature branch.
2. Add or update tests for the feature.
3. Run the test suite before opening a pull request.
4. Keep secrets in `.env`, never in committed source files.
5. Use database migrations when changing models.

When tests are available, run them with:

```bash
pytest
```

## Roadmap

1. Create the Flask application and base templates.
2. Add the SQLite database, models, and migrations.
3. Implement registration, login, and the student dashboard.
4. Add an admin content-management interface for creating more Reading and Listening mocks.
5. Add Speaking and Writing prompts and submission history.
6. Add attempt-limit enforcement and premium access rules for all skills.
7. Replace demo speech synthesis with protected recorded audio files.
8. Integrate and test a secure payment provider.
9. Deploy the application with PostgreSQL and production configuration.

## License

No license has been selected yet. Add a license before accepting outside contributions or distributing the platform publicly.
