-- Create Film table
CREATE TABLE FILM (
    ID SERIAL PRIMARY KEY,
    FilmName TEXT NOT NULL,
    Year INTEGER NOT NULL,
    Description TEXT
);

-- Create User table
CREATE TABLE FILMUSER (
    ID SERIAL PRIMARY KEY,
    Email TEXT NOT NULL UNIQUE,
    Name TEXT NOT NULL,
    Gender TEXT,
    DateOfBirth DATE,
    HashedPassword TEXT NOT NULL,
    Role TEXT NOT NULL DEFAULT 'user'
);

-- Create Genre table
CREATE TABLE GENRE (
    ID SERIAL PRIMARY KEY,
    GenreName TEXT NOT NULL UNIQUE
);

-- Create Review table
CREATE TABLE REVIEW (
    ID SERIAL PRIMARY KEY,
    ReviewText TEXT NOT NULL,
    TenGrade INTEGER NOT NULL CHECK (TenGrade >= 1 AND TenGrade <= 10),
    BinaryGrade BOOLEAN NOT NULL,
    FilmID INTEGER NOT NULL,
    UserID INTEGER NOT NULL,
    CONSTRAINT fk_user FOREIGN KEY (UserID) REFERENCES FILMUSER (ID),
    CONSTRAINT fk_film FOREIGN KEY (FilmID) REFERENCES FILM (ID)
);

-- Create a joint table for MtM relationship of Genre and Film
CREATE TABLE FILM_GENRE (
    GenreID INTEGER NOT NULL,
    FilmID INTEGER NOT NULL,
    PRIMARY KEY (GenreID, FilmID),
    CONSTRAINT fk_genre FOREIGN KEY (GenreID) REFERENCES GENRE (ID),
    CONSTRAINT fk_film FOREIGN KEY (FilmID) REFERENCES FILM (ID)
);
