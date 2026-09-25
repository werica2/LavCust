from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

DATABASE = "lavcust.db"

# Necessário para o sistema de login/sessão
app.secret_key = "lavcust-chave-secreta-2026"


# =========================================================
# BANCO DE DADOS
# =========================================================

def conectar_banco():
    conexao = sqlite3.connect(DATABASE)
    conexao.row_factory = sqlite3.Row
    return conexao


def criar_banco():

    conexao = conectar_banco()

    # -----------------------------------------------------
    # TABELA DE DESPESAS
    # -----------------------------------------------------

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS custos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lavoura TEXT NOT NULL DEFAULT '',
            categoria TEXT NOT NULL DEFAULT '',
            descricao TEXT NOT NULL DEFAULT '',
            quantidade REAL NOT NULL DEFAULT 1,
            valor REAL NOT NULL DEFAULT 0,
            data TEXT,
            safra TEXT
        )
    """)

    # -----------------------------------------------------
    # TABELA DE USUÁRIOS
    # -----------------------------------------------------

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL
        )
    """)

    # -----------------------------------------------------
    # TABELA DE VENDAS
    # -----------------------------------------------------

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto TEXT DEFAULT '',
            quantidade_sacas REAL NOT NULL DEFAULT 0,
            preco_por_saca REAL NOT NULL DEFAULT 0,
            data TEXT,
            comprador TEXT DEFAULT '',
            observacoes TEXT DEFAULT ''
        )
    """)

    # -----------------------------------------------------
    # VERIFICA COLUNAS ANTIGAS
    # -----------------------------------------------------

    colunas = [
        ("lavoura", "TEXT DEFAULT ''"),
        ("categoria", "TEXT DEFAULT ''"),
        ("descricao", "TEXT DEFAULT ''"),
        ("quantidade", "REAL DEFAULT 1"),
        ("valor", "REAL DEFAULT 0"),
        ("data", "TEXT"),
        ("safra", "TEXT")
    ]

    existentes = [
        coluna["name"]
        for coluna in conexao.execute(
            "PRAGMA table_info(custos)"
        ).fetchall()
    ]

    for nome, tipo in colunas:

        if nome not in existentes:

            conexao.execute(
                f"ALTER TABLE custos ADD COLUMN {nome} {tipo}"
            )

    conexao.commit()
    conexao.close()


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def converter_numero(valor, padrao=0):

    if valor is None:
        return padrao

    valor = str(valor).strip()

    if not valor:
        return padrao

    try:

        # Se tiver vírgula, consideramos o formato brasileiro
        if "," in valor:
            valor = valor.replace(".", "")
            valor = valor.replace(",", ".")

        return float(valor)

    except ValueError:
        return padrao


def usuario_logado():
    return session.get("usuario_id") is not None


# =========================================================
# PÁGINA INICIAL
# =========================================================

@app.route("/")
def index():

    # Primeiro acesso: cadastro
    if "usuario_id" not in session:
        return redirect(url_for("cadastro_usuario"))

    conexao = conectar_banco()

    # Despesas
    custos = conexao.execute("""
        SELECT *
        FROM custos
        ORDER BY id DESC
    """).fetchall()

    # Total de despesas
    total_despesas = conexao.execute("""
        SELECT SUM(quantidade * valor) AS total
        FROM custos
    """).fetchone()["total"]

    # Total de vendas
    total_vendas = conexao.execute("""
        SELECT SUM(
            quantidade_sacas * preco_por_saca
        ) AS total
        FROM vendas
    """).fetchone()["total"]

    # Quantidade de despesas
    qtd_registros = conexao.execute("""
        SELECT COUNT(*) AS quantidade
        FROM custos
    """).fetchone()["quantidade"]

    # Valores por categoria
    dados_categorias = conexao.execute("""
        SELECT
            categoria,
            SUM(quantidade * valor) AS total
        FROM custos
        GROUP BY categoria
        ORDER BY total DESC
    """).fetchall()

    conexao.close()

    if total_despesas is None:
        total_despesas = 0

    if total_vendas is None:
        total_vendas = 0

    lucro = total_vendas - total_despesas

    nome = session.get(
        "usuario_nome",
        ""
    )

    # Preparação dos dados para os gráficos
    categorias = []
    valores_categorias = []

    for item in dados_categorias:
        categorias.append(
            item["categoria"] or "Outros"
        )

        valores_categorias.append(
            item["total"] or 0
        )

    return render_template(
        "index.html",

        custos=custos,

        total=total_despesas,

        total_despesas=total_despesas,

        total_vendas=total_vendas,

        lucro=lucro,

        qtd_registros=qtd_registros,

        quantidade=qtd_registros,

        nome=nome,

        categorias=categorias,

        valores_categorias=valores_categorias
    )
# =========================================================
# CADASTRO DE USUÁRIO
# =========================================================

@app.route("/cadastro-usuario", methods=["GET", "POST"])
def cadastro_usuario():

    erro = None

    if request.method == "POST":

        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        confirmar_senha = request.form.get(
            "confirmar_senha",
            ""
        )

        if not nome or not email or not senha:

            erro = "Preencha todos os campos."

        elif len(senha) < 8:

            erro = "A senha deve ter pelo menos 8 caracteres."

        elif not any(char.isdigit() for char in senha):

            erro = "A senha deve conter pelo menos 1 número."

        elif senha != confirmar_senha:

            erro = "As senhas não coincidem."

        else:

            conexao = conectar_banco()

            usuario_existente = conexao.execute("""
                SELECT id
                FROM usuarios
                WHERE email = ?
            """, (email,)).fetchone()

            if usuario_existente:

                erro = "Este e-mail já está cadastrado."

                conexao.close()

            else:

                senha_hash = generate_password_hash(senha)

                conexao.execute("""
                    INSERT INTO usuarios
                    (nome, email, senha)
                    VALUES (?, ?, ?)
                """, (
                    nome,
                    email,
                    senha_hash
                ))

                conexao.commit()
                conexao.close()

                return redirect(url_for("login"))

    return render_template(
        "cadastro_usuario.html",
        erro=erro
    )


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    erro = None

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        senha = request.form.get(
            "senha",
            ""
        )

        conexao = conectar_banco()

        usuario = conexao.execute("""
            SELECT *
            FROM usuarios
            WHERE email = ?
        """, (email,)).fetchone()

        conexao.close()

        if usuario and check_password_hash(
            usuario["senha"],
            senha
        ):

            session["usuario_id"] = usuario["id"]
            session["usuario_nome"] = usuario["nome"]

            return redirect(url_for("index"))

        erro = "E-mail ou senha incorretos."

    return render_template(
        "login.html",
        erro=erro
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================================================
# CADASTRO DE DESPESA
# =========================================================

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():

    if request.method == "POST":

        lavoura = request.form.get(
            "lavoura",
            ""
        )

        categoria = request.form.get(
            "categoria",
            ""
        )

        descricao = request.form.get(
            "descricao",
            ""
        )

        quantidade = converter_numero(
            request.form.get("quantidade"),
            1
        )

        valor = converter_numero(
            request.form.get("valor"),
            0
        )

        data = request.form.get(
            "data",
            ""
        )

        safra = request.form.get(
            "safra",
            ""
        )

        conexao = conectar_banco()

        conexao.execute("""
            INSERT INTO custos
            (
                lavoura,
                categoria,
                descricao,
                quantidade,
                valor,
                data,
                safra
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            lavoura,
            categoria,
            descricao,
            quantidade,
            valor,
            data,
            safra
        ))

        conexao.commit()
        conexao.close()

        return redirect(
            url_for("listar_despesas")
        )

    return render_template(
        "cadastro.html"
    )


# =========================================================
# LISTA DE DESPESAS
# =========================================================

@app.route("/despesas")
def listar_despesas():

    pesquisa = request.args.get(
        "pesquisa",
        ""
    )

    conexao = conectar_banco()

    custos = conexao.execute("""
        SELECT *
        FROM custos

        WHERE descricao LIKE ?
           OR categoria LIKE ?
           OR lavoura LIKE ?
           OR safra LIKE ?

        ORDER BY id DESC
    """, (
        f"%{pesquisa}%",
        f"%{pesquisa}%",
        f"%{pesquisa}%",
        f"%{pesquisa}%"
    )).fetchall()

    conexao.close()

    return render_template(
        "despesas.html",
        despesas=custos,
        custos=custos,
        pesquisa=pesquisa
    )
# Compatibilidade com templates antigos
app.add_url_rule(
    "/despesas",
    endpoint="despesas",
    view_func=listar_despesas
)


# =========================================================
# COMPATIBILIDADE COM /custos
# =========================================================

@app.route("/custos")
def custos():

    return listar_despesas()


# =========================================================
# EDITAR DESPESA
# =========================================================

@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):

    conexao = conectar_banco()

    custo = conexao.execute("""
        SELECT *
        FROM custos
        WHERE id = ?
    """, (id,)).fetchone()

    if custo is None:

        conexao.close()

        return "Custo não encontrado!"

    if request.method == "POST":

        lavoura = request.form.get(
            "lavoura",
            ""
        )

        categoria = request.form.get(
            "categoria",
            ""
        )

        descricao = request.form.get(
            "descricao",
            ""
        )

        quantidade = converter_numero(
            request.form.get("quantidade"),
            1
        )

        valor = converter_numero(
            request.form.get("valor"),
            0
        )

        data = request.form.get(
            "data",
            ""
        )

        safra = request.form.get(
            "safra",
            ""
        )

        conexao.execute("""
            UPDATE custos

            SET
                lavoura = ?,
                categoria = ?,
                descricao = ?,
                quantidade = ?,
                valor = ?,
                data = ?,
                safra = ?

            WHERE id = ?
        """, (
            lavoura,
            categoria,
            descricao,
            quantidade,
            valor,
            data,
            safra,
            id
        ))

        conexao.commit()
        conexao.close()

        return redirect(
            url_for("listar_despesas")
        )

    conexao.close()

    return render_template(
        "editar.html",
        custo=custo,
        despesa=custo
    )


# =========================================================
# EXCLUIR DESPESA
# =========================================================

@app.route("/excluir/<int:id>")
def excluir(id):

    conexao = conectar_banco()

    conexao.execute("""
        DELETE FROM custos
        WHERE id = ?
    """, (id,))

    conexao.commit()
    conexao.close()

    return redirect(
        url_for("listar_despesas")
    )


# =========================================================
# REGISTRAR VENDA
# =========================================================

@app.route("/cadastrar-venda", methods=["GET", "POST"])
def cadastrar_venda():

    if request.method == "POST":

        produto = request.form.get(
            "produto",
            ""
        )

        quantidade_sacas = converter_numero(
            request.form.get(
                "quantidade_sacas"
            ),
            0
        )

        preco_por_saca = converter_numero(
            request.form.get(
                "preco_por_saca"
            ),
            0
        )

        data = request.form.get(
            "data",
            ""
        )

        comprador = request.form.get(
            "comprador",
            ""
        )

        observacoes = request.form.get(
            "observacoes",
            ""
        )

        conexao = conectar_banco()

        conexao.execute("""
            INSERT INTO vendas
            (
                produto,
                quantidade_sacas,
                preco_por_saca,
                data,
                comprador,
                observacoes
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            produto,
            quantidade_sacas,
            preco_por_saca,
            data,
            comprador,
            observacoes
        ))

        conexao.commit()
        conexao.close()

        return redirect(
            url_for("index")
        )

    return render_template(
        "cadastrar_venda.html"
    )


# =========================================================
# RELATÓRIO
# =========================================================

@app.route("/relatorio", methods=["GET", "POST"])
def relatorio():

    conexao = conectar_banco()

    custos = conexao.execute("""
        SELECT *
        FROM custos
        ORDER BY lavoura, categoria
    """).fetchall()

    vendas = conexao.execute("""
        SELECT *
        FROM vendas
        ORDER BY id DESC
    """).fetchall()

    total_despesas = conexao.execute("""
        SELECT SUM(quantidade * valor) AS total
        FROM custos
    """).fetchone()["total"]

    total_vendas = conexao.execute("""
        SELECT SUM(
            quantidade_sacas * preco_por_saca
        ) AS total
        FROM vendas
    """).fetchone()["total"]

    conexao.close()

    if total_despesas is None:
        total_despesas = 0

    if total_vendas is None:
        total_vendas = 0

    lucro = total_vendas - total_despesas

    # -----------------------------------------------------
    # CATEGORIAS PARA O RELATÓRIO
    # -----------------------------------------------------

    categorias = {}

    for custo in custos:

        categoria = custo["categoria"] or "Outros"

        valor_total = (
            custo["quantidade"] *
            custo["valor"]
        )

        categorias[categoria] = (
            categorias.get(categoria, 0)
            + valor_total
        )

    return render_template(
        "relatorio.html",

        custos=custos,

        despesas=custos,

        vendas=vendas,

        total=total_despesas,

        total_despesas=total_despesas,

        total_vendas=total_vendas,

        receita=total_vendas,

        lucro=lucro,

        categorias=categorias
    )


# =========================================================
# CONSULTA
# =========================================================

@app.route("/consulta")
def consulta():

    # A antiga página consulta foi incorporada
    # à página de despesas.

    return redirect(
        url_for("listar_despesas")
    )


# =========================================================
# CÁLCULOS
# =========================================================

@app.route("/calculos")
def calculos():

    conexao = conectar_banco()

    quantidade = conexao.execute("""
        SELECT COUNT(*) AS quantidade
        FROM custos
    """).fetchone()["quantidade"]

    total = conexao.execute("""
        SELECT SUM(
            quantidade * valor
        ) AS total
        FROM custos
    """).fetchone()["total"]

    total_vendas = conexao.execute("""
        SELECT SUM(
            quantidade_sacas * preco_por_saca
        ) AS total
        FROM vendas
    """).fetchone()["total"]

    conexao.close()

    if total is None:
        total = 0

    if total_vendas is None:
        total_vendas = 0

    lucro = total_vendas - total

    despesas = quantidade > 0

    media = 0

    if quantidade > 0:
        media = total / quantidade

    return render_template(
        "calculos.html",

        despesas=despesas,

        quantidade=quantidade,

        total=total,

        total_vendas=total_vendas,

        lucro=lucro,

        media=media
    )


# =========================================================
# SOBRE
# =========================================================

@app.route("/sobre")
def sobre():

    return render_template(
        "sobre.html"
    )


# =========================================================
# INICIALIZAÇÃO
# =========================================================

if __name__ == "__main__":

    criar_banco()

    app.run(
        debug=True
    )
