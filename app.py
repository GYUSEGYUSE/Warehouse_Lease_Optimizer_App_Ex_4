import pandas as pd
import streamlit as st
from scipy.optimize import linprog

st.set_page_config(page_title="Warehouse Lease Optimizer", layout="wide")
st.title("Web Mercantile: Warehouse Lease Optimizer")
st.write(
    "Pick how many square feet to lease, and for how long, each month so that "
    "every month's space requirement is met at the lowest total cost."
)

DEFAULT_REQ = [30000, 20000, 40000, 10000, 50000]
DEFAULT_COST = [65, 100, 135, 160, 190]


def solve(req, cost):
    n = len(req)
    # One variable per (start month, lease length) pair
    combos = [(s, d) for s in range(n) for d in range(1, n - s + 1)]
    c = [cost[d - 1] for s, d in combos]
    # Space in month m must be >= requirement  ->  -sum(x) <= -req
    A = [[-1 if s <= m < s + d else 0 for s, d in combos] for m in range(n)]
    b = [-r for r in req]
    res = linprog(c, A_ub=A, b_ub=b, bounds=(0, None), method="highs")
    return combos, res


left, right = st.columns(2)
with left:
    st.subheader("Space required")
    req_df = st.data_editor(
        pd.DataFrame({"Month": range(1, 6), "Required sq ft": DEFAULT_REQ}),
        num_rows="dynamic",
        hide_index=True,
        key="req",
    )
with right:
    st.subheader("Cost per sq ft by lease length")
    cost_df = st.data_editor(
        pd.DataFrame({"Lease months": range(1, 6), "Cost per sq ft ($)": DEFAULT_COST}),
        num_rows="dynamic",
        hide_index=True,
        key="cost",
    )

req = req_df["Required sq ft"].dropna().astype(float).tolist()
cost = cost_df["Cost per sq ft ($)"].dropna().astype(float).tolist()

if len(req) == 0:
    st.warning("Enter at least one month of required space.")
elif len(cost) < len(req):
    st.warning(
        f"Add cost rows so every lease length from 1 to {len(req)} months has a price."
    )
elif st.button("Solve", type="primary"):
    combos, res = solve(req, cost)
    if not res.success:
        st.error("No solution found: " + res.message)
    else:
        st.metric("Minimum total leasing cost", f"${res.fun:,.0f}")

        rows = [
            {
                "Start month": s + 1,
                "Length (months)": d,
                "End month": s + d,
                "Sq ft leased": round(x),
                "Cost": round(x * cost[d - 1]),
            }
            for (s, d), x in zip(combos, res.x)
            if x > 0.5
        ]
        st.subheader("Leases to sign")
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

        n = len(req)
        leased = [
            sum(x for (s, d), x in zip(combos, res.x) if s <= m < s + d)
            for m in range(n)
        ]
        chart = pd.DataFrame(
            {"Required": req, "Leased": [round(v) for v in leased]},
            index=[f"Month {m + 1}" for m in range(n)],
        )
        st.subheader("Required vs leased space")
        st.bar_chart(chart)
