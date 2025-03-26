import mysql.connector
from datetime import datetime, timedelta
import requests
import json
from PySide6.QtCore import QDateTime
import subprocess

DISCORD_BOT_TOKEN = ''
GUILD_ID = '1247225498887782441'
VERIFY_ROLE_ID = '1352392665156817006'


def get_hwid():
    try:
        result = subprocess.check_output('wmic csproduct get uuid').decode().split('\n')[1].strip()
        return result
    except Exception as e:
        print(f"Failed to get HWID: {str(e)}")
        return None
    

def get_mysql_connection():
    return mysql.connector.connect(
        host="185.233.164.124",
        user="admin",  # MySQL kullanıcı adı
        password="xLfjf5216n8cx",  # MySQL kullanıcı şifresi
        database="myapp_db"  # MySQL veritabanı adı
    )

def validate_license_key(license_key, discord_user_id):
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM licenses WHERE token=%s AND discord_user_id=%s", (license_key, discord_user_id))
    license = cursor.fetchone()
    cursor.close()

    if not license:
        return False, "Geçersiz lisans anahtarı veya Discord User ID."

    expiration_date = license['expiration_date']
    hwid = license.get('hwid')
    current_hwid = get_hwid()

    if datetime.now().date() > expiration_date:
        return False, "Lisans süresi dolmuş."

    if hwid:
        if hwid != current_hwid:
            return False, "Lisans anahtarı bu bilgisayar için geçerli değil."
    else:
        cursor = conn.cursor()
        cursor.execute("UPDATE licenses SET hwid=%s WHERE token=%s AND discord_user_id=%s", (current_hwid, license_key, discord_user_id))
        conn.commit()
        cursor.close()

    conn.close()
    return True, "Lisans doğrulandı. Uygulamayı kullanabilirsiniz."

def check_user_role(discord_user_id):
    headers = {
        'Authorization': f'Bot {DISCORD_BOT_TOKEN}'
    }
    response = requests.get(f'https://discord.com/api/v9/guilds/{GUILD_ID}/members/{discord_user_id}', headers=headers)
    if response.status_code == 200:
        member = response.json()
        roles = member.get('roles', [])
        return VERIFY_ROLE_ID in roles
    else:
        return False
    

def get_user_info(discord_user_id):
    headers = {
        'Authorization': f'Bot {DISCORD_BOT_TOKEN}'
    }
    response = requests.get(f'https://discord.com/api/v9/users/{discord_user_id}', headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch user info. Status code: {response.status_code}")
        return None    
    
def get_license_expiry(discord_user_id):
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT expiration_date FROM licenses WHERE discord_user_id=%s", (discord_user_id,))
    result = cursor.fetchall()  # Fetch all rows to clear the unread results
    cursor.close()
    conn.close()

    if result:
        expiration_date = result[0]['expiration_date']
        return QDateTime.fromString(expiration_date.strftime('%Y-%m-%d %H:%M:%S'), 'yyyy-MM-dd HH:mm:ss')
    else:
        return None
    

def get_user_discord_id(token):
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT discord_user_id FROM licenses WHERE token=%s", (token,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
        return user['discord_user_id']
    else:
        return None


def save_login_data(token, discord_user_id):
    data = {
        "token": token,
        "discord_user_id": discord_user_id
    }
    with open("login_data.json", "w") as file:
        json.dump(data, file)

def load_login_data():
    try:
        with open("login_data.json", "r") as file:
            data = json.load(file)
            return data["token"], data["discord_user_id"]
    except (FileNotFoundError, KeyError):
        return None, None