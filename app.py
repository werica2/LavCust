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
            valor REAL NOT NULL
        )
    """)

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

        lavoura = request.form["lavoura"]
        categoria = request.form["categoria"]
        descricao = request.form["descricao"]
        quantidade = float(request.form["quantidade"])
        valor = float(request.form["valor"])

        conexao = conectar_banco()

        conexao.execute("""
            INSERT INTO custos
            (lavoura, categoria, descricao, quantidade, valor)
            VALUES (?, ?, ?, ?, ?)
        """, (
            lavoura,
            categoria,
            descricao,
            quantidade,
            valor
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

        lavoura = request.form["lavoura"]
        categoria = request.form["categoria"]
        descricao = request.form["descricao"]
        quantidade = float(request.form["quantidade"])
        valor = float(request.form["valor"])

        conexao.execute("""
            UPDATE custos
            SET lavoura = ?,
                categoria = ?,
                descricao = ?,
                quantidade = ?,
                valor = ?
            WHERE id = ?
        """, (
            lavoura,
            categoria,
            descricao,
            quantidade,
            valor,
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