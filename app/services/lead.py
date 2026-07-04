from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lead import Lead
from app.schemas.lead import LeadCreate


async def create_lead(db: AsyncSession, data: LeadCreate) -> Lead:
    lead = Lead(name=data.name, phone=data.phone, email=data.email, source=data.source)
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead
