import streamlit as st
import json
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Gametrade利润计算器", layout="wide")

def persist_all():
    data = {
        "exchange_rate": st.session_state["exchange_rate"],
        "gt_fee_pct": st.session_state["gt_fee_pct"],
        "withdraw_fixed_jpy": st.session_state["withdraw_fixed_jpy"],
        "wise_fee_pct": st.session_state["wise_fee_pct"],
        "ledger": st.session_state["ledger"]
    }
    st.components.v1.html(f"""
    <script>
    window.localStorage.setItem('gt_profit_data', JSON.stringify({json.dumps(data, ensure_ascii=False)}));
    </script>
    """, height=0)

st.components.v1.html("""
<script>
const raw = window.localStorage.getItem('gt_profit_data');
if(raw){
    window.gt_cache = JSON.parse(raw);
}
</script>
""", height=0)

if "init_flag" not in st.session_state:
    st.session_state.init_flag = True
    st.session_state["exchange_rate"] = 0.041
    st.session_state["gt_fee_pct"] = 0.10
    st.session_state["withdraw_fixed_jpy"] = 220
    st.session_state["wise_fee_pct"] = 0.012
    st.session_state["ledger"] = []

# ========== 侧边栏：全局费率设置 ==========
with st.sidebar:
    st.header("⚙️ 全局参数（自动保存）")
    exchange_rate = st.number_input("汇率 日元→人民币", value=st.session_state["exchange_rate"], min_value=0.001, max_value=0.2, step=0.0001, format="%.4f")
    gt_fee_pct = st.number_input("Gametrade平台费率(%)", value=st.session_state["gt_fee_pct"]*100, min_value=0.0, max_value=30.0, step=0.1)/100
    withdraw_fixed_jpy = st.number_input("GT提现固定手续费(日元)", value=int(st.session_state["withdraw_fixed_jpy"]), min_value=0, step=10)
    wise_fee_pct = st.number_input("Wise兑换费率(%)", value=st.session_state["wise_fee_pct"]*100, min_value=0.0, max_value=10.0, step=0.1)/100

    st.session_state["exchange_rate"] = exchange_rate
    st.session_state["gt_fee_pct"] = gt_fee_pct
    st.session_state["withdraw_fixed_jpy"] = withdraw_fixed_jpy
    st.session_state["wise_fee_pct"] = wise_fee_pct
    persist_all()

    st.divider()
    if st.button("🗑️ 清空全部台账（不可恢复）"):
        st.session_state["ledger"] = []
        persist_all()
        st.rerun()

# ========== 主页面 ==========
st.title("📊 Gametrade 日元交易利润计算器【完整版｜可编辑+删除+筛选】")

# -------- CSV导入模块 --------
st.subheader("📥 导入CSV备份恢复台账")
upload_file = st.file_uploader("上传导出的 gt_profit_ledger.csv", type="csv")
if upload_file is not None:
    import_df = pd.read_csv(upload_file, encoding="utf-8-sig")
    import_rows = import_df.to_dict("records")
    mode = st.radio("导入模式", ["追加到现有台账", "覆盖当前全部台账"], horizontal=True)
    if st.button("✅ 确认导入"):
        if mode == "覆盖当前全部台账":
            st.session_state["ledger"] = import_rows
        else:
            st.session_state["ledger"].extend(import_rows)
        persist_all()
        st.success(f"✅ 导入成功，共 {len(import_rows)} 条订单")
        st.rerun()

st.divider()

# -------- 新增订单 --------
st.subheader("➕ 添加新订单")
col1,col2,col3,col4 = st.columns(4)
sell_jpy = col1.number_input("售出金额（日元）", min_value=0, step=100)
cost_cny = col2.number_input("账号成本（人民币）", min_value=0.0, step=0.1)
game_name = col3.text_input("游戏名称", value="")
note = col4.text_input("备注", value="")

if st.button("✅ 添加到台账") and sell_jpy>0:
    gt_fee_jpy = sell_jpy * gt_fee_pct
    after_gt = sell_jpy - gt_fee_jpy
    after_withdraw = after_gt - withdraw_fixed_jpy
    wise_fee_jpy = after_withdraw * wise_fee_pct
    final_jpy = after_withdraw - wise_fee_jpy
    final_cny = final_jpy * exchange_rate
    profit_cny = final_cny - cost_cny
    if cost_cny > 0:
        rate = profit_cny / cost_cny
        rate_str = f"{rate*100:.1f}%"
    else:
        rate_str = "无成本"

    row = {
        "游戏": game_name,
        "备注": note,
        "售价日元": sell_jpy,
        "GT手续费日元": round(gt_fee_jpy,2),
        "提现后日元": round(after_withdraw,2),
        "Wise手续费日元": round(wise_fee_jpy,2),
        "到手日元": round(final_jpy,2),
        "到手人民币": round(final_cny,2),
        "成本CNY": cost_cny,
        "净利润CNY": round(profit_cny,2),
        "毛利率": rate_str
    }
    st.session_state["ledger"].append(row)
    persist_all()
    st.success("✅ 订单已加入台账，自动保存！")
    st.rerun()

# -------- 台账 + 筛选 + 编辑/删除单行 --------
st.divider()
st.subheader("📋 交易台账")
ledger = st.session_state["ledger"]

if ledger:
    df_all = pd.DataFrame(ledger).reset_index(drop=True)
    df_all.insert(0, "序号", list(range(1, len(df_all)+1)))

    # 游戏筛选
    all_games = ["全部游戏"] + sorted(df_all["游戏"].unique().tolist())
    select_game = st.selectbox("🔍 筛选游戏", all_games)
    if select_game != "全部游戏":
        df_filter = df_all[df_all["游戏"] == select_game].copy()
    else:
        df_filter = df_all.copy()

    st.dataframe(df_filter, use_container_width=True, hide_index=True)

    # 筛选后汇总统计
    sum_sell = df_filter["售价日元"].sum()
    sum_final_cny = df_filter["到手人民币"].sum()
    sum_cost = df_filter["成本CNY"].sum()
    sum_profit = df_filter["净利润CNY"].sum()
    st.markdown(f"""
    ### 📈 当前筛选结果汇总
    - 订单数量：{len(df_filter)} 条
    - 总售出日元：**{sum_sell:,.0f} JPY**
    - 总到手人民币：**{sum_final_cny:,.2f} CNY**
    - 总成本：**{sum_cost:,.2f} CNY**
    - 总净利润：**{sum_profit:,.2f} CNY**
    """)

    # 导出全部台账
    output = BytesIO()
    df_all.drop(columns=["序号"]).to_csv(output, index=False, encoding="utf-8-sig")
    st.download_button(
        label="💾 导出【全部台账】CSV备份",
        data=output.getvalue(),
        file_name="gt_profit_ledger.csv",
        mime="text/csv"
    )

    st.divider()
    st.subheader("✏️ 编辑 / 🗑️ 删除单条记录")
    edit_del_idx = st.number_input("输入要操作的【原始序号】", min_value=1, max_value=len(df_all), step=1)
    real_idx = edit_del_idx - 1
    target_row = st.session_state["ledger"][real_idx]

    tab_edit, tab_del = st.tabs(["✏️ 编辑这条记录", "🗑️ 删除这条记录"])
    with tab_edit:
        e_game = st.text_input("游戏名称", value=target_row["游戏"])
        e_note = st.text_input("备注", value=target_row["备注"])
        e_sell = st.number_input("售出金额（日元）", value=int(target_row["售价日元"]), min_value=0, step=100)
        e_cost = st.number_input("账号成本（人民币）", value=float(target_row["成本CNY"]), min_value=0.0, step=0.1)
        if st.button("✅ 保存修改"):
            # 重新计算
            gt_fee_jpy = e_sell * gt_fee_pct
            after_gt = e_sell - gt_fee_jpy
            after_withdraw = after_gt - withdraw_fixed_jpy
            wise_fee_jpy = after_withdraw * wise_fee_pct
            final_jpy = after_withdraw - wise_fee_jpy
            final_cny = final_jpy * exchange_rate
            profit_cny = final_cny - e_cost
            if e_cost > 0:
                rate = profit_cny / e_cost
                rate_str = f"{rate*100:.1f}%"
            else:
                rate_str = "无成本"
            new_row = {
                "游戏": e_game,
                "备注": e_note,
                "售价日元": e_sell,
                "GT手续费日元": round(gt_fee_jpy,2),
                "提现后日元": round(after_withdraw,2),
                "Wise手续费日元": round(wise_fee_jpy,2),
                "到手日元": round(final_jpy,2),
                "到手人民币": round(final_cny,2),
                "成本CNY": e_cost,
                "净利润CNY": round(profit_cny,2),
                "毛利率": rate_str
            }
            st.session_state["ledger"][real_idx] = new_row
            persist_all()
            st.success(f"✅ 序号 {edit_del_idx} 修改完成！")
            st.rerun()

    with tab_del:
        st.warning(f"⚠️ 确认删除序号 {edit_del_idx} 的记录吗？删除后只能靠CSV备份恢复！")
        if st.button("🗑️ 确认删除"):
            st.session_state["ledger"].pop(real_idx)
            persist_all()
            st.success(f"✅ 序号 {edit_del_idx} 已删除！")
            st.rerun()

else:
    st.info("暂无交易记录，添加订单或者上传CSV备份")

# -------- 快速试算 --------
st.divider()
st.subheader("⚡ 快速试算（临时，不存入台账）")
test_jpy = st.number_input("试算：售价日元", min_value=0, step=100, key="test")
if test_jpy>0:
    gt_fee_jpy = test_jpy * gt_fee_pct
    after_gt = test_jpy - gt_fee_jpy
    after_withdraw = after_gt - withdraw_fixed_jpy
    wise_fee_jpy = after_withdraw * wise_fee_pct
    final_jpy = after_withdraw - wise_fee_jpy
    final_cny = final_jpy * exchange_rate
    st.write(f"""
    - GT手续费：{gt_fee_jpy:.0f} JPY
    - 扣提现费后：{after_withdraw:.0f} JPY
    - Wise手续费：{wise_fee_jpy:.0f} JPY
    - 最终到手日元：{final_jpy:.0f} JPY
    - 折合人民币：**{final_cny:.2f} CNY**
    """)

