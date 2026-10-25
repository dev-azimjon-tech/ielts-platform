# IELTS Platform

An affordable IELTS preparation platform for students from our hometown and other learners who cannot afford expensive test-preparation services.

The platform will provide realistic practice tests for all four IELTS skills, track each learner's progress, and offer a low-cost premium plan after the free practice allowance has been used.

## Current status

The first working slice is now available:

- Registration and login pages
- SQLite user database
- Secure password hashing
- Logout and protected dashboard route
- Student dashboard showing completed mocks, averages, recent results, and remaining allowance
- 10 original full Reading mocks with automatic scoring
- 10 original full Listening mocks with browser-based demo audio and automatic scoring
- Separate passage/section screens with Previous and Next navigation
- A 20-second Listening reading countdown before each section's audio starts
- Protected admin panel for managing mock content and premium access
- AI Speaking practice with microphone recording, transcription, examiner questions, and feedback
- AI Writing practice with IELTS-style band estimates and criterion-by-criterion feedback
- 10 Speaking and 10 Writing AI mocks, with 2 free mocks and 10 premium mocks per skill

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
- 2 Speaking AI mocks
- 2 Writing AI checkers

The platform should show the user's remaining attempts and stop new attempts when a limit is reached.

### Premium plan

After reaching the free limits, users can purchase premium access for **$5**. Premium users can complete up to 10 Speaking AI mocks and 10 Writing AI checkers. Reading and Listening premium access currently bypasses their free attempt limit.

Payment processing is not implemented yet. A payment provider such as Stripe can be added after the core practice and account features are working.

### Other planned functionality

- User registration, login, and logout
- Personal dashboard with progress and remaining attempts
- Reading questions with automatic scoring
- Listening audio, questions, and automatic scoring
- AI Speaking examiner that asks IELTS-style Part 1, Part 2, and Part 3 questions
- AI transcription and structured Speaking feedback
- AI Writing checker for Task 2 essays
- Admin tools for adding and managing mock tests
- Basic results history and score tracking

## Technology stack

- **Backend:** Python and Flask
- **Frontend:** HTML, CSS, and Jinja templates
- **Database:** SQLite for development and the first release
- **Database access:** Python's built-in `sqlite3` module
- **Authentication:** Flask-Login and Werkzeug password hashing
- **AI:** Local Ollama model for text feedback and local faster-whisper model for Speaking transcription
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
ollama
faster-whisper
pytest
```

### 4. Configure environment variables

Create a local `.env` file in the project root. Do not commit this file or put real secrets in the repository.

```dotenv
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=replace-this-with-a-long-random-value
DATABASE_PATH=instance/ielts_platform.sqlite3
OLLAMA_HOST=http://localhost:11434
OLLAMA_TEXT_MODEL=llama3.2:3b
WHISPER_MODEL=base.en
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

AI runs locally and does not require an API key. Ollama must be running on the same machine as Flask, and faster-whisper downloads its selected transcription model the first time it is used. For production, use a strong secret key and make sure the server has enough CPU/RAM for both local models.

### 5. Initialize the database

Create the SQLite database and users table with:

```bash
flask --app run.py init-db
```

The database file is created at `instance/ielts_platform.sqlite3` by default. It is ignored by Git. To use another location, set `DATABASE_PATH` in `.env`.

The current startup command also adds the admin column to an older local database automatically.

### 6. Load the demo mocks

Seed 10 original full Reading mocks, 10 original full Listening mocks, 10 Speaking AI mocks, and 10 Writing AI checkers:

```bash
flask --app run.py seed-content
```

The seed command is safe to run again; it will not create duplicate demo mocks.

The Listening mock currently uses the browser's built-in speech synthesis so the feature works without an audio file. Replace it with a professionally recorded MP3 before production.

To seed only the AI content later, run:

```bash
flask --app run.py seed-ai-content
```

### 7. Install and start local AI

Install [Ollama](https://ollama.com/download), then download the default local text model:

```bash
ollama pull llama3.2:3b
ollama serve
```

Leave `ollama serve` running in a separate terminal. The first Speaking submission downloads the `base.en` faster-whisper model automatically. Use `small.en` for better transcription if your computer has more memory, or `tiny.en` for a lighter setup.

### 8. Create the first admin account

Run this command after initializing the database. It asks for the admin's name, email, and password without putting the password in shell history:

```bash
flask --app run.py create-admin
```

If the email already belongs to a student account, the command promotes that account to admin and updates its password. Sign in normally, then open <http://127.0.0.1:5000/admin>.

For this local demo, the administrator account is also available from the main menu through **Log in as admin** with username `admin` and password `admin123`. Change these credentials before deploying publicly.

### 9. Run the development server

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
│   ├── admin/               # Protected admin dashboard and content tools
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

- **User:** account information, password hash, premium status, and admin status
- **MockTest:** skill type, title, instructions, and published status
- **Question:** question content, answer options, correct answer, and score value
- **Attempt:** user, mock test, submitted answers, score, and completion time
- **AIMock:** Speaking or Writing task prompt and AI practice configuration
- **AIAttempt:** transcript or essay, AI feedback JSON, estimated band score, and completion time
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

## What the admin can do

The admin panel is available only to users with the admin flag. The first admin is created with the `create-admin` command above, and regular students cannot open admin routes.

From `/admin`, an admin can:

- See an overview of registered users, premium users, published mocks, and completed attempts.
- Create Reading or Listening mock drafts and edit their title, description, and time limit.
- Add separate Reading passages or Listening sections and edit their text.
- Add and edit multiple-choice, True/False/Not Given, and short-answer questions with options, correct answers, and explanations.
- Review question counts, delete questions, and publish a mock only after it contains content and questions.
- Move a published mock back to draft while it is being edited.
- View student accounts and give or remove the `$5` premium access flag after payment is confirmed.
- Review recent users and completed mock attempts without seeing student passwords.

The current panel intentionally does not process payments. A payment provider should update the premium flag only after a verified payment webhook in production.

## Roadmap

1. Create the Flask application and base templates.
2. Add the SQLite database, models, and migrations.
3. Implement registration, login, and the student dashboard.
4. Improve AI Speaking pronunciation analysis with a voice-capable evaluation flow.
5. Add attempt-limit enforcement and premium access rules for all skills.
6. Replace demo speech synthesis with protected recorded audio files.
7. Integrate and test a secure payment provider.
8. Deploy the application with PostgreSQL and production configuration.

## License

No license has been selected yet. Add a license before accepting outside contributions or distributing the platform publicly.
