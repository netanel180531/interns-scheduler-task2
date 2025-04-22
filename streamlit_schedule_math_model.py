
import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model
from datetime import date, timedelta

st.set_page_config(page_title="שיבוץ מתמחים - הגדרה מתמטית", layout="wide")
st.title("📅 שיבוץ מתמחים לפי מודל מתמטי מלא (משימה 2)")

st.markdown("המערכת מוצאת את מספר המתמחים המינימלי הנדרש כדי לעמוד בכל הדרישות של משימה 2 לחודש ספטמבר 2025.")

if st.button("▶ הפעל שיבוץ"):
    # שלב 1: הגדרת לוח השנה - ספטמבר 2025
    start_date = date(2025, 9, 1)
    days = [start_date + timedelta(days=i) for i in range(30)]
    day_types = []

    for d in days:
        weekday = d.weekday()  # 0=Mon, ..., 6=Sun
        if weekday in range(0, 5):  # אמצ"ש
            day_types.append((d, 'בוקר', 8, 7))
            day_types.append((d, 'תורנות', 16, 4))
        elif weekday == 5:  # שישי
            day_types.append((d, 'בוקר', 5, 6))
            day_types.append((d, 'תורנות', 19, 4))
        elif weekday == 6:  # שבת
            day_types.append((d, 'תורנות', 24, 4))

    model = cp_model.CpModel()
    interns_range = list(range(15, 46))
    solution_found = False

    for n_interns in interns_range:
        X = {}
        Y = {}
        for i in range(n_interns):
            Y[i] = model.NewBoolVar(f"Y_{i}")
            for d, shift_type, hours, req in day_types:
                X[(i, d, shift_type)] = model.NewBoolVar(f"X_{i}_{d}_{shift_type}")

        # אילוץ 1: כל משמרת מכוסה
        for d, s, h, r in day_types:
            model.Add(sum(X[(i, d, s)] for i in range(n_interns)) == r)

        # אילוץ 2: כל מתמחה - מקסימום משמרת אחת ביום
        for i in range(n_interns):
            for d in days:
                model.Add(sum(X.get((i, d, s), 0) for s in ['בוקר', 'תורנות']) <= 1)

        # אילוץ 3: יום לפני ואחרי תורנות - לא רגילה
        for i in range(n_interns):
            for idx, (d, s, h, r) in enumerate(day_types):
                if s == 'תורנות':
                    prev_day = d - timedelta(days=1)
                    next_day = d + timedelta(days=1)
                    if (i, prev_day, 'בוקר') in X:
                        model.Add(X[(i, prev_day, 'בוקר')] + X[(i, d, 'תורנות')] <= 1)
                    if (i, next_day, 'בוקר') in X:
                        model.Add(X[(i, next_day, 'בוקר')] + X[(i, d, 'תורנות')] <= 1)

        # אילוץ 4: 48 שעות בין תורנויות
        for i in range(n_interns):
            for idx in range(len(day_types) - 1):
                d1, s1, _, _ = day_types[idx]
                d2, s2, _, _ = day_types[idx + 1]
                if s1 == 'תורנות' and s2 == 'תורנות' and (d2 - d1).days <= 1:
                    model.Add(X[(i, d1, 'תורנות')] + X[(i, d2, 'תורנות')] <= 1)

        # אילוץ 5: עד 6 תורנויות
        for i in range(n_interns):
            model.Add(sum(X[(i, d, s)] for (d, s, h, r) in day_types if s == 'תורנות') <= 6)

        # אילוץ 6: עד 2 תורנויות בכל שבוע (נעשה לפי חלונות של 7 ימים)
        for i in range(n_interns):
            for start in range(0, len(days) - 6):
                window = days[start:start + 7]
                model.Add(sum(X.get((i, d, 'תורנות'), 0) for d in window) <= 2)

        # אילוץ 7: מקסימום 286 שעות
        for i in range(n_interns):
            total_hours = []
            for d, s, h, r in day_types:
                total_hours.append(X[(i, d, s)] * h)
            model.Add(cp_model.LinearExpr.Sum(total_hours) <= 286)

        # אילוץ 8: אם Y_i = 0 אז X_... = 0
        for i in range(n_interns):
            for d, s, _, _ in day_types:
                model.Add(X[(i, d, s)] <= Y[i])

        # פונקציית מטרה: מזער מספר מתמחים
        model.Minimize(sum(Y[i] for i in range(n_interns)))

        # פתרון
        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            st.success(f"✔ נמצא פתרון עם {solver.ObjectiveValue()} מתמחים")
            rows = []
            for (i, d, s), var in X.items():
                if solver.Value(var):
                    rows.append({'מתמחה': i, 'תאריך': d.strftime('%d/%m'), 'משמרת': s})
            df = pd.DataFrame(rows)
            st.dataframe(df)
            st.download_button("📥 הורד ל-Excel", df.to_excel(index=False), "schedule_math_model.xlsx")
            solution_found = True
            break

    if not solution_found:
        st.error("❌ לא נמצא פתרון בין 15 ל-45 מתמחים.")
