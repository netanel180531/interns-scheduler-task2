
import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model

st.set_page_config(page_title="שיבוץ מתמחים - גרסה נקייה", layout="wide")
st.title("📅 שיבוץ מתמחים - גרסה מדויקת לפי משימה 2")

st.markdown("המערכת מריצה פתרון מ-15 עד 40 מתמחים ומציגה את המספר המינימלי שעומד בכל האילוצים.")

run = st.button("▶ התחל שיבוץ")

if run:
    shifts_data = [
        (1, 'תורנות', 16, 4), (1, 'רגילה', 8, 7),
        (2, 'תורנות', 16, 4), (2, 'רגילה', 8, 7),
        (3, 'תורנות', 16, 4), (3, 'רגילה', 8, 7),
        (4, 'תורנות', 16, 4), (4, 'רגילה', 8, 7),
        (5, 'תורנות', 16, 4), (5, 'רגילה', 8, 7),
        (6, 'תורנות', 16, 4), (6, 'רגילה', 8, 7),
        (7, 'תורנות', 16, 4),
        (8, 'תורנות', 16, 4),
        (9, 'רגילה', 8, 7),
        (10, 'תורנות', 16, 4),
        (11, 'רגילה', 5, 6), (11, 'תורנות', 19, 4),
        (12, 'תורנות', 24, 4),
        (13, 'תורנות', 24, 6),
    ]

    NUM_DAYS = 13
    found = False
    final_df = None

    for num_interns in range(15, 41):
        model = cp_model.CpModel()
        A = {}

        for i in range(num_interns):
            for d, typ, hrs, req in shifts_data:
                A[(i, d, typ)] = model.NewBoolVar(f"A_{i}_{d}_{typ}")

        # כל משמרת מאוישת לפי הדרישה
        for d, typ, hrs, req in shifts_data:
            model.Add(sum(A[(i, d, typ)] for i in range(num_interns)) == req)

        # לא יותר ממשמרת אחת ביום
        for i in range(num_interns):
            for d in range(1, NUM_DAYS + 1):
                model.Add(sum(A.get((i, d, t), 0) for t in ['רגילה', 'תורנות']) <= 1)

        # לא לעבוד יום לפני/אחרי תורנות
        for i in range(num_interns):
            for d in range(1, NUM_DAYS + 1):
                if (i, d, 'תורנות') in A:
                    if (i, d - 1, 'רגילה') in A:
                        model.Add(A[(i, d - 1, 'רגילה')] + A[(i, d, 'תורנות')] <= 1)
                    if (i, d + 1, 'רגילה') in A:
                        model.Add(A[(i, d + 1, 'רגילה')] + A[(i, d, 'תורנות')] <= 1)

        # לפחות 48 שעות בין תורנויות (אין תורנויות יומיים ברצף)
        for i in range(num_interns):
            for d in range(1, NUM_DAYS):
                if (i, d, 'תורנות') in A and (i, d + 1, 'תורנות') in A:
                    model.Add(A[(i, d, 'תורנות')] + A[(i, d + 1, 'תורנות')] <= 1)

        # עד 6 תורנויות בחודש
        for i in range(num_interns):
            model.Add(sum(A.get((i, d, 'תורנות'), 0) for d in range(1, NUM_DAYS + 1)) <= 6)

        # עד 2 תורנויות בשבוע (נדגום כל מקטע של 7 ימים)
        for i in range(num_interns):
            for start in range(1, NUM_DAYS - 5):
                model.Add(sum(A.get((i, d, 'תורנות'), 0) for d in range(start, min(start + 7, NUM_DAYS + 1))) <= 2)

        # עד 286 שעות סה״כ
        for i in range(num_interns):
            total = []
            for d, typ, hrs, req in shifts_data:
                total.append(A[(i, d, typ)] * hrs)
            model.Add(cp_model.LinearExpr.Sum(total) <= 286)

        # מטרה: איזון עומס
        loads = []
        for i in range(num_interns):
            loads.append(sum(A[(i, d, typ)] * hrs for (d, typ, hrs, _) in shifts_data if (i, d, typ) in A))
        max_load = model.NewIntVar(0, 1000, "max")
        min_load = model.NewIntVar(0, 1000, "min")
        model.AddMaxEquality(max_load, loads)
        model.AddMinEquality(min_load, loads)
        model.Minimize(max_load - min_load)

        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            rows = []
            for (i, d, typ), var in A.items():
                if solver.Value(var):
                    rows.append({'יום': d, 'משמרת': typ, 'מתמחה': i})
            final_df = pd.DataFrame(rows)
            st.success(f"✔ נמצא פתרון עבור {num_interns} מתמחים!")
            st.dataframe(final_df)
            excel_data = final_df.to_excel(index=False)
            st.download_button("📥 הורד שיבוץ ל-Excel", data=excel_data, file_name="schedule_clean.xlsx")
            found = True
            break

    if not found:
        st.error("❌ לא נמצא פתרון תקף בין 15 ל-40 מתמחים.")
