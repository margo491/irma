from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.blog_post import BlogPost
from app.schemas.blog_post import BlogPostOut

router = APIRouter()


@router.get("/", response_model=list[BlogPostOut])
async def list_blog(limit: int = Query(50, le=100), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BlogPost).order_by(BlogPost.published_at.desc()).limit(limit))
    return result.scalars().all()


@router.get("/{post_id}", response_model=BlogPostOut)
async def get_blog_post(post_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.get(BlogPost, post_id)
    if not item:
        raise HTTPException(status_code=404, detail="Post not found")
    return item
