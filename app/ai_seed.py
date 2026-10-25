import json

from .database import get_db


SPEAKING_MOCKS = [
    {
        "title": "Speaking Mock 1: Home and Daily Life",
        "description": "An AI-led Speaking practice test about home, routines, memories, and community life.",
        "part1_topic": "Home and daily routines",
        "part2": "Describe a useful object in your home. You should say what it is, how often you use it, where you got it, and explain why it is useful.",
        "part3_topic": "Convenience, technology, and modern lifestyles",
    },
    {
        "title": "Speaking Mock 2: Learning and Skills",
        "description": "An AI-led Speaking practice test about learning experiences, skills, and education.",
        "part1_topic": "Learning new things",
        "part2": "Describe a skill you would like to learn. You should say what it is, why you want to learn it, how you would learn it, and explain how it could help you.",
        "part3_topic": "Education, teachers, and lifelong learning",
    },
    {
        "title": "Speaking Mock 3: Travel and Places",
        "description": "An AI-led Speaking practice test about places, journeys, and travel choices.",
        "part1_topic": "Places near where you live",
        "part2": "Describe a memorable journey you have taken. You should say where you went, how you travelled, who you travelled with, and explain why you remember it.",
        "part3_topic": "Tourism, transport, and responsible travel",
    },
    {
        "title": "Speaking Mock 4: Food and Health",
        "description": "An AI-led Speaking practice test about meals, cooking, and healthy habits.",
        "part1_topic": "Food preferences and meals",
        "part2": "Describe a meal you enjoyed with other people. You should say what you ate, where you had it, who was there, and explain why you enjoyed it.",
        "part3_topic": "Public health, diet, and food culture",
    },
    {
        "title": "Speaking Mock 5: Work and Ambition",
        "description": "An AI-led Speaking practice test about work, goals, and professional life.",
        "part1_topic": "Work and future plans",
        "part2": "Describe a job you would like to do in the future. You should say what the job is, what skills it needs, where you would like to do it, and explain why it interests you.",
        "part3_topic": "Careers, job satisfaction, and workplace change",
    },
    {
        "title": "Speaking Mock 6: Technology and Communication",
        "description": "An AI-led Speaking practice test about devices, communication, and digital habits.",
        "part1_topic": "Phones, apps, and communication",
        "part2": "Describe a piece of technology that has changed your life. You should say what it is, when you started using it, what you use it for, and explain how it changed your life.",
        "part3_topic": "Digital communication, privacy, and access",
    },
    {
        "title": "Speaking Mock 7: Nature and the Environment",
        "description": "An AI-led Speaking practice test about nature, weather, and environmental responsibility.",
        "part1_topic": "Weather and outdoor activities",
        "part2": "Describe a natural place you would recommend to a visitor. You should say where it is, what people can see there, how to get there, and explain why you recommend it.",
        "part3_topic": "Environmental protection and urban development",
    },
    {
        "title": "Speaking Mock 8: Books and Stories",
        "description": "An AI-led Speaking practice test about reading, stories, and creative interests.",
        "part1_topic": "Reading and entertainment",
        "part2": "Describe a book or story that you remember well. You should say what it was about, when you read or heard it, what you liked about it, and explain why you remember it.",
        "part3_topic": "Stories, education, and digital media",
    },
    {
        "title": "Speaking Mock 9: Festivals and Traditions",
        "description": "An AI-led Speaking practice test about celebrations, traditions, and social change.",
        "part1_topic": "Celebrations and special days",
        "part2": "Describe a celebration that is important in your culture. You should say when it happens, what people do, who takes part, and explain why it is important.",
        "part3_topic": "Tradition, identity, and changing societies",
    },
    {
        "title": "Speaking Mock 10: Cities and the Future",
        "description": "An AI-led Speaking practice test about towns, cities, and plans for the future.",
        "part1_topic": "Your town or city",
        "part2": "Describe one improvement you would make in your town or city. You should say what it would be, where it would be made, who would benefit, and explain why it is needed.",
        "part3_topic": "Urban planning, public services, and the future",
    },
]


WRITING_MOCKS = [
    {
        "title": "Writing Checker 1: Online Learning",
        "description": "Submit an IELTS Academic Task 2 essay about the benefits and limits of online education.",
        "prompt": "Some people believe that online education is a better way to learn than studying in a classroom. To what extent do you agree or disagree?",
    },
    {
        "title": "Writing Checker 2: Public Transport",
        "description": "Submit an IELTS Academic Task 2 essay about transport policy and city life.",
        "prompt": "Governments should spend more money on public transport and less money on building new roads. To what extent do you agree or disagree?",
    },
    {
        "title": "Writing Checker 3: Technology at Work",
        "description": "Submit an IELTS Academic Task 2 essay about technology and employment.",
        "prompt": "Some people think that the increasing use of technology at work is good for employees, while others think it causes problems. Discuss both views and give your own opinion.",
    },
    {
        "title": "Writing Checker 4: Healthy Lifestyles",
        "description": "Submit an IELTS Academic Task 2 essay about responsibility for public health.",
        "prompt": "Some people believe that individuals are responsible for their own health, while others believe governments should take responsibility. Discuss both views and give your own opinion.",
    },
    {
        "title": "Writing Checker 5: International Tourism",
        "description": "Submit an IELTS Academic Task 2 essay about the effects of international tourism.",
        "prompt": "International tourism has brought many benefits to countries, but it can also cause problems. Discuss the advantages and disadvantages of international tourism.",
    },
    {
        "title": "Writing Checker 6: University Education",
        "description": "Submit an IELTS Academic Task 2 essay about access to higher education.",
        "prompt": "University education should be free for everyone, regardless of their financial situation. To what extent do you agree or disagree?",
    },
    {
        "title": "Writing Checker 7: Advertising",
        "description": "Submit an IELTS Academic Task 2 essay about advertising and consumer choices.",
        "prompt": "Advertising encourages people to buy things they do not need. To what extent do you agree or disagree?",
    },
    {
        "title": "Writing Checker 8: Environmental Action",
        "description": "Submit an IELTS Academic Task 2 essay about individual and government environmental action.",
        "prompt": "Individuals can do very little to improve the environment; only governments and large companies can make a real difference. To what extent do you agree or disagree?",
    },
    {
        "title": "Writing Checker 9: Children and Screen Time",
        "description": "Submit an IELTS Academic Task 2 essay about children, technology, and family life.",
        "prompt": "Children today spend too much time using computers and smartphones. What are the reasons for this, and is it a positive or negative development?",
    },
    {
        "title": "Writing Checker 10: Work-Life Balance",
        "description": "Submit an IELTS Academic Task 2 essay about working hours and quality of life.",
        "prompt": "Many people find it difficult to balance their work with other parts of their lives. Why is this the case, and what can people do to solve this problem?",
    },
]


def _speaking_task(pack):
    return {
        "parts": [
            {
                "part": 1,
                "title": "Part 1 — Interview",
                "instruction": "Answer each question naturally in two or three sentences.",
                "topic": pack["part1_topic"],
                "questions": [
                    f"How often do you think about {pack['part1_topic'].lower()}?",
                    f"What do you enjoy most about {pack['part1_topic'].lower()}?",
                    f"Has your opinion about {pack['part1_topic'].lower()} changed over time?",
                    f"Would you like to spend more time on this in the future? Why?",
                ],
                "prep_seconds": 0,
            },
            {
                "part": 2,
                "title": "Part 2 — Individual long turn",
                "instruction": "You have one minute to prepare. Speak for up to two minutes.",
                "topic": "Long turn",
                "questions": [pack["part2"]],
                "prep_seconds": 60,
            },
            {
                "part": 3,
                "title": "Part 3 — Discussion",
                "instruction": "Give developed answers and explain your ideas with reasons or examples.",
                "topic": pack["part3_topic"],
                "questions": [
                    f"Why is {pack['part3_topic'].lower()} important to society?",
                    f"What are the main advantages and disadvantages of changes in {pack['part3_topic'].lower()}?",
                    f"How might {pack['part3_topic'].lower()} develop in the next twenty years?",
                    f"What should governments or communities do about {pack['part3_topic'].lower()}?",
                ],
                "prep_seconds": 0,
            },
        ]
    }


def seed_ai_content():
    db = get_db()
    for pack in SPEAKING_MOCKS:
        task = _speaking_task(pack)
        db.execute(
            """
            INSERT INTO ai_mocks (skill, title, description, task_json, time_limit_minutes, is_published)
            SELECT 'speaking', ?, ?, ?, 15, 1
            WHERE NOT EXISTS (SELECT 1 FROM ai_mocks WHERE title = ?)
            """,
            (
                pack["title"],
                pack["description"],
                json.dumps(task),
                pack["title"],
            ),
        )

    for pack in WRITING_MOCKS:
        task = {
            "task_type": "IELTS Academic Writing Task 2",
            "instructions": "Write at least 250 words. Support your ideas with reasons and relevant examples.",
            "prompt": pack["prompt"],
            "minimum_words": 250,
        }
        db.execute(
            """
            INSERT INTO ai_mocks (skill, title, description, task_json, time_limit_minutes, is_published)
            SELECT 'writing', ?, ?, ?, 60, 1
            WHERE NOT EXISTS (SELECT 1 FROM ai_mocks WHERE title = ?)
            """,
            (
                pack["title"],
                pack["description"],
                json.dumps(task),
                pack["title"],
            ),
        )
    db.commit()
