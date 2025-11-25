"""
User profile and related queries
"""

CREATE_USER_PROFILE = """
INSERT INTO user_profiles (user_id, bio, avatar_url, date_of_birth, created_at)
VALUES (%s, %s, %s, %s, %s)
RETURNING id
"""

GET_USER_PROFILE = """
SELECT * FROM user_profiles 
WHERE user_id = %s
"""

UPDATE_USER_PROFILE = """
UPDATE user_profiles 
SET bio = %s, avatar_url = %s, date_of_birth = %s, updated_at = CURRENT_TIMESTAMP
WHERE user_id = %s
"""

GET_USER_WITH_PROFILE = """
SELECT 
    u.*,
    up.bio,
    up.avatar_url,
    up.date_of_birth,
    up.created_at as profile_created_at
FROM users u
LEFT JOIN user_profiles up ON u.id = up.user_id
WHERE u.id = %s
"""

GET_USER_STATS = """
SELECT 
    u.id,
    u.display_name,
    u.email,
    COUNT(DISTINCT f.id) as flashcard_count,
    COUNT(DISTINCT p.id) as portfolio_count,
    u.created_at
FROM users u
LEFT JOIN flashcards f ON u.id = f.user_id
LEFT JOIN portfolio_items p ON u.id = p.user_id
WHERE u.id = %s
GROUP BY u.id, u.display_name, u.email, u.created_at
"""