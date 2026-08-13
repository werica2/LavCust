from flask import Flask, render_template, request

app = Flask(__name__)

despesas = [
    {
        "id": 1,
        "descricao": "Compra de sementes",
        "categoria": "Sementes",
        "valor": 5000.00,
        "data": "10/08/2026",
        "safra": "Soja 2026"
    },
    {
        "id": 2,
        "descricao": "Compra de fertilizantes",
        "categoria": "Fertilizantes",
        "valor": 3500.00,
        "data": "12/08/2026",
        "safra": "Milho 2026"
    },
    {
        "id": 3,
        "descricao": "Compra de defensivos agrícolas",
        "categoria": "Defensivos",
        "valor": 2800.00,
        "data": "13/08/2026",
        "safra": "Soja 2026"
    },
    {
        "id": 4,
        "descricao": "Manutenção de máquinas agrícolas",
        "categoria": "Manutenção",
        "valor": 4200.00,
        "data": "14/08/2026",
        "safra": "Milho 2026"
    },
    {
        "id": 5,
        "descricao": "Combustível para máquinas",
        "categoria": "Combustível",
        "valor": 1850.00,
        "data": "15/08/2026",
        "safra": "Soja 2026"
    },
    {
        "id": 6,
        "descricao": "Mão de obra para plantio",
        "categoria": "Mão de obra",
        "valor": 3200.00,
        "data": "16/08/2026",
        "safra": "Milho 2026"
    },
    {
        "id": 7,
        "descricao": "Aluguel de máquinas",
        "categoria": "Máquinas",
        "valor": 4500.00,
        "data": "17/08/2026",
        "safra": "Soja 2026"
    },
    {
        "id": 8,
        "descricao": "Compra de herbicidas",
        "categoria": "Defensivos",
        "valor": 2150.00,
        "data": "18/08/2026",
        "safra": "Milho 2026"
    },
    {
        "id": 9,
        "descricao": "Transporte da produção",
        "categoria": "Transporte",
        "valor": 2700.00,
        "data": "19/08/2026",
        "safra": "Soja 2026"
    },
    {
        "id": 10,
        "descricao": "Análise e correção do solo",
        "categoria": "Solo",
        "valor": 1200.00,
        "data": "20/08/2026",
        "safra": "Milho 2026"
    },
    {
        "id": 11,
        "descricao": "Compra de calcário",
        "categoria": "Insumos",
        "valor": 2900.00,
        "data": "21/08/2026",
        "safra": "Soja 2026"
    },
    {
        "id": 12,
        "descricao": "Manutenção do sistema de irrigação",
        "categoria": "Irrigação",
        "valor": 1600.00,
        "data": "22/08/2026",
        "safra": "Milho 2026"
    }
]



@app.route("/", methods=["GET", "POST"])
def inicio():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]

        if usuario == "admin" and senha == "1234":
            return render_template(
                "despesas.html",
                despesas=despesas,
                pesquisa=""
            )

        return render_template(
            "login.html",
            erro="Usuário ou senha incorretos!"
        )

    return render_template("login.html")


@app.route("/despesas")
def listar_despesas():
    pesquisa = request.args.get("pesquisa", "")

    despesas_filtradas = []

    for despesa in despesas:
        if pesquisa.lower() in despesa["descricao"].lower():
            despesas_filtradas.append(despesa)

    return render_template(
        "despesas.html",
        despesas=despesas_filtradas,
        pesquisa=pesquisa
    )


if __name__ == "__main__":
    app.run(debug=True)