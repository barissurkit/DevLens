from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# BaseModel: Pydantic'İn type hintlere göre veri doğrulayan ve proje nesnesi oluşturan temel sınıfıdır.


class GitHubUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    github_user_id: int = Field(validation_alias="id", ge=1)
    username: str = Field(validation_alias="login")  # login -> username
    name: str | None
    avatar_url: str
    bio: str | None
    public_repos: int
    followers: int
    following: int
    html_url: str
    created_at: datetime


class GitHubRepository(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str | None
    html_url: str
    primary_language: str | None = Field(validation_alias="language")
    stars: int = Field(validation_alias="stargazers_count")
    forks: int = Field(validation_alias="forks_count")
    topics: list[str]
    created_at: datetime
    updated_at: datetime
    archived: bool
    fork: bool
    default_branch: str


class GitHubFileContent(BaseModel):
    path: str
    name: str
    content: str
    size: int
    sha: str


class GitHubRepositoryTree(BaseModel):
    paths: list[str]
    truncated: bool


"""
GitHubUser pydantic modelini tanımlar.

Burada:
    - DevLens'in kullanacağı user alanları belirlendi
    - login alanı username olarak eşlendi
    - Nullable alanlar str|None olarak tanımlandı
    - created_at string'ini datetime nesnesine dönüştürüldü
    - eksik veya yanlış tipteki verilerin validation hatası vermesi sağlandı
"""
