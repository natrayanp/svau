"""
Flashcard management queries
"""

CREATE_FLASHCARD = """
    INSERT INTO flashcards (question, answer, deck_id, user_id)
    VALUES (%s, %s, %s, %s)
    RETURNING id
"""

GET_FLASHCARDS = """
    SELECT * FROM flashcards 
    WHERE user_id = %s 
    ORDER BY created_at DESC
"""

GET_FLASHCARDS_BY_DECK = """
    SELECT * FROM flashcards 
    WHERE deck_id = %s AND user_id = %s
    ORDER BY created_at DESC
"""

GET_FLASHCARD_BY_ID = "SELECT * FROM flashcards WHERE id = %s AND user_id = %s"

UPDATE_FLASHCARD = """
    UPDATE flashcards 
    SET question = %s, answer = %s, deck_id = %s, updated_at = CURRENT_TIMESTAMP
    WHERE id = %s AND user_id = %s
"""

DELETE_FLASHCARD = "DELETE FROM flashcards WHERE id = %s AND user_id = %s"

GET_USER_FLASHCARDS = """
    SELECT f.*, d.name as deck_name
    FROM flashcards f
    LEFT JOIN decks d ON f.deck_id = d.id
    WHERE f.user_id = %s
    ORDER BY f.created_at DESC
"""