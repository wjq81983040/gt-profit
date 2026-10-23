import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO

st.set_page_config(page_title="Gametrade双人台账｜内存共享版", layout="wide")

# 北京时间
def get_beijing_now():
    utc_now = datetime.utcnow()
    bj_now = utc_now + timedelta(hours=8)
    return bj_now

# ========= 全局共享台账（核心：cache_resource，全用户共用同一份数据，就是你之前老版本的同步逻辑） =========
@st.cache_resource
def get_shared_ledger():
    return []

ledger = get_shared_ledger()

# 侧边栏全局参数
with st.sidebar:
    st.header("⚙️ 全局参数")
    exchange_rate = st.number_input("汇率 日元→人民币", value=0.04, min_value=0.001, max_value=0.2, step=0.0001, format="%.4f")
    gt_fee_pct = st.number_input("Gametrade平台费率(%)", value=8.8, min_value=0.0, max_value=30.0, step=0.1)/100
    withdraw_fixed_jpy = st.number_input("GT提现固定手续费(日元)", value=0, min_value=0, step=10)
    wise_fee_pct = st.number_input("Wise兑换费率(%)", value=0.0, min_value=0.0, max_value=10.0, step=0.1)/100

    st.divider()
    st.warning("⚠️ 注意：免费云容器休眠/重启会清空内存台账！记得经常导出CSV备份！")
    if st.button("🗑️ 清空全部台账（不可恢复）"):
        ledger.clear()
        st.rerun()

st.title("📊 Gametrade 双人垫款利润台账｜共享内存版")

# -------- 快速试算（放最前面） --------
st.subheader("⚡ 快速试算（临时预览，不写入台账）")
t1, t2 = st.columns(2)
test_jpy = t1.number_input("试算：售价日元", min_value=0, step=100, key="test_jpy")
test_taobao_cost = t2.number_input("试算：淘宝总成本(元)", min_value=0.0, step=0.1, key="test_taobao")

if test_jpy>0:
    gt_fee_jpy = test_jpy * gt_fee_pct
    after_gt = test_jpy - gt_fee_jpy
    after_withdraw = after_gt - withdraw_fixed_jpy
    wise_fee_jpy = after_withdraw * wise_fee_pct
    final_jpy = after_withdraw - wise_fee_jpy
    final_cny = final_jpy * exchange_rate
    net_test_profit = final_cny - test_taobao_cost

    st.write(f"""
    - GT手续费：{gt_fee_jpy:.0f} JPY
    - 扣固定提现费后：{after_withdraw:.0f} JPY
    - Wise手续费：{wise_fee_jpy:.0f} JPY
    - 最终到手日元：{final_jpy:.0f} JPY
    - 折合到手人民币：**{final_cny:.2f} 元**
    - 淘宝总成本：{test_taobao_cost:.2f} 元
    - 【净利润】：{net_test_profit:.2f} 元
    """)

st.divider()

# -------- CSV导入模块 --------
st.subheader("📥 导入CSV备份恢复台账")
upload_file = st.file_uploader("上传导出的 gt_profit_ledger.csv", type="csv")
if upload_file is not None:
    import_df = pd.read_csv(upload_file, encoding="utf-8-sig")
    import_rows = import_df.to_dict("records")
    mode = st.radio("导入模式", ["追加到现有台账", "覆盖当前全部台账"], horizontal=True)
    if st.button("✅ 确认导入"):
        if mode == "覆盖当前全部台账":
            ledger.clear()
        ledger.extend(import_rows)
        st.success(f"✅ 导入成功，共 {len(import_rows)} 条订单")
        st.rerun()

st.divider()

# -------- 新增订单（上下垂直排列W/D垫款，自动北京时间） --------
st.subheader("➕ 添加新订单（自动记录北京时间）")
sell_jpy = st.number_input("售出金额（日元）", min_value=0, step=100, key="add_sell")
game_name = st.text_input("游戏名称", value="", key="add_game")
w_cost = st.number_input("W垫款(元)", min_value=0.0, step=0.1, key="add_w")
d_cost = st.number_input("D垫款(元)", min_value=0.0, step=0.1, key="add_d")
note = st.text_input("备注", value="", key="add_note")

if st.button("✅ 添加订单到台账") and sell_jpy>0:
    bj_time_str = get_beijing_now().strftime("%Y-%m-%d %H:%M:%S")
    gt_fee_jpy = sell_jpy * gt_fee_pct
    after_gt = sell_jpy - gt_fee_jpy
    after_withdraw = after_gt - withdraw_fixed_jpy
    wise_fee_jpy = after_withdraw * wise_fee_pct
    final_jpy = after_withdraw - wise_fee_jpy
    final_cny = final_jpy * exchange_rate

    total_cost = w_cost + d_cost
    net_profit = final_cny - total_cost
    w_get = w_cost + net_profit / 2
    d_get = d_cost + net_profit / 2

    new_row = {
        "交易时间": bj_time_str,
        "游戏": game_name,
        "备注": note,
        "售价日元": sell_jpy,
        "W垫款(元)": w_cost,
        "D垫款(元)": d_cost,
        "GT手续费日元": round(gt_fee_jpy,2),
        "提现后日元": round(after_withdraw,2),
        "Wise手续费日元": round(wise_fee_jpy,2),
        "到手日元": round(final_jpy,2),
        "到手人民币": round(final_cny,2),
        "总垫款(元)": round(total_cost,2),
        "净利润(元)": round(net_profit,2),
        "W总共分得(元)": round(w_get,2),
        "D总共分得(元)": round(d_get,2)
    }
    ledger.append(new_row)
    st.success(f"✅ 订单新增成功！北京时间：{bj_time_str}")
    st.rerun()

# -------- 台账展示、筛选、统计 --------
st.divider()
st.subheader("📋 交易台账")
df_all = pd.DataFrame(ledger)

if not df_all.empty:
    df_display = df_all.copy()
    df_display.insert(0, "序号", list(range(1, len(df_display)+1)))
    all_games = ["全部游戏"] + sorted(df_display["游戏"].unique().tolist())
    select_game = st.selectbox("🔍 筛选游戏", all_games)
    if select_game != "全部游戏":
        df_filter = df_display[df_display["游戏"] == select_game].copy()
    else:
        df_filter = df_display.copy()
    st.dataframe(df_filter, use_container_width=True, hide_index=True)

    # 日/月统计
    now_bj = get_beijing_now()
    today_str = now_bj.strftime("%Y-%m-%d")
    month_prefix = now_bj.strftime("%Y-%m")
    df_all["日期"] = df_all["交易时间"].str[:10]
    df_today = df_all[df_all["日期"] == today_str]
    df_month = df_all[df_all["交易时间"].str.startswith(month_prefix)]

    st.divider()
    st.subheader("📈 收益汇总统计")
    col_today, col_month = st.columns(2)
    with col_today:
        st.markdown("### 📅 今日统计")
        st.write(f"今日成交单数：{len(df_today)} 单")
        st.write(f"今日到手人民币：{df_today['到手人民币'].sum():.2f} 元")
        st.write(f"W今日垫款合计：{df_today['W垫款(元)'].sum():.2f} 元")
        st.write(f"D今日垫款合计：{df_today['D垫款(元)'].sum():.2f} 元")
        st.write(f"💰 今日净利润合计：{df_today['净利润(元)'].sum():.2f} 元")
    with col_month:
        st.markdown("### 🗓️ 当月统计")
        st.write(f"当月成交单数：{len(df_month)} 单")
        st.write(f"当月到手人民币：{df_month['到手人民币'].sum():.2f} 元")
        st.write(f"W当月垫款合计：{df_month['W垫款(元)'].sum():.2f} 元")
        st.write(f"D当月垫款合计：{df_month['D垫款(元)'].sum():.2f} 元")
        st.write(f"💰 当月净利润合计：{df_month['净利润(元)'].sum():.2f} 元")

    # 导出全部台账
    output = BytesIO()
    df_all.to_csv(output, index=False, encoding="utf-8-sig")
    st.download_button(
        label="💾 导出【全部台账】CSV备份",
        data=output.getvalue(),
        file_name="gt_profit_ledger.csv",
        mime="text/csv"
    )

    st.divider()
    st.subheader("✏️ 编辑 / 🗑️ 删除单条记录")
    edit_del_idx = st.number_input("输入要操作的【原始序号】", min_value=1, max_value=len(df_all), step=1, key="edit_idx_input")
    real_idx = edit_del_idx - 1
    target_row = ledger[real_idx]

    tab_edit, tab_del = st.tabs(["✏️ 编辑这条记录", "🗑️ 删除这条记录"])
    with tab_edit:
        e_game = st.text_input("游戏名称", value=target_row["游戏"], key="e_game")
        e_note = st.text_input("备注", value=target_row["备注"], key="e_note")
        e_sell = st.number_input("售出金额（日元）", value=int(target_row["售价日元"]), min_value=0, step=100, key="e_sell")
        e_w_cost = st.number_input("W垫款(元)", value=float(target_row["W垫款(元)"]), min_value=0.0, step=0.1, key="e_w")
        e_d_cost = st.number_input("D垫款(元)", value=float(target_row["D垫款(元)"]), min_value=0.0, step=0.1, key="e_d")
        e_date = st.text_input("交易时间(YYYY-MM-DD HH:MM:SS)", value=target_row["交易时间"], key="e_date")

        if st.button("✅ 保存修改", key="save_edit_btn"):
            gt_fee_jpy = e_sell * gt_fee_pct
            after_gt = e_sell - gt_fee_jpy
            after_withdraw = after_gt - withdraw_fixed_jpy
            wise_fee_jpy = after_withdraw * wise_fee_pct
            final_jpy = after_withdraw - wise_fee_jpy
            final_cny = final_jpy * exchange_rate
            total_cost = e_w_cost + e_d_cost
            net_profit = final_cny - total_cost
            w_get = e_w_cost + net_profit / 2
            d_get = e_d_cost + net_profit / 2

            ledger[real_idx] = {
                "交易时间": e_date,
                "游戏": e_game,
                "备注": e_note,
                "售价日元": e_sell,
                "W垫款(元)": e_w_cost,
                "D垫款(元)": e_d_cost,
                "GT手续费日元": round(gt_fee_jpy,2),
                "提现后日元": round(after_withdraw,2),
                "Wise手续费日元": round(wise_fee_jpy,2),
                "到手日元": round(final_jpy,2),
                "到手人民币": round(final_cny,2),
                "总垫款(元)": round(total_cost,2),
                "净利润(元)": round(net_profit,2),
                "W总共分得(元)": round(w_get,2),
                "D总共分得(元)": round(d_get,2)
            }
            st.success(f"✅ 序号 {edit_del_idx} 修改完成！")
            st.rerun()

    with tab_del:
        st.warning(f"⚠️ 确认删除序号 {edit_del_idx} 的记录吗？")
        if st.button("🗑️ 确认删除", key="del_btn"):
            ledger.pop(real_idx)
            st.success(f"✅ 序号 {edit_del_idx} 已删除！")
            st.rerun()
else:
    st.info("暂无交易记录，添加订单或者上传CSV备份")
