from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from app.modules.users.user_model import User, Profile
from app.modules.users.user_schema import UserUpdate


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        stmt = select(User).options(selectinload(User.profile)).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_users(self, page: int = 1, limit: int = 20) -> Tuple[List[User], int]:
        offset = (page - 1) * limit
        count_result = await self.db.execute(select(func.count()).select_from(User))
        total = count_result.scalar_one()
        stmt = (
            select(User)
            .options(selectinload(User.profile))
            .offset(offset)
            .limit(limit)
            .order_by(User.id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def search_users(self, email: Optional[str] = None, limit: int = 10, offset: int = 0) -> Tuple[List[User], int]:
        stmt = select(User).options(selectinload(User.profile))
        if email:
            stmt = stmt.where(User.email.ilike(f"%{email}%"))
        count_result = await self.db.execute(select(func.count()).select_from(stmt.subquery()))
        total = count_result.scalar_one()
        stmt = stmt.offset(offset).limit(limit).order_by(User.id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def update_user(self, user_id: int, user_update: UserUpdate) -> Optional[User]:
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        if not user.profile:
            user.profile = Profile(user_id=user.id)
            self.db.add(user.profile)

        update_data = user_update.model_dump(exclude_unset=True)
        profile_fields = {
            "first_name", "last_name", "full_name", "bio", "phone",
            "location", "github_url", "linkedin_url", "degree", "school",
        }

        for field, value in update_data.items():
            if field in profile_fields:
                setattr(user.profile, field, value)
            elif hasattr(user, field):
                setattr(user, field, value)

        await self.db.commit()

        # Recharger avec le profil pour que le validator trouve full_name dans __dict__
        refreshed = await self.get_user_by_id(user_id)
        return refreshed

    async def delete_user(self, user_id: int) -> bool:
        stmt = update(User).where(User.id == user_id).values(is_active=False)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0