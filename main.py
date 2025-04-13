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


# %%

# ==== Streamlitタイトル ====
st.title("🏃 健康スコアアプリ")
st.write("あなたの運動データを入力して、健康スコアを計算し、アドバイスを受けましょう！")


# %%

# ==== Step 1：運動データ入力 ====
st.header("📥 今日の運動データを入力")

steps = st.number_input("📍 歩数", min_value=0, value=5000, step=100)
active_minutes = st.number_input("⏱ アクティブ時間（分）", min_value=0, value=30, step=5)
distance = st.number_input("🛣 移動距離（km）", min_value=0.0, value=3.0, step=0.1)


# %%

# ==== 健康スコア計算関数 ====
def calc_score(steps, active_minutes, distance):
    score = 0
    score += 40 if steps >= 10000 else 30 if steps >= 7000 else 20 if steps >= 4000 else 10
    score += 30 if active_minutes >= 60 else 20 if active_minutes >= 30 else 10 if active_minutes >= 15 else 5
    score += 30 if distance >= 8 else 20 if distance >= 5 else 10 if distance >= 2 else 5
    return score

score = calc_score(steps, active_minutes, distance)


# %%
st.metric("📊 健康スコア", f"{score}/100")

# ==== Step 2：ChatGPTでアドバイス ====
st.subheader("💬 ChatGPT からのアドバイス")


# %%

client = OpenAI()

def get_health_advice(score, steps, active_minutes, distance):
    prompt = f"""
    ユーザーの今日の運動データは以下の通りです：
    - 歩数: {steps}
    - アクティブ時間: {active_minutes}分
    - 移動距離: {distance}km
    健康スコアは {score}/100 です。
    この情報をもとに、日本語で200文字以内の健康アドバイスをお願いします。
    """
    res = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "あなたはユーザーに健康アドバイスをする専門家です。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=150
    )
    return res.choices[0].message.content.strip()


# %%

if st.button("💡 ChatGPTアドバイスを見る"):
    with st.spinner("アドバイス生成中..."):
        advice = get_health_advice(score, steps, active_minutes, distance)
        st.success("今日のアドバイス")
        st.write(advice)

# ==== Step 3：天気APIで運動提案 ====
st.header("☀️ 明日は何にチャレンジしますか？")

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
    suggestion = "外でウォーキングしましょう！" if "晴" in weather or "曇" in weather else "室内でストレッチやヨガをしましょう。"
    return f"明日の天気は「{weather}」です。\n{suggestion}"


# %%

if st.button("🔍 天気に応じた提案を見る"):
    with st.spinner("天気情報を取得中..."):
        suggestion = get_weather_and_suggestion(city)
        st.info(suggestion)
        
if st.button("💾 今日のデータを保存"):
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("INSERT INTO health_log VALUES (?, ?, ?, ?, ?)", (today, steps, active_minutes, distance, score))
    conn.commit()
    st.success("✅ データを保存しました！")

# ==== Step 5：履歴チャート ====
st.header("📈 健康スコアの記録をグラフで確認")

df = pd.read_sql("SELECT * FROM health_log", conn)

if not df.empty:
    df["date"] = pd.to_datetime(df["date"])
    chart = alt.Chart(df).mark_line(point=True).encode(
        x='date:T',
        y='score:Q',
        tooltip=['date:T', 'score:Q']
    ).properties(title="📊 健康スコアの推移", width=600)

    st.altair_chart(chart, use_container_width=True)
else:
    st.info("まだ記録がありません。運動データを保存してみましょう！")