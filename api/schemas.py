from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import date

class UserBase(BaseModel):
    email: EmailStr
    name: str
    gender: Optional[str] = None
    dateofbirth: Optional[date] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    role: str

    class Config:
        orm_mode = True

class FilmBase(BaseModel):
    filmname: str
    description: Optional[str] = None
    year: int

class FilmCreate(FilmBase):
    genres: List[str] = []

class Film(BaseModel):
    id: int
    filmname: str
    description: str
    year: int
    genres: List[str]
    average_rating: float

    class Config:
        from_attributes = True

class ReviewBase(BaseModel):
    reviewtext: str
    tengrade: int
    binarygrade: bool

class ReviewCreate(BaseModel):
    reviewtext: str
    tengrade: int = Field(..., ge=1, le=10)
    binarygrade: bool

class ReviewUpdate(ReviewBase):
    pass

class Review(ReviewBase):
    id: int
    film: Film
    user: User

    class Config:
        orm_mode = True

class GenreBase(BaseModel):
    genrename: str

class GenreCreate(GenreBase):
    pass

class Genre(GenreBase):
    id: int

    class Config:
        orm_mode = True

class FilmUpdate(BaseModel):
    filmname: Optional[str] = None
    description: Optional[str] = None
    year: Optional[int] = None
    genres: Optional[List[str]] = None

class FilmInReview(BaseModel):
    id: int
    filmname: str
    description: str
    year: int
    genres: List[str]
    average_rating: float

class UserInReview(BaseModel):
    id: int
    name: str
    email: str
    role: str

class ReviewWithFilmAndUser(BaseModel):
    id: int
    reviewtext: str
    tengrade: int
    binarygrade: bool
    film: FilmInReview
    user: UserInReview
