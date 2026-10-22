import asyncio
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.future import select

from app.database import AsyncSessionLocal, Base, engine
from app.models import Module, Program, Lesson, Quiz, QuizQuestion, QuizOption

programs_data = [
    {
        "slug": "tech-ai",
        "title": "Tech & AI Fundamentals",
        "description": "Master foundational technology, artificial intelligence literacy, and practical modern build techniques.",
        "path": "Builder Path",
        "modules": [
            {
                "title": "Intro to Tech Careers & Systems",
                "order": 1,
                "description": "Overview of modern software engineering and digital systems.",
                "lessons": [
                    {
                        "title": "Understanding the Modern Digital Ecosystem",
                        "order": 1,
                        "duration": 15,
                        "content": "### Welcome to Tech & AI\n\nIn this foundational lesson, we explore how software architectures connect users, APIs, and cloud databases.\n\nKey takeaways:\n- Client-server relationships\n- Cloud compute models\n- Decoupled modern frontend and backend architectures"
                    },
                    {
                        "title": "Setting Up Your Development Environment",
                        "order": 2,
                        "duration": 20,
                        "content": "### Tools of the Trade\n\nEvery builder needs an efficient workspace.\n\n1. Version control with Git\n2. Shell navigation & CLI mastery\n3. Code formatting & linting best practices"
                    }
                ]
            },
            {
                "title": "AI Literacy & Prompt Engineering Basics",
                "order": 2,
                "description": "Understanding generative models, practical AI tools, and ethics.",
                "lessons": [
                    {
                        "title": "How Large Language Models Work",
                        "order": 1,
                        "duration": 25,
                        "content": "### The Mechanics of LLMs\n\nTransformers, tokenization, and attention mechanisms.\n\nWe break down how generative models predict next tokens and how to optimize prompts with context, constraints, and examples."
                    },
                    {
                        "title": "Practical Prompt Engineering Frameworks",
                        "order": 2,
                        "duration": 20,
                        "content": "### The CO-STAR Framework\n\nLearn Context, Objective, Style, Tone, Audience, and Response structuring for maximum AI output quality."
                    }
                ]
            },
            {
                "title": "Capstone Builder Project",
                "order": 3,
                "description": "Build and showcase a real-world digital prototype.",
                "lessons": [
                    {
                        "title": "Project Specification & Scoping",
                        "order": 1,
                        "duration": 30,
                        "content": "### Designing Your Capstone Prototype\n\nDefine the user journey, write acceptance criteria, and plan your database schema before writing code."
                    },
                    {
                        "title": "Deployment & Portfolio Presentation",
                        "order": 2,
                        "duration": 25,
                        "content": "### Launching to the World\n\nDeploy your project to production, test endpoints, and prepare a crisp 2-minute walkthrough."
                    }
                ]
            },
        ],
        "quiz": {
            "title": "Tech & AI Capstone Assessment",
            "description": "Test your mastery of digital architecture, AI literacy, and deployment workflows.",
            "passing_score": 80,
            "questions": [
                {
                    "text": "Which component in prompt engineering provides background and domain knowledge to the LLM?",
                    "explanation": "Context gives the model domain background and situation constraints.",
                    "options": [
                        ("Context", True),
                        ("Temperature", False),
                        ("Tokenizer", False),
                        ("Hyperparameter", False)
                    ]
                },
                {
                    "text": "What is the primary role of an API in client-server architecture?",
                    "explanation": "APIs define the interface and protocol for client-server communication.",
                    "options": [
                        ("Provide a standardized interface for data exchange", True),
                        ("Compile machine code into binaries", False),
                        ("Store persistent rows on magnetic disks", False),
                        ("Render CSS styles on the GPU", False)
                    ]
                }
            ]
        }
    },
    {
        "slug": "leadership",
        "title": "Leadership & Mentorship",
        "description": "Develop high-impact leadership skills, team communication, project direction, and structured mentoring.",
        "path": "Mentorship Path",
        "modules": [
            {
                "title": "Foundations of Empathetic Leadership",
                "order": 1,
                "description": "Principles of inspiring teams and active listening.",
                "lessons": [
                    {
                        "title": "The Mindset of a Servant Leader",
                        "order": 1,
                        "duration": 15,
                        "content": "### Leadership Through Service\n\nEffective leadership begins by removing blockers for your team and enabling others to perform at their highest potential."
                    },
                    {
                        "title": "Active Listening & Constructive Feedback",
                        "order": 2,
                        "duration": 20,
                        "content": "### Feedback Loops That Build Trust\n\nHow to provide clear, actionable feedback without diminishing psychological safety."
                    }
                ]
            },
            {
                "title": "Mentoring Others & Structured Coaching",
                "order": 2,
                "description": "Frameworks for guiding peers and junior mentees.",
                "lessons": [
                    {
                        "title": "The GROW Coaching Model",
                        "order": 1,
                        "duration": 25,
                        "content": "### Goal, Reality, Options, Will\n\nMaster the standard coaching framework to guide mentees toward self-discovered solutions."
                    }
                ]
            },
            {
                "title": "Leading Projects & Strategic Decision Making",
                "order": 3,
                "description": "Managing complex initiatives from start to finish.",
                "lessons": [
                    {
                        "title": "Prioritization Under Ambiguity",
                        "order": 1,
                        "duration": 20,
                        "content": "### Decision Matrices & Resource Allocation\n\nBalancing urgency, impact, and feasibility when resources are constrained."
                    }
                ]
            }
        ],
        "quiz": {
            "title": "Leadership & Mentorship Final Check",
            "description": "Demonstrate understanding of coaching models and empathetic management.",
            "passing_score": 80,
            "questions": [
                {
                    "text": "In the GROW coaching model, what does the 'R' represent?",
                    "explanation": "R stands for Reality — assessing the current situation honestly.",
                    "options": [
                        ("Reality", True),
                        ("Responsibility", False),
                        ("Revenue", False),
                        ("Recognition", False)
                    ]
                }
            ]
        }
    },
    {
        "slug": "finance",
        "title": "Personal Finance & Financial Literacy",
        "description": "Build financial independence, money mindset, budgeting systems, and personal asset strategies.",
        "path": "Explorer Path",
        "modules": [
            {
                "title": "Money Mindset & Financial Literacy",
                "order": 1,
                "description": "Understanding wealth principles and cash flow dynamics.",
                "lessons": [
                    {
                        "title": "The Fundamentals of Personal Cash Flow",
                        "order": 1,
                        "duration": 15,
                        "content": "### Cash Flow vs Net Worth\n\nLearn how income, expenses, assets, and liabilities interact over a multi-year horizon."
                    }
                ]
            },
            {
                "title": "Budgeting & Investment Basics",
                "order": 2,
                "description": "Building sustainable personal asset strategies.",
                "lessons": [
                    {
                        "title": "Compound Interest & Diversified Portfolios",
                        "order": 1,
                        "duration": 20,
                        "content": "### The Power of Compounding\n\nHow index funds, dollar-cost averaging, and time horizon drive wealth accumulation."
                    }
                ]
            },
            {
                "title": "Starting & Validating a Side Venture",
                "order": 3,
                "description": "From idea validation to your first paying customer.",
                "lessons": [
                    {
                        "title": "Low-Risk Venture Validation",
                        "order": 1,
                        "duration": 20,
                        "content": "### Pre-Selling & Market Testing\n\nHow to validate economic willingness to pay before writing checks or investing capital."
                    }
                ]
            }
        ]
    },
    {
        "slug": "wellness",
        "title": "Wellness & Self-Discovery",
        "description": "Cultivate emotional regulation, deep reflection, self-awareness, and sustainable life habits.",
        "path": "Reflector Path",
        "modules": [
            {
                "title": "Self-Awareness & Core Values",
                "order": 1,
                "description": "Discover internal values and emotional clarity.",
                "lessons": [
                    {
                        "title": "Identifying Your Non-Negotiables",
                        "order": 1,
                        "duration": 15,
                        "content": "### Values-Driven Alignment\n\nUnderstanding what drives fulfillment versus what creates burnout in high-performance environments."
                    }
                ]
            },
            {
                "title": "Sustainable Habit Architecture",
                "order": 2,
                "description": "Building sustainable day-to-day rituals.",
                "lessons": [
                    {
                        "title": "Habit Stacking & Friction Elimination",
                        "order": 1,
                        "duration": 20,
                        "content": "### Small Daily Increments\n\nDesigning micro-habits that survive busy weeks and stress cycles."
                    }
                ]
            }
        ]
    },
    {
        "slug": "research",
        "title": "Research & Systems Innovation",
        "description": "Rigorous critical thinking, hypothesis testing, literature synthesis, and structured innovation.",
        "path": "Innovator Path",
        "modules": [
            {
                "title": "Formulating Testable Hypotheses",
                "order": 1,
                "description": "Scientific rigor in business and product ideas.",
                "lessons": [
                    {
                        "title": "From Observation to Problem Statement",
                        "order": 1,
                        "duration": 20,
                        "content": "### Dissecting Core Assumptions\n\nHow to identify the critical falsifiable hypothesis behind any product or organizational proposal."
                    }
                ]
            }
        ]
    },
    {
        "slug": "relationships",
        "title": "Relationships & Social Capital",
        "description": "Authentic networking, relational intelligence, community dynamics, and long-term partnerships.",
        "path": "Connector Path",
        "modules": [
            {
                "title": "The Currency of Trust",
                "order": 1,
                "description": "How high-trust networks outperform transactional connections.",
                "lessons": [
                    {
                        "title": "Generous Networking & Relationship Architecture",
                        "order": 1,
                        "duration": 20,
                        "content": "### Giving Before Asking\n\nHow connecting others and delivering unsolicited value creates long-lasting social capital."
                    }
                ]
            }
        ]
    },
    {
        "slug": "healing",
        "title": "Holistic Healing & Resilience",
        "description": "Restoration, cognitive clarity, overcoming setbacks, and nervous system regulation.",
        "path": "Restorer Path",
        "modules": [
            {
                "title": "Bouncing Back From Failure",
                "order": 1,
                "description": "Psychological resilience for modern professionals.",
                "lessons": [
                    {
                        "title": "Reframing Failure As Feedback",
                        "order": 1,
                        "duration": 20,
                        "content": "### Post-Traumatic Growth\n\nTools to navigate setbacks, grief, and professional disruptions without losing your core identity."
                    }
                ]
            }
        ]
    },
    {
        "slug": "entrepreneurship",
        "title": "Entrepreneurship & Venture Building",
        "description": "0-to-1 company creation, business modeling, pricing, distribution, and unit economics.",
        "path": "Founder Path",
        "modules": [
            {
                "title": "0-to-1 Idea Discovery",
                "order": 1,
                "description": "Finding high-value underserved niches.",
                "lessons": [
                    {
                        "title": "Customer Discovery Interviews",
                        "order": 1,
                        "duration": 25,
                        "content": "### Asking The Right Questions\n\nHow to interview target users using The Mom Test principles to uncover genuine willingness to pay."
                    }
                ]
            }
        ]
    },
    {
        "slug": "ai-strategy-executive",
        "title": "AI Strategy & Executive Leadership",
        "description": "Enterprise AI adoption, governance, risk frameworks, and executive decision-making.",
        "path": "Executive Path",
        "modules": [
            {
                "title": "AI Opportunity Matrix",
                "order": 1,
                "description": "Assessing where generative AI moves margins.",
                "lessons": [
                    {
                        "title": "Evaluating ROI and Enterprise AI Risk",
                        "order": 1,
                        "duration": 30,
                        "content": "### The Board-Level AI Roadmap\n\nFrameworks for choosing between off-the-shelf APIs, fine-tuning, and proprietary models."
                    }
                ]
            }
        ]
    }
]


async def seed_programs():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        for pdata in programs_data:
            result = await session.execute(
                select(Program).where(Program.slug == pdata["slug"])
            )
            program = result.scalars().first()

            if not program:
                program = Program(
                    slug=pdata["slug"],
                    title=pdata["title"],
                    description=pdata["description"],
                    path=pdata["path"],
                    is_active=True,
                    published=True,
                )
                session.add(program)
                await session.flush()
                print(f"Created program: '{program.title}' ({program.slug})")
            else:
                program.title = pdata["title"]
                program.description = pdata["description"]
                program.path = pdata["path"]
                program.is_active = True
                program.published = True
                print(f"Updated program: '{program.title}' ({program.slug})")

            # Seed modules & lessons
            for mdata in pdata.get("modules", []):
                mod_res = await session.execute(
                    select(Module).where(Module.program_id == program.id).where(Module.order == mdata["order"])
                )
                mod = mod_res.scalars().first()
                if not mod:
                    mod = Module(
                        program_id=program.id,
                        title=mdata["title"],
                        order=mdata["order"],
                        description=mdata["description"],
                    )
                    session.add(mod)
                    await session.flush()

                for ldata in mdata.get("lessons", []):
                    less_res = await session.execute(
                        select(Lesson).where(Lesson.module_id == mod.id).where(Lesson.order == ldata["order"])
                    )
                    less = less_res.scalars().first()
                    if not less:
                        less = Lesson(
                            module_id=mod.id,
                            title=ldata["title"],
                            order=ldata["order"],
                            content_type="text",
                            content_body=ldata["content"],
                            duration_minutes=ldata.get("duration", 15),
                        )
                        session.add(less)
                        await session.flush()

            # Seed Final Assessment Quiz if defined
            qdata = pdata.get("quiz")
            if qdata:
                q_res = await session.execute(
                    select(Quiz).where(Quiz.program_id == program.id).where(Quiz.quiz_type == "final_assessment")
                )
                quiz = q_res.scalars().first()
                if not quiz:
                    quiz = Quiz(
                        program_id=program.id,
                        quiz_type="final_assessment",
                        title=qdata["title"],
                        description=qdata["description"],
                        passing_score=qdata.get("passing_score", 80),
                        max_retries=3,
                    )
                    session.add(quiz)
                    await session.flush()

                    for i, quest_data in enumerate(qdata.get("questions", []), 1):
                        quest = QuizQuestion(
                            quiz_id=quiz.id,
                            question_text=quest_data["text"],
                            explanation=quest_data.get("explanation"),
                            order=i
                        )
                        session.add(quest)
                        await session.flush()

                        for opt_text, is_corr in quest_data.get("options", []):
                            opt = QuizOption(
                                question_id=quest.id,
                                option_text=opt_text,
                                is_correct=is_corr
                            )
                            session.add(opt)

        await session.commit()
        print("All 9 tracks seeded with modules and lessons successfully!")


if __name__ == "__main__":
    asyncio.run(seed_programs())
