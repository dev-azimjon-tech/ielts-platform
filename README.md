# IELTS Platform

An affordable IELTS preparation platform for students from our hometown and other learners who cannot afford expensive test-preparation services.

The platform will provide realistic practice tests for all four IELTS skills, track each learner's progress, and offer a low-cost premium plan after the free practice allowance has been used.

## Current status

The first working slice is now available:

- Registration and login pages
- Light and dark modes with a header toggle, device preference detection, and a saved browser preference
- Private vocabulary collections with editable flashcards, shuffled study sessions, and multiple-choice vocabulary quizzes
- A public video guide with an original narrated walkthrough, English captions, chapter navigation, and written instructions
- SQLite user database
- Secure password hashing
- Logout and protected dashboard route
- Student dashboard showing completed mocks, averages, recent results, and remaining allowance
- 10 original full Reading mocks with automatic scoring
- 10 original full Listening mocks with browser-based demo audio and automatic scoring
- Separate passage/section screens with Previous and Next navigation
- A 20-second Listening reading countdown before each section's audio starts
- Free Cambridge sample-paper download and official IELTS full Reading/Listening sample links in the practice library
- Reading and Listening filters and a focused test view with theme and Exit controls in the header
- Side-by-side Reading passages and questions on larger screens
- Question navigation and answered-question progress
- Notes per passage/section, selected-text highlighting, and selection-to-notes tools
- Browser autosave for answers, notes, highlights, and the current section
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

SQLite is the initial database because it requires no separate database server and is easy to use locally. Moving to PostgreSQL would require a database adapter, compatible queries, and schema migrations.

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

### Official Cambridge and IELTS practice

The mock library also includes free official resources verified on 29 October 2026:

- [Cambridge English IELTS preparation](https://www.cambridgeenglish.org/exams-and-tests/ielts/preparation/) and its free sample-paper ZIP download.
- [Official IELTS Academic sample tests](https://ielts.org/take-a-test/preparation-resources/sample-test-questions/academic-test), including the full 40-question Reading and Listening computer samples.

Publisher resources open in a new tab or download from the publisher. They do not consume the platform's free attempts and their results are not imported into the dashboard. Published Cambridge books and tests are not copied into the platform. The resource URLs and source pages are maintained in `app/practice_resources.py`.

During a platform mock, select text in a passage or question and choose **Highlight selection** (or Alt+H). **Add selection to notes** copies it into the current section's notes. Open **Notes** to write reminders or clear the current section's highlights. Answers and study tools save in this browser, separately for each user and mock; they do not sync between devices. Browser storage must be enabled for autosave. Successful submission clears the saved draft for that mock. The Exit button asks for confirmation, and saved work remains available when the user returns.

Use the sun/moon button in the header to switch between light and dark modes, including during a mock. The platform follows your device's color preference until you choose a mode. Your choice is saved in this browser and shared across open platform tabs. If browser storage is disabled, the toggle still works for the current page.

### Vocabulary flashcards

Open **Flashcards** in the navigation after signing in. Save a word or phrase, its meaning or translation, and an optional example sentence. You can edit and delete your cards. Vocabulary is private to each student and saved in the database.

**Study flashcards** presents your words in a shuffled order. Try to recall the meaning, select the card to reveal it, and use Previous, Next, or Shuffle to continue practicing. Study navigation requires JavaScript; the vocabulary collection and quizzes work without it.

Save at least two words with different meanings to unlock **Multiple-choice quiz**. Each quiz selects up to 10 saved words and offers two to four distinct meanings from your own collection as choices. Answers are scored on the server after every question is answered. Results include the correct meanings and your examples, and the three most recent completed quizzes appear in your collection. Each quiz saves a snapshot, so editing or deleting vocabulary does not change an existing quiz or result. Vocabulary practice does not use your mock-test allowance.

For an existing installation, run `flask --app run.py init-db` and restart Flask to enable the new vocabulary tables and routes. Initialization preserves existing accounts, vocabulary, and results.

### User video guide

Choose **Video guide** in the header or **Help & video guide** in the footer, or open `/guide`. The guide is available before and after signing in. Its original illustrated video explains accounts and the dashboard, Reading and Listening mocks, notes and saved work, AI practice, flashcards, and appearance and progress.

The player includes English narration and captions, six selectable chapters, native playback controls, and a download link. Written steps and links to the relevant features remain available without JavaScript or video playback. The video is served by the platform; it does not depend on an external video service.

The guide script is maintained in `app/platform_guide.py`; media, captions, and chapter timings are in `app/static/media/`. `scripts/build_platform_guide.py` rebuilds the illustrations and MP4 from separately narrated WAV segments. Optional build dependencies are Pillow and imageio-ffmpeg; the app needs neither at runtime. To regenerate on macOS, install those tools in your build environment, run `python scripts/build_platform_guide.py --prepare`, synthesize each generated text file with the `say` command documented in that script, then run `python scripts/build_platform_guide.py`. Keep the video, captions, poster, and timing manifest together when deploying.

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

Run the tests through the active Python environment:

```bash
python -m pytest -q
```

The practice libraries fetch attempt counts once per page. Dashboard band averages use grouped database summaries, and history/content indexes keep common lookups efficient. Test JavaScript and CSS are separate static assets that support conditional browser caching. After updating an existing installation, run `flask --app run.py init-db` once to add the new indexes without removing accounts or results.

## What the admin can do

The admin panel is available only to users with the admin flag. The first admin is created with the `create-admin` command above, and regular students cannot open admin routes.

From `/admin`, an admin can:

- Move between Overview, Mock library, and Students & access through shared admin navigation.
- Search users by name or email, filter by role and plan, and browse results in pages of 20.
- Search mock titles, filter by skill and publication status, and continue unfinished drafts from the overview.
- See completed practice across all four skills, AI content availability, and aggregate vocabulary activity.
- Confirm premium-access changes before submitting them; repeated submissions preserve the requested access state.
- See an overview of registered users, premium users, published mocks, and completed attempts.
- Create Reading or Listening mock drafts and edit their title, description, and time limit.
- Add separate Reading passages or Listening sections and edit their text.
- Add and edit multiple-choice, True/False/Not Given, and short-answer questions with options, correct answers, and explanations.
- Review question counts, delete questions, and publish a mock only after it contains content and questions.
- Move a published mock back to draft while it is being edited.
- View student accounts and give or remove the `$5` premium access flag after payment is confirmed.
- Review recent users and completed mock attempts without seeing student passwords.

The current panel intentionally does not process payments. A payment provider should update the premium flag only after a verified payment webhook in production.

Admin forms include session-bound CSRF protection. Refresh an older open admin page before submitting it after this update. Student vocabulary and essay text are not included in the admin activity overview.

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

### Learning hub

Signed-in students can open **Learning hub** from the header or dashboard:

1. **Mistake notebook** collects missed Reading and Listening questions from saved mocks, with retries and explanations. A later correct full-mock answer clears the question.
2. **Vocabulary review** schedules private cards using Again (today), Good (at least tomorrow, doubling intervals), and Easy (at least four days, tripling intervals). Existing words start due immediately. The library and daily review show due/new/scheduled counts, cards reviewed today, and the next review day. Rating buttons preview the saved interval; Again cycles through the other due cards before returning. Changing a term or meaning resets its schedule; example-only edits preserve review progress.
3. **Study plan** saves a target band, exam date, and daily time budget. Daily tasks explain their recommendations, use the latest five scores per skill to prioritise target gaps and untried skills, and rotate across skills. Blocks sum to the daily budget; the final week allocates more time to recall and reflection. A seven-day preview ends at the exam date. Today’s session is saved so new results do not replace tasks mid-session. Goal changes update an unstarted session immediately, or apply tomorrow if any task is already complete. Students can mark tasks complete or undo completion; displayed minutes are planned blocks, not measured study time. Saved daily sessions use the additive `study_days` table, created by `init-db`.
4. **Progress** supports skill and all-time/30-day/90-day filters, with latest-five averages, latest and best bands, target gaps, and comparisons against the preceding five once ten attempts are available. Separate accessible SVG charts show up to 30 recent attempts per skill on a fixed 0–9 scale, with links to results. Question-type accuracy counts the latest answer per distinct question in the selected period (including blanks); AI criterion averages use available scores from the latest five attempts per skill. Personal next steps link to baseline practice, target-gap sessions, mistakes, or AI feedback. History is paginated at 20 attempts with filters preserved. Revisions remain in their own comparison view.
5. **Exam simulation** sequences selected Listening, Reading, Writing, and Speaking mocks. Each section clock starts on first opening, survives reloads, and synchronises with server time. Answers and essays autosave to the private session; uploaded Speaking turns can be restored, while an interrupted recording needs rerecording. Conflicting tabs receive a reload message instead of overwriting a newer draft. Rendered submissions carry session/stage identity to prevent duplicate saved attempts. Reading/Listening submit when time runs out; Writing requires 50 words for AI feedback. Failed AI checks preserve submitted content and offer a retry without automatic resubmission loops. Students can end a section unscored or end the whole session early; reports retain drafts and clearly label late submissions. An equal-weight combined band is shown only with four scored sections. Sessions use existing allowances and selected mock durations/content. These are practice simulations, not official IELTS exams. Run `init-db` to add the `exam_section_state` table before using saved sessions.
6. **Writing revisions** open from a Writing result. The editor restores the latest saved draft, autosaves with conflict detection, and offers a manual Save draft button without JavaScript. Draft saves are free, including empty/short drafts; successful feedback checks consume the shared Writing allowance. Failed checks preserve the draft for retry. Completed submissions carry a replay token so reloading or retrying the same submission does not save or charge twice. Compare any two checked versions with overall/criterion changes and side-by-side added/removed text; long essays show full text without highlighting. Original essays, every checked revision, and their feedback remain available. Edits made in another tab while AI feedback is pending survive its return. Run `init-db` to add `writing_revision_drafts` and `writing_revision_submissions`.
7. **Speaking review** opens from the Learning hub or AI practice library. Search your own result titles/transcripts, filter by audio availability, and browse history in pages of 12. Each result groups answers by Speaking part, with native audio controls, a shared playback speed selector, replay/loop controls, downloads, transcripts, and links to older/newer results. Only one answer plays at a time; no recording autoplays. Downloads preserve the recorded format, including MP4/M4A recordings. A confirmed per-answer deletion removes audio while retaining transcripts, scores, and feedback. Playback and history remain available when AI allowances are exhausted. Audio streams, downloads, and history are private; recording references must belong to the current user and result to appear in a player. Older/deleted recordings show a transcript-only state. Abandoned audio older than one day is cleaned up on the next successful upload; recordings referenced by unfinished exam drafts are retained. Run `init-db` to add the recording lookup index.
8. **Teacher workspace** supports searchable/paginated rosters, recent skill averages, class status counts, assignment filters, and batch assignments to connected students. Students explicitly join using a teacher invitation code, and either side can end the connection. Codes can be replaced without removing existing students. Students start practice from an assignment, then explicitly hand in an eligible result completed after assignment creation. Teachers see score history and the response handed in; private Speaking audio stays owner-only. Pending, overdue, awaiting-review, reviewed, and cancelled states are derived from real hand-ins. Feedback is tied to a hand-in version; newer hand-ins return to awaiting-review, and stale review forms preserve the teacher's text for checking against the latest result. Teachers can edit instructions/deadlines and cancel/restore assignments. Batch creation tokens prevent repeated form submissions from creating duplicates. Assignments use students' existing allowances. Existing assignment notes remain saved, and historical assignments use their creation timestamp to determine eligible results. Run `init-db` for `assignment_tracking`, `assignment_submissions`, and `assignment_creation_tokens`.

For an existing installation, run `.venv/bin/flask --app run.py init-db` before opening the new pages. This adds tables without resetting existing data. New Speaking recordings are stored in SQLite; account for their size when backing up the database. Ollama and Whisper are still required for real AI feedback and transcription.

### Code review fixes

- Authentication, mock submissions, and AI endpoints now require session-bound CSRF tokens, alongside the existing protected admin/learning/flashcard forms. Browser AI requests send `X-CSRF-Token`; refresh old open pages after updating.
- Login resets prior account session state and resumes a validated local `next` destination. Missing or example session secrets generate a random per-process key. Set a persistent, randomly generated `SECRET_KEY` in `.env` for sessions to survive restarts or multiple workers.
- New mock attempts store immutable question reviews. Before an admin changes or deletes questions, the current review for legacy attempts is preserved without changing stored marks. Historical changes made before this update cannot be reconstructed. Review lookups are batched for history pages.
- Mistake retries attach to a specific attempt, work for deleted questions, and no longer carry an old successful badge into a later missed mock.
- Mock quotas and Speaking quotas are rechecked under the database write lock. Initial Writing retries use replay tokens, as revision checks already do.
- Malformed Speaking requests and invalid/incomplete model feedback fail cleanly. Bands must be finite numbers from 0 to 9; invalid legacy scores are excluded from analytics and exam totals.
- Exam autosaves finish before submission, stale tabs cannot replace newer drafts, and active exam audio survives ordinary orphan cleanup.
- Vocabulary ratings are atomic. Saved plans resolve practice actions to score review or free Writing drafts when a student's allowance is exhausted.
- Teacher hand-in choices load metadata instead of full essays; validation uses a targeted result lookup. Stale/invalid review versions and reviews without a hand-in are rejected.
- Frontend regressions cover canceled/duplicate submits, real form-value saves, blocked storage, guide media failure, and flashcard keyboard focus.

Run `.venv/bin/flask --app run.py init-db` after updating to add `attempt_snapshots`, `mistake_retries`, and `ai_writing_submission_tokens`. Existing accounts and stored scores are retained. Python/Flask tests use isolated temporary databases; Node-backed controller checks are included when Node is available. AI tests mock the local provider and microphone transcription rather than running a live model or accessing a microphone.

Speaking recovery: failed uploads keep the recording in the open tab with a Retry upload button. Successful standalone answers are restored from tab-scoped browser storage for up to 24 hours; unfinished microphone audio cannot survive closing the page. Storage-blocked browsers can still record normally. If the AI follow-up generator is unavailable after successful transcription, practice continues with the planned question; final AI scoring still requires Ollama.

Speaking transcription decodes recordings directly to 16 kHz mono samples before calling Whisper. This supports the installed PyAV 19 API and avoids faster-whisper's incompatible `metadata_errors` file-decoding call. Answers are limited to 15 MB and ten minutes of decoded audio. The audio decoder has regression tests using real WAV data.
