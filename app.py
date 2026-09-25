from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "lavcust.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = "lavcust-secret-key-change-in-production"

CATEGORIES = [
    "Sementes", "Fertilizantes", "Defensivos",
    "Combustível", "Mão de obra", "Outros"
]
CULTURES = ["Soja", "Milho"]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        culture TEXT NOT NULL CHECK(culture IN ('Soja','Milho')),
        harvest TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        amount REAL NOT NULL CHECK(amount >= 0),
        planned_amount REAL NOT NULL DEFAULT 0 CHECK(planned_amount >= 0),
        expense_date TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        culture TEXT NOT NULL CHECK(culture IN ('Soja','Milho')),
        harvest TEXT NOT NULL,
        quantity REAL NOT NULL CHECK(quantity >= 0),
        price_per_bag REAL NOT NULL CHECK(price_per_bag >= 0),
        total REAL NOT NULL CHECK(total >= 0),
        sale_date TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    conn.commit()
    conn.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Faça login para acessar o sistema.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def current_user():
    if "user_id" not in session:
        return None
    conn = get_db()
    user = conn.execute("SELECT id, name, email FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    return user


@app.context_processor
def inject_globals():
    return {"current_user": current_user(), "categories": CATEGORIES, "cultures": CULTURES}


@app.route("/")
def index():
    if "user_id" not in session:
        return render_template("landing.html")
    return redirect(url_for("dashboard"))


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("Preencha todos os campos.", "danger")
            return render_template("cadastro.html")
        if len(password) < 8 or not any(c.isdigit() for c in password):
            flash("A senha deve ter pelo menos 8 caracteres e 1 número.", "danger")
            return render_template("cadastro.html")
        if password != confirm:
            flash("As senhas não conferem.", "danger")
            return render_template("cadastro.html")

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users(name,email,password_hash,created_at) VALUES (?,?,?,?)",
                (name, email, generate_password_hash(password), now())
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash("Este e-mail já está cadastrado.", "danger")
            return render_template("cadastro.html")
        conn.close()
        flash("Cadastro realizado com sucesso! Agora você já pode entrar no LavCust.", "success")
        return redirect(url_for("login"))
    return render_template("cadastro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            flash(f"Bem-vindo, {user['name']}! 🌱", "success")
            return redirect(url_for("dashboard"))
        flash("E-mail ou senha incorretos.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu do LavCust.", "info")
    return redirect(url_for("login"))


@app.route("/esqueci-senha", methods=["GET", "POST"])
def forgot_password():
    # Demo segura: não revela se o e-mail existe.
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        conn = get_db()
        user = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if user:
            # Em produção, substituir por envio de link/token por e-mail.
            conn.close()
            flash("Se o e-mail estiver cadastrado, as instruções de recuperação serão enviadas.", "info")
            return redirect(url_for("login"))
        conn.close()
        flash("Se o e-mail estiver cadastrado, as instruções de recuperação serão enviadas.", "info")
        return redirect(url_for("login"))
    return render_template("forgot_password.html")


@app.route("/dashboard")
@login_required
def dashboard():
    uid = session["user_id"]
    conn = get_db()
    totals = conn.execute("""
        SELECT
            COALESCE((SELECT SUM(amount) FROM expenses WHERE user_id=?),0) AS expenses,
            COALESCE((SELECT SUM(total) FROM sales WHERE user_id=?),0) AS sales,
            COALESCE((SELECT SUM(CASE WHEN planned_amount > amount THEN planned_amount-amount ELSE 0 END)
                      FROM expenses WHERE user_id=?),0) AS savings
    """, (uid, uid, uid)).fetchone()
    recent = conn.execute("""
        SELECT 'Despesa' AS kind, culture, harvest, amount AS value, expense_date AS date
        FROM expenses WHERE user_id=?
        UNION ALL
        SELECT 'Venda', culture, harvest, total, sale_date
        FROM sales WHERE user_id=?
        ORDER BY date DESC LIMIT 6
    """, (uid, uid)).fetchall()
    conn.close()
    expenses = float(totals["expenses"])
    sales = float(totals["sales"])
    result = sales - expenses
    return render_template("dashboard.html", totals=totals, result=result, recent=recent)


@app.route("/despesas", methods=["GET"])
@login_required
def despesas():
    uid = session["user_id"]
    q = request.args.get("q", "").strip()
    culture = request.args.get("culture", "").strip()
    harvest = request.args.get("harvest", "").strip()
    category = request.args.get("category", "").strip()

    sql = "SELECT * FROM expenses WHERE user_id=?"
    params = [uid]
    if q:
        sql += " AND (description LIKE ? OR category LIKE ? OR harvest LIKE ?)"
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    if culture in CULTURES:
        sql += " AND culture=?"; params.append(culture)
    if harvest:
        sql += " AND harvest=?"; params.append(harvest)
    if category in CATEGORIES:
        sql += " AND category=?"; params.append(category)
    sql += " ORDER BY expense_date DESC, id DESC"

    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    harvests = [r["harvest"] for r in conn.execute(
        "SELECT DISTINCT harvest FROM expenses WHERE user_id=? ORDER BY harvest DESC", (uid,)
    ).fetchall()]
    conn.close()
    return render_template("despesas.html", expenses=rows, harvests=harvests,
                           filters={"q": q, "culture": culture, "harvest": harvest, "category": category})


@app.route("/despesas/nova", methods=["GET", "POST"])
@login_required
def nova_despesa():
    if request.method == "POST":
        data = request.form
        try:
            amount = float(data.get("amount", "0").replace(",", "."))
            planned = float(data.get("planned_amount", "0").replace(",", ".") or 0)
        except ValueError:
            flash("Informe valores numéricos válidos.", "danger")
            return render_template("nova_despesa.html")
        culture = data.get("culture")
        harvest = data.get("harvest", "").strip()
        category = data.get("category")
        expense_date = data.get("expense_date")
        if culture not in CULTURES or category not in CATEGORIES or not harvest or not expense_date or amount < 0 or planned < 0:
            flash("Preencha corretamente os campos obrigatórios.", "danger")
            return render_template("nova_despesa.html")
        conn = get_db()
        conn.execute("""
            INSERT INTO expenses(user_id,culture,harvest,category,description,amount,planned_amount,expense_date,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (session["user_id"], culture, harvest, category, data.get("description","").strip(),
              amount, planned, expense_date, now()))
        conn.commit(); conn.close()
        flash("Despesa cadastrada com sucesso!", "success")
        return redirect(url_for("despesas"))
    return render_template("nova_despesa.html", today=datetime.now().strftime("%Y-%m-%d"))


@app.route("/despesas/<int:expense_id>/editar", methods=["GET", "POST"])
@login_required
def editar_despesa(expense_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id=? AND user_id=?", (expense_id, session["user_id"])).fetchone()
    if not row:
        conn.close(); flash("Despesa não encontrada.", "danger"); return redirect(url_for("despesas"))
    if request.method == "POST":
        data = request.form
        try:
            amount = float(data.get("amount","0").replace(",", "."))
            planned = float(data.get("planned_amount","0").replace(",", ".") or 0)
        except ValueError:
            conn.close(); flash("Valores inválidos.", "danger"); return render_template("editar.html", expense=row)
        conn.execute("""
            UPDATE expenses SET culture=?,harvest=?,category=?,description=?,amount=?,planned_amount=?,expense_date=?
            WHERE id=? AND user_id=?
        """, (data.get("culture"), data.get("harvest","").strip(), data.get("category"),
              data.get("description","").strip(), amount, planned, data.get("expense_date"),
              expense_id, session["user_id"]))
        conn.commit(); conn.close()
        flash("Despesa atualizada com sucesso!", "success")
        return redirect(url_for("despesas"))
    conn.close()
    return render_template("editar.html", expense=row)


@app.post("/despesas/<int:expense_id>/excluir")
@login_required
def excluir_despesa(expense_id):
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (expense_id, session["user_id"]))
    conn.commit(); conn.close()
    flash("Despesa excluída com sucesso.", "success")
    return redirect(url_for("despesas"))


@app.route("/vendas", methods=["GET"])
@login_required
def vendas():
    conn = get_db()
    rows = conn.execute("SELECT * FROM sales WHERE user_id=? ORDER BY sale_date DESC, id DESC", (session["user_id"],)).fetchall()
    conn.close()
    return render_template("vendas.html", sales=rows)


@app.route("/vendas/nova", methods=["GET", "POST"])
@login_required
def nova_venda():
    if request.method == "POST":
        data = request.form
        try:
            quantity = float(data.get("quantity","0").replace(",", "."))
            price = float(data.get("price_per_bag","0").replace(",", "."))
        except ValueError:
            flash("Quantidade e preço devem ser numéricos.", "danger")
            return render_template("nova_venda.html", today=datetime.now().strftime("%Y-%m-%d"))
        culture = data.get("culture")
        harvest = data.get("harvest","").strip()
        sale_date = data.get("sale_date")
        if culture not in CULTURES or not harvest or not sale_date or quantity <= 0 or price < 0:
            flash("Preencha corretamente os campos obrigatórios.", "danger")
            return render_template("nova_venda.html", today=datetime.now().strftime("%Y-%m-%d"))
        total = quantity * price
        conn = get_db()
        conn.execute("""
            INSERT INTO sales(user_id,culture,harvest,quantity,price_per_bag,total,sale_date,created_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, (session["user_id"], culture, harvest, quantity, price, total, sale_date, now()))
        conn.commit(); conn.close()
        flash("Venda registrada com sucesso!", "success")
        return redirect(url_for("vendas"))
    return render_template("nova_venda.html", today=datetime.now().strftime("%Y-%m-%d"))


@app.post("/vendas/<int:sale_id>/excluir")
@login_required
def excluir_venda(sale_id):
    conn = get_db()
    conn.execute("DELETE FROM sales WHERE id=? AND user_id=?", (sale_id, session["user_id"]))
    conn.commit(); conn.close()
    flash("Venda excluída com sucesso.", "success")
    return redirect(url_for("vendas"))


@app.route("/relatorios")
@login_required
def relatorios():
    uid = session["user_id"]
    culture = request.args.get("culture","").strip()
    harvest = request.args.get("harvest","").strip()

    conn = get_db()
    where_e = "user_id=?"; pe = [uid]
    where_s = "user_id=?"; ps = [uid]
    if culture in CULTURES:
        where_e += " AND culture=?"; pe.append(culture)
        where_s += " AND culture=?"; ps.append(culture)
    if harvest:
        where_e += " AND harvest=?"; pe.append(harvest)
        where_s += " AND harvest=?"; ps.append(harvest)

    totals = conn.execute(f"""
        SELECT
          COALESCE((SELECT SUM(amount) FROM expenses WHERE {where_e}),0) expenses,
          COALESCE((SELECT SUM(total) FROM sales WHERE {where_s}),0) sales,
          COALESCE((SELECT SUM(CASE WHEN planned_amount > amount THEN planned_amount-amount ELSE 0 END)
                    FROM expenses WHERE {where_e}),0) savings
    """, pe + ps + pe).fetchone()

    cats = conn.execute(f"""
        SELECT category, ROUND(SUM(amount),2) total
        FROM expenses WHERE {where_e}
        GROUP BY category ORDER BY total DESC
    """, pe).fetchall()

    by_culture = conn.execute("""
        SELECT culture,
          COALESCE((SELECT SUM(amount) FROM expenses e2 WHERE e2.user_id=? AND e2.culture=e.culture),0) expenses,
          COALESCE((SELECT SUM(total) FROM sales s2 WHERE s2.user_id=? AND s2.culture=e.culture),0) sales
        FROM (SELECT DISTINCT culture FROM expenses WHERE user_id=?
              UNION SELECT DISTINCT culture FROM sales WHERE user_id=?) e
    """, (uid, uid, uid, uid)).fetchall()

    harvests = [r["harvest"] for r in conn.execute("""
        SELECT harvest FROM (
          SELECT DISTINCT harvest FROM expenses WHERE user_id=?
          UNION SELECT DISTINCT harvest FROM sales WHERE user_id=?
        ) ORDER BY harvest DESC
    """, (uid, uid)).fetchall()]
    conn.close()

    expenses = float(totals["expenses"]); sales = float(totals["sales"])
    result = sales - expenses
    return render_template("relatorios.html", totals=totals, result=result, cats=cats,
                           by_culture=by_culture, harvests=harvests,
                           filters={"culture": culture, "harvest": harvest})

@app.route("/calculos")
@login_required
def calculos():
    uid = session["user_id"]

    culture = request.args.get("culture", "").strip()
    harvest = request.args.get("harvest", "").strip()

    conn = get_db()

    # Filtros das despesas
    where_e = "user_id=?"
    params_e = [uid]

    # Filtros das vendas
    where_s = "user_id=?"
    params_s = [uid]

    if culture in CULTURES:
        where_e += " AND culture=?"
        params_e.append(culture)

        where_s += " AND culture=?"
        params_s.append(culture)

    if harvest:
        where_e += " AND harvest=?"
        params_e.append(harvest)

        where_s += " AND harvest=?"
        params_s.append(harvest)

    # Totais gerais
    totals = conn.execute(f"""
        SELECT
            COALESCE((SELECT SUM(amount)
                      FROM expenses
                      WHERE {where_e}), 0) AS expenses,

            COALESCE((SELECT SUM(total)
                      FROM sales
                      WHERE {where_s}), 0) AS sales,

            COALESCE((SELECT SUM(
                CASE
                    WHEN planned_amount > amount
                    THEN planned_amount - amount
                    ELSE 0
                END)
                FROM expenses
                WHERE {where_e}), 0) AS savings
    """, params_e + params_s + params_e).fetchone()

    # Soma por categoria
    categories = conn.execute(f"""
        SELECT
            category,
            ROUND(SUM(amount), 2) AS total
        FROM expenses
        WHERE {where_e}
        GROUP BY category
        ORDER BY total DESC
    """, params_e).fetchall()

    # Lista de safras disponíveis
    harvests = [
        row["harvest"]
        for row in conn.execute("""
            SELECT harvest FROM (
                SELECT DISTINCT harvest
                FROM expenses
                WHERE user_id=?

                UNION

                SELECT DISTINCT harvest
                FROM sales
                WHERE user_id=?
            )
            ORDER BY harvest DESC
        """, (uid, uid)).fetchall()
    ]

    conn.close()

    expenses = float(totals["expenses"])
    sales = float(totals["sales"])

    # Resultado financeiro
    result = sales - expenses

    # Separar lucro e prejuízo
    profit = result if result > 0 else 0
    loss = abs(result) if result < 0 else 0

    return render_template(
    "calculos.html",
    totals=totals,
    categories=categories,
    harvests=harvests,
    cultures=CULTURES,
    result=result,
    profit=profit,
    loss=loss,
    filters={
        "culture": culture,
        "harvest": harvest
    }
)


@app.route("/sobre")
def sobre():
    return render_template("sobre.html")


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


if __name__ == "__main__":
    init_db()
    app.run(debug=True)