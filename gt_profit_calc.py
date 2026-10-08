import streamlit as st
import pandas as pd
from datetime import datetime
import os
import plotly.express as px

DATA_FILE = "gt_trade_data.csv"

# 初始化数据
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE, parse_dates=["date"])
else:
    df = pd.DataFrame(columns=[
        "date", "goods_name", "remark", "gt_price_jpy", "cost_cny", "buyer_person",
        "after_fee_jpy", "receive_cny", "total_profit_cny",
        "W_profit", "D_profit"
    ])

st.set_page_config(page_title="Gametrade收益计算器｜W&D对半分利润", layout="wide")
st.title("Gametrade 账号交易收益统计")

# ====================== 【网页端可修改参数区域】 ======================
st.subheader("⚙️ 参数设置（实时生效）")
col_param1, col_param2 = st.columns(2)
with col_param1:
    FEE_RATE = st.number_input("GT平台手续费(%)", min_value=0.0, max_value=30.0, value=8.8, step=0.1) / 100
with col_param2:
    EXCHANGE_RATE = st.number_input("汇率：1日元 = ? 人民币", min_value=0.001, max_value=0.2, value=0.041, step=0.001)
st.divider()
# =====================================================================

# ========== 录入表单 ==========
with st.form("add_form"):
    col1, col2 = st.columns(2)
    with col1:
        goods_name = st.text_input("商品名称（游戏名）")
        remark = st.text_input("备注（例如：FGO日服、栄冠クロス，可空）")
        gt_price_jpy = st.number_input("GT售卖价（日元）", min_value=0.0, step=100)
        cost_cny = st.number_input("淘宝进货垫付成本（人民币）", min_value=0.0, step=0.1)
    with col2:
        buyer_person = st.selectbox("进货垫付人", ["W", "D"])
        trade_date = st.date_input("交易日期", value=datetime.now())
    submitted = st.form_submit_button("添加这条交易记录")

    if submitted:
        # 核心计算
        after_fee_jpy = gt_price_jpy * (1 - FEE_RATE)
        receive_cny = after_fee_jpy * EXCHANGE_RATE
        total_profit_cny = receive_cny - cost_cny
        w_profit = total_profit_cny * 0.5
        d_profit = total_profit_cny * 0.5

        new_row = pd.DataFrame({
            "date": [trade_date],
            "goods_name": [goods_name],
            "remark": [remark],
            "gt_price_jpy": [gt_price_jpy],
            "cost_cny": [cost_cny],
            "buyer_person": [buyer_person],
            "after_fee_jpy": [after_fee_jpy],
            "receive_cny": [receive_cny],
            "total_profit_cny": [total_profit_cny],
            "W_profit": [w_profit],
            "D_profit": [d_profit]
        })
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.success(f"""✅ 记录保存成功
这笔订单总利润：{total_profit_cny:.2f}元
W分得：{w_profit:.2f}元｜D分得：{d_profit:.2f}元
垫付人：{buyer_person}""")

st.divider()

# ========== 月份筛选 ==========
st.subheader("📋 交易记录查询")
df["year_month"] = df["date"].dt.strftime("%Y-%m")
month_list = sorted(df["year_month"].unique(), reverse=True)
select_month = st.selectbox("选择月份（全部则选全部）", ["全部"] + month_list)

if select_month != "全部":
    df_show = df[df["year_month"] == select_month].copy()
else:
    df_show = df.copy()

# 显示表格 + 删除行功能
st.dataframe(df_show, use_container_width=True)
row_to_del = st.number_input("输入要删除的行索引（录错的订单）", min_value=0, max_value=max(len(df)-1,0), value=0)
if st.button("删除该条记录"):
    df = df.drop(row_to_del).reset_index(drop=True)
    df.to_csv(DATA_FILE, index=False)
    st.success("✅ 删除成功，页面刷新后生效")

# 导出CSV
csv_data = df_show.to_csv(index=False, encoding="utf-8-sig")
st.download_button(label="📥 导出当前筛选记录为CSV(Excel可打开)", data=csv_data, file_name="gt_trade_records.csv", mime="text/csv")

st.divider()

# ========== 每日收益折线图 ==========
st.subheader("📈 每日营收&利润趋势图")
if not df_show.empty:
    # 按日期聚合
    daily_summary = df_show.groupby("date").agg(
        daily_receive=("receive_cny", "sum"),
        daily_profit=("total_profit_cny", "sum")
    ).reset_index()
    fig_line = px.line(daily_summary, x="date", y=["daily_receive","daily_profit"],
                  labels={"value":"金额(CNY)", "date":"日期", "variable":"项目"},
                  title="每日到手营收 & 每日总利润")
    fig_line.for_each_trace(lambda t: t.update(name="每日到手营收" if t.name=="daily_receive" else "每日总利润"))
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("暂无数据，添加订单后会自动生成图表")

st.divider()

# ========== 按游戏名称统计饼图 ==========
st.subheader("🥧 各游戏总利润占比饼图")
if not df_show.empty:
    game_summary = df_show.groupby("goods_name")["total_profit_cny"].sum().reset_index()
    fig_pie = px.pie(game_summary, values="total_profit_cny", names="goods_name",
                     title="各游戏利润占比",
                     labels={"total_profit_cny":"总利润(CNY)", "goods_name":"游戏名称"})
    fig_pie.update_traces(texttemplate='%{percent:.1%}<br>%{value:.2f}元', textposition='inside')
    st.plotly_chart(fig_pie, use_container_width=True)
else:
    st.info("暂无订单数据，录入订单后自动生成饼图")

st.divider()

# ========== 汇总统计 ==========
st.subheader("💰 汇总统计（当前筛选周期）")
# 全局合计
sum_total_receive = df_show["receive_cny"].sum()
sum_total_cost = df_show["cost_cny"].sum()
sum_total_profit = df_show["total_profit_cny"].sum()
sum_w_profit = df_show["W_profit"].sum()
sum_d_profit = df_show["D_profit"].sum()

# 垫付成本拆分：W垫付总额 / D垫付总额
sum_cost_w = df_show[df_show["buyer_person"] == "W"]["cost_cny"].sum()
sum_cost_d = df_show[df_show["buyer_person"] == "D"]["cost_cny"].sum()

col1, col2, col3 = st.columns(3)
col1.metric("总到手营收(人民币)", f"{sum_total_receive:.2f}")
col2.metric("总垫付进货成本", f"{sum_total_cost:.2f}")
col3.metric("全部订单总利润", f"{sum_total_profit:.2f}")

st.markdown("---")
colA, colB = st.columns(2)
with colA:
    st.markdown("### W")
    st.metric("W 总分得利润", f"{sum_w_profit:.2f} CNY")
    st.metric("W 垫付的进货总成本", f"{sum_cost_w:.2f} CNY")
    w_final = sum_w_profit + sum_cost_w
    st.info(f"""W 结算净额参考（回款后）
= W利润 + 拿回自己垫付本金
= {sum_w_profit:.2f} + {sum_cost_w:.2f} = {w_final:.2f}""")

with colB:
    st.markdown("### D")
    st.metric("D 总分得利润", f"{sum_d_profit:.2f} CNY")
    st.metric("D 垫付的进货总成本", f"{sum_cost_d:.2f} CNY")
    d_final = sum_d_profit + sum_cost_d
    st.info(f"""D 结算净额参考（回款后）
= D利润 + 拿回自己垫付本金
= {sum_d_profit:.2f} + {sum_cost_d:.2f} = {d_final:.2f}""")

st.divider()
st.warning("""📌结算说明：
1. 无论W还是D垫付进货，每一笔订单产生的净利润两人对半平分。
2. 垫付的进货成本，结算时归还给垫付人。
3. 【结算净额参考】= 个人分得利润 + 自己垫付的本金。
4. 所有金额仅为内部记账对账使用。""")
