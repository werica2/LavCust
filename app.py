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
            lavoura TEXT NOT NULL,
            categoria TEXT NOT NULL,
            descricao TEXT NOT NULL,
            quantidade REAL NOT NULL,
            valor REAL NOT NULL,
            data TEXT,
            safra TEXT
        )
    """)

    conexao.commit()
    conexao.close()


@app.route("/", methods=["GET", "POST"])
def inicio():

    if request.method == "POST":
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")

        if usuario == "admin" and senha == "1234":
            return redirect(url_for("custos"))

        return render_template(
            "login.html",
            erro="Usuário ou senha incorretos!"
        )

    return render_template("login.html")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():

    if request.method == "POST":

        lavoura = request.form.get("lavoura", "")
        categoria = request.form.get("categoria", "")
        descricao = request.form.get("descricao", "")
        quantidade = float(request.form.get("quantidade", 1))
        valor = request.form.get("valor", "0")
        data = request.form.get("data", "")
        safra = request.form.get("safra", "")

        valor = valor.replace(".", "").replace(",", ".")

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
            float(valor),
            data,
            safra
        ))

        conexao.commit()
        conexao.close()

        return redirect(url_for("custos"))

    return render_template("cadastro.html")


@app.route("/custos")
def custos():

    conexao = conectar_banco()

    custos = conexao.execute(
        "SELECT * FROM custos ORDER BY id DESC"
    ).fetchall()

    conexao.close()

    return render_template(
        "custos.html",
        custos=custos
    )


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
        pesquisa=pesquisa
    )


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
        quantidade = float(request.form.get("quantidade", 1))
        valor = request.form.get("valor", "0")
        data = request.form.get("data", "")
        safra = request.form.get("safra", "")

        valor = valor.replace(".", "").replace(",", ".")

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
            float(valor),
            data,
            safra,
            id
        ))

        conexao.commit()
        conexao.close()

        return redirect(url_for("custos"))

    conexao.close()

    return render_template(
        "editar.html",
        custo=custo
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

    return redirect(url_for("custos"))


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