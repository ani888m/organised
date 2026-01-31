import sqlite3

def save_order(order_number, customer_name):

    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO orders (order_number, customer_name, status)
        VALUES (?, ?, ?)
    """, (order_number, customer_name, "NEW"))

    conn.commit()
    conn.close()
