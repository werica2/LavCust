from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

DATABASE = "lavcust.db"


def conectar_banco():
    conexao = sqlite3.connect(DATABASE)
    conexao.row_factory = sqlite3.Row
    return conexao


def criar_banco():
    conexao = conectar_banco()

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

    # Garante que bancos antigos tenham as novas colunas
    colunas = [
        ("lavoura", "TEXT DEFAULT ''"),
        ("quantidade", "REAL DEFAULT 1"),
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


@app.route("/")
def index():
    conexao = conectar_banco()

    custos = conexao.execute(
        "SELECT * FROM custos ORDER BY id DESC"
    ).fetchall()

    total = conexao.execute(
        "SELECT SUM(quantidade * valor) AS total FROM custos"
    ).fetchone()["total"]

    conexao.close()

    if total is None:
        total = 0

    return render_template(
        "index.html",
        custos=custos,
        total=total
    )


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():

    if request.method == "POST":

        lavoura = request.form.get("lavoura", "")
        categoria = request.form.get("categoria", "")
        descricao = request.form.get("descricao", "")
        quantidade = request.form.get("quantidade", "1")
        valor = request.form.get("valor", "0")
        data = request.form.get("data", "")
        safra = request.form.get("safra", "")

        try:
            quantidade = float(quantidade.replace(",", "."))
        except ValueError:
            quantidade = 1

        valor = valor.replace(".", "").replace(",", ".")

        try:
            valor = float(valor)
        except ValueError:
            valor = 0

        conexao = conectar_banco()

        conexao.execute("""
            INSERT INTO custos
            (lavoura, categoria, descricao, quantidade, valor, data, safra)
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

        return redirect(url_for("listar_despesas"))

    return render_template("cadastro.html")


@app.route("/despesas")
def listar_despesas():

    pesquisa = request.args.get("pesquisa", "")

    conexao = conectar_banco()

    custos = conexao.execute("""
        SELECT * FROM custos
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


@app.route("/custos")
def custos():
    return listar_despesas()


@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):

    conexao = conectar_banco()

    custo = conexao.execute(
        "SELECT * FROM custos WHERE id = ?",
        (id,)
    ).fetchone()

    if custo is None:
        conexao.close()
        return "Custo não encontrado!"

    if request.method == "POST":

        lavoura = request.form.get("lavoura", "")
        categoria = request.form.get("categoria", "")
        descricao = request.form.get("descricao", "")
        quantidade = request.form.get("quantidade", "1")
        valor = request.form.get("valor", "0")
        data = request.form.get("data", "")
        safra = request.form.get("safra", "")

        try:
            quantidade = float(quantidade.replace(",", "."))
        except ValueError:
            quantidade = 1

        valor = valor.replace(".", "").replace(",", ".")

        try:
            valor = float(valor)
        except ValueError:
            valor = 0

        conexao.execute("""
            UPDATE custos
            SET lavoura = ?,
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

        return redirect(url_for("listar_despesas"))

    conexao.close()

    return render_template(
        "editar.html",
        custo=custo,
        despesa=custo
    )


@app.route("/excluir/<int:id>")
def excluir(id):

    conexao = conectar_banco()

    conexao.execute(
        "DELETE FROM custos WHERE id = ?",
        (id,)
    )

    conexao.commit()
    conexao.close()

    return redirect(url_for("listar_despesas"))


@app.route("/relatorio", methods=["GET", "POST"])
def relatorio():

    conexao = conectar_banco()

    custos = conexao.execute(
        "SELECT * FROM custos ORDER BY lavoura, categoria"
    ).fetchall()

    total = conexao.execute(
        "SELECT SUM(quantidade * valor) AS total FROM custos"
    ).fetchone()["total"]

    conexao.close()

    if total is None:
        total = 0

    lucro = None
    receita = None

    if request.method == "POST":

        quantidade_sacas = float(
            request.form["quantidade_sacas"]
        )

        preco_saca = float(
            request.form["preco_saca"]
        )

        receita = quantidade_sacas * preco_saca
        lucro = receita - total

    return render_template(
        "relatorio.html",
        custos=custos,
        total=total,
        receita=receita,
        lucro=lucro
    )


if __name__ == "__main__":
    criar_banco()
    app.run(debug=True)