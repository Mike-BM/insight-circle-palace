import asyncio
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.future import select
from app.database import AsyncSessionLocal, engine, Base
from app.models import Program, Module

programs_data = [
    {
        "slug": "tech-ai",
        "title": "Tech & AI Fundamentals",
        "description": "Master foundational technology, artificial intelligence literacy, and practical modern build techniques.",
        "path": "Builder Path",
        "modules": [
            {"title": "Intro to Tech Careers & Systems", "order": 1, "description": "Overview of modern software engineering and digital systems."},
            {"title": "AI Literacy & Prompt Engineering Basics", "order": 2, "description": "Understanding generative models, practical AI tools, and ethics."},
            {"title": "Capstone Builder Project", "order": 3, "description": "Build and showcase a real-world digital prototype."}
        ]
    },
    {
        "slug": "wellness",
        "title": "Wellness & Self-Discovery",
        "description": "Cultivate emotional regulation, deep reflection, self-awareness, and sustainable life habits.",
        "path": "Reflector Path",
        "modules": [
            {"title": "Understanding Yourself & Core Values", "order": 1, "description": "Uncover intrinsic motivators and core behavioral patterns."},
            {"title": "Emotional Regulation & Mindfulness", "order": 2, "description": "Practical tools for clarity, focus, and stress management."},
            {"title": "Designing Sustainable Life Habits", "order": 3, "description": "Building long-term routines aligned with your vision."}
        ]
    },
    {
        "slug": "leadership",
        "title": "Leadership & Mentorship",
        "description": "Develop high-impact leadership skills, team communication, project direction, and structured mentoring.",
        "path": "Mentorship Path",
        "modules": [
            {"title": "Foundations of Empathetic Leadership", "order": 1, "description": "Principles of inspiring teams and active listening."},
            {"title": "Mentoring Others & Structured Coaching", "order": 2, "description": "Frameworks for guiding peers and junior mentees."},
            {"title": "Leading Projects & Strategic Decision Making", "order": 3, "description": "Managing complex initiatives from start to finish."}
        ]
    },
    {
        "slug": "finance",
        "title": "Personal Finance & Entrepreneurship",
        "description": "Build financial independence, money mindset, budgeting systems, and venture validation.",
        "path": "Explorer Path",
        "modules": [
            {"title": "Money Mindset & Financial Literacy", "order": 1, "description": "Understanding wealth principles and cash flow dynamics."},
            {"title": "Budgeting & Investment Basics", "order": 2, "description": "Building sustainable personal asset strategies."},
            {"title": "Starting & Validating a Side Venture", "order": 3, "description": "From idea validation to your first paying customer."}
        ]
    }
]

async def seed_programs():
    # Ensure tables are created
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        for pdata in programs_data:
            result = await session.execute(select(Program).where(Program.slug == pdata["slug"]))
            existing_program = result.scalars().first()

            if not existing_program:
                program = Program(
                    slug=pdata["slug"],
                    title=pdata["title"],
                    description=pdata["description"],
                    path=pdata["path"],
                    is_active=True
                )
                session.add(program)
                await session.commit()
                await session.refresh(program)
                print(f"Created program: '{program.title}' ({program.slug})")

                # Add modules
                for mdata in pdata["modules"]:
                    module = Module(
                        program_id=program.id,
                        title=mdata["title"],
                        order=mdata["order"],
                        description=mdata["description"]
                    )
                    session.add(module)
                await session.commit()
                print(f"  Added {len(pdata['modules'])} modules for {program.slug}")
            else:
                print(f"Program '{existing_program.title}' ({existing_program.slug}) already exists. Skipping.")

if __name__ == "__main__":
    asyncio.run(seed_programs())
