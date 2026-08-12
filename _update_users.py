import sqlite3

conn = sqlite3.connect('sistema_grafica.db')
cur = conn.cursor()
cur.execute("UPDATE pedidos SET usuario_nome = 'Thaissa' WHERE usuario_nome = 'Thaissa/Michel'")
conn.commit()
print(cur.rowcount)
conn.close()
