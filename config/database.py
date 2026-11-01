import sqlite3

DB_NAME = "sistema_grafica.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # 1. TABELA DE CLIENTES
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                documento TEXT DEFAULT '',
                telefone TEXT DEFAULT '',
                email TEXT DEFAULT '',
                endereco TEXT DEFAULT ''
            )
        """)

        # 2. TABELA DE PRODUTOS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preco_venda REAL DEFAULT 0.0,
                quantidade INTEGER DEFAULT 0
            )
        """)

        # 3. TABELA DE USUÁRIOS / PERFIS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                senha TEXT NOT NULL
            )
        """)

        usuarios_padrao = [
            ('Thaissa', '230605'),
            ('Michel', '230605'),
            ('Davi', '080813'),
            ('Marketing', '021206')
        ]

        cursor.executemany("""
            INSERT OR IGNORE INTO usuarios (nome, senha) VALUES (?, ?)
        """, usuarios_padrao)

        # 4. TABELA DE PEDIDOS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER,
                valor_total REAL DEFAULT 0.0,
                valor_pago REAL DEFAULT 0.0,
                desconto REAL DEFAULT 0.0,
                status_producao TEXT DEFAULT 'PENDENTE',
                status_pagamento TEXT DEFAULT 'PENDENTE',
                forma_pagamento TEXT DEFAULT '',
                observacao TEXT DEFAULT '',
                data TEXT,
                usuario_nome TEXT DEFAULT 'Sistema',
                tipo TEXT DEFAULT 'VENDA',
                FOREIGN KEY (cliente_id) REFERENCES clientes (id)
            )
        """)

        # 5. TABELA: ITENS DO PEDIDO (Com coluna de observacao individual por item)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS itens_pedido (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL,
                produto_id INTEGER,
                nome_produto TEXT NOT NULL,
                quantidade INTEGER NOT NULL,
                preco_unitario REAL NOT NULL,
                subtotal REAL NOT NULL,
                observacao TEXT DEFAULT '',
                FOREIGN KEY (pedido_id) REFERENCES pedidos (id) ON DELETE CASCADE,
                FOREIGN KEY (produto_id) REFERENCES produtos (id)
            )
        """)

        # 6. TABELA: IMAGENS DO PEDIDO
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pedido_imagens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL,
                caminho_arquivo TEXT NOT NULL,
                FOREIGN KEY (pedido_id) REFERENCES pedidos (id) ON DELETE CASCADE
            )
        """)

        # 7. TABELA: CONTAS A PAGAR
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contas_a_pagar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descricao TEXT NOT NULL,
                categoria TEXT DEFAULT 'Geral',
                valor REAL NOT NULL,
                data_vencimento TEXT NOT NULL,
                status TEXT DEFAULT 'PENDENTE',
                data_pagamento TEXT,
                recorrente INTEGER DEFAULT 0,
                dia_vencimento INTEGER
            )
        """)

        # 8. TABELA: CONFIGURAÇÕES DO SISTEMA
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracoes (
                chave TEXT PRIMARY KEY,
                valor TEXT DEFAULT ''
            )
        """)

        configs_padrao = [
            ('nome_empresa', 'SISTEMA GRÁFICA'),
            ('subtitulo_empresa', 'Gestão Interna & Produção Gráfica'),
            ('documento_empresa', ''),
            ('telefone_empresa', ''),
            ('endereco_empresa', ''),
            ('modelo_impressao_padrao', 'os'),
            ('obs_padrao_impressao', 'Obrigado pela preferência!')
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES (?, ?)
        """, configs_padrao)

        # MIGRAÇÕES AUTOMÁTICAS
        cursor.execute("PRAGMA table_info(clientes)")
        colunas_clientes = [coluna[1] for coluna in cursor.fetchall()]
        if 'documento' not in colunas_clientes:
            cursor.execute("ALTER TABLE clientes ADD COLUMN documento TEXT DEFAULT ''")
        if 'endereco' not in colunas_clientes:
            cursor.execute("ALTER TABLE clientes ADD COLUMN endereco TEXT DEFAULT ''")

        cursor.execute("PRAGMA table_info(pedidos)")
        colunas_pedidos = [coluna[1] for coluna in cursor.fetchall()]
        if 'desconto' not in colunas_pedidos:
            cursor.execute("ALTER TABLE pedidos ADD COLUMN desconto REAL DEFAULT 0.0")
        if 'usuario_nome' not in colunas_pedidos:
            cursor.execute("ALTER TABLE pedidos ADD COLUMN usuario_nome TEXT DEFAULT 'Sistema'")
        if 'forma_pagamento' not in colunas_pedidos:
            cursor.execute("ALTER TABLE pedidos ADD COLUMN forma_pagamento TEXT DEFAULT ''")
        if 'observacao' not in colunas_pedidos:
            cursor.execute("ALTER TABLE pedidos ADD COLUMN observacao TEXT DEFAULT ''")
        if 'tipo' not in colunas_pedidos:
            cursor.execute("ALTER TABLE pedidos ADD COLUMN tipo TEXT DEFAULT 'VENDA'")
            cursor.execute("UPDATE pedidos SET tipo = 'VENDA' WHERE tipo IS NULL OR tipo = ''")

        cursor.execute("PRAGMA table_info(itens_pedido)")
        colunas_itens = [coluna[1] for coluna in cursor.fetchall()]
        if 'observacao' not in colunas_itens:
            cursor.execute("ALTER TABLE itens_pedido ADD COLUMN observacao TEXT DEFAULT ''")

        cursor.execute("PRAGMA table_info(contas_a_pagar)")
        colunas_contas = [coluna[1] for coluna in cursor.fetchall()]
        if 'recorrente' not in colunas_contas:
            cursor.execute("ALTER TABLE contas_a_pagar ADD COLUMN recorrente INTEGER DEFAULT 0")
        if 'dia_vencimento' not in colunas_contas:
            cursor.execute("ALTER TABLE contas_a_pagar ADD COLUMN dia_vencimento INTEGER")

        cursor.execute("UPDATE pedidos SET usuario_nome = 'Thaissa' WHERE usuario_nome = 'Thaissa/Michel'")

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
