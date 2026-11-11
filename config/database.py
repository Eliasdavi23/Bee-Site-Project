import sqlite3

DB_NAME = "sistema_grafica.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _criar_tabelas_whatsapp(cursor):
    """Tabelas do atendimento via WhatsApp (conversas + histórico de mensagens)."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_conversas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telefone TEXT NOT NULL UNIQUE,
            nome_contato TEXT DEFAULT '',
            cliente_id INTEGER,
            modo_auto INTEGER DEFAULT 1,
            precisa_atendente INTEGER DEFAULT 0,
            nao_lidas INTEGER DEFAULT 0,
            aguardando_nome INTEGER DEFAULT 0,
            atendente_nome TEXT DEFAULT '',
            ultima_mensagem TEXT DEFAULT '',
            ultima_mensagem_em TEXT,
            criada_em TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE SET NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversa_id INTEGER NOT NULL,
            direcao TEXT NOT NULL,
            autor TEXT NOT NULL,
            texto TEXT NOT NULL,
            status TEXT DEFAULT 'RECEBIDA',
            id_externo TEXT,
            usuario TEXT DEFAULT '',
            criada_em TEXT,
            midia_url TEXT DEFAULT '',
            midia_tipo TEXT DEFAULT '',
            FOREIGN KEY (conversa_id) REFERENCES whatsapp_conversas (id) ON DELETE CASCADE
        )
    """)
    # Impede gravar duas vezes a mesma mensagem quando o provedor reenvia o webhook
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_whatsapp_msg_id_externo
        ON whatsapp_mensagens (id_externo) WHERE id_externo IS NOT NULL
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_whatsapp_msg_conversa
        ON whatsapp_mensagens (conversa_id, id)
    """)
    cursor.executemany("""
        INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES (?, ?)
    """, [
        ('whatsapp_auto_resposta', '0'),  # Sem mensagens automáticas de IA (apenas aviso de ligação)
        ('whatsapp_aviso_status', '1'),   # Avisar cliente quando o status do pedido mudar
    ])


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
                quantidade REAL DEFAULT 0.0
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
                quantidade REAL NOT NULL,
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
            ('cidade_empresa', 'Franca'),
            ('estado_empresa', 'SP'),
            ('endereco_empresa', ''),
            ('modelo_impressao_padrao', 'os'),
            ('obs_padrao_impressao', 'Obrigado pela preferência!')
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES (?, ?)
        """, configs_padrao)

        _criar_tabelas_whatsapp(cursor)

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

        cursor.execute("PRAGMA table_info(whatsapp_mensagens)")
        colunas_wa_msg = [coluna[1] for coluna in cursor.fetchall()]
        if 'midia_url' not in colunas_wa_msg:
            cursor.execute("ALTER TABLE whatsapp_mensagens ADD COLUMN midia_url TEXT DEFAULT ''")
        if 'midia_tipo' not in colunas_wa_msg:
            cursor.execute("ALTER TABLE whatsapp_mensagens ADD COLUMN midia_tipo TEXT DEFAULT ''")

        cursor.execute("PRAGMA table_info(whatsapp_conversas)")
        colunas_wa_conv = [coluna[1] for coluna in cursor.fetchall()]
        if 'aguardando_nome' not in colunas_wa_conv:
            cursor.execute("ALTER TABLE whatsapp_conversas ADD COLUMN aguardando_nome INTEGER DEFAULT 0")
        if 'atendente_nome' not in colunas_wa_conv:
            cursor.execute("ALTER TABLE whatsapp_conversas ADD COLUMN atendente_nome TEXT DEFAULT ''")

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
