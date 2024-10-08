from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from database import get_db
import schemas, crud
from crud import authenticate_user
from psycopg2.extras import RealDictConnection
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
FILMADMIN = "filmadmin"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")



def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), conn: RealDictConnection = Depends(get_db)):
    print(f"Attempting to get current user with token: {token[:10]}...")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"Token decoded successfully. Payload: {payload}")
        email = payload.get("sub")
        print(f"Extracted email: {email}")
        if email is None:
            print("Email not found in token payload")
            raise credentials_exception
    except JWTError as e:
        print(f"JWT decode error: {str(e)}")
        raise credentials_exception
    user = crud.get_user_by_email(conn, email=email)
    if user is None:
        print(f"User not found for email: {email}")
        raise credentials_exception
    print(f"User found: {user['email']}")
    return user

def check_filmadmin(current_user: dict = Depends(get_current_user), conn: RealDictConnection = Depends(get_db)):
    print(f"Checking filmadmin for user: {current_user}")
    user_role = crud.get_user_role(conn, current_user['id'])
    print(f"User role: {user_role}")
    if user_role != FILMADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return current_user

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), conn: RealDictConnection = Depends(get_db)):
    try:
        user = authenticate_user(conn, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user['email']}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, conn: RealDictConnection = Depends(get_db)):
    db_user = crud.get_user_by_email(conn, email=user.email)
    if db_user:
        raise HTTPException(status_code=403, detail="Email already registered")
    try:
        return crud.create_user(conn=conn, user=user)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@app.get("/users/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, conn: RealDictConnection = Depends(get_db)):
    users = crud.get_users(conn, skip=skip, limit=limit)
    return users

@app.post("/films/", response_model=schemas.Film)
def create_film(film: schemas.FilmCreate, conn: RealDictConnection = Depends(get_db), current_user: dict = Depends(check_filmadmin)):
    return crud.create_film(conn=conn, film=film)

@app.get("/films/", response_model=List[schemas.Film])
def read_films(response: Response, skip: int = 0, limit: int = 100, conn: RealDictConnection = Depends(get_db)):
    films, total_count = crud.get_films(conn, skip=skip, limit=limit)
    response.headers["X-Total-Count"] = str(total_count)
    return films

@app.get("/reviews/", response_model=List[schemas.Review])
def read_reviews(skip: int = 0, limit: int = 100, conn: RealDictConnection = Depends(get_db)):
    reviews = crud.get_reviews(conn, skip=skip, limit=limit)
    return reviews

@app.get("/films/search/", response_model=List[schemas.Film])
def search_films(name: str = None, genre: str = None, year: int = None, conn: RealDictConnection = Depends(get_db)):
    return crud.search_films(conn, name=name, genre=genre, year=year)

@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user

@app.post("/genres/", response_model=schemas.Genre)
def create_genre(genre: schemas.GenreCreate, conn: RealDictConnection = Depends(get_db), current_user: dict = Depends(check_filmadmin)):
    print(f"Attempting to create genre {genre}")
    print(f"Creating genre {genre} by user {current_user['email']}")
    return crud.create_genre(conn, genre)

@app.get("/genres/", response_model=List[schemas.Genre])
def read_genres(skip: int = 0, limit: int = 100, conn: RealDictConnection = Depends(get_db)):
    genres = crud.get_genres(conn, skip=skip, limit=limit)
    return genres

@app.get("/films/{film_id}", response_model=schemas.Film)
def read_film(film_id: int, conn: RealDictConnection = Depends(get_db)):
    film = crud.get_film(conn, film_id)
    if film is None:
        raise HTTPException(status_code=404, detail="Film not found")
    return film

@app.post("/films/{film_id}/update", response_model=schemas.Film)
def update_film(
    film_id: int,
    film: schemas.FilmUpdate,
    conn: RealDictConnection = Depends(get_db),
    current_user: dict = Depends(check_filmadmin)
):
    print(f"Attempting to update film {film_id}")
    print(f"Updating film {film_id} by user {current_user['email']}")
    updated_film = crud.update_film(conn, film_id, film.dict(exclude_unset=True))
    if updated_film is None:
        raise HTTPException(status_code=404, detail="Film not found")
    return updated_film

@app.delete("/films/{film_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_film(film_id: int, conn: RealDictConnection = Depends(get_db), current_user: dict = Depends(check_filmadmin)):
    if not crud.delete_film(conn, film_id):
        raise HTTPException(status_code=404, detail="Film not found")

@app.post("/genres/{genre_id}/update", response_model=schemas.Genre)
def update_genre(genre_id: int, genre: schemas.GenreCreate, conn: RealDictConnection = Depends(get_db), current_user: dict = Depends(check_filmadmin)):
    updated_genre = crud.update_genre(conn, genre_id, genre.dict())
    if updated_genre is None:
        raise HTTPException(status_code=404, detail="Genre not found")
    return updated_genre

@app.delete("/genres/{genre_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_genre(genre_id: int, conn: RealDictConnection = Depends(get_db), current_user: dict = Depends(check_filmadmin)):
    if not crud.delete_genre(conn, genre_id):
        raise HTTPException(status_code=404, detail="Genre not found")

@app.get("/films/{film_id}/reviews", response_model=List[schemas.ReviewWithFilmAndUser])
def read_film_reviews(film_id: int, skip: int = 0, limit: int = 100, conn: RealDictConnection = Depends(get_db)):
    reviews = crud.get_film_reviews(conn, film_id, skip=skip, limit=limit)
    return reviews

@app.post("/films/{film_id}/reviews", response_model=schemas.ReviewWithFilmAndUser)
def create_or_update_review(
    film_id: int,
    review: schemas.ReviewCreate,
    current_user: dict = Depends(get_current_user),
    conn: RealDictConnection = Depends(get_db)
):
    return crud.create_or_update_review(conn, review.dict(), film_id, current_user["id"])

@app.post("/reviews/{review_id}/update", response_model=schemas.ReviewWithFilmAndUser)
def update_review(
    review_id: int,
    review: schemas.ReviewUpdate,
    current_user: dict = Depends(get_current_user),
    conn: RealDictConnection = Depends(get_db)
):
    db_review = crud.get_review(conn, review_id)
    if db_review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    if db_review['userid'] != current_user['id'] and current_user['role'] != 'filmadmin':
        raise HTTPException(status_code=403, detail="Not authorized to update this review")
    return crud.update_review(conn, review_id, review.dict())

@app.delete("/reviews/{review_id}", response_model=schemas.ReviewWithFilmAndUser)
def delete_review(
    review_id: int, 
    conn: RealDictConnection = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    db_review = crud.get_review(conn, review_id)
    if db_review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    if db_review['userid'] != current_user['id'] and current_user['role'] != FILMADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to delete this review")
    deleted_review = crud.delete_review(conn, review_id)
    if deleted_review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return deleted_review

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)