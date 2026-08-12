from datetime import datetime

from pydantic import BaseModel, Field

# BaseModel: Pydantic'İn type hintlere göre veri doğrulayan ve proje nesnesi oluşturan temel sınıfıdır.


class GitHubUser(BaseModel):
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


"""
GitHubUser pydantic modelini tanımlar.

Burada:
    - DevLens'in kullanacağı user alanları belirlendi
    - login alanı username olarak eşlendi
    - Nullable alanlar str|None olarak tanımlandı
    - created_at string'ini datetime nesnesine dönüştürüldü
    - eksik veya yanlış tipteki verilerin validation hatası vermesi sağlandı
"""
