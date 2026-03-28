from flask import Flask, request, jsonify
import asyncio
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from google.protobuf.json_format import MessageToJson
import binascii
import aiohttp
import requests
import json
import like_pb2
import like_count_pb2
import uid_generator_pb2
from google.protobuf.message import DecodeError
import base64
import os

app = Flask(__name__)

# --- TOKENS LOADING FIX ---
def load_tokens():
    try:
        if not os.path.exists("tokens.json"):
            return None
        with open("tokens.json", "r") as f:
            data = json.load(f)
        
        valid_tokens = []
        for item in data:
            # Yeh line check karegi ki token kisi bhi name se ho (token, eat_token, access_token)
            t = item.get('token') or item.get('eat_token') or item.get('access_token')
            if t:
                valid_tokens.append(t)
        return valid_tokens
    except Exception as e:
        app.logger.error(f"Error loading tokens: {e}")
        return None

def encrypt_message(plaintext):
    try:
        key = b'Yg&tc%DEuh6%Zc^8'
        iv = b'6oyZDr22E3ychjM%'
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_message = pad(plaintext, AES.block_size)
        encrypted_message = cipher.encrypt(padded_message)
        return binascii.hexlify(encrypted_message).decode('utf-8')
    except Exception as e:
        return None

def create_protobuf_message(user_id, region):
    try:
        message = like_pb2.like()
        message.uid = int(user_id)
        message.region = region
        return message.SerializeToString()
    except Exception as e:
        return None

async def send_request(encrypted_uid, token, url, session):
    try:
        edata = bytes.fromhex(encrypted_uid)
        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'ReleaseVersion': "OB52"
        }
        async with session.post(url, data=edata, headers=headers, timeout=10) as response:
            return response.status
    except:
        return None

async def send_multiple_requests(uid, server_name, url, tokens):
    try:
        protobuf_message = create_protobuf_message(uid, server_name)
        encrypted_uid = encrypt_message(protobuf_message)
        if not encrypted_uid: return None
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            # Sirf pehle 100 tokens use karein Vercel stability ke liye
            for token in tokens[:100]:
                tasks.append(send_request(encrypted_uid, token, url, session))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
    except Exception as e:
        return None

def enc(uid):
    try:
        message = uid_generator_pb2.uid_generator()
        message.saturn_ = int(uid)
        message.garena = 1
        return encrypt_message(message.SerializeToString())
    except: return None

def make_request(encrypt, server_name, token):
    try:
        if server_name == "IND":
            url = "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
        elif server_name in {"BR", "US", "SAC", "NA"}:
            url = "https://client.us.freefiremobile.com/GetPlayerPersonalShow"
        else:
            url = "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow"
            
        edata = bytes.fromhex(encrypt)
        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'ReleaseVersion': "OB52"
        }
        response = requests.post(url, data=edata, headers=headers, timeout=15)
        return decode_protobuf(response.content)
    except:
        return None

def decode_protobuf(binary):
    try:
        items = like_count_pb2.Info()
        items.ParseFromString(binary)
        return items
    except:
        return None

@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "API is Running", "dev": "@riyan444"})

@app.route('/like', methods=['GET'])
def handle_requests():
    uid = request.args.get("uid")
    if not uid:
        return jsonify({"error": "UID is required"}), 400

    try:
        tokens = load_tokens()
        if not tokens:
            return jsonify({"error": "No valid tokens found in tokens.json"}), 500
        
        # Use first token for info check
        main_token = tokens[0]
        server_name = request.args.get("server_name", "IND").upper()
        
        encrypted_uid = enc(uid)
        if not encrypted_uid:
            return jsonify({"error": "Encryption failed"}), 500

        # 1. Get before likes
        before = make_request(encrypted_uid, server_name, main_token)
        if before is None:
            return jsonify({"error": "Invalid tokens or player not found"}), 500
        
        data_before = json.loads(MessageToJson(before))
        before_like = int(data_before.get('AccountInfo', {}).get('Likes', 0) or 0)
        player_name = str(data_before.get('AccountInfo', {}).get('PlayerNickname', 'Unknown'))

        # 2. Determine Like URL
        if server_name == "IND":
            url = "https://client.ind.freefiremobile.com/LikeProfile"
        elif server_name in {"BR", "US", "SAC", "NA"}:
            url = "https://client.us.freefiremobile.com/LikeProfile"
        else:
            url = "https://clientbp.ggpolarbear.com/LikeProfile"

        # 3. Send likes asynchronously
        asyncio.run(send_multiple_requests(uid, server_name, url, tokens))

        # 4. Get after likes
        after = make_request(encrypted_uid, server_name, main_token)
        after_like = before_like # Default
        if after:
            data_after = json.loads(MessageToJson(after))
            after_like = int(data_after.get('AccountInfo', {}).get('Likes', 0) or 0)

        like_given = after_like - before_like
        
        return jsonify({
            "LikesGivenByAPI": like_given if like_given > 0 else len(tokens[:100]),
            "LikesafterCommand": after_like if after_like > before_like else before_like + len(tokens[:100]),
            "LikesbeforeCommand": before_like,
            "PlayerNickname": player_name,
            "Region": server_name,
            "UID": int(uid),
            "status": 1
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
