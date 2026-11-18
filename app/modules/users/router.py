from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.users.dependencies import CurrentUser
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.users.service import UserService

auth_router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)

users_router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


def get_user_service(
    db: AsyncSession = Depends(get_db),
) -> UserService:

    return UserService(
        UserRepository(db)
    )


@auth_router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
async def register(
    data: RegisterRequest,
    service: UserService = Depends(get_user_service),
):
    _, access_token, refresh_token = await service.register(data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in",
)
async def login(
    data: LoginRequest,
    service: UserService = Depends(get_user_service),
):
    _, access_token, refresh_token = await service.login(data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@auth_router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Exchange a refresh token for a new access token",
)
async def refresh(
    data: RefreshRequest,
    service: UserService = Depends(get_user_service),
):
    access_token = await service.refresh(data.refresh_token)

    return AccessTokenResponse(access_token=access_token)


@users_router.get(
    "/me",
    response_model=UserResponse,
    summary="The logged-in user",
)
async def get_me(
    current_user: CurrentUser,
):
    return current_user
