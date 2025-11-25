"""
Stock portfolio management queries
"""

CREATE_STOCK = """
    INSERT INTO stocks (symbol, name, quantity, purchase_price, user_id)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id
"""

GET_ALL_STOCKS = """
    SELECT * FROM stocks 
    WHERE user_id = %s 
    ORDER BY created_at DESC
"""

GET_STOCK_BY_ID = "SELECT * FROM stocks WHERE id = %s AND user_id = %s"

UPDATE_STOCK = """
    UPDATE stocks 
    SET symbol = %s, name = %s, quantity = %s, purchase_price = %s
    WHERE id = %s AND user_id = %s
"""

DELETE_STOCK = "DELETE FROM stocks WHERE id = %s AND user_id = %s"

GET_PORTFOLIO_SUMMARY = """
    SELECT 
        COUNT(*) as total_stocks,
        SUM(quantity * purchase_price) as total_value,
        AVG(purchase_price) as avg_price
    FROM stocks 
    WHERE user_id = %s
"""