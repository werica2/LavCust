from flask import Flask, render_template

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
    }
]


@app.route("/")
def inicio():
    return render_template("despesas.html", despesas=despesas)


if __name__ == "__main__":
    app.run(debug=True)