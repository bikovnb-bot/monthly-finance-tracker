import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
import sqlite3

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

# CSS для современного вида
st.markdown("""
<style>
    :root {
        --primary: #e67e22;
        --primary-light: #f39c12;
        --gray-bg: #f8fafc;
        --card-shadow: 0 8px 20px rgba(0,0,0,0.05);
    }
    .metric-card {
        background: white;
        border-radius: 20px;
        padding: 1rem;
        box-shadow: var(--card-shadow);
        transition: transform 0.2s;
        border-left: 4px solid var(--primary);
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
        background: var(--primary) !important;
        color: white !important;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton button:hover {
        background: #d35400 !important;
        transform: scale(1.02);
    }
    .css-1d391kg {
        background: #ffffff;
        border-right: 1px solid #eef2ff;
    }
    .stRadio > div {
        gap: 8px;
    }
    .stRadio label {
        background: #f1f5f9;
        padding: 8px 16px;
        border-radius: 40px;
        transition: all 0.2s;
    }
    .stRadio label:hover {
        background: #e2e8f0;
    }
    .stRadio [data-baseweb="radio"]:checked + div {
        background: var(--primary);
        color: white;
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
    }
</style>
""", unsafe_allow_html=True)

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
            UNIQUE(year, month)
        )
    ''')
    c.execute("PRAGMA table_info(budgets)")
    columns = [col[1] for col in c.fetchall()]
    if 'budget' not in columns:
        c.execute("ALTER TABLE budgets ADD COLUMN budget REAL DEFAULT 0")
    conn.commit()
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

def main():
    init_db()
    st.title("💰 Мои финансы")

    menu = ["Дашборд", "Редактирование месяцев", "Бюджет"]
    choice = st.sidebar.radio("Меню", menu, format_func=lambda x: {
        "Дашборд": "📊 Дашборд",
        "Редактирование месяцев": "✏️ Редактирование месяцев",
        "Бюджет": "💰 Бюджет расходов"
    }[x])

    df = load_all_data()
    budgets_df = load_budgets()

    if choice == "Дашборд":
        st.header("📊 Аналитика")
        if df.empty:
            st.info("Нет данных. Добавьте месяцы в разделе 'Редактирование месяцев'.")
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

        # Адаптивные метрики (оставляем видимыми)
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
                <div style="font-size: 0.7rem; color: #94a3b8;">с учётом оставшихся дней</div>
            </div>
            """, unsafe_allow_html=True)

        st.subheader("📋 Контроль бюджета расходов по месяцам")
        display = merged[['month_name', 'budget', 'expense', 'budget_left', 'days_left', 'allowed_per_day']].copy()
        display = display.rename(columns={
            'month_name': 'Месяц',
            'budget': 'Бюджет (₽)',
            'expense': 'Потрачено (₽)',
            'budget_left': 'Остаток бюджета (₽)',
            'days_left': 'Осталось дней',
            'allowed_per_day': 'Можно тратить в день (₽)'
        })

        def color_negative(val):
            if isinstance(val, (int, float)) and val < 0:
                return 'color: red; font-weight: bold'
            return ''

        styled = display.style.format({
            'Бюджет (₽)': '{:,.2f}',
            'Потрачено (₽)': '{:,.2f}',
            'Остаток бюджета (₽)': '{:,.2f}',
            'Можно тратить в день (₽)': '{:,.2f}'
        }).map(color_negative, subset=['Остаток бюджета (₽)'])

        st.dataframe(styled, use_container_width=True)

        # Все графики оборачиваем в st.expander (свёрнуты по умолчанию)
        # 1. Динамика доходов и расходов
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
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )
            st.plotly_chart(fig_main, use_container_width=True)

        # 2. Бюджет vs факт
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
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_budget, use_container_width=True)

        # 3. Средние ежедневные расходы
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
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_avg, use_container_width=True)

        # 4. Круговая диаграмма
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
                template='plotly_white'
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    elif choice == "Редактирование месяцев":
        st.header("✏️ Управление месячными записями")
        available_years = list(range(2020, date.today().year + 5))
        col1, col2 = st.columns(2)
        with col1:
            edit_year = st.selectbox("Год", available_years, index=available_years.index(date.today().year))
        with col2:
            edit_month = st.selectbox("Месяц", list(range(1, 13)), format_func=lambda m: MONTHS_RU[m])

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
            st.dataframe(all_months[['Месяц', 'expense', 'income', 'days']].rename(
                columns={'expense': 'Расход (₽)', 'income': 'Доход (₽)', 'days': 'Дней учтено'}
            ).style.format({'Расход (₽)': '{:,.2f}', 'Доход (₽)': '{:,.2f}'}), use_container_width=True)

    elif choice == "Бюджет":
        st.header("💰 Установка бюджета расходов на месяц")
        available_years = list(range(2020, date.today().year + 5))
        col1, col2 = st.columns(2)
        with col1:
            plan_year = st.selectbox("Год", available_years, index=available_years.index(date.today().year), key="budget_year")
        with col2:
            plan_month = st.selectbox("Месяц", list(range(1, 13)), format_func=lambda m: MONTHS_RU[m], key="budget_month")

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
            st.dataframe(budgets_display[['Месяц', 'budget']].rename(
                columns={'budget': 'Бюджет расходов (₽)'}
            ).style.format({'Бюджет расходов (₽)': '{:,.2f}'}), use_container_width=True)

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