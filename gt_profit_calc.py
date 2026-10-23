import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
from webdav3.client import Client

st.set_page_config(page_title="Gametrade双人台账｜内存共享+自动备份版", layout="wide")

# 获取北京时间 UTC+8
def get_beijing_now():
    utc_now = datetime.utcnow()
    bj_now = utc_now + timedelta(hours=8)
    return bj_now

# ========= WebDav坚果云备份配置 =========
@st.cache_resource
def get_webdav_client():
    options = {
        'webdav_hostname': st.secrets["WEBDAV_URL"],
        'webdav_login': st.secrets["WEBDAV_USER"],
        'webdav_password': st.secrets["WEBDAV_PASS"],
    }
    return Client(options)

# 全局共享台账（双人共用同一份内存数据）
@st.cache_resource
def get_shared_ledger():
    return []

@st.cache_resource
def get_backup_time_record():
    return {"last_backup": None}

ledger = get_shared_ledger()
backup_record = get_backup_time_record()

# 自动备份函数
def auto_backup():
    if len(ledger) == 0:
        return False, "台账为空，跳过备份"
    df = pd.DataFrame(ledger)
    bio = BytesIO()
    df.to_csv(bio, index=False, encoding="utf-8-sig")
    bio.seek(0)
    bj_now = get_beijing_now()
    fname = f"gt_backup_{bj_now.strftime('%Y%m%d_%H%M%S')}.csv"
    try:
        client = get_webdav_client()
        client.upload_to(bio, fname)
        backup_record["last_backup"] = bj_now
        return True, f"备份成功，文件名：{fname}"
    except Exception as e:
        return False, f"备份失败：{str(e)}"

# 页面加载自动判断备份间隔
bj_now = get_beijing_now()
if backup_record["last_backup"] is not None:
    diff = bj_now - backup_record["last_backup"]
    if diff.total_seconds() >= 24 * 3600:
        succ, msg = auto_backup()
        if succ:
            st.success("⏰ 触发每日自动备份：" + msg)
        else:
            st.warning("⏰ 自动备份触发但是失败：" + msg)

# 侧边栏全局参数
with st.sidebar:
    st.header("⚙️ 全局参数")
    exchange_rate = st.number_input("汇率 日元→人民币", value=0.04, min_value=0.001, max_value=0.2, step=0.0001, format="%.4f")
    gt_fee_pct = st.number_input("Gametrade平台费率(%)", value=8.8, min_value=0.0, max_value=30.0, step=0.1)/100
    withdraw_fixed_jpy = st.number_input("GT提现固定手续费(日元)", value=0, min_value=0, step=10)
    wise_fee_pct = st.number_input("Wise兑换费率(%)", value=0.0, min_value=0.0, max_value=10.0, step=0.1)/100

    st.divider()
    st.warning("⚠️ Streamlit免费容器休眠重启会清空内存台账！请定期备份到坚果云")
    if st.button("💾 手动一键备份到坚果云"):
        succ, msg = auto_backup()
        if succ:
            st.success(msg)
        else:
            st.error(msg)
    if st.button("🗑️ 清空全部台账（不可恢复）"):
        ledger.clear()
        st.rerun()

st.title("📊 Gametrade 出单利润台账｜共享内存版")

# -------- 快速试算（放最前面） --------
st.subheader("⚡ 快速试算（临时预览，不写入台账）")
t1, t2 = st.columns(2)
test_jpy = t1.number_input("试算：售价日元", min_value=0, step=100, key="test_jpy")
test_taobao_cost = t2.number_input("试算：淘宝进货价(元)", min_value=0.0, step=0.1, key="test_taobao")

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
    - 扣平台费后到手日元：{after_withdraw:.0f} JPY
    - Wise手续费：{wise_fee_jpy:.0f} JPY
    - 折合到手人民币：**{final_cny:.2f} 元**
    - 淘宝进货成本：{test_taobao_cost:.2f} 元
    - 【单笔净利润】：{net_test_profit:.2f} 元
    """)

st.divider()

# -------- 新增订单区域（修改为：淘宝进货价 + 垫款人） --------
st.subheader("➕ 添加新订单（自动记录北京时间）")
sell_jpy = st.number_input("售出金额（日元）", min_value=0, step=100, key="add_sell")
game_name = st.text_input("游戏名称", value="", key="add_game")
buy_cost = st.number_input("淘宝进货价（元）", min_value=0.0, step=0.1, key="add_buycost")
payer = st.text_input("垫款人", value="", key="add_payer")
note = st.text_input("备注", value="", key="add_note")

if st.button("✅ 添加订单到台账") and sell_jpy>0:
    bj_time_str = get_beijing_now().strftime("%Y-%m-%d %H:%M:%S")
    gt_fee_jpy = sell_jpy * gt_fee_pct
    after_gt = sell_jpy - gt_fee_jpy
    after_withdraw = after_gt - withdraw_fixed_jpy
    wise_fee_jpy = after_withdraw * wise_fee_pct
    final_jpy = after_withdraw - wise_fee_jpy
    final_cny = final_jpy * exchange_rate

    net_profit = final_cny - buy_cost

    new_row = {
        "交易时间": bj_time_str,
        "游戏": game_name,
        "垫款人": payer,
        "备注": note,
        "售价日元": sell_jpy,
        "淘宝进货价(元)": buy_cost,
        "GT手续费日元": round(gt_fee_jpy,2),
        "提现后日元": round(after_withdraw,2),
        "Wise手续费日元": round(wise_fee_jpy,2),
        "到手人民币": round(final_cny,2),
        "单笔净利润(元)": round(net_profit,2)
    }
    ledger.append(new_row)
    st.success(f"✅ 订单新增成功！北京时间：{bj_time_str}，净利润：{net_profit:.2f} 元")
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
        st.write(f"今日总到手人民币：{df_today['到手人民币'].sum():.2f} 元")
        st.write(f"今日总进货成本：{df_today['淘宝进货价(元)'].sum():.2f} 元")
        st.write(f"💰 今日净利润合计：{df_today['单笔净利润(元)'].sum():.2f} 元")
    with col_month:
        st.markdown("### 🗓️ 当月统计")
        st.write(f"当月成交单数：{len(df_month)} 单")
        st.write(f"当月总到手人民币：{df_month['到手人民币'].sum():.2f} 元")
        st.write(f"当月总进货成本：{df_month['淘宝进货价(元)'].sum():.2f} 元")
        st.write(f"💰 当月净利润合计：{df_month['单笔净利润(元)'].sum():.2f} 元")

    # 导出下载
    output = BytesIO()
    df_all.to_csv(output, index=False, encoding="utf-8-sig")
    st.download_button(
        label="💾 临时导出CSV（下载到本机）",
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
        e_payer = st.text_input("垫款人", value=target_row["垫款人"], key="e_payer")
        e_note = st.text_input("备注", value=target_row["备注"], key="e_note")
        e_sell = st.number_input("售出金额（日元）", value=int(target_row["售价日元"]), min_value=0, step=100, key="e_sell")
        e_buycost = st.number_input("淘宝进货价（元）", value=float(target_row["淘宝进货价(元)"]), min_value=0.0, step=0.1, key="e_buycost")
        e_date = st.text_input("交易时间(YYYY-MM-DD HH:MM:SS)", value=target_row["交易时间"], key="e_date")

        if st.button("✅ 保存修改", key="save_edit_btn"):
            gt_fee_jpy = e_sell * gt_fee_pct
            after_gt = e_sell - gt_fee_jpy
            after_withdraw = after_gt - withdraw_fixed_jpy
            wise_fee_jpy = after_withdraw * wise_fee_pct
            final_jpy = after_withdraw - wise_fee_jpy
            final_cny = final_jpy * exchange_rate
            net_profit = final_cny - e_buycost

            ledger[real_idx] = {
                "交易时间": e_date,
                "游戏": e_game,
                "垫款人": e_payer,
                "备注": e_note,
                "售价日元": e_sell,
                "淘宝进货价(元)": e_buycost,
                "GT手续费日元": round(gt_fee_jpy,2),
                "提现后日元": round(after_withdraw,2),
                "Wise手续费日元": round(wise_fee_jpy,2),
                "到手人民币": round(final_cny,2),
                "单笔净利润(元)": round(net_profit,2)
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
    st.info("暂无交易记录，请添加订单")

# -------- CSV导入恢复模块，放到页面最底部 --------
st.divider()
st.subheader("📥 导入CSV备份恢复台账（较少使用）")
upload_file = st.file_uploader("上传备份CSV文件恢复数据", type="csv")
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
