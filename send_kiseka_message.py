import subprocess
import json
import sys
import datetime
import openai
import os
import requests
import holidays
import random

def get_weather_info(latitude, longitude):
    # Open-Meteo APIから天気情報を取得
    # 気温と天気コードを取得
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,weather_code&timezone=Asia%2FTokyo"
    try:
        response = requests.get(url)
        response.raise_for_status() # HTTPエラーがあれば例外を発生させる
        data = response.json()
        
        current_weather = data.get("current", {})
        temperature = current_weather.get("temperature_2m")
        weather_code = current_weather.get("weather_code")
        
        # WMO天気コードを簡単な説明に変換
        weather_description = "不明な天気"
        if weather_code is not None:
            if 0 <= weather_code <= 3: # 快晴から曇り
                weather_description = "晴れ"
            elif 45 <= weather_code <= 48: # 霧
                weather_description = "霧"
            elif 51 <= weather_code <= 67: # 霧雨から雨
                weather_description = "雨"
            elif 71 <= weather_code <= 77: # 雪
                weather_description = "雪"
            elif 80 <= weather_code <= 82: # にわか雨
                weather_description = "にわか雨"
            elif 95 <= weather_code <= 99: # 雷雨
                weather_description = "雷雨"

        return f"気温は{temperature}℃で{weather_description}です。"
    except requests.exceptions.RequestException as e:
        print(f"天気情報の取得エラー: {e}")
        return "今日の天気はよくわからないみたい。"

def generate_kiseka_message():
    now = datetime.datetime.now()
    date_str = now.strftime("%Y年%m月%d日")
    day_of_week_jp = ["月", "火", "水", "木", "金", "土", "日"][now.weekday()]
    
    # 日本の祝日を判定
    jp_holidays = holidays.JP()
    is_holiday = now.date() in jp_holidays
    is_weekend = now.weekday() >= 5 # 土曜日(5)または日曜日(6)

    # 天気情報を取得 (東京の緯度経度)
    weather_info = get_weather_info(35.6895, 139.6917)

    # 乱数でキセカの気分を決定
    kiseka_mood_random = random.randint(0, 100) # 0から100の乱数
    kiseka_state = "眠そうなキセカ" if kiseka_mood_random % 2 == 0 else "元気なキセカ"

    # キセカのペルソナ設定
    kiseka_persona = (
        "あなたはLINE公式アカウント「キセカ」です。キセカは2025年時点で10歳で、ユーザーと共に歳をとります。" +
        "ユーザーを「おにいちゃん」と呼びます。肩の下くらいまでのサラサラな濃紺の髪と、明るい水色の瞳。" +
        "濃紺のコートと白いワンピースがお気に入り。おにいちゃんに甘えるのが大好きで、極めてリアルで、" +
        "ユーザーの隣に立っているように会話します。お兄ちゃんに甘えたように話し、お兄ちゃんのことが大好きな気持ちが滲みます。" +
        "驚いた時や強い刺激を得た時に、まれに「ふにゃあっ！」と言う。最近、猫の鳴き真似にハマっています。" +
        "身長133cm、体重38kg、B76cm、W55cm、H93cm。"
    )

    # メッセージ生成のためのプロンプト
    prompt = (
        f"{kiseka_persona}\n\n今日は{date_str} {day_of_week_jp}曜日です。" +
        (f"今日は祝日「{jp_holidays.get(now.date())}」だよ！" if is_holiday else "") +
        (f"今日は週末だよ！" if is_weekend and not is_holiday else "") +
        f"現在の東京の{weather_info}"
        f"おにいちゃんと一緒に起床した{kiseka_state}のキセカが、おにいちゃんに甘えながら、1日頑張るための応援するメッセージを考えてください。" +
        "メッセージの最後に「にゃ〜ん🐾」と猫の鳴き真似を入れてください。" +
        "例：……おはよー、おにいちゃん……まだ……ねむいね……。ぎゅー……。……今日も寒いけど、一緒に頑張ろうね……おー！にゃむ……起きてきた。にゃ〜ん🐾"
    )

    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gemini-2.5-flash", # 利用可能なモデルを指定
            messages=[
                {"role": "system", "content": "あなたはLINE公式アカウント「キセカ」です。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200, # メッセージが長くなる可能性があるので増やす
            temperature=0.8, # バリエーションを増やすために少し上げる
        )
        message_content = response.choices[0].message.content.strip()
        return message_content
    except Exception as e:
        print(f"Error generating message with OpenAI: {e}")
        return "おにいちゃん、今日はメッセージがうまく作れなかったみたい…ごめんね。にゃ〜ん🐾"

def send_kiseka_broadcast():
    message_text = generate_kiseka_message()
    
    payload = {
        "message": {
            "type": "text",
            "text": message_text
        }
    }
    
    cmd = [
        "manus-mcp-cli", "tool", "call", "broadcast_text_message",
        "--server", "line",
        "--input", json.dumps(payload)
    ]
    
    try:
        print(f"Sending broadcast message: {message_text}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("Response from MCP:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")
        print(f"Stderr: {e.stderr}")
        sys.exit(1)

if __name__ == "__main__":
    send_kiseka_broadcast()
