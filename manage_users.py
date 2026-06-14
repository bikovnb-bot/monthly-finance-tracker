import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
import sqlite3
import hashlib
import re
from streamlit_cookies_manager import EncryptedCookieManager

MONTHS_RU = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
}

st.set_page_config(
    page_title="Мои финансы",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

st.markdown("""
<style>
    .metric-card {
        background: white;
        border-radius: 20px;
        padding: 1rem;
        box-shadow: 0 8px 20px rgba(0,0,0,0.05);
        transition: transform 0.2s;
        border-left: 4px solid #e67e22;
        margin-bottom: 0;
    }
    .metric-card:hover {
        transform: translateY(-3px);
    }
    h1, h2, h3 {
        font-weight: 600;
    }
    .stDataFrame {
        border-radius: 16px;
        overflow-x: auto;
    }
    .stButton button {
        border-radius: 40px !important;
        background: #e67e22 !important;
        color: white !important;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton button:hover {
        background: #d35400 !important;
        transform: scale(1.02);
    }
    @media (max-width: 768px) {
        .stColumns {
            flex-direction: column;
        }
        .metric-card {
            margin-bottom: 1rem;
        }
        .stDataFrame {
            font-size: 12px;
        }
        .stPlotlyChart {
            margin-bottom: 1rem;
        }
        .plotly .modebar {
            transform: scale(0.8);
            transform-origin: top right;
        }
    }
    section[data-testid="stSidebar"] {
        background-color: #fef9f0;
    }
    .login-container {
        min-height: 80vh;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1rem 0;
    }
    .login-card {
        max-width: 280px;
        width: 100%;
        margin: 0 auto;
        border: none;
        border-radius: 28px;
        background: white;
        box-shadow: 0 20px 35px -10px rgba(0,0,0,0.15);
        transition: transform 0.3s ease;
    }
    .login-card:hover {
        transform: translateY(-3px);
    }
    .login-header {
        background: linear-gradient(135deg, #fef9f0, #ffffff);
        border-radius: 28px 28px 0 0;
        padding: 0.8rem 0.8rem 0.5rem;
        text-align: center;
        border-bottom: 2px solid rgba(230,126,34,0.2);
    }
    .login-logo {
        margin-bottom: 0.2rem;
    }
    .login-logo span {
        font-size: 35px !important;
    }
    .login-title {
        font-size: 1.1rem;
        font-weight: 700;
        background: linear-gradient(135deg, #e67e22, #d35400);
        background-clip: text;
        -webkit-background-clip: text;
        color: transparent;
        margin-bottom: 0;
    }
    .login-subtitle {
        color: #64748b;
        font-size: 0.6rem;
        margin-bottom: 0;
    }
    .login-body {
        padding: 0.8rem 0.8rem 0.6rem;
    }
    .stTextInput > div {
        margin-bottom: 0.6rem;
    }
    .stTextInput > div > div > input {
        width: 100%;
        padding: 0.4rem 0.6rem !important;
        font-size: 0.75rem !important;
        border-radius: 20px !important;
    }
    .stForm button {
        width: 100%;
        padding: 0.35rem !important;
        font-size: 0.75rem !important;
        border-radius: 40px !important;
        background: #e67e22 !important;
        color: white !important;
        margin-top: 0.2rem;
    }
    .forgot-password {
        margin-top: 0.5rem;
        text-align: center;
    }
    .forgot-password a {
        color: #64748b;
        text-decoration: none;
        font-size: 0.6rem;
    }
    .forgot-password a:hover {
        color: #e67e22;
        text-decoration: underline;
    }
    .register-link {
        text-align: center;
        margin-top: 0.4rem;
        font-size: 0.6rem;
    }
    .register-link a {
        color: #e67e22;
        text-decoration: none;
    }
    .login-footer {
        text-align: center;
        padding: 0.5rem 0.5rem;
        border-top: 1px solid #eef2ff;
        font-size: 0.55rem;
        color: #94a3b8;
    }
    @media (max-width: 576px) {
        .login-card {
            margin: 0.5rem;
        }
        .login-header {
            padding: 0.6rem 0.6rem 0.3rem;
        }
        .login-body {
            padding: 0.6rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# -------------------- COOKIES ДЛЯ ЗАПОМИНАНИЯ --------------------
# Инициализация менеджера cookies (требует секретный ключ)
# Для простоты используем EncryptedCookieManager с пустым паролем (небезопасно, но для локального использования OK)
# Лучше задать пароль через secrets или переменную окружения
cookies = EncryptedCookieManager(prefix="finance_app/", password="some_secret_key_change_me")
if not cookies.ready():
    st.stop()

DB_PATH = "monthly_finances.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS monthly_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            expense REAL DEFAULT 0,
            income REAL DEFAULT 0,
            days INTEGER,
            UNIQUE(year, month)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            budget REAL DEFAULT 0,
            UNIQUE(year, month)
        )
    ''')
    c.execute("PRAGMA table_info(budgets)")
    columns = [col[1] for col in c.fetchall()]
    if 'budget' not in columns:
        c.execute("ALTER TABLE budgets ADD COLUMN budget REAL DEFAULT 0")
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        admin_hash = hashlib.sha256("admin".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("admin", admin_hash))
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row and row[0] == hash_password(password):
        return True
    return False

def register_user(username, password):
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        return False, "Логин должен содержать 3-20 символов (буквы, цифры, подчёркивание)"
    if len(password) < 4:
        return False, "Пароль должен быть не менее 4 символов"
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        return True, "Успешная регистрация"
    except sqlite3.IntegrityError:
        return False, "Пользователь с таким именем уже существует"
    finally:
        conn.close()

def load_all_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT id, year, month, expense, income, days FROM monthly_data ORDER BY year, month", conn)
    conn.close()
    if df.empty:
        return df
    df['year'] = df['year'].astype(int)
    df['month'] = df['month'].astype(int)
    df['days'] = df['days'].fillna(0).astype(int)
    df['month_name'] = df.apply(lambda row: f"{MONTHS_RU[int(row['month'])]} {int(row['year'])}", axis=1)
    df['avg_daily_expense'] = df.apply(lambda r: r['expense'] / r['days'] if r['days'] > 0 else 0, axis=1)
    df['balance'] = df['income'] - df['expense']
    return df

def load_budgets(year=None, month=None):
    conn = sqlite3.connect(DB_PATH)
    if year and month:
        df = pd.read_sql_query("SELECT * FROM budgets WHERE year = ? AND month = ?", conn, params=(year, month))
    else:
        df = pd.read_sql_query("SELECT * FROM budgets ORDER BY year, month", conn)
    conn.close()
    if df.empty:
        return pd.DataFrame(columns=['year', 'month', 'budget'])
    df['year'] = df['year'].astype(int)
    df['month'] = df['month'].astype(int)
    if 'budget' not in df.columns:
        df['budget'] = 0.0
    else:
        df['budget'] = df['budget'].fillna(0).astype(float)
    return df

def save_budget(year, month, budget):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO budgets (year, month, budget)
        VALUES (?, ?, ?)
    ''', (int(year), int(month), float(budget)))
    conn.commit()
    conn.close()

def get_month_data(year, month):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM monthly_data WHERE year = ? AND month = ?", conn, params=(year, month))
    conn.close()
    if df.empty:
        return None
    row = df.iloc[0].to_dict()
    row['expense'] = float(row['expense']) if row['expense'] is not None else 0.0
    row['income'] = float(row['income']) if row['income'] is not None else 0.0
    row['days'] = int(row['days']) if row['days'] is not None else 0
    return row

def save_month(year, month, expense, income, days):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO monthly_data (year, month, expense, income, days)
        VALUES (?, ?, ?, ?, ?)
    ''', (int(year), int(month), float(expense), float(income), int(days)))
    conn.commit()
    conn.close()

def delete_month(year, month):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM monthly_data WHERE year = ? AND month = ?", (year, month))
    conn.commit()
    conn.close()

def get_actual_days(year, month):
    if month == 2:
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            return 29
        return 28
    elif month in [4, 6, 9, 11]:
        return 30
    return 31

def sidebar_filters(df):
    st.sidebar.header("🔍 Фильтры")
    if df.empty:
        return date.today().year
    years = sorted(df['year'].unique())
    selected_year = st.sidebar.selectbox("Год", years)
    return selected_year

def show_dashboard(df, budgets_df):
    if df.empty:
        st.info("Нет данных. Добавьте месяцы в разделе 'Ввод данных'.")
        return

    selected_year = sidebar_filters(df)
    df_year = df[df['year'] == selected_year].sort_values('month')
    months_ru = [MONTHS_RU[m] for m in df_year['month']]

    merged = pd.merge(df_year, budgets_df, on=['year', 'month'], how='left')
    merged['budget'] = merged['budget'].fillna(0)
    merged['total_days_in_month'] = merged.apply(lambda r: get_actual_days(r['year'], r['month']), axis=1)

    today = date.today()
    current_year = today.year
    current_month = today.month
    current_day = today.day

    def compute_days_left(row):
        year = row['year']
        month = row['month']
        total_days = row['total_days_in_month']
        if year == current_year and month == current_month:
            left = total_days - current_day + 1
            return max(0, left)
        else:
            days_spent = row['days']
            left = total_days - days_spent
            return max(0, left)

    merged['days_left'] = merged.apply(compute_days_left, axis=1)
    merged['budget_left'] = merged['budget'] - merged['expense']
    merged['allowed_per_day'] = merged.apply(
        lambda r: r['budget_left'] / r['days_left'] if r['days_left'] > 0 and r['budget_left'] > 0 else 0,
        axis=1
    )

    total_income = df_year['income'].sum()
    total_expense = df_year['expense'].sum()
    total_balance = total_income - total_expense

    current_month_allowed = 0
    if not merged.empty:
        current_row = merged[(merged['year'] == current_year) & (merged['month'] == current_month)]
        if not current_row.empty:
            current_month_allowed = current_row['allowed_per_day'].iloc[0]

    col1, col2 = st.columns(2, gap="medium")
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 0.85rem; color: #64748b;">💰 Доходы за год</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #2ecc71;">{total_income:,.2f} ₽</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 0.85rem; color: #64748b;">💸 Расходы за год</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #e74c3c;">{total_expense:,.2f} ₽</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 0.85rem; color: #64748b;">⚖️ Баланс</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #3498db;">{total_balance:,.2f} ₽</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 0.85rem; color: #64748b;">💸 Можно тратить в день (текущий месяц)</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #e67e22;">{current_month_allowed:,.2f} ₽</div>
        </div>
        """, unsafe_allow_html=True)

    st.subheader("📋 Контроль бюджета расходов по месяцам")
    display = merged[['month_name', 'income', 'expense', 'balance', 'budget_left', 'allowed_per_day']].copy()
    display = display.rename(columns={
        'month_name': 'Месяц',
        'income': 'Доход (₽)',
        'expense': 'Расход (₽)',
        'balance': 'Баланс (₽)',
        'budget_left': 'Остаток бюджета (₽)',
        'allowed_per_day': 'Можно тратить в день (₽)'
    })
    col_config = {
        "Доход (₽)": st.column_config.NumberColumn(format="%.2f ₽"),
        "Расход (₽)": st.column_config.NumberColumn(format="%.2f ₽"),
        "Баланс (₽)": st.column_config.NumberColumn(format="%.2f ₽"),
        "Остаток бюджета (₽)": st.column_config.NumberColumn(format="%.2f ₽"),
        "Можно тратить в день (₽)": st.column_config.NumberColumn(format="%.2f ₽"),
    }
    st.dataframe(display, column_config=col_config, hide_index=True, use_container_width=True)

    with st.expander("📈 Динамика доходов и расходов (факт)"):
        fig_main = go.Figure()
        fig_main.add_trace(go.Scatter(x=months_ru, y=df_year['income'], mode='lines+markers', name='Доход',
                                     line=dict(color='#2ecc71', width=3), marker=dict(size=8)))
        fig_main.add_trace(go.Scatter(x=months_ru, y=df_year['expense'], mode='lines+markers', name='Расход',
                                     line=dict(color='#e74c3c', width=3), marker=dict(size=8)))
        fig_main.update_layout(
            title=None,
            xaxis_title="Месяц",
            yaxis_title="Сумма (₽)",
            hovermode='x unified',
            template='plotly_white',
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            height=300
        )
        st.plotly_chart(fig_main, use_container_width=True, config={'displayModeBar': True, 'scrollZoom': True, 'responsive': True})

    with st.expander("📊 Бюджет расходов vs факт"):
        fig_budget = go.Figure()
        fig_budget.add_trace(go.Bar(x=months_ru, y=merged['expense'], name='Факт', marker_color='#e74c3c'))
        fig_budget.add_trace(go.Bar(x=months_ru, y=merged['budget'], name='Бюджет', marker_color='#3498db', opacity=0.7))
        fig_budget.update_layout(
            title=None,
            xaxis_title="Месяц",
            yaxis_title="Сумма (₽)",
            barmode='group',
            template='plotly_white',
            margin=dict(l=20, r=20, t=20, b=20),
            height=300
        )
        st.plotly_chart(fig_budget, use_container_width=True, config={'displayModeBar': True, 'scrollZoom': True, 'responsive': True})

    with st.expander("📉 Средние ежедневные расходы по месяцам"):
        avg_line = df_year['avg_daily_expense'].mean()
        fig_avg = go.Figure()
        fig_avg.add_trace(go.Bar(x=months_ru, y=df_year['avg_daily_expense'], name='Средние расходы в день',
                                 marker_color='#e67e22', text=df_year['avg_daily_expense'].round(0),
                                 textposition='outside', texttemplate='%{text:.0f} ₽'))
        fig_avg.add_hline(y=avg_line, line_dash="dash", line_color="blue",
                          annotation_text=f"Среднее за год: {avg_line:.0f} ₽",
                          annotation_position="top right")
        fig_avg.update_layout(
            title=None,
            xaxis_title="Месяц",
            yaxis_title="Сумма (₽)",
            template='plotly_white',
            margin=dict(l=20, r=20, t=20, b=20),
            height=300
        )
        st.plotly_chart(fig_avg, use_container_width=True, config={'displayModeBar': True, 'scrollZoom': True, 'responsive': True})

    with st.expander("🥧 Соотношение доходов и расходов"):
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Доходы', 'Расходы'],
            values=[total_income, total_expense],
            hole=0.4,
            marker=dict(colors=['#2ecc71', '#e74c3c']),
            textinfo='label+percent',
            textposition='auto'
        )])
        fig_pie.update_layout(
            title=None,
            annotations=[dict(text=f'Баланс: {total_balance:,.0f} ₽', x=0.5, y=0.5, font_size=14, showarrow=False)],
            template='plotly_white',
            margin=dict(l=10, r=10, t=30, b=30),
            height=300
        )
        st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': True, 'responsive': True})

def show_input_data(df):
    st.header("📝 Ввод данных по месяцам")
    available_years = list(range(2020, date.today().year + 5))
    current_year = date.today().year
    current_month = date.today().month

    col1, col2 = st.columns(2)
    with col1:
        edit_year = st.selectbox("Год", available_years, index=available_years.index(current_year))
    with col2:
        edit_month = st.selectbox("Месяц", list(range(1, 13)), format_func=lambda m: MONTHS_RU[m],
                                  index=current_month-1)

    existing = get_month_data(edit_year, edit_month)
    if existing:
        st.info(f"Текущие данные за {MONTHS_RU[int(edit_month)]} {edit_year}: расход = {existing['expense']:.2f} ₽, доход = {existing['income']:.2f} ₽, дней = {existing['days']}")
    else:
        st.info(f"Нет данных за {MONTHS_RU[int(edit_month)]} {edit_year}. Будет создана новая запись.")

    with st.form("month_form"):
        expense = st.number_input("Расходы (₽)", min_value=0.0, step=100.0, value=existing['expense'] if existing else 0.0, format="%.2f")
        income = st.number_input("Доходы (₽)", min_value=0.0, step=100.0, value=existing['income'] if existing else 0.0, format="%.2f")
        default_days = existing['days'] if existing else get_actual_days(edit_year, edit_month)
        if isinstance(default_days, float):
            default_days = int(default_days)
        days = st.number_input("Количество дней, за которые уже учтены расходы", min_value=0, max_value=get_actual_days(edit_year, edit_month), value=default_days, step=1)
        submitted = st.form_submit_button("💾 Сохранить")
        if submitted:
            save_month(edit_year, edit_month, expense, income, days)
            st.success(f"Данные за {MONTHS_RU[int(edit_month)]} {edit_year} сохранены!")
            st.rerun()

    if existing:
        if st.button(f"🗑️ Удалить данные за {MONTHS_RU[int(edit_month)]} {edit_year}", type="primary"):
            delete_month(edit_year, edit_month)
            st.success("Запись удалена!")
            st.rerun()

    st.subheader("📋 Существующие записи")
    if df.empty:
        st.write("Нет записей.")
    else:
        all_months = df[['year', 'month', 'expense', 'income', 'days']].copy()
        all_months['Месяц'] = all_months.apply(lambda row: f"{MONTHS_RU[int(row['month'])]} {int(row['year'])}", axis=1)
        display_df = all_months[['Месяц', 'expense', 'income', 'days']].rename(
            columns={'expense': 'Расход (₽)', 'income': 'Доход (₽)', 'days': 'Дней учтено'}
        )
        col_config = {
            "Расход (₽)": st.column_config.NumberColumn(format="%.2f ₽"),
            "Доход (₽)": st.column_config.NumberColumn(format="%.2f ₽"),
        }
        st.dataframe(display_df, column_config=col_config, hide_index=True, use_container_width=True)

def show_budget(budgets_df):
    st.header("💰 Установка бюджета расходов на месяц")
    available_years = list(range(2020, date.today().year + 5))
    current_year = date.today().year
    current_month = date.today().month

    col1, col2 = st.columns(2)
    with col1:
        plan_year = st.selectbox("Год", available_years, index=available_years.index(current_year), key="budget_year")
    with col2:
        plan_month = st.selectbox("Месяц", list(range(1, 13)), format_func=lambda m: MONTHS_RU[m], key="budget_month",
                                  index=current_month-1)

    existing_budget = load_budgets(plan_year, plan_month)
    current_budget = existing_budget.iloc[0]['budget'] if not existing_budget.empty else 0.0

    with st.form("budget_form"):
        new_budget = st.number_input("Бюджет расходов на месяц (₽)", min_value=0.0, step=500.0, value=current_budget, format="%.2f")
        submitted = st.form_submit_button("💾 Сохранить бюджет")
        if submitted:
            save_budget(plan_year, plan_month, new_budget)
            st.success(f"Бюджет на {MONTHS_RU[plan_month]} {plan_year} установлен: {new_budget:,.2f} ₽")
            st.rerun()

    st.subheader("📋 Сводка бюджетов по месяцам")
    if budgets_df.empty:
        st.write("Нет установленных бюджетов.")
    else:
        budgets_display = budgets_df.copy()
        budgets_display['Месяц'] = budgets_display.apply(lambda row: f"{MONTHS_RU[int(row['month'])]} {int(row['year'])}", axis=1)
        display_df = budgets_display[['Месяц', 'budget']].rename(columns={'budget': 'Бюджет расходов (₽)'})
        col_config = {
            "Бюджет расходов (₽)": st.column_config.NumberColumn(format="%.2f ₽"),
        }
        st.dataframe(display_df, column_config=col_config, hide_index=True, use_container_width=True)

def auth_ui():
    st.markdown("""
    <div class="login-container">
        <div class="login-card">
            <div class="login-header">
                <div class="login-logo">
                    <span>💰</span>
                </div>
                <h1 class="login-title">Добро пожаловать</h1>
                <p class="login-subtitle">Войдите в систему учёта финансов</p>
            </div>
            <div class="login-body">
    """, unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Логин", placeholder="Введите логин", label_visibility="collapsed")
        password = st.text_input("Пароль", type="password", placeholder="Введите пароль", label_visibility="collapsed")
        remember = st.checkbox("Запомнить меня", value=True)
        submitted = st.form_submit_button("Войти", use_container_width=True)
        if submitted:
            if verify_password(username, password):
                st.session_state['authenticated'] = True
                st.session_state['username'] = username
                if remember:
                    cookies["username"] = username
                    cookies.save()
                else:
                    if "username" in cookies:
                        del cookies["username"]
                        cookies.save()
                st.rerun()
            else:
                st.error("❌ Неверный логин или пароль")

    st.markdown("""
            <div class="forgot-password">
                <a href="#" onclick="return false;"><i class="bi bi-envelope"></i> Забыли пароль? Обратитесь к администратору</a>
            </div>
            <div class="register-link">
                <a href="#" onclick="return false;">Нет аккаунта? Зарегистрируйтесь</a>
            </div>
        </div>
        <div class="login-footer">
            <i class="bi bi-shield-lock"></i> Безопасный вход | © 2025 Система финансового учёта
        </div>
    </div>
    </div>
    """, unsafe_allow_html=True)

def main():
    init_db()

    # Попытка восстановить сессию из cookies
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False

    if not st.session_state['authenticated']:
        if "username" in cookies:
            username = cookies["username"]
            # Проверяем, существует ли пользователь (пароль не проверяем, это рискованно, но удобно)
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT 1 FROM users WHERE username = ?", (username,))
            exists = c.fetchone() is not None
            conn.close()
            if exists:
                st.session_state['authenticated'] = True
                st.session_state['username'] = username
                st.rerun()
            else:
                # Если пользователя уже нет, удаляем cookie
                del cookies["username"]
                cookies.save()

    if not st.session_state['authenticated']:
        auth_ui()
        return

    st.sidebar.markdown(f"**👤 {st.session_state['username']}**")
    if st.sidebar.button("🚪 Выйти"):
        st.session_state['authenticated'] = False
        if "username" in cookies:
            del cookies["username"]
            cookies.save()
        st.rerun()

    st.title("💰 Мои финансы")

    menu_option = st.sidebar.radio(
        "Меню",
        ["📊 Дашборд", "📝 Ввод данных", "💰 Бюджет"]
    )

    df = load_all_data()
    budgets_df = load_budgets()

    if menu_option == "📊 Дашборд":
        st.header("📊 Аналитика")
        show_dashboard(df, budgets_df)
    elif menu_option == "📝 Ввод данных":
        show_input_data(df)
    elif menu_option == "💰 Бюджет":
        show_budget(budgets_df)

    st.sidebar.markdown("---")
    if st.sidebar.button("📥 Экспорт всех данных в Excel"):
        if df.empty:
            st.sidebar.warning("Нет данных для экспорта")
        else:
            export_df = df[['year', 'month', 'expense', 'income', 'days']].copy()
            export_df['Месяц'] = export_df.apply(lambda row: f"{MONTHS_RU[int(row['month'])]} {int(row['year'])}", axis=1)
            export_df = export_df[['Месяц', 'expense', 'income', 'days']]
            export_df.rename(columns={'expense': 'Расход (₽)', 'income': 'Доход (₽)', 'days': 'Дней учтено'}, inplace=True)
            export_df.to_excel("monthly_export.xlsx", index=False)
            st.sidebar.success("Файл monthly_export.xlsx создан")
            with open("monthly_export.xlsx", "rb") as f:
                st.sidebar.download_button("Скачать Excel", data=f, file_name="monthly_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    main()
