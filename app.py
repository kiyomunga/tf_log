import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection

# ==========================================
# ⚙️ Configuration & DB Init
# ==========================================
st.set_page_config(page_title="WPT - カンカレ特化版 V4.7", layout="wide")
st.title("❄️ WPT: Kanto-Incolle 2027 Tracker")

# 【重要】 あなたのスプレッドシートIDに書き換えてください
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1wwCZCXt35ElkLSX5NHGeTGylP8LsEoH8F1zaFXV3OB8/edit?gid=970575452#gid=970575452"
conn = st.connection("gsheets", type=GSheetsConnection)

PHASES = ["PHASE 1 (10/28〜1/9)", "PHASE 2.1 (1/18〜2/21)", "PHASE 2.2 (2/22〜3/14)"]
EXERCISES = {
    "ウエイト": ["バックスクワット(SQ)", "ベンチプレス(BP)"],
    "コントロールテスト": ["立ち幅跳び", "立ち五段跳び", "MBフロント(3kg)", "MBバック(3kg)", "ハードルジャンプ五連"],
    "投げ": ["砲丸", "円盤", "やり"]
}

# ==========================================
# 📊 Data Fetching
# ==========================================
@st.cache_data
def load_data():
    try:
        df_logs = conn.read(spreadsheet=spreadsheet_url, worksheet="Logs")
        df_targets = conn.read(spreadsheet=spreadsheet_url, worksheet="Targets")
        df_matches = conn.read(spreadsheet=spreadsheet_url, worksheet="Matches")
        return df_logs, df_targets, df_matches
    except Exception as e:
        st.error(f"DB読み込みエラー: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

logs_df, targets_df, matches_df = load_data()

# --- 💡 データクレンジング ---
if not logs_df.empty:
    logs_df['日付'] = pd.to_datetime(logs_df['日付'], errors='coerce')
    for col in ['重量', '回数', 'セット数', '記録']:
        if col in logs_df.columns:
            logs_df[col] = pd.to_numeric(logs_df[col], errors='coerce')
    for col in ['フェーズ', '種目']:
        if col in logs_df.columns:
            logs_df[col] = logs_df[col].astype(object)

if not targets_df.empty:
    for col in ['目標重量', '目標回数', '目標セット数', '目標記録']:
        if col in targets_df.columns:
            targets_df[col] = pd.to_numeric(targets_df[col], errors='coerce')
    for col in ['フェーズ', '種目']:
        if col in targets_df.columns:
            targets_df[col] = targets_df[col].astype(object)

if not matches_df.empty:
    matches_df['試合日'] = pd.to_datetime(matches_df['試合日'], errors='coerce')
    for col in ['目標記録', '実績記録']:
        if col in matches_df.columns:
            matches_df[col] = pd.to_numeric(matches_df[col], errors='coerce')
    for col in ['大会名', '出場種目', '技術テーマ', 'コンディション', '要因分析', 'ステータス']:
        if col in matches_df.columns:
            matches_df[col] = matches_df[col].astype(object)

tab1, tab2, tab3 = st.tabs(["📝 Tab 1: 統合入力コンソール", "📊 Tab 2: 冬季練進捗ダッシュボード", "🏟️ Tab 3: カンカレ実戦 & PB管理"])

# ==========================================
# Tab 1: Input Console (Write)
# ==========================================
with tab1:
    st.header("📝 統合入力コンソール")
    input_mode = st.radio("入力モードを選択", 
                          ["① 日常トレーニング記録", "② フェーズ別目標設定", "③ 試合エントリー (Pre-Match)", "④ 試合結果アップデート (Post-Match)"], 
                          horizontal=True)
    
    # -----------------------------------------
    # ① 日常トレーニング記録
    # -----------------------------------------
    if input_mode == "① 日常トレーニング記録":
        st.subheader("🏋️ コア指標ロギング")
        date = st.date_input("日付", datetime.date.today(), key="log_date")
        phase = st.selectbox("対象フェーズ", PHASES, key="log_phase")
        category = st.selectbox("練習カテゴリ", list(EXERCISES.keys()), key="log_cat")
        exercise = st.selectbox("種目", EXERCISES[category], key="log_ex")
        
        with st.form("log_form"):
            weight, reps, sets, record = None, None, None, None
            is_completed = False
            
            if category == "ウエイト":
                c1, c2, c3 = st.columns(3)
                with c1: weight = st.number_input("重量 (kg)", min_value=0.0, step=2.5)
                with c2: reps = st.number_input("回数", min_value=0, step=1)
                with c3: sets = st.number_input("セット数", min_value=0, step=1)
            else:
                record = st.number_input("記録 (m / sec)", min_value=0.0, step=0.01)
                
            if category == "ウエイト" or exercise == "ハードルジャンプ五連":
                st.info("💡 プロトコル・トラッキング")
                is_completed = st.checkbox("✅ 設定された目標（プロトコル・高さ）を完遂/クリアした", value=False)
                
            submitted = st.form_submit_button("Logs シートへ保存")
            if submitted:
                new_row = pd.DataFrame([{
                    "日付": date.strftime("%Y-%m-%d"), "フェーズ": phase,
                    "種目": exercise, "重量": weight, "回数": reps,
                    "セット数": sets, "記録": record, "完遂": is_completed
                }])
                updated = pd.concat([logs_df, new_row], ignore_index=True)
                # 💡 [パッチ] 送信直前に日付をStringへ再フォーマット＆NaNを空白化
                updated['日付'] = pd.to_datetime(updated['日付'], errors='coerce').dt.strftime('%Y-%m-%d')
                updated = updated.fillna("")
                
                conn.update(spreadsheet=spreadsheet_url, worksheet="Logs", data=updated)
                st.cache_data.clear()
                st.success("日常トレーニングを記録しました！")
                st.rerun()

    # -----------------------------------------
    # ② フェーズ別目標設定
    # -----------------------------------------
    elif input_mode == "② フェーズ別目標設定":
        st.subheader("🎯 目標値の動的設定・更新")
        t_date = st.date_input("設定日", datetime.date.today(), key="target_date")
        t_phase = st.selectbox("対象フェーズ", PHASES, key="target_phase")
        flat_ex = [ex for cat_list in EXERCISES.values() for ex in cat_list]
        t_exercise = st.selectbox("対象種目", flat_ex, key="target_ex")
        
        with st.form("target_form"):
            t_w, t_r, t_s, t_rec = None, None, None, None
            if t_exercise in EXERCISES["ウエイト"]:
                c1, c2, c3 = st.columns(3)
                with c1: t_w = st.number_input("目標 重量 (kg)", min_value=0.0, step=2.5)
                with c2: t_r = st.number_input("目標 回数", min_value=0, step=1)
                with c3: t_s = st.number_input("目標 セット数", min_value=0, step=1)
            else:
                t_rec = st.number_input("目標 記録 (m / sec)", min_value=0.0, step=0.01)
                
            submitted = st.form_submit_button("Targets シートへ保存")
            if submitted:
                new_row = pd.DataFrame([{
                    "設定日": t_date.strftime("%Y-%m-%d"), "フェーズ": t_phase,
                    "種目": t_exercise, "目標重量": t_w, "目標回数": t_r,
                    "目標セット数": t_s, "目標記録": t_rec
                }])
                updated = pd.concat([targets_df, new_row], ignore_index=True)
                # 💡 [パッチ]
                updated['設定日'] = pd.to_datetime(updated['設定日'], errors='coerce').dt.strftime('%Y-%m-%d')
                updated = updated.fillna("")
                
                conn.update(spreadsheet=spreadsheet_url, worksheet="Targets", data=updated)
                st.cache_data.clear()
                st.success("目標値を更新しました！")
                st.rerun()

    # -----------------------------------------
    # ③ 試合エントリー (Pre-Match)
    # -----------------------------------------
    elif input_mode == "③ 試合エントリー (Pre-Match)":
        st.subheader("🏟️ 試合前エントリー（一括登録）")
        m_date = st.date_input("試合日", datetime.date.today(), key="pre_date")
        m_name = st.text_input("大会名")
        
        m_ex_list = st.multiselect("出場種目を選択 (複数可)", ["砲丸", "円盤", "やり", "100m", "その他"], default=["砲丸"])
        
        if m_ex_list:
            with st.form("pre_match_form"):
                st.write("各エントリーの目標・意図設定")
                inputs = {}
                for ex in m_ex_list:
                    st.markdown(f"**■ {ex}**")
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        t = st.number_input(f"目標記録 ({ex})", min_value=0.0, step=0.01, key=f"tgt_{ex}")
                    with c2:
                        th = st.text_area(f"技術テーマ ({ex})", key=f"thm_{ex}")
                    inputs[ex] = {"target": t, "theme": th}
                    
                submitted = st.form_submit_button("選択した全種目を一括エントリー (Pre-Match)")
                
                if submitted:
                    new_rows = []
                    for ex in m_ex_list:
                        new_rows.append({
                            "試合日": m_date.strftime("%Y-%m-%d"), "大会名": m_name,
                            "出場種目": ex, "目標記録": inputs[ex]["target"], "技術テーマ": inputs[ex]["theme"],
                            "実績記録": None, "コンディション": None, "要因分析": None,
                            "ステータス": "予定"
                        })
                    
                    updated = pd.concat([matches_df, pd.DataFrame(new_rows)], ignore_index=True)
                    # 💡 [パッチ] 複数行追加時も確実に日付をString化し、GS側での日付消失を防止
                    updated['試合日'] = pd.to_datetime(updated['試合日'], errors='coerce').dt.strftime('%Y-%m-%d')
                    updated = updated.fillna("")
                    
                    conn.update(spreadsheet=spreadsheet_url, worksheet="Matches", data=updated)
                    st.cache_data.clear()
                    st.success(f"{len(m_ex_list)}種目の試合エントリーを一括登録しました！")
                    st.rerun()
        else:
            st.warning("出場種目を1つ以上選択してください。")

    # -----------------------------------------
    # ④ 試合結果アップデート (Post-Match)
    # -----------------------------------------
    elif input_mode == "④ 試合結果アップデート (Post-Match)":
        st.subheader("🏆 試合後アップデート（結果とPDCA）")
        
        if matches_df.empty or "ステータス" not in matches_df.columns:
            st.info("登録されている試合データがありません。")
        else:
            valid_matches = matches_df.dropna(subset=["試合日"])
            pending_matches = valid_matches[valid_matches["ステータス"] == "予定"]
            
            if pending_matches.empty:
                st.info("現在、結果待ち（予定）の有効な試合はありません。")
            else:
                match_options = {f"{row['試合日'].strftime('%Y-%m-%d')} - {row['大会名']} ({row['出場種目']})": idx for idx, row in pending_matches.iterrows()}
                selected_label = st.selectbox("結果を入力する試合・種目を選択", list(match_options.keys()))
                target_idx = match_options[selected_label]
                
                target_row = matches_df.loc[target_idx]
                st.write(f"📌 **種目**: {target_row.get('出場種目')} | **目標記録**: {target_row.get('目標記録', 'N/A')} | **技術テーマ**: {target_row.get('技術テーマ', 'N/A')}")
                
                with st.form("post_match_form"):
                    p_result = st.number_input("実績記録", min_value=0.0, step=0.01)
                    p_condi = st.text_input("コンディション (天候・気温・体調など自由記述)", placeholder="例: 晴れ, 18℃, 向かい風2m")
                    p_analysis = st.text_area("要因分析・感想")
                    
                    submitted = st.form_submit_button("試合結果を確定 (Post-Match)")
                    if submitted:
                        matches_df.loc[target_idx, "実績記録"] = p_result
                        matches_df.loc[target_idx, "コンディション"] = p_condi
                        matches_df.loc[target_idx, "要因分析"] = p_analysis
                        matches_df.loc[target_idx, "ステータス"] = "完了"
                        
                        updated = matches_df.copy()
                        # 💡 [パッチ]
                        updated['試合日'] = pd.to_datetime(updated['試合日'], errors='coerce').dt.strftime('%Y-%m-%d')
                        updated = updated.fillna("")
                        
                        conn.update(spreadsheet=spreadsheet_url, worksheet="Matches", data=updated)
                        st.cache_data.clear()
                        st.success("試合結果とPDCAを同期しました！")
                        st.rerun()

# ==========================================
# Tab 2: Winter Training Progress
# ==========================================
with tab2:
    st.header("📊 冬季練コア指標ダッシュボード")
    active_phase = st.radio("表示フェーズ選択", PHASES, horizontal=True, key="dash_phase")
    
    def render_progress(category_name, ex_list):
        for ex in ex_list:
            t_val = 0
            t_w, t_r, t_s = 0, 0, 0
            
            if not targets_df.empty:
                t_filtered = targets_df[(targets_df["フェーズ"] == active_phase) & (targets_df["種目"] == ex)]
                if not t_filtered.empty:
                    t_row = t_filtered.iloc[-1]
                    if category_name == "ウエイト":
                        t_w, t_r, t_s = t_row.get("目標重量", 0), t_row.get("目標回数", 0), t_row.get("目標セット数", 0)
                        t_val = t_w
                    else:
                        t_val = t_row.get("目標記録", 0)
            
            ex_logs = pd.DataFrame()
            if not logs_df.empty:
                if category_name == "ウエイト":
                    ex_logs = logs_df[(logs_df["フェーズ"] == active_phase) & (logs_df["種目"] == ex)].dropna(subset=["重量"]).sort_values("日付")
                else:
                    ex_logs = logs_df[(logs_df["フェーズ"] == active_phase) & (logs_df["種目"] == ex)].dropna(subset=["記録"]).sort_values("日付")
                    
            if ex_logs.empty or pd.isna(t_val) or t_val == 0:
                st.write(f"**{ex}**")
                if category_name == "ウエイト":
                    st.progress(0, text=f"データ未達 / 目標: {t_w}kg × {t_r}回 × {t_s}セット")
                else:
                    st.progress(0, text=f"データ未達 / 目標: {t_val}")
            else:
                if category_name == "ウエイト":
                    curr_w = ex_logs["重量"].iloc[-1]
                    curr_r = ex_logs["回数"].iloc[-1]
                    curr_s = ex_logs["セット数"].iloc[-1]
                    is_cleared = ex_logs["完遂"].iloc[-1] if "完遂" in ex_logs.columns else False
                    status_icon = "✅ 完遂" if is_cleared else "⚠️ 未完遂"
                    ratio = min(curr_w / t_val, 1.0)
                    st.write(f"**{ex}**")
                    st.progress(ratio, text=f"現在: {curr_w}kg × {curr_r}回 × {curr_s}セット ({status_icon}) / 目標: {t_val}kg × {t_r}回 × {t_s}セット")
                else:
                    curr_rec = ex_logs["記録"].max()
                    ratio = min(curr_rec / t_val, 1.0)
                    status_icon = ""
                    if ex == "ハードルジャンプ五連":
                        is_cleared = ex_logs["完遂"].iloc[-1] if "完遂" in ex_logs.columns else False
                        status_icon = " (✅ 完遂)" if is_cleared else " (⚠️ 未完遂)"
                        
                    st.write(f"**{ex}**")
                    st.progress(ratio, text=f"現在ベスト: {curr_rec}{status_icon} / 目標: {t_val} ({int(ratio*100)}%)")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("🏋️ ウエイト")
        render_progress("ウエイト", EXERCISES["ウエイト"])
        st.subheader("🏃‍♂️ コントロールテスト")
        render_progress("コントロールテスト", EXERCISES["コントロールテスト"])
    with col2:
        st.subheader("☄️ 投擲")
        render_progress("投げ", EXERCISES["投げ"])
        st.divider()
        st.subheader("📈 練習トレンドグラフ")
        all_ex = [e for cat_list in EXERCISES.values() for e in cat_list]
        g_ex = st.selectbox("グラフ表示種目", all_ex, key="graph_ex")
        
        if not logs_df.empty:
            g_df = logs_df.dropna(subset=["日付"])
            g_df = g_df[g_df["種目"] == g_ex].sort_values("日付")
            if not g_df.empty:
                if g_ex in EXERCISES["ウエイト"]:
                    st.line_chart(g_df.set_index("日付")["重量"])
                else:
                    st.line_chart(g_df.set_index("日付")["記録"])
            else:
                st.info("該当するデータがありません。")

# ==========================================
# Tab 3: Match & PB Analytics
# ==========================================
with tab3:
    st.header("🏟️ 関東インカレへの実戦・PB分析")
    st.subheader("👑 公式試合 自己ベスト (PB)")
    if not matches_df.empty and "ステータス" in matches_df.columns:
        done_matches = matches_df[matches_df["ステータス"] == "完了"].dropna(subset=["実績記録"])
        
        c1, c2, c3, c4 = st.columns(4)
        
        pb_sp = done_matches[done_matches["出場種目"] == "砲丸"]["実績記録"].max() if not done_matches.empty else 0
        pb_dt = done_matches[done_matches["出場種目"] == "円盤"]["実績記録"].max() if not done_matches.empty else 0
        pb_jt = done_matches[done_matches["出場種目"] == "やり"]["実績記録"].max() if not done_matches.empty else 0
        
        m100_recs = done_matches[done_matches["出場種目"] == "100m"]["実績記録"]
        m100_recs = m100_recs[m100_recs > 0]
        pb_100 = m100_recs.min() if not m100_recs.empty else 0
        
        c1.metric("砲丸投げ PB", f"{pb_sp if pd.notna(pb_sp) and pb_sp > 0 else 0:.2f}m")
        c2.metric("円盤投げ PB", f"{pb_dt if pd.notna(pb_dt) and pb_dt > 0 else 0:.2f}m")
        c3.metric("やり投げ PB", f"{pb_jt if pd.notna(pb_jt) and pb_jt > 0 else 0:.2f}m")
        c4.metric("100m PB", f"{pb_100 if pd.notna(pb_100) and pb_100 > 0 else 0:.2f}秒")
    else:
        st.info("完了した試合データがありません。")
        
    st.divider()
    st.subheader("📋 試合履歴 & PDCAログ (Pre / Post)")
    if not matches_df.empty:
        st.dataframe(matches_df.dropna(subset=["試合日"]), use_container_width=True)
    else:
        st.info("試合データが登録されていません。")