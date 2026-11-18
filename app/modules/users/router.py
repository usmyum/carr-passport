from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.users.dependencies import CurrentUser
from app.modules.users.repository import (
    OneTimeTokenRepository,
    RefreshTokenRepository,
    UserRepository,
)
from app.modules.users.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.modules.users.service import UserService
from app.shared.email import EmailSender, get_email_sender
from app.shared.rate_limit import rate_limit

auth_router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)

users_router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

MINUTE = 60
HOUR = 60 * MINUTE


def get_user_service(
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSender = Depends(get_email_sender),
) -> UserService:

    return UserService(
        repository=UserRepository(db),
        refresh_token_repository=RefreshTokenRepository(db),
        one_time_token_repository=OneTimeTokenRepository(db),
        email_sender=email_sender,
    )


@auth_router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account (sends a verification email)",
    dependencies=[Depends(rate_limit("register", 10, HOUR))],
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
    dependencies=[Depends(rate_limit("login", 10, MINUTE))],
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
    response_model=TokenResponse,
    summary="Swap a refresh token for a new access + refresh token",
    description=(
        "The refresh token you send is used up — store the new one. "
        "Sending a used token again logs that session out everywhere."
    ),
    dependencies=[Depends(rate_limit("refresh", 30, MINUTE))],
)
async def refresh(
    data: RefreshRequest,
    service: UserService = Depends(get_user_service),
):
    access_token, refresh_token = await service.refresh(data.refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@auth_router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="End this session",
)
async def logout(
    data: RefreshRequest,
    service: UserService = Depends(get_user_service),
):
    await service.logout(data.refresh_token)


@auth_router.post(
    "/verify-email",
    response_model=UserResponse,
    summary="Confirm your email with the token from the verification email",
    dependencies=[Depends(rate_limit("verify-email", 10, 15 * MINUTE))],
)
async def verify_email(
    data: VerifyEmailRequest,
    service: UserService = Depends(get_user_service),
):
    return await service.verify_email(data.token)


@auth_router.post(
    "/resend-verification",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send the verification email again",
    dependencies=[Depends(rate_limit("resend-verification", 3, 15 * MINUTE))],
)
async def resend_verification(
    current_user: CurrentUser,
    service: UserService = Depends(get_user_service),
):
    await service.resend_verification(current_user)


@auth_router.post(
    "/forgot-password",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Email a password-reset link",
    description="Always answers 202, whether or not the email has an account.",
    dependencies=[Depends(rate_limit("forgot-password", 5, 15 * MINUTE))],
)
async def forgot_password(
    data: ForgotPasswordRequest,
    service: UserService = Depends(get_user_service),
):
    await service.forgot_password(data.email)


@auth_router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Set a new password with the token from the reset email",
    description="Also logs out every existing session.",
    dependencies=[Depends(rate_limit("reset-password", 10, 15 * MINUTE))],
)
async def reset_password(
    data: ResetPasswordRequest,
    service: UserService = Depends(get_user_service),
):
    await service.reset_password(data)


@users_router.get(
    "/me",
    response_model=UserResponse,
    summary="The logged-in user",
)
async def get_me(
    current_user: CurrentUser,
):
    return current_user
