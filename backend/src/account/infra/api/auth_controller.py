from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

from account.application.use_cases.authenticate_user import (
    AuthenticateUserInput,
    AuthenticateUserUseCase,
)
from account.application.use_cases.common.user_output import UserOutput
from account.application.use_cases.create_user import (
    CreateUserInput,
    CreateUserUseCase,
)
from account.domain.user import UserRole, normalize_email
from account.infra.api.user_dependencies import (
    get_authenticate_user_use_case,
    get_create_user_use_case,
)
from account.infra.api.user_presenter import UserPresenter
from shared.infra.api.auth_cookies import clear_auth_cookie, set_auth_cookie
from shared.infra.api.auth_dependencies import AuthContext, require_authenticated

router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register", response_model=UserPresenter, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    use_case: CreateUserUseCase = Depends(get_create_user_use_case),
):
    output = await use_case.execute(
        CreateUserInput(
            name=request.name,
            email=normalize_email(str(request.email)),
            password=request.password,
            role=request.role,
        )
    )
    return UserPresenter.from_output(output)


@router.post("/login", response_model=UserPresenter, status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest,
    use_case: AuthenticateUserUseCase = Depends(get_authenticate_user_use_case),
):
    output = await use_case.execute(
        AuthenticateUserInput(
            email=normalize_email(str(request.email)),
            password=request.password,
        )
    )
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content=UserPresenter.from_output(output.user).model_dump(mode="json"),
    )
    set_auth_cookie(response, output.access_token)
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookie(response)
    return response


@router.get("/me", response_model=UserPresenter, status_code=status.HTTP_200_OK)
async def me(auth: AuthContext = Depends(require_authenticated)):
    return UserPresenter.from_output(UserOutput.from_entity(auth.user))
