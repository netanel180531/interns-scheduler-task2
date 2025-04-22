import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model
from datetime import date, timedelta

st.set_page_config(page_title="שיבוץ מתמחים לפי מודל מתמטי מלא", layout="wide")
st.title("📅 שיבוץ מתמחים - ספטמבר 2025 (משימה 2)")

st.markdown("המערכת מבצעת שיבוץ אופטימלי של מתמחים בהתאם לכל אילוצי משימה 2, בהתבסס על לוח ספטמבר 2025.")

if st.button("▶ התחל שיבוץ"):
    start_date = date(2025, 9, 1)
    days = [start_date + timedelta(days=i) for i in range(30)]
    schedule = []
    for d in days:
        wd = d.weekday()
        if wd in range(0, 5):
            schedule.append((d, 'בוקר', 8, 7))
            schedule.append((d, 'תורנות', 16, 4))
        elif wd == 5:
            schedule.append((d, 'בוקר', 5, 6))
            schedule.append((d, 'תורנות', 19, 4))
        elif wd == 6:
            schedule.append((d, 'תורנות', 24, 4))

    model = cp_model.CpModel()
    min_interns, max_interns = 15, 50
    found_solution = False

    for n in range(min_interns, max_interns + 1):
        st.write(f"🔍 בודק פתרון עבור {n} מתמחים...")
        X = {}
        Y = {}

        for i in range(n):
            Y[i] = model.NewBoolVar(f"Y_{i}")
            for d, s, h, r in schedule:
                X[(i, d, s)] = model.NewBoolVar(f"X_{i}_{d}_{s}")

        for d, s, h, r in schedule:
            model.Add(sum(X[(i, d, s)] for i in range(n)) == r)

        for i in range(n):
            for d in days:
                model.Add(sum(X.get((i, d, s), 0) for s in ['בוקר', 'תורנות']) <= 1)

        for i in range(n):
            for d, s, h, r in schedule:
                if s == 'תורנות':
                    prev_day = d - timedelta(days=1)
                    next_day = d + timedelta(days=1)
                    if (i, prev_day, 'בוקר') in X:
                        model.Add(X[(i, prev_day, 'בוקר')] + X[(i, d, 'תורנות')] <= 1)
                    if (i, next_day, 'בוקר') in X:
                        model.Add(X[(i, next_day, 'בוקר')] + X[(i, d, 'תורנות')] <= 1)

        for i in range(n):
            for idx in range(len(schedule) - 1):
                d1, s1, _, _ = schedule[idx]
                d2, s2, _, _ = schedule[idx + 1]
                if s1 == 'תורנות' and s2 == 'תורנות' and (d2 - d1).days <= 1:
                    model.Add(X[(i, d1, 'תורנות')] + X[(i, d2, 'תורנות')] <= 1)

        for i in range(n):
            model.Add(sum(X[(i, d, s)] for (d, s, h, r) in schedule if s == 'תורנות') <= 6)

        for i in range(n):
            for start in range(len(days) - 6):
                week_days = days[start:start + 7]
                model.Add(sum(X.get((i, d, 'תורנות'), 0) for d in week_days) <= 2)

        for i in range(n):
            total_hours = [X[(i, d, s)] * h for (d, s, h, r) in schedule]
            model.Add(cp_model.LinearExpr.Sum(total_hours) <= 286)

        for i in range(n):
            for d, s, _, _ in schedule:
                model.Add(X[(i, d, s)] <= Y[i])

        model.Minimize(sum(Y[i] for i in range(n)))

        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            found_solution = True
            st.success(f"✔ נמצא פתרון עבור {int(solver.ObjectiveValue())} מתמחים")
            output = []
            for (i, d, s), var in X.items():
                if solver.Value(var):
                    output.append({"מתמחה": i, "תאריך": d.strftime('%d/%m'), "משמרת": s})
            df = pd.DataFrame(output)
            st.dataframe(df)
            st.download_button("📥 הורד קובץ Excel", df.to_excel(index=False), "schedule_final.xlsx")
            break
        else:
            st.info(f"❌ לא נמצא פתרון עבור {n} מתמחים.")

    if not found_solution:
        st.error("❌ לא נמצא פתרון תקף בין 15 ל-50 מתמחים.")
