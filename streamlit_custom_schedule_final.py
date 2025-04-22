
import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model

st.set_page_config(page_title="שיבוץ מתמחים - מותאם", layout="wide")
st.title("📅 שיבוץ רופאים מתמחים - לפי משימה 2")

st.markdown("האפליקציה יוצרת שיבוץ לפי טבלת משמרות קבועה ותנאים נוקשים בהתאם למשימה 2.")

run_button = st.button("▶ הרץ שיבוץ")

if run_button:
    # נתוני הטבלה (יום, סוג משמרת, שעות, דרישה)
    shifts_data = [
        (1, 'תורנות', 16, 4),
        (1, 'שעות רגילות', 8, 7),
        (2, 'תורנות', 16, 4),
        (2, 'שעות רגילות', 8, 7),
        (3, 'תורנות', 16, 4),
        (3, 'שעות רגילות', 8, 7),
        (4, 'תורנות', 16, 4),
        (4, 'שעות רגילות', 8, 7),
        (5, 'תורנות', 16, 4),
        (5, 'שעות רגילות', 8, 7),
        (6, 'תורנות', 16, 4),
        (6, 'שעות רגילות', 8, 7),
        (7, 'תורנות', 16, 4),
        (8, 'תורנות', 16, 4),
        (9, 'שעות רגילות', 8, 7),
        (10, 'תורנות', 16, 4),
        (11, 'שעות רגילות', 5, 6),
        (11, 'תורנות', 19, 4),
        (12, 'תורנות', 24, 4),
        (13, 'תורנות', 24, 6),
    ]

    NUM_DAYS = max([row[0] for row in shifts_data])
    model = cp_model.CpModel()
    interns = list(range(5, 35))
    final_df = None
    found = False

    for num_interns in interns:
        assigned = {}
        for i in range(num_interns):
            for d, typ, hours, req in shifts_data:
                assigned[(i, d, typ)] = model.NewBoolVar(f"intern_{i}_day_{d}_{typ}")

        for d, typ, hours, req in shifts_data:
            model.Add(sum(assigned[(i, d, typ)] for i in range(num_interns)) == req)

        for i in range(num_interns):
            for d in range(1, NUM_DAYS + 1):
                model.Add(sum(assigned.get((i, d, t), 0) for t in ['שעות רגילות', 'תורנות']) <= 1)

        for i in range(num_interns):
            model.Add(sum(assigned.get((i, d, 'תורנות'), 0) for d in range(1, NUM_DAYS + 1)) <= 6)

        for i in range(num_interns):
            for d in range(1, NUM_DAYS + 1):
                if (i, d, 'תורנות') in assigned:
                    if (i, d - 1, 'שעות רגילות') in assigned:
                        model.Add(assigned[(i, d - 1, 'שעות רגילות')] + assigned[(i, d, 'תורנות')] <= 1)
                    if (i, d + 1, 'שעות רגילות') in assigned:
                        model.Add(assigned[(i, d + 1, 'שעות רגילות')] + assigned[(i, d, 'תורנות')] <= 1)

        for i in range(num_interns):
            for d in range(1, NUM_DAYS):
                if (i, d, 'תורנות') in assigned and (i, d + 1, 'תורנות') in assigned:
                    model.Add(assigned[(i, d, 'תורנות')] + assigned[(i, d + 1, 'תורנות')] <= 1)

        for i in range(num_interns):
            total_hours = []
            for d, typ, hours, req in shifts_data:
                total_hours.append(assigned[(i, d, typ)] * hours)
            model.Add(cp_model.LinearExpr.Sum(total_hours) <= 286)

        loads = []
        for i in range(num_interns):
            loads.append(cp_model.LinearExpr.Sum(
                assigned[(i, d, typ)] * hours for (d, typ, hours, req) in shifts_data if (i, d, typ) in assigned
            ))
        max_load = model.NewIntVar(0, 1000, 'max_load')
        min_load = model.NewIntVar(0, 1000, 'min_load')
        model.AddMaxEquality(max_load, loads)
        model.AddMinEquality(min_load, loads)
        model.Minimize(max_load - min_load)

        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            rows = []
            for (i, d, typ), var in assigned.items():
                if solver.Value(var):
                    rows.append({'יום': d, 'משמרת': typ, 'מתמחה': i})
            final_df = pd.DataFrame(rows)
            found = True
            break

    if found:
        st.success(f"✔ נמצא פתרון שיבוץ עבור {num_interns} מתמחים!")
        st.dataframe(final_df)
        excel_data = final_df.to_excel(index=False)
        st.download_button("📥 הורד לקובץ Excel", data=excel_data, file_name="schedule_task2_custom.xlsx")
    else:
        st.error("❌ לא נמצא פתרון תקף לשיבוץ עבור עד 35 מתמחים.")
