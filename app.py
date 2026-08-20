from flask import Flask, render_template, request

app = Flask(__name__)

# Lista para guardar as despesas cadastradas
despesas = []


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():

    if request.method == "POST":

        descricao = request.form.get("descricao")
        categoria = request.form.get("categoria")
        valor = request.form.get("valor")
        data = request.form.get("data")
        safra = request.form.get("safra")

        # Converte o valor de "1.234,56" para número
        valor = valor.replace(".", "").replace(",", ".")

        try:
            valor = float(valor)
        except ValueError:
            valor = 0.0

        # Cria a despesa
        despesa = {
            "descricao": descricao,
            "categoria": categoria,
            "valor": valor,
            "data": data,
            "safra": safra
        }

        # Adiciona à lista
        despesas.append(despesa)

    return render_template(
        "cadastro.html",
        despesas=despesas
    )


@app.route("/consulta")
def consulta():
    return render_template(
        "consulta.html",
        despesas=despesas
    )


@app.route("/calculos")
def calculos():

    total = sum(
        despesa["valor"]
        for despesa in despesas
    )

    quantidade = len(despesas)

    return render_template(
        "calculos.html",
        despesas=despesas,
        total=total,
        quantidade=quantidade
    )


if __name__ == "__main__":
    app.run(debug=True)