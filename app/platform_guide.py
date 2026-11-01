"""Student guide content shared by the guide page and its narrated video."""


GUIDE_CHAPTERS = (
    {
        "id": "getting-started",
        "title": "Start with your dashboard",
        "summary": "Create an account, sign in, and find your next practice session.",
        "narration": (
            "Welcome to IELTS Platform. To begin, choose Create account and enter your name, "
            "email address, and a password of at least eight characters. Confirm your password, "
            "then create your account. Already registered? Choose Log in instead. Your dashboard "
            "shows your completed mocks, average estimated band scores, and remaining practice "
            "allowance. Use the navigation to open Mocks, AI practice, or Flashcards."
        ),
        "steps": (
            "Choose Create account and enter your name, email, and matching passwords of at least 8 characters.",
            "Choose Log in whenever you return to an existing account.",
            "Open Dashboard to see completed mocks, average estimated bands, and remaining practice.",
        ),
        "action_endpoint": "auth.register",
        "action_label": "Create an account",
    },
    {
        "id": "mock-tests",
        "title": "Take a Reading or Listening mock",
        "summary": "Choose a skill, move between sections, and submit your answers.",
        "narration": (
            "Open Mocks and filter the library by Reading or Listening. Choose Start mock "
            "on an available test. In Reading, read the passage and answer its questions. "
            "In Listening, choose Start audio: you have twenty seconds to read before playback "
            "begins. Use Previous, Next, or the numbered question buttons to move around. "
            "At the final section, choose Submit mock and confirm to see your score and answer review."
        ),
        "steps": (
            "Open Mocks, choose Reading or Listening, and select Start mock on an available test.",
            "For Listening, select Start audio and use the 20-second preparation time to read the questions.",
            "Use Previous, Next passage or Next section, and the numbered question buttons to navigate.",
            "At the final section, select Submit mock and confirm your submission to see your results.",
        ),
        "action_endpoint": "mocks.index",
        "action_label": "Browse mock tests",
    },
    {
        "id": "study-tools",
        "title": "Use notes, highlights, and saved work",
        "summary": "Keep useful details close while you work through a mock.",
        "narration": (
            "During a Reading or Listening mock, select text in a passage or question, "
            "then choose Highlight selection. Choose Add selection to notes to keep the text "
            "with your own reminders. Open Notes to write or review them. Answers, notes, "
            "highlights, and your current section save in this browser when storage is available. "
            "Use Exit to leave; return on the same device and browser to continue your saved work."
        ),
        "steps": (
            "Select passage or question text, then choose Highlight selection or press Alt+H.",
            "Choose Add selection to notes to copy selected text into your current section's notes.",
            "Open Notes to write reminders; notes and highlights are not scored.",
            "Check the saved-work status. Drafts stay in this browser; they do not sync between devices.",
        ),
        "action_endpoint": "mocks.index",
        "action_label": "Try the study tools",
    },
    {
        "id": "ai-practice",
        "title": "Practice Speaking and Writing with AI",
        "summary": "Record answers or submit an essay for practice feedback.",
        "narration": (
            "Open AI practice and select an available Speaking or Writing mock. For Speaking, "
            "allow microphone access when asked. Listen to the question, choose Start recording, "
            "speak naturally, then choose Stop answer. Continue through the questions to receive "
            "feedback. For Writing, read the task, write your essay, and choose Check with AI. "
            "Read the feedback and suggested improvements. AI band estimates are for practice, "
            "not official IELTS results."
        ),
        "steps": (
            "Open AI practice and choose Start speaking or Start writing on an available mock.",
            "For Speaking, allow microphone access, use Start recording, and select Stop answer after each response.",
            "For Writing, follow the task instructions, write your essay, and select Check with AI.",
            "Use the feedback to plan your next practice session. AI scores are estimates, not official IELTS bands.",
        ),
        "action_endpoint": "ai.index",
        "action_label": "Open AI practice",
    },
    {
        "id": "flashcards",
        "title": "Build vocabulary with flashcards",
        "summary": "Save new words, reveal their meanings, and test your memory.",
        "narration": (
            "Open Flashcards to build your personal vocabulary collection. Enter a word or "
            "phrase, its meaning or translation, and an optional example, then choose Save word. "
            "Choose Study flashcards, try to recall each meaning, and select the card to reveal "
            "it. Use Next card or Shuffle cards to keep practicing. Save at least two words "
            "with different meanings to unlock a multiple choice quiz, then review your answers and score."
        ),
        "steps": (
            "Open Flashcards, enter a word or phrase and its meaning, optionally add an example, and choose Save word.",
            "Choose Study flashcards, recall the meaning, then select the card to reveal it.",
            "Use Previous, Next card, and Shuffle cards to review your collection.",
            "Save at least 2 words with different meanings, then choose Multiple-choice quiz and Check my answers.",
        ),
        "action_endpoint": "flashcards.index",
        "action_label": "Build your vocabulary",
    },
    {
        "id": "progress-and-appearance",
        "title": "Make the platform work for you",
        "summary": "Choose a comfortable theme and return to your progress.",
        "narration": (
            "Use the sun or moon button in the header to switch between light and dark mode, "
            "including during a mock. Your choice is remembered in this browser when storage "
            "is available. After submitting practice, return to Dashboard to check your average "
            "scores and recent results. Vocabulary quiz results stay in Flashcards. Choose one "
            "area to improve, practice a little regularly, and return to this guide whenever "
            "you need a reminder."
        ),
        "steps": (
            "Select the sun or moon button in the header to switch between light and dark mode.",
            "Return to Dashboard after submitting mocks to see your updated estimated bands and recent results.",
            "Open Flashcards to revisit your recent vocabulary quiz results.",
            "Choose your next practice session using the feedback from your last attempt.",
        ),
        "action_endpoint": "main.dashboard",
        "action_label": "Go to your dashboard",
    },
)
