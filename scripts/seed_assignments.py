import asyncio
import uuid
from app.database import AsyncSessionLocal
from app.models import Program, Assignment, Module
from sqlalchemy import select

ASSIGNMENTS_DATA = [
    {
        "program_slug": "leadership",
        "assignments": [
            {
                "title": "Leadership Philosophy & Emotional Intelligence Audit",
                "description": "Synthesize your leadership core values and conduct a 360-degree emotional intelligence self-assessment across self-awareness, empathy, and organizational influence.",
                "instructions": (
                    "### Objectives & Deliverables\n\n"
                    "1. **Core Philosophy Statement**: Articulate your foundational leadership philosophy in 150-250 words, citing the primary ethical and strategic pillars that guide your decision-making.\n"
                    "2. **EI Quadrant Evaluation**: Evaluate your current behavioral strengths and friction points across Daniel Goleman's 4 EI domains (Self-Awareness, Self-Management, Social Awareness, Relationship Management).\n"
                    "3. **Active Listening Action Plan**: Document 3 tangible commitments for active listening in high-stakes meetings.\n"
                    "4. **Format**: Submit as formatted text below or provide a direct link to your shared document (PDF, Google Doc, Word)."
                ),
                "rubric": "Depth of self-reflection (40%), Alignment with EI framework (30%), Concrete actionable goals (30%)",
                "submission_type": "text_or_file",
                "max_points": 100,
                "due_days": 7,
                "order": 1,
            },
            {
                "title": "GROW Coaching Mentorship Case Study",
                "description": "Apply Sir John Whitmore's GROW coaching framework to resolve performance and motivation barriers in a realistic organizational scenario.",
                "instructions": (
                    "### Case Study Scenario\n\n"
                    "Choose an actual colleague mentorship opportunity or an industry case study where a high-potential individual feels disconnected or underperforming.\n\n"
                    "### Required Elements\n"
                    "- **Goal (G)**: Clarify specific, inspiring, measurable outcomes.\n"
                    "- **Reality (R)**: Objective diagnostic questions without judgment.\n"
                    "- **Options (O)**: Brainstorming minimum 4 strategic approaches.\n"
                    "- **Will/Way Forward (W)**: Commitment cadence, accountability checks, timeline.\n"
                    "- Provide dialogue scripts illustrating powerful open-ended questions."
                ),
                "rubric": "Clarity of Coaching Structure (35%), Quality of Open-Ended Inquiry (35%), Practical Accountability System (30%)",
                "submission_type": "text_or_file",
                "max_points": 100,
                "due_days": 14,
                "order": 2,
            },
        ],
    },
    {
        "program_slug": "tech-ai",
        "assignments": [
            {
                "title": "AI System Architecture & Ethics Evaluation",
                "description": "Evaluate the enterprise integration of generative AI models, assessing data governance, hallucination mitigation, and ethical boundaries.",
                "instructions": (
                    "### Assignment Requirements\n\n"
                    "1. Propose an architectural diagram/overview for a Retrieval-Augmented Generation (RAG) pipeline.\n"
                    "2. Explain your vector embedding database choice, chunking strategy, and reranking strategy.\n"
                    "3. Define guardrails for bias detection, prompt injection mitigation, and PII anonymization.\n"
                    "4. Submit your written report or architecture blueprint."
                ),
                "rubric": "Technical Feasibility (40%), Security & Ethics Guardrails (35%), Architectural Clarity (25%)",
                "submission_type": "text_or_file",
                "max_points": 100,
                "due_days": 10,
                "order": 1,
            }
        ],
    },
    {
        "program_slug": "finance",
        "assignments": [
            {
                "title": "Personal Capital Allocation & Cash Flow Blueprint",
                "description": "Build an exhaustive personal wealth-building model integrating cash flow buffers, tax-advantaged accounts, and risk-adjusted asset allocation.",
                "instructions": (
                    "### Blueprint Specifications\n\n"
                    "1. **Cash Flow Breakdown**: Structure 50/30/20 or personalized allocation ratios for monthly inflows.\n"
                    "2. **Risk Reserves**: Define liquid emergency reserve requirements and high-yield placement.\n"
                    "3. **Long-Term Growth**: Outline diversified low-cost index and real estate allocation targets.\n"
                    "4. **Downside Hedging**: Identify term life, health, and property risk mitigation policies."
                ),
                "rubric": "Financial Rigor (40%), Comprehensive Asset Strategy (35%), Execution Feasibility (25%)",
                "submission_type": "text_or_file",
                "max_points": 100,
                "due_days": 10,
                "order": 1,
            }
        ],
    },
]

async def seed_assignments():
    async with AsyncSessionLocal() as db:
        for prog_data in ASSIGNMENTS_DATA:
            slug = prog_data["program_slug"]
            res = await db.execute(select(Program).where(Program.slug == slug))
            program = res.scalar_one_or_none()
            if not program:
                print(f"Program with slug '{slug}' not found, skipping.")
                continue

            # Fetch first module for association if available
            res_mod = await db.execute(
                select(Module).where(Module.program_id == program.id).order_by(Module.order)
            )
            modules = res_mod.scalars().all()

            for idx, a_data in enumerate(prog_data["assignments"]):
                # Check if assignment with same title already exists in this program
                res_exist = await db.execute(
                    select(Assignment).where(
                        Assignment.program_id == program.id,
                        Assignment.title == a_data["title"],
                    )
                )
                if res_exist.scalar_one_or_none():
                    print(f"Assignment '{a_data['title']}' already exists for {slug}.")
                    continue

                mod_id = modules[idx % len(modules)].id if modules else None
                assignment = Assignment(
                    id=str(uuid.uuid4()),
                    program_id=program.id,
                    module_id=mod_id,
                    title=a_data["title"],
                    description=a_data["description"],
                    instructions=a_data["instructions"],
                    rubric=a_data["rubric"],
                    submission_type=a_data["submission_type"],
                    max_points=a_data["max_points"],
                    due_days=a_data["due_days"],
                    order=a_data["order"],
                )
                db.add(assignment)
                print(f"Added assignment: '{a_data['title']}' to {slug}")

        await db.commit()
        print("All assignments seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_assignments())
