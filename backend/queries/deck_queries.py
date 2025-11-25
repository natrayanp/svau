"""
Flashcard deck management queries
"""

CREATE_DECK = """
    INSERT INTO decks (name, description, user_id)
    VALUES (%s, %s, %s)
    RETURNING id
"""

GET_ALL_DECKS = """
    SELECT * FROM decks 
    WHERE user_id = %s 
    ORDER BY created_at DESC
"""

GET_DECK_BY_ID = "SELECT * FROM decks WHERE id = %s AND user_id = %s"

GET_DECK_WITH_FLASHCARDS = """
    SELECT d.*, 
           JSON_AGG(
               JSON_BUILD_OBJECT(
                   'id', f.id,
                   'question', f.question,
                   'answer', f.answer,
                   'created_at', f.created_at
               ) ORDER BY f.created_at DESC
           ) as flashcards
    FROM decks d
    LEFT JOIN flashcards f ON d.id = f.deck_id AND f.user_id = %s
    WHERE d.id = %s AND d.user_id = %s
    GROUP BY d.id
"""

UPDATE_DECK = """
    UPDATE decks 
    SET name = %s, description = %s 
    WHERE id = %s AND user_id = %s
"""

DELETE_DECK = "DELETE FROM decks WHERE id = %s AND user_id = %s"