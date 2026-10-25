import streamlit as st
import pandas as pd
from datetime import datetime
import io

# ===================== 全局默认参数 =====================
DEFAULT_EX_RATE = 0.04
DEFAULT_PLATFORM_FEE_RATE = 0.088
DEFAULT_GT_FEE = 0
DEFAULT_WISE_FEE = 0

# 初始化session数据
if "order_data" not in st.session_state:
    st.session_state["order_data"] = pd.DataFrame(
        columns=[
            "交易时间",
            "游戏名称",
            "售出日元",
            "平台手续费率",
            "GT提现手续费日元",
            "Wise手续费日元",
            "淘宝进货价(元)",
            "垫款人",
            "备注"
        ]
    )

df = st.session_state["order_data"]

st.set_page_config(page_title="GT合伙利润台账", layout="wide")
st.title("📊 GameTrade 合伙利润台账")

# 全局参数设置区
with st.expander("⚙️ 全局参数设置"):
    col1, col2, col3, col4 = st.columns(4)
    ex_rate = col1.number_input("日元兑人民币汇率", value=DEFAULT_EX_RATE, min_value=0.0001, step=0.001)
    platform_fee_rate = col2.number_input("平台手续费率", value=DEFAULT_PLATFORM_FEE_RATE, min_value=0.0, max_value=1.0, step=0.001)
    gt_fee = col3.number_input("GT提现手续费(日元)", value=DEFAULT_GT_FEE, min_value=0, step=1)
    wise_fee = col4.number_input("Wise手续费(日元)", value=DEFAULT_WISE_FEE, min_value=0, step=1)

# ---------------- 快速试算模块 ----------------
st.subheader("⚡ 快速试算")
col_a1, col_a2 = st.columns(2)
trial_sell_jpy = col_a1.number_input("售出日元金额", min_value=0, value=0)
trial_cost_rmb = col_a2.number_input("淘宝进货价(元)", min_value=0.0, value=0.0)

trial_after_platform = trial_sell_jpy * (1 - platform_fee_rate)
trial_final_jpy = trial_after_platform - gt_fee - wise_fee
trial_final_rmb = trial_final_jpy * ex_rate
trial_profit = trial_final_rmb - trial_cost_rmb
st.markdown(f"""
> 到手日元：{trial_final_jpy:.2f} JPY<br>
> 折合人民币：{trial_final_rmb:.2f} 元<br>
> 预估单笔利润：**{trial_profit:.2f} 元**
""")
st.divider()

# ---------------- 添加新订单 ----------------
st.subheader("➕ 添加新订单")
now_bj = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
col_b1, col_b2 = st.columns(2)
game_name = col_b1.text_input("游戏名称")
sell_jpy = col_b2.number_input("售出日元", min_value=0, step=1)
col_b3, col_b4 = st.columns(2)
buy_cost_rmb = col_b3.number_input("淘宝进货价(元)", min_value=0.0, step=0.01)
payer_name = col_b4.text_input("垫款人")
note = st.text_input("备注")

if st.button("✅ 新增这条订单"):
    new_row = {
        "交易时间": now_bj,
        "游戏名称": game_name,
        "售出日元": sell_jpy,
        "平台手续费率": platform_fee_rate,
        "GT提现手续费日元": gt_fee,
        "Wise手续费日元": wise_fee,
        "淘宝进货价(元)": buy_cost_rmb,
        "垫款人": payer_name,
        "备注": note
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    st.session_state["order_data"] = df
    st.success("订单添加成功！")
st.divider()

# ---------------- 订单列表、编辑删除 ----------------
st.subheader("📋 订单列表")
if len(df) > 0:
    show_df = df.copy()
    st.dataframe(show_df, use_container_width=True)

    idx_del = st.selectbox("选择要删除的订单行号", options=range(len(df)), format_func=lambda x: f"第{x+1}行 | {df.iloc[x]['交易时间']} {df.iloc[x]['游戏名称']}")
    if st.button("🗑️ 删除选中单行"):
        df = df.drop(idx_del).reset_index(drop=True)
        st.session_state["order_data"] = df
        st.success("已删除")
else:
    st.info("暂无订单记录")
st.divider()

# ---------------- 统计汇总板块 ----------------
st.subheader("📈 收益统计 & 垫款人分润")
if len(df) > 0:
    # 计算每条订单实际利润
    calc_df = df.copy()
    calc_df["扣除平台费日元"] = calc_df["售出日元"] * (1 - calc_df["平台手续费率"])
    calc_df["最终到手日元"] = calc_df["扣除平台费日元"] - calc_df["GT提现手续费日元"] - calc_df["Wise手续费日元"]
    calc_df["到手人民币"] = calc_df["最终到手日元"] * ex_rate
    calc_df["单笔利润"] = calc_df["到手人民币"] - calc_df["淘宝进货价(元)"]

    # 当日筛选
    today_str = datetime.now().strftime("%Y-%m-%d")
    calc_df["日期"] = calc_df["交易时间"].str[:10]
    today_df = calc_df[calc_df["日期"] == today_str]

    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    col_c1.metric("今日成交单数", len(today_df))
    col_c2.metric("今日到手人民币", f"{today_df['到手人民币'].sum():.2f}")
    col_c3.metric("今日进货总成本", f"{today_df['淘宝进货价(元)'].sum():.2f}")
    col_c4.metric("今日净利润", f"{today_df['单笔利润'].sum():.2f}")

    st.markdown("### 当月汇总（全部数据）")
    total_rmb_get = calc_df["到手人民币"].sum()
    total_cost = calc_df["淘宝进货价(元)"].sum()
    total_profit = calc_df["单笔利润"].sum()
    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("总到手人民币", f"{total_rmb_get:.2f}")
    cc2.metric("总垫款进货成本", f"{total_cost:.2f}")
    cc3.metric("累计总利润", f"{total_profit:.2f}")

    st.markdown("### 按垫款人汇总")
    group_payer = calc_df.groupby("垫款人").agg({
        "售出日元": "sum",
        "淘宝进货价(元)": "sum",
        "单笔利润": ["count", "sum"]
    }).round(2)
    group_payer.columns = ["售出日元合计", "垫款总额(元)", "订单数量", "该垫款人对应利润合计"]
    st.dataframe(group_payer, use_container_width=True)

    st.info("💡结算说明：总到手扣除全部垫款成本后的剩余利润，由你们两人自行约定平分。本台账只负责统计数据，自动计算单笔利润。")
else:
    st.info("添加订单后才能查看统计")
st.divider()

# ---------------- CSV导出 ----------------
st.subheader("💾 导出台账CSV备份")
buf = io.StringIO()
df.to_csv(buf, index=False, encoding="utf-8-sig")
csv_bytes = buf.getvalue().encode("utf-8-sig")
st.download_button(
    label="📥 下载CSV备份文件",
    data=csv_bytes,
    file_name=f"gt台账_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv"
)
st.divider()

# ---------------- CSV导入（放在页面最底部） ----------------
st.subheader("📂 导入CSV备份恢复台账（页面底部）")
uploaded_file = st.file_uploader("上传之前导出的csv文件恢复数据", type="csv")
if uploaded_file is not None:
    try:
        import_df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
        st.session_state["order_data"] = import_df
        st.success("✅ 导入成功，数据已覆盖！")
    except Exception as e:
        st.error(f"导入失败：{e}")
