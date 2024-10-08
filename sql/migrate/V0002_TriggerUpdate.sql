-- Create a function to calculate average rating for a film
CREATE OR REPLACE FUNCTION calculate_average_rating(film_id INTEGER)
RETURNS NUMERIC(4,2) AS $$
DECLARE
    avg_rating NUMERIC(4,2);
BEGIN
    SELECT COALESCE(AVG(TenGrade)::NUMERIC(4,2), 0)
    INTO avg_rating
    FROM REVIEW
    WHERE FilmID = film_id;
    
    RETURN avg_rating;
END;
$$ LANGUAGE plpgsql;

-- Create a trigger to update film rating after a review is added or updated
CREATE OR REPLACE FUNCTION update_film_rating()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE FILM
    SET average_rating = calculate_average_rating(NEW.FilmID)
    WHERE ID = NEW.FilmID;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_film_rating_trigger
AFTER INSERT OR UPDATE ON REVIEW
FOR EACH ROW
EXECUTE FUNCTION update_film_rating();

-- Create a stored procedure to add a new film with genres
CREATE OR REPLACE PROCEDURE add_film_with_genres(
    film_name TEXT,
    film_year INTEGER,
    film_description TEXT,
    genre_names TEXT[]
)
LANGUAGE plpgsql
AS $$
DECLARE
    new_film_id INTEGER;
    genre_id INTEGER;
    genre_name TEXT;
BEGIN
    -- Insert the new film
    INSERT INTO FILM (FilmName, Year, Description)
    VALUES (film_name, film_year, film_description)
    RETURNING ID INTO new_film_id;

    -- Add genres
    FOREACH genre_name IN ARRAY genre_names
    LOOP
        -- Check if the genre exists, if not, create it
        SELECT ID INTO genre_id FROM GENRE WHERE GenreName = genre_name;
        IF NOT FOUND THEN
            INSERT INTO GENRE (GenreName) VALUES (genre_name) RETURNING ID INTO genre_id;
        END IF;

        -- Link the film to the genre
        INSERT INTO FILM_GENRE (FilmID, GenreID) VALUES (new_film_id, genre_id);
    END LOOP;
END;
$$;

-- Add average_rating column to FILM table
ALTER TABLE FILM ADD COLUMN average_rating NUMERIC(3,2) DEFAULT 0;
ALTER TABLE FILM ALTER COLUMN average_rating TYPE NUMERIC(4,2);