from passlib.context import CryptContext
from psycopg2.extras import RealDictCursor
from datetime import date

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_email(conn, email: str):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM filmuser WHERE email = %s", (email,))
        user = cur.fetchone()
        if user:
            print(f"User found: {user}")
        else:
            print(f"No user found for email: {email}")
        return user

def create_user(conn, user):
    # Calculate age
    today = date.today()
    birth_date = user.dateofbirth
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    if age < 13:
        raise ValueError("User must be at least 13 years old to register")

    hashed_password = pwd_context.hash(user.password)
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO filmuser (email, name, gender, dateofbirth, hashedpassword, role)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, email, name, gender, dateofbirth, role
        """, (user.email, user.name, user.gender, user.dateofbirth, hashed_password, 'user'))
        conn.commit()
        return cur.fetchone()

def get_users(conn, skip: int = 0, limit: int = 100):
    with conn.cursor() as cur:
        cur.execute("SELECT id, email, name, gender, dateofbirth FROM filmuser OFFSET %s LIMIT %s", (skip, limit))
        return cur.fetchall()

def create_film(conn, film):
    with conn.cursor() as cur:
        genre_names = film.genres if film.genres else []
        cur.execute("""
            CALL add_film_with_genres(%s, %s, %s, %s::text[]);
            SELECT id, filmname, description, year, average_rating
            FROM film
            WHERE filmname = %s AND year = %s
            ORDER BY id DESC
            LIMIT 1;
        """, (film.filmname, film.year, film.description, genre_names, film.filmname, film.year))
        new_film = cur.fetchone()
        
        film_id = new_film['id']
        
        cur.execute("""
            SELECT g.genrename
            FROM genre g
            JOIN film_genre fg ON g.id = fg.genreid
            WHERE fg.filmid = %s
        """, (film_id,))
        genres = [row['genrename'] for row in cur.fetchall()]
        
        conn.commit()
        
        return {**new_film, 'genres': genres}

def get_films(conn, skip: int = 0, limit: int = 100):
    with conn.cursor() as cur:
        # Get total count
        cur.execute("SELECT COUNT(*) FROM film")
        total_count = cur.fetchone()['count']

        # Get films with pagination
        cur.execute("""
            SELECT f.id, f.filmname, f.description, f.year, 
                   COALESCE(array_agg(g.genrename) FILTER (WHERE g.genrename IS NOT NULL), ARRAY[]::text[]) as genres,
                   COALESCE(AVG(r.tengrade), 0) as average_rating
            FROM film f
            LEFT JOIN film_genre fg ON f.id = fg.filmid
            LEFT JOIN genre g ON fg.genreid = g.id
            LEFT JOIN review r ON f.id = r.filmid
            GROUP BY f.id, f.filmname, f.description, f.year
            ORDER BY f.id
            OFFSET %s LIMIT %s
        """, (skip, limit))
        films = cur.fetchall()

        # Round average_rating to 2 decimal places
        for film in films:
            film['average_rating'] = round(film['average_rating'], 2)

    return films or [], total_count  # Return an empty list if films is None or empty

def create_or_update_review(conn, review_data, film_id, user_id):
    with conn.cursor() as cur:
        # Ensure tengrade is within valid range (1 to 10)
        tengrade = max(1, min(review_data['tengrade'], 10))
        
        cur.execute("""
            SELECT id FROM REVIEW 
            WHERE FilmID = %s AND UserID = %s
        """, (film_id, user_id))
        existing_review = cur.fetchone()

        if existing_review:
            cur.execute("""
                UPDATE REVIEW 
                SET ReviewText = %s, TenGrade = %s, BinaryGrade = %s
                WHERE id = %s
                RETURNING id, ReviewText, TenGrade, BinaryGrade, FilmID, UserID
            """, (review_data['reviewtext'], tengrade, review_data['binarygrade'], existing_review['id']))
        else:
            cur.execute("""
                INSERT INTO REVIEW (ReviewText, TenGrade, BinaryGrade, FilmID, UserID)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, ReviewText, TenGrade, BinaryGrade, FilmID, UserID
            """, (review_data['reviewtext'], tengrade, review_data['binarygrade'], film_id, user_id))

        review = cur.fetchone()

        # Fetch updated film details
        cur.execute("""
            SELECT f.id, f.filmname, f.description, f.year,
                   COALESCE(array_agg(DISTINCT g.genrename) FILTER (WHERE g.genrename IS NOT NULL), ARRAY[]::text[]) as genres,
                   f.average_rating
            FROM film f
            LEFT JOIN film_genre fg ON f.id = fg.filmid
            LEFT JOIN genre g ON fg.genreid = g.id
            WHERE f.id = %s
            GROUP BY f.id
        """, (film_id,))
        film = cur.fetchone()

        # Fetch user details
        cur.execute("""
            SELECT id, name, email, role
            FROM filmuser
            WHERE id = %s
        """, (user_id,))
        user = cur.fetchone()

        conn.commit()

        return {
            'id': review['id'],
            'reviewtext': review['reviewtext'],
            'tengrade': review['tengrade'],
            'binarygrade': review['binarygrade'],
            'film': {
                'id': film['id'],
                'filmname': film['filmname'],
                'description': film['description'],
                'year': film['year'],
                'genres': film['genres'],
                'average_rating': float(film['average_rating'])
            },
            'user': user
        }

def get_film_reviews(conn, film_id: int, skip: int = 0, limit: int = 100):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT r.id, r.reviewtext, r.tengrade, r.binarygrade, 
                   r.userid, u.name as username, u.email, u.role,
                   f.id as film_id, f.filmname, f.description, f.year,
                   COALESCE(array_agg(g.genrename) FILTER (WHERE g.genrename IS NOT NULL), ARRAY[]::text[]) as genres,
                   COALESCE(AVG(r2.tengrade), 0) as average_rating
            FROM review r
            JOIN filmuser u ON r.userid = u.id
            JOIN film f ON r.filmid = f.id
            LEFT JOIN film_genre fg ON f.id = fg.filmid
            LEFT JOIN genre g ON fg.genreid = g.id
            LEFT JOIN review r2 ON f.id = r2.filmid
            WHERE r.filmid = %s
            GROUP BY r.id, u.id, f.id
            ORDER BY r.id
            OFFSET %s LIMIT %s
        """, (film_id, skip, limit))
        reviews = cur.fetchall()
        
        # Restructure the data to match ReviewWithFilmAndUser
        return [{
            'id': review['id'],
            'reviewtext': review['reviewtext'],
            'tengrade': review['tengrade'],
            'binarygrade': review['binarygrade'],
            'film': {
                'id': review['film_id'],
                'filmname': review['filmname'],
                'description': review['description'],
                'year': review['year'],
                'genres': review['genres'],
                'average_rating': round(review['average_rating'], 2)
            },
            'user': {
                'id': review['userid'],
                'name': review['username'],
                'email': review['email'],
                'role': review['role']
            }
        } for review in reviews]

def get_review(conn, review_id: int):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM review WHERE id = %s", (review_id,))
        return cur.fetchone()

def update_review(conn, review_id: int, review_data: dict):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE review
            SET reviewtext = %s, tengrade = %s, binarygrade = %s
            WHERE id = %s
            RETURNING id, reviewtext, tengrade, binarygrade, filmid, userid
        """, (review_data['reviewtext'], review_data['tengrade'], review_data['binarygrade'], review_id))
        updated_review = cur.fetchone()

        if updated_review:
            cur.execute("""
                SELECT f.id, f.filmname, f.description, f.year,
                       COALESCE(array_agg(DISTINCT g.genrename) FILTER (WHERE g.genrename IS NOT NULL), ARRAY[]::text[]) as genres,
                       COALESCE(AVG(r.tengrade), 0) as average_rating
                FROM film f
                LEFT JOIN film_genre fg ON f.id = fg.filmid
                LEFT JOIN genre g ON fg.genreid = g.id
                LEFT JOIN review r ON f.id = r.filmid
                WHERE f.id = %s
                GROUP BY f.id
            """, (updated_review['filmid'],))
            film = cur.fetchone()

            cur.execute("""
                SELECT id, name, email, role
                FROM filmuser
                WHERE id = %s
            """, (updated_review['userid'],))
            user = cur.fetchone()

            conn.commit()

            return {
                'id': updated_review['id'],
                'reviewtext': updated_review['reviewtext'],
                'tengrade': updated_review['tengrade'],
                'binarygrade': updated_review['binarygrade'],
                'film': {
                    'id': film['id'],
                    'filmname': film['filmname'],
                    'description': film['description'],
                    'year': film['year'],
                    'genres': film['genres'],
                    'average_rating': round(film['average_rating'], 2)
                },
                'user': user
            }
    return None

def delete_review(conn, review_id: int):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT r.id, r.reviewtext, r.tengrade, r.binarygrade, r.filmid, r.userid,
                   f.filmname, f.description, f.year,
                   u.name as username, u.email, u.role
            FROM review r
            JOIN film f ON r.filmid = f.id
            JOIN filmuser u ON r.userid = u.id
            WHERE r.id = %s
        """, (review_id,))
        review_data = cur.fetchone()

        if not review_data:
            return None

        cur.execute("DELETE FROM review WHERE id = %s", (review_id,))

        cur.execute("""
            SELECT COALESCE(AVG(r.tengrade), 0) as average_rating,
                   COALESCE(array_agg(DISTINCT g.genrename) FILTER (WHERE g.genrename IS NOT NULL), ARRAY[]::text[]) as genres
            FROM film f
            LEFT JOIN review r ON f.id = r.filmid
            LEFT JOIN film_genre fg ON f.id = fg.filmid
            LEFT JOIN genre g ON fg.genreid = g.id
            WHERE f.id = %s
            GROUP BY f.id
        """, (review_data['filmid'],))
        film_data = cur.fetchone()

        conn.commit()

        return {
            'id': review_data['id'],
            'reviewtext': review_data['reviewtext'],
            'tengrade': review_data['tengrade'],
            'binarygrade': review_data['binarygrade'],
            'film': {
                'id': review_data['filmid'],
                'filmname': review_data['filmname'],
                'description': review_data['description'],
                'year': review_data['year'],
                'genres': film_data['genres'],
                'average_rating': round(film_data['average_rating'], 2)
            },
            'user': {
                'id': review_data['userid'],
                'name': review_data['username'],
                'email': review_data['email'],
                'role': review_data['role']
            }
        }

def search_films(conn, name: str = None, genre: str = None, year: int = None):
    query = """
        SELECT DISTINCT f.id, f.filmname, f.description, f.year,
               COALESCE(array_agg(g.genrename) FILTER (WHERE g.genrename IS NOT NULL), ARRAY[]::text[]) as genres,
               COALESCE(AVG(r.tengrade), 0) as average_rating
        FROM film f
        LEFT JOIN film_genre fg ON f.id = fg.filmid
        LEFT JOIN genre g ON fg.genreid = g.id
        LEFT JOIN review r ON f.id = r.filmid
        WHERE 1=1
    """
    params = []
    if name:
        query += " AND f.filmname ILIKE %s"
        params.append(f"%{name}%")
    if genre:
        query += " AND g.genrename = %s"
        params.append(genre)
    if year:
        query += " AND f.year = %s"
        params.append(year)
    
    query += " GROUP BY f.id, f.filmname, f.description, f.year"
    
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()

def create_genre(conn, genre):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO genre (genrename)
            VALUES (%s)
            RETURNING id, genrename
        """, (genre.genrename,))
        conn.commit()
        return cur.fetchone()

def get_genres(conn, skip: int = 0, limit: int = 100):
    with conn.cursor() as cur:
        cur.execute("SELECT id, genrename FROM genre OFFSET %s LIMIT %s", (skip, limit))
        return cur.fetchall()

def add_film_genre(conn, film_id: int, genre_id: int):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO film_genre (filmid, genreid)
            VALUES (%s, %s)
            RETURNING filmid, genreid
        """, (film_id, genre_id))
        conn.commit()
        return cur.fetchone()

def get_film(conn, film_id: int):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT f.*, 
                   ARRAY_AGG(DISTINCT g.genrename) AS genres,
                   COALESCE(AVG(r.tengrade), 0) AS average_rating
            FROM FILM f
            LEFT JOIN FILM_GENRE fg ON f.id = fg.filmid
            LEFT JOIN GENRE g ON fg.genreid = g.id
            LEFT JOIN REVIEW r ON f.id = r.filmid
            WHERE f.id = %s
            GROUP BY f.id
        """, (film_id,))
        film = cur.fetchone()
        if film:
            film['average_rating'] = round(film['average_rating'], 2)  # Округляем до двух знаков после запятой
        return film

def update_film(conn, film_id: int, film_data: dict):
    with conn.cursor() as cur:
        # Подготовим запрос и параметры
        update_fields = []
        params = []
        if 'filmname' in film_data:
            update_fields.append("filmname = %s")
            params.append(film_data['filmname'])
        if 'description' in film_data:
            update_fields.append("description = %s")
            params.append(film_data['description'])
        if 'year' in film_data:
            update_fields.append("year = %s")
            params.append(film_data['year'])
        
        if not update_fields:
            return None  # Нет данных для обновления
        
        update_query = f"""
            UPDATE film
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING id, filmname, description, year
        """
        params.append(film_id)
        
        cur.execute(update_query, params)
        updated_film = cur.fetchone()
        print(f"Updated film: {updated_film}")

        if 'genres' in film_data:
            cur.execute("DELETE FROM film_genre WHERE filmid = %s", (film_id,))
            print(f"Deleted film genres for film {film_id}")
            
            for genre_name in film_data['genres']:
                cur.execute("SELECT id FROM genre WHERE genrename = %s", (genre_name,))
                genre = cur.fetchone()
                if genre:
                    cur.execute("INSERT INTO film_genre (filmid, genreid) VALUES (%s, %s)", (film_id, genre['id']))
                else:
                    cur.execute("INSERT INTO genre (genrename) VALUES (%s) RETURNING id", (genre_name,))
                    new_genre_id = cur.fetchone()['id']
                    cur.execute("INSERT INTO film_genre (filmid, genreid) VALUES (%s, %s)", (film_id, new_genre_id))
                print(f"Added film genre {genre_name} for film {film_id}")

        cur.execute("""
            SELECT f.id, f.filmname, f.description, f.year, 
                   COALESCE(array_agg(g.genrename) FILTER (WHERE g.genrename IS NOT NULL), ARRAY[]::text[]) as genres,
                   COALESCE(AVG(r.tengrade), 0) as average_rating
            FROM film f
            LEFT JOIN film_genre fg ON f.id = fg.filmid
            LEFT JOIN genre g ON fg.genreid = g.id
            LEFT JOIN review r ON f.id = r.filmid
            WHERE f.id = %s
            GROUP BY f.id, f.filmname, f.description, f.year
        """, (film_id,))
        updated_film_with_genres = cur.fetchone()
        updated_film_with_genres['average_rating'] = round(updated_film_with_genres['average_rating'], 2)

        conn.commit()
        return updated_film_with_genres

def delete_film(conn, film_id: int):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM film_genre WHERE filmid = %s", (film_id,))
        cur.execute("DELETE FROM film WHERE id = %s RETURNING id", (film_id,))
        deleted = cur.fetchone()
        conn.commit()
        return deleted is not None

def authenticate_user(conn, email: str, password: str):
    user = get_user_by_email(conn, email)
    if not user:
        return False
    if not pwd_context.verify(password, user['hashedpassword']):
        return False
    return user

def get_user_role(conn, user_id: int):
    with conn.cursor() as cur:
        cur.execute("SELECT role FROM filmuser WHERE id = %s", (user_id,))
        result = cur.fetchone()
        return result['role'] if result else None

def update_genre(conn, genre_id: int, genre_data: dict):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE genre
            SET genrename = %s
            WHERE id = %s
            RETURNING id, genrename
        """, (genre_data['genrename'], genre_id))
        updated_genre = cur.fetchone()
        conn.commit()
        return updated_genre

def delete_genre(conn, genre_id: int):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM film_genre WHERE genreid = %s", (genre_id,))
        cur.execute("DELETE FROM genre WHERE id = %s RETURNING id", (genre_id,))
        deleted = cur.fetchone()
        conn.commit()
        return deleted is not None
