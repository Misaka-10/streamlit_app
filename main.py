# %%
import streamlit as st
from openai import OpenAI
import os
import requests
import sqlite3
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv

# ==== APIキー設定 ====

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")


# %%

    # ==== SQLiteデータベース接続 ====
conn = sqlite3.connect("health_data.db", check_same_thread=False)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS health_log (
        date TEXT,
        steps INTEGER,
        active_minutes INTEGER,
        distance REAL,
        score INTEGER
    )
''')
conn.commit()

st.markdown(
    """
    <style>
    /* Google Fonts：Kosugi Maru を読み込み */
    @import url('https://fonts.googleapis.com/css2?family=Kosugi+Maru&display=swap');

    /* 全体背景＆文字スタイル */
    .stApp {
        background-color: #fdf6e3;  /* ライトベージュ */
        font-family: 'Kosugi Maru', 'Yu Gothic UI', 'Hiragino Kaku Gothic ProN', sans-serif;
        color: #4b4b4b;
    }

    /* サイドバーをやわらかいウォームベージュに */
    section[data-testid="stSidebar"] {
        background-color: #f5e8da !important;
    }

    /* タイトル・見出しをナチュラルに */
    h1, h2, h3 {
        font-family: 'Kosugi Maru', 'Yu Gothic UI', sans-serif;
        color: #5a4e3c;
        letter-spacing: 0.5px;
        margin-bottom: 0.8rem;
    }

    /* ボタン：キャラメルピンク系 + 丸み + 影 */
    button[kind="primary"] {
        background-color: #eecfcf !important;
        color: #4b4b4b !important;
        border-radius: 12px !important;
        padding: 12px 28px !important;
        font-size: 16px !important;
        border: none !important;
        font-family: 'Kosugi Maru', 'Yu Gothic UI', sans-serif;
        box-shadow: 2px 2px 6px rgba(200, 150, 150, 0.2);
        transition: all 0.3s ease;
    }

    button[kind="primary"]:hover {
        background-color: #e6bcbc !important;
        color: black !important;
    }

    /* メトリック（スコア）表示をカード風に */
    .element-container .stMetric {
        background-color: #fffaf3;
        border-radius: 12px;
        padding: 14px;
        box-shadow: 0 0 8px rgba(0, 0, 0, 0.05);
    }

    /* 全体の余白設定 */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)




# ==== Streamlitタイトル ====
#空白
st.markdown("<br>", unsafe_allow_html=True)
st.title("🌸 StepUp! スコア 🏃")
st.markdown("あたたかい春の空の下、身体を動かしましょう！")
st.divider()

#空白
st.markdown("<br>", unsafe_allow_html=True)


# ==== Step 1：運動データ入力 ====
st.subheader("📥 今日はどれくらい歩きましたか？")

steps = st.number_input("📍 歩数", min_value=0, value=5000, step=100)
active_minutes = st.number_input("⏱ アクティブ時間（分）", min_value=0, value=30, step=30)
distance = st.number_input("🛣 移動距離（km）", min_value=0.0, value=3.0, step=1.0)




# ==== 健康スコア計算関数 ====
def calc_score(steps, active_minutes, distance):
    score = 0
    score += 40 if steps >= 10000 else 30 if steps >= 7000 else 20 if steps >= 4000 else 10
    score += 30 if active_minutes >= 60 else 20 if active_minutes >= 30 else 10 if active_minutes >= 15 else 5
    score += 30 if distance >= 8 else 20 if distance >= 5 else 10 if distance >= 2 else 5
    return score

score = calc_score(steps, active_minutes, distance)
st.metric("📊 健康スコア", f"{score}/100")

#空白
st.markdown("<br>", unsafe_allow_html=True)

# ==== スコアの保存ボタン ====


if st.button("💾 今日のデータを保存"):
    today = datetime.now().strftime("%Y-%m-%d")
    # 既存のレコードがあるか確認
    c.execute("SELECT * FROM health_log WHERE date = ?", (today,))
    existing = c.fetchone()

    if existing:
        # 上書き保存（UPDATE）
        c.execute("""
            UPDATE health_log 
            SET steps = ?, active_minutes = ?, distance = ?, score = ?
            WHERE date = ?
        """, (steps, active_minutes, distance, score, today))
        st.success("✅ 既存のデータを上書きしました！")
    else:
        # 新規保存（INSERT）
        c.execute("INSERT INTO health_log VALUES (?, ?, ?, ?, ?)", (today, steps, active_minutes, distance, score))
        st.success("✅ 新しいデータを保存しました！")

        
st.divider()

# ==== Step 2：ChatGPTでアドバイス ====
st.subheader("💬 AI 健康管理士 からのアドバイス")


# %%

client = OpenAI()

def get_health_advice(score, steps, active_minutes, distance):
    prompt = f"""
    ユーザーの今日の運動データは以下の通りです：
    - 歩数: {steps}
    - アクティブ時間: {active_minutes}分
    - 移動距離: {distance}km
    健康スコアは {score}/100 です。
    この情報をもとに、日本語で300文字以内で完結する文章で、健康アドバイスをお願いします。
    今日頑張ったことへの褒め言葉を含めてください。 
    """
    res = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "あなたはユーザーに健康アドバイスをする専門家です。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=400,        
    )
    return res.choices[0].message.content.strip()


# %%

if st.button("💡 アドバイスを見る"):
    with st.spinner("アドバイス生成中..."):
        advice = get_health_advice(score, steps, active_minutes, distance)
        st.success("今日のアドバイス")
        st.write(advice)
    
st.divider()

# ==== Step 3：天気APIで運動提案 ====
#空白
st.markdown("<br>", unsafe_allow_html=True)
st.header("☀️ 明日のチャレンジ！")

city = st.text_input("🌍 都市名を入力してください（例：Tokyo）", value="Tokyo")



# %%
def get_weather_and_suggestion(city):
    WEATHER_API_KEY = os.environ["WEATHER_API_KEY"]
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ja"
    res = requests.get(url).json()
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    forecast = [item for item in res["list"] if tomorrow in item["dt_txt"]]
    if not forecast:
        return "天気情報を取得できませんでした。"
    weather = forecast[0]["weather"][0]["description"]
    if "晴" in weather or "雲" in weather:
        suggestion = "外でランニングしましょう！"
    elif "雨" in weather:
        suggestion = "室内でヨガやストレッチをしましょう。"
    else:
        suggestion = "室内で有酸素運動をしましょう。"    
    
    return f"明日の天気は「{weather}」です。\n{suggestion}"



if st.button("🔍 天気に応じたエクササイズは？"):
    with st.spinner("天気情報を取得中..."):
        suggestion_text = get_weather_and_suggestion(city)
        st.info(suggestion_text)

        # 天気の種類を抽出（文字列から天気だけを取得）
        weather_keyword = None
        for keyword in ["晴", "雨","雲"]:
            if keyword in suggestion_text:
                weather_keyword = keyword
                break

        # 天気に応じたYouTube動画の出し分け
        if weather_keyword in ["晴", "雲"]: 
            video_url = "https://www.youtube.com/watch?v=uh82wP51EdM?feature=share"
            video_title = "☀️ ランニングに挑戦してみましょう！"
        elif weather_keyword == "雨":
            video_url = "https://www.youtube.com/watch?v=D0LS8rVto0o"
            video_title = "☔ 雨の日に最適なリラックスヨガ"        
        else:
            video_url = "https://www.youtube.com/watch?v=lCMN-y0BDM4"
            video_title = "🏠 室内でできる有酸素運動"

        # 動画表示
        st.markdown(f"### {video_title}")
        st.video(video_url)

      
# ==== Step 5：履歴チャート ====
st.sidebar.header("💾 過去のデータ")
st.sidebar.markdown("<br><br>", unsafe_allow_html=True)

df = pd.read_sql("SELECT * FROM health_log", conn)

if not df.empty:
    df["date"] = pd.to_datetime(df["date"])    
    chart = alt.Chart(df).mark_line(        
        color='green',       # 線の色
        strokeWidth=3        # 線の太さ        
    ).encode(
        #Altairでカテゴリ（Nominal）として描画
        #Altair の X軸ラベル（今回の「4/19」など）を水平方向（横書き）にする
        x=alt.X('date:T', axis=alt.Axis(format='%m-%d',title='日付', labelAngle=-45)),
        y=alt.Y('score:Q',axis=alt.Axis(title='スコア', labelAngle=0)),
        tooltip=['日付:T', 'スコア:Q']
    ).properties(width=800)
    


    st.sidebar.altair_chart(chart, use_container_width=True)
else:
    st.info("まだ記録がありません。運動データを保存してみましょう！")