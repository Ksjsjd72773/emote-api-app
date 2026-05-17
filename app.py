import requests , os , psutil , sys , jwt , pickle , json , binascii , time , urllib3 , base64 , datetime , re , socket , threading , ssl , pytz , aiohttp
from protobuf_decoder.protobuf_decoder import Parser
from xC4 import * ; from xHeaders import *
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from concurrent.futures import ThreadPoolExecutor
from threading import Thread
import DEcwHisPErMsG_pb2 , MajoRLoGinrEs_pb2 , PorTs_pb2 , MajoRLoGinrEq_pb2 , sQ_pb2 , Team_msg_pb2
from cfonts import render, say
from flask import Flask, request, jsonify
import asyncio


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  

# =============================================================================
# إعدادات الحسابات المتعددة
# =============================================================================
MAX_ACCOUNTS = 100  # الحد الأقصى: 100 حساب
ACCOUNTS_FILE = "accounts.txt"  # ملف الحسابات: uid:password (سطر واحد لكل حساب)

# تخزين جلسات كل حساب متصل
# {uid: {"online_writer": writer, "whisper_writer": writer, "key": key, "iv": iv, "region": region, "auth_token": token, "name": name, "ready": bool, "busy": bool}}
bot_sessions = {}
sessions_lock = threading.Lock()
account_busy = {}  # {uid: bool} - يمنع تنفيذ أمرين على نفس الحساب
busy_lock = threading.Lock()

# أوامر معلقة للتنفيذ
pending_commands = []

# ========== نظام الدور (Round-Robin) ==========
# كل أمر يروح لحساب واحد بس، والامر الجاي للحساب اللي بعده
account_order = []       # قائمة مرتبة بـ UID الحسابات المتصلة
current_account_idx = 0 # مؤشر الدور الحالي
rotation_lock = threading.Lock()

app = Flask(__name__)

# =============================================================================
# تحميل الحسابات من الملف
# =============================================================================
def load_accounts():
    """تحميل الحسابات من ملف accounts.txt"""
    if not os.path.exists(ACCOUNTS_FILE):
        print(f"[ERROR] File '{ACCOUNTS_FILE}' not found!")
        print(f"[INFO] Create '{ACCOUNTS_FILE}' with format: uid:password (one per line)")
        return []
    
    accounts = []
    with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue  # تجاهل الأسطر الفارغة والتعليقات
            
            # استبدال الفاصلة العربية بالإنجليزية
            line = line.replace('\u060c', ':').replace('\uff1a', ':').replace(';', ':')
            
            if ':' not in line:
                print(f"[WARN] Line {line_num}: Invalid format (expected uid:password) - Skipping")
                continue
            
            parts = line.split(':', 1)
            uid = parts[0].strip()
            password = parts[1].strip()
            
            if not uid or not password:
                print(f"[WARN] Line {line_num}: Empty uid or password - Skipping")
                continue
            
            if len(accounts) >= MAX_ACCOUNTS:
                print(f"[WARN] Reached max accounts limit ({MAX_ACCOUNTS}) - Stopping")
                break
            
            accounts.append((uid, password))
    
    print(f"[INFO] Loaded {len(accounts)} accounts from '{ACCOUNTS_FILE}'")
    return accounts
Hr = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip",
    "Authorization": "Bearer {token}",
    "Content-Type": "application/x-www-form-urlencoded",
    "Expect": "100-continue",
    "X-Unity-Version": "2018.4.11f1",
    "X-GA": "v1 1",
    "ReleaseVersion": "OB53" 
}


# =============================================================================
# Flask API Routes
# =============================================================================
@app.route('/join', methods=['GET'])
def join_and_emote():
    try:
        uid1 = request.args.get('uid1', '')
        uid2 = request.args.get('uid2', '')
        uid3 = request.args.get('uid3', '')
        uid4 = request.args.get('uid4', '')
        emote_id = request.args.get('emote_id', '')
        team_code = request.args.get('tc', '')
        
        if not emote_id:
            return jsonify({"status": "error", "message": "emote_id is required"})
        
        command = {
            'type': 'dance_all',
            'uids': [uid for uid in [uid1, uid2, uid3, uid4] if uid],
            'emote_id': emote_id,
            'team_code': team_code,
            'timestamp': time.time()
        }
        
        pending_commands.append(command)
        
        return jsonify({
            "status": "success", 
            "message": f"Dance command queued - next account in rotation will handle it",
            "active_accounts": len(bot_sessions),
            "data": command
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/join_squad', methods=['GET'])
def join_squad_only():
    try:
        team_code = request.args.get('tc', '')
        if not team_code:
            return jsonify({"status": "error", "message": "Team code is required"})
        
        command = {
            'type': 'join_only',
            'team_code': team_code,
            'timestamp': time.time()
        }
        
        pending_commands.append(command)
        return jsonify({"status": "success", "message": f"Join squad command queued - next account in rotation will handle it"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/send_emote', methods=['GET'])
def send_emote_only():
    try:
        uid1 = request.args.get('uid1', '')
        uid2 = request.args.get('uid2', '')
        uid3 = request.args.get('uid3', '')
        uid4 = request.args.get('uid4', '')
        emote_id = request.args.get('emote_id', '')
        
        if not emote_id:
            return jsonify({"status": "error", "message": "emote_id is required"})
        
        command = {
            'type': 'emote_only',
            'uids': [uid for uid in [uid1, uid2, uid3, uid4] if uid],
            'emote_id': emote_id,
            'timestamp': time.time()
        }
        
        pending_commands.append(command)
        return jsonify({"status": "success", "message": f"Emote command queued - next account in rotation will handle it"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/dance_all', methods=['GET'])
def dance_all_uids():
    try:
        uid1 = request.args.get('uid1', '')
        uid2 = request.args.get('uid2', '')
        uid3 = request.args.get('uid3', '')
        uid4 = request.args.get('uid4', '')
        emote_id = request.args.get('emote_id', '')
        team_code = request.args.get('tc', '')
        
        if not emote_id:
            return jsonify({"status": "error", "message": "emote_id is required"})
        
        command = {
            'type': 'dance_all',
            'uids': [uid for uid in [uid1, uid2, uid3, uid4] if uid],
            'emote_id': emote_id,
            'team_code': team_code,
            'timestamp': time.time()
        }
        
        pending_commands.append(command)
        return jsonify({
            "status": "success", 
            "message": f"Dance all command queued - next account in rotation will handle it",
            "active_accounts": len(bot_sessions),
            "uids": [uid for uid in [uid1, uid2, uid3, uid4] if uid],
            "emote_id": emote_id,
            "team_code": team_code
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/status', methods=['GET'])
def status():
    accounts_info = []
    with sessions_lock:
        for uid, session in bot_sessions.items():
            accounts_info.append({
                "uid": uid,
                "name": session.get("name", "Unknown"),
                "region": session.get("region", "Unknown"),
                "online": bool(session.get("online_writer")),
                "chat": bool(session.get("whisper_writer"))
            })
    
    # معلومات الدور
    with rotation_lock:
        total_ready = len([u for u, s in bot_sessions.items() if s.get("online_writer")])
        next_idx = current_account_idx % max(total_ready, 1)
        next_uid = account_order[next_idx] if account_order else None
        next_name = bot_sessions[next_uid]["name"] if next_uid and next_uid in bot_sessions else "N/A"
    
    return jsonify({
        "status": "running", 
        "mode": "round-robin",
        "max_accounts": MAX_ACCOUNTS,
        "active_accounts": len(bot_sessions),
        "ready_accounts": total_ready,
        "next_account": {"uid": next_uid, "name": next_name} if next_uid else None,
        "accounts": accounts_info,
        "pending_commands": len(pending_commands)
    })

@app.route('/accounts', methods=['GET'])
def list_accounts():
    """عرض قائمة الحسابات المسجلة"""
    accounts = load_accounts()
    return jsonify({
        "total_registered": len(accounts),
        "max_allowed": MAX_ACCOUNTS,
        "active_online": len(bot_sessions),
        "accounts": [{"uid": uid, "password": pw[:10] + "..."} for uid, pw in accounts]
    })

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "Multi-Account Emote Bot API",
        "active_accounts": len(bot_sessions),
        "max_accounts": MAX_ACCOUNTS,
        "endpoints": {
            "/join": "Auto join + dance (one account per request, rotates)",
            "/dance_all": "Dance to UIDs (one account per request, rotates)",
            "/send_emote": "Send emote only (one account per request, rotates)",
            "/join_squad": "Join squad only (one account per request, rotates)",
            "/status": "Check bot status, active accounts & rotation info",
            "/accounts": "List registered accounts"
        }
    })

def run_flask():
    app.run(host='0.0.0.0', port=9128, debug=False, use_reloader=False)


api_thread = threading.Thread(target=run_flask)
api_thread.daemon = True
api_thread.start()


# =============================================================================
# معالج الأوامر - يبث الأمر لكل الحسابات المتصلة
# =============================================================================
async def get_next_account():
    """إرجاع الحساب التالي في الدور (Round-Robin) - جاهز + مش مشغول"""
    global current_account_idx, account_order
    
    with sessions_lock:
        # فقط الحسابات اللي جاهزين (online + chat متصلين) و مش مشغولين
        account_order = [
            uid for uid, session in bot_sessions.items()
            if session.get("ready") and session.get("online_writer") and session.get("key") and session.get("iv")
        ]
    
    with busy_lock:
        # استبعاد الحسابات المشغولة حالياً
        available = [uid for uid in account_order if not account_busy.get(uid, False)]
    
    if not available:
        return None, None
    
    with rotation_lock:
        if current_account_idx >= len(available):
            current_account_idx = 0
        
        selected_uid = available[current_account_idx]
        
        current_account_idx += 1
        if current_account_idx >= len(available):
            current_account_idx = 0
    
    with sessions_lock:
        session = bot_sessions.get(selected_uid)
    
    return selected_uid, session


async def command_checker():
    """فحص الأوامر المعلقة كل 0.5 ثانية - حساب واحد بس بالدور"""
    global pending_commands
    print("[Command Checker] Started - Round-Robin mode (one account per command)")
    
    while True:
        try:
            if pending_commands:
                # نسخ الأوامر وتفريغ القائمة
                current_commands = pending_commands.copy()
                pending_commands.clear()
                
                for command in current_commands:
                    try:
                        # أخذ الحساب التالي في الدور (جاهز + مش مشغول)
                        uid, session = await get_next_account()
                        
                        if not uid or not session:
                            # الأمر ما نفذ، ارجعه للقائمة
                            pending_commands.insert(0, command)
                            print("[Command Checker] No ready accounts - Command re-queued")
                            break
                        
                        online_w = session.get("online_writer")
                        key = session.get("key")
                        iv = session.get("iv")
                        region = session.get("region")
                        acc_name = session.get("name", "?")
                        
                        if not online_w or not key or not iv:
                            pending_commands.insert(0, command)
                            print(f"[SKIP] Account {uid} - Not ready, re-queuing")
                            break
                        
                        # وضع علامة مشغول على هذا الحساب
                        with busy_lock:
                            account_busy[uid] = True
                        
                        print(f"[API] Command: {command['type']} => Account [{uid}] ({acc_name})")
                        
                        try:
                            if command['type'] == 'join_only':
                                print(f"  [{uid}] Joining squad: {command['team_code']}")
                                join_packet = await GenJoinSquadsPacket(command['team_code'], key, iv)
                                online_w.write(join_packet)
                                await online_w.drain()
                                
                            elif command['type'] == 'emote_only':
                                for target_uid in command['uids']:
                                    if target_uid and target_uid.isdigit():
                                        print(f"  [{uid}] Sending emote {command['emote_id']} to UID: {target_uid}")
                                        emote_packet = await Emote_k(int(target_uid), int(command['emote_id']), key, iv, region)
                                        online_w.write(emote_packet)
                                        await online_w.drain()
                                        await asyncio.sleep(0.3)
                                        
                            elif command['type'] == 'dance_all':
                                await process_dance_for_account(uid, session, command)
                        
                        except ConnectionResetError:
                            print(f"  [ERROR] Account {uid} connection lost during command")
                        except Exception as e:
                            print(f"  [ERROR] Account {uid} command error: {e}")
                        finally:
                            # إزالة علامة مشغول
                            with busy_lock:
                                account_busy[uid] = False
                        
                        print(f"[API] Done => Account [{uid}] ({acc_name}) | Next command goes to next account")
                        
                    except Exception as e:
                        print(f"[API] Error processing command: {e}")
            
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"[Command Checker] Error: {e}")
            await asyncio.sleep(1)


async def process_dance_for_account(uid, session, command):
    """تنفيذ أوامر الترقيص لحساب واحد فقط"""
    try:
        online_w = session.get("online_writer")
        key = session.get("key")
        iv = session.get("iv")
        region = session.get("region")
        uids = command['uids']
        emote_id = command['emote_id']
        team_code = command.get('team_code', '')
        
        if not uids:
            return
            
        # الخطوة 1: دخول السكواد إذا وجد كود
        if team_code:
            print(f"  [{uid}] Joining squad: {team_code}")
            join_packet = await GenJoinSquadsPacket(team_code, key, iv)
            online_w.write(join_packet)
            await online_w.drain()
            await asyncio.sleep(2)
        
        # الخطوة 2: الترقيص لكل اليوزرات مع فارق 0.5 ثانية
        for i, target_uid in enumerate(uids):
            if target_uid and target_uid.isdigit():
                print(f"  [{uid}] [{i+1}/{len(uids)}] Dancing emote {emote_id} to UID: {target_uid}")
                emote_packet = await Emote_k(int(target_uid), int(emote_id), key, iv, region)
                online_w.write(emote_packet)
                await online_w.drain()
                
                if i < len(uids) - 1:
                    await asyncio.sleep(0.5)
        
        # الخطوة 3: انتظار 2 ثانية
        await asyncio.sleep(2)
        
        # الخطوة 4: الخروج من السكواد
        if team_code:
            print(f"  [{uid}] Leaving squad...")
            leave_packet = await GenLeaveSquadPacket(key, iv)
            if leave_packet:
                online_w.write(leave_packet)
                await online_w.drain()
        
    except Exception as e:
        print(f"  [ERROR] Dance error for {uid}: {e}")


# ---- Random Colores ----
def get_random_color():
    colors = [
        "[FF0000]", "[00FF00]", "[0000FF]", "[FFFF00]", "[FF00FF]", "[00FFFF]", "[FFFFFF]", "[FFA500]",
        "[A52A2A]", "[800080]", "[000000]", "[808080]", "[C0C0C0]", "[FFC0CB]", "[FFD700]", "[ADD8E6]",
        "[90EE90]", "[D2691E]", "[DC143C]", "[00CED1]", "[9400D3]", "[F08080]", "[20B2AA]", "[FF1493]",
        "[7CFC00]", "[B22222]", "[FF4500]", "[DAA520]", "[00BFFF]", "[00FF7F]", "[4682B4]", "[6495ED]",
        "[5F9EA0]", "[DDA0DD]", "[E6E6FA]", "[B0C4DE]", "[556B2F]", "[8FBC8F]", "[2E8B57]", "[3CB371]",
        "[6B8E23]", "[808000]", "[B8860B]", "[CD5C5C]", "[8B0000]", "[FF6347]", "[FF8C00]", "[BDB76B]",
        "[9932CC]", "[8A2BE2]", "[4B0082]", "[6A5ACD]", "[7B68EE]", "[4169E1]", "[1E90FF]", "[191970]",
        "[00008B]", "[000080]", "[008080]", "[008B8B]", "[B0E0E6]", "[AFEEEE]", "[E0FFFF]", "[F5F5DC]",
        "[FAEBD7]"
    ]
    return random.choice(colors)

async def encrypted_proto(encoded_hex):
    key = b'Yg&tc%DEuh6%Zc^8'
    iv = b'6oyZDr22E3ychjM%'
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_message = pad(encoded_hex, AES.block_size)
    encrypted_payload = cipher.encrypt(padded_message)
    return encrypted_payload
    
async def GeNeRaTeAccEss(uid , password):
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    headers = {
        "Host": "100067.connect.garena.com",
        "User-Agent": (await Ua()),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "close"}
    data = {
        "uid": uid,
        "password": password,
        "response_type": "token",
        "client_type": "2",
        "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        "client_id": "100067"}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=Hr, data=data) as response:
            if response.status != 200: return "Failed to get access token"
            data = await response.json()
            open_id = data.get("open_id")
            access_token = data.get("access_token")
            return (open_id, access_token) if open_id and access_token else (None, None)

async def EncRypTMajoRLoGin(open_id, access_token):
    major_login = MajoRLoGinrEq_pb2.MajorLogin()
    major_login.event_time = str(datetime.now())[:-7]
    major_login.game_name = "free fire"
    major_login.platform_id = 1
    major_login.client_version = "1.123.1"
    major_login.system_software = "Android OS 9 / API-28 (PQ3B.190801.10101846/G9650ZHU2ARC6)"
    major_login.system_hardware = "Handheld"
    major_login.telecom_operator = "Verizon"
    major_login.network_type = "WIFI"
    major_login.screen_width = 1920
    major_login.screen_height = 1080
    major_login.screen_dpi = "280"
    major_login.processor_details = "ARM64 FP ASIMD AES VMH | 2865 | 4"
    major_login.memory = 3003
    major_login.gpu_renderer = "Adreno (TM) 640"
    major_login.gpu_version = "OpenGL ES 3.1 v1.46"
    major_login.unique_device_id = "Google|34a7dcdf-a7d5-4cb6-8d7e-3b0e448a0c57"
    major_login.client_ip = "223.191.51.89"
    major_login.language = "en"
    major_login.open_id = open_id
    major_login.open_id_type = "4"
    major_login.device_type = "Handheld"
    memory_available = major_login.memory_available
    memory_available.version = 55
    memory_available.hidden_value = 81
    major_login.access_token = access_token
    major_login.platform_sdk_id = 1
    major_login.network_operator_a = "Verizon"
    major_login.network_type_a = "WIFI"
    major_login.client_using_version = "7428b253defc164018c604a1ebbfebdf"
    major_login.external_storage_total = 36235
    major_login.external_storage_available = 31335
    major_login.internal_storage_total = 2519
    major_login.internal_storage_available = 703
    major_login.game_disk_storage_available = 25010
    major_login.game_disk_storage_total = 26628
    major_login.external_sdcard_avail_storage = 32992
    major_login.external_sdcard_total_storage = 36235
    major_login.login_by = 3
    major_login.library_path = "/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/lib/arm64"
    major_login.reg_avatar = 1
    major_login.library_token = "5b892aaabd688e571f688053118a162b|/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/base.apk"
    major_login.channel_type = 3
    major_login.cpu_type = 2
    major_login.cpu_architecture = "64"
    major_login.client_version_code = "2019118695"
    major_login.graphics_api = "OpenGLES2"
    major_login.supported_astc_bitset = 16383
    major_login.login_open_id_type = 4
    major_login.analytics_detail = b"FwQVTgUPX1UaUllDDwcWCRBpWAUOUgsvA1snWlBaO1kFYg=="
    major_login.loading_time = 13564
    major_login.release_channel = "android"
    major_login.extra_info = "KqsHTymw5/5GB23YGniUYN2/q47GATrq7eFeRatf0NkwLKEMQ0PK5BKEk72dPflAxUlEBir6Vtey83XqF593qsl8hwY="
    major_login.android_engine_init_flag = 110009
    major_login.if_push = 1
    major_login.is_vpn = 1
    major_login.origin_platform_type = "4"
    major_login.primary_platform_type = "4"
    string = major_login.SerializeToString()
    return  await encrypted_proto(string)

async def MajorLogin(payload):
    url = "https://loginbp.ggblueshark.com/MajorLogin"
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=Hr, ssl=ssl_context) as response:
            if response.status == 200: return await response.read()
            return None

async def GetLoginData(base_url, payload, token):
    url = f"{base_url}/GetLoginData"
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    Hr['Authorization']= f"Bearer {token}"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=Hr, ssl=ssl_context) as response:
            if response.status == 200: return await response.read()
            return None

async def DecRypTMajoRLoGin(MajoRLoGinResPonsE):
    proto = MajoRLoGinrEs_pb2.MajorLoginRes()
    proto.ParseFromString(MajoRLoGinResPonsE)
    return proto

async def DecRypTLoGinDaTa(LoGinDaTa):
    proto = PorTs_pb2.GetLoginData()
    proto.ParseFromString(LoGinDaTa)
    return proto

async def DecodeWhisperMessage(hex_packet):
    packet = bytes.fromhex(hex_packet)
    proto = DEcwHisPErMsG_pb2.DecodeWhisper()
    proto.ParseFromString(packet)
    return proto
    
async def decode_team_packet(hex_packet):
    packet = bytes.fromhex(hex_packet)
    proto = sQ_pb2.recieved_chat()
    proto.ParseFromString(packet)
    return proto
    
async def xAuThSTarTuP(TarGeT, token, timestamp, key, iv):
    uid_hex = hex(TarGeT)[2:]
    uid_length = len(uid_hex)
    encrypted_timestamp = await DecodE_HeX(timestamp)
    encrypted_account_token = token.encode().hex()
    encrypted_packet = await EnC_PacKeT(encrypted_account_token, key, iv)
    encrypted_packet_length = hex(len(encrypted_packet) // 2)[2:]
    if uid_length == 9: headers = '0000000'
    elif uid_length == 8: headers = '00000000'
    elif uid_length == 10: headers = '000000'
    elif uid_length == 7: headers = '000000000'
    else: print('Unexpected length') ; headers = '0000000'
    return f"0115{headers}{uid_hex}{encrypted_timestamp}00000{encrypted_packet_length}{encrypted_packet}"
     
async def cHTypE(H):
    if not H: return 'Squid'
    elif H == 1: return 'CLan'
    elif H == 2: return 'PrivaTe'
    
async def SEndMsG(H , message , Uid , chat_id , key , iv):
    TypE = await cHTypE(H)
    if TypE == 'Squid': msg_packet = await xSEndMsgsQ(message , chat_id , key , iv)
    elif TypE == 'CLan': msg_packet = await xSEndMsg(message , 1 , chat_id , chat_id , key , iv)
    elif TypE == 'PrivaTe': msg_packet = await xSEndMsg(message , 2 , Uid , Uid , key , iv)
    return msg_packet


async def TcPOnLine(account_uid, ip, port, key, iv, AutHToKen, region, reconnect_delay=3):
    """TCP Online connection لكل حساب - اتصال مستقر مع إعادة اتصال ذكية"""
    reconnect_count = 0
    max_fast_reconnects = 5  # بعد 5 محاولات سريعة، انتظر أطول
    
    while True:
        try:
            reader, writer = await asyncio.open_connection(ip, int(port))
            reconnect_count = 0  # نجح الاتصال، تصفير العداد
            
            # تسجيل الـ online_writer في جلسة هذا الحساب
            with sessions_lock:
                if account_uid in bot_sessions:
                    bot_sessions[account_uid]["online_writer"] = writer
                    # إذا كان Chat متصل، الحساب جاهز
                    if bot_sessions[account_uid].get("whisper_writer"):
                        bot_sessions[account_uid]["ready"] = True
            
            bytes_payload = bytes.fromhex(AutHToKen)
            writer.write(bytes_payload)
            await writer.drain()
            print(f"  [{account_uid}] Online connected to {ip}:{port}")
            
            while True:
                try:
                    data2 = await reader.read(9999)
                    if not data2:
                        print(f"  [{account_uid}] Online EOF - Connection closed by server")
                        break
                    
                    if data2.hex().startswith('0500') and len(data2.hex()) > 1000:
                        try:
                            packet = await DeCode_PackEt(data2.hex()[10:])
                            packet = json.loads(packet)
                            OwNer_UiD , CHaT_CoDe , SQuAD_CoDe = await GeTSQDaTa(packet)

                            JoinCHaT = await AutH_Chat(3 , OwNer_UiD , CHaT_CoDe, key,iv)
                            
                            with sessions_lock:
                                whisper_w = bot_sessions.get(account_uid, {}).get("whisper_writer")
                            
                            if whisper_w:
                                whisper_w.write(JoinCHaT)
                                await whisper_w.drain()

                            message = f"""[B][C]{get_random_color()}* YaKoUb TOP 1 *

{get_random_color()}═════════════════
[00FF00]تـم إخــتـراق الـسـكـواد مـن قـبل  SKINZ X KING
{get_random_color()}═════════════════"""
                            P = await SEndMsG(0 , message , OwNer_UiD , OwNer_UiD , key , iv)
                            
                            if whisper_w:
                                whisper_w.write(P)
                                await whisper_w.drain()

                        except Exception as e:
                            print(f"  [{account_uid}] Online parse error: {e}")
                except (ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError) as e:
                    print(f"  [{account_uid}] Online connection lost: {type(e).__name__}")
                    break
                except Exception as e:
                    print(f"  [{account_uid}] Online read error: {e}")
                    break

            # تنظيف عند قطع الاتصال
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
            
            with sessions_lock:
                if account_uid in bot_sessions:
                    bot_sessions[account_uid]["online_writer"] = None
                    bot_sessions[account_uid]["ready"] = False
            
            print(f"  [{account_uid}] Online disconnected - Reconnecting... ({reconnect_count + 1})")

        except Exception as e:
            reconnect_count += 1
            
            with sessions_lock:
                if account_uid in bot_sessions:
                    bot_sessions[account_uid]["online_writer"] = None
                    bot_sessions[account_uid]["ready"] = False
            
            if reconnect_count <= max_fast_reconnects:
                print(f"  [{account_uid}] Online reconnect ({reconnect_count}/{max_fast_reconnects}) in {reconnect_delay}s")
            else:
                # انتظر أطول بعد محاولات كثيرة
                wait_time = min(reconnect_count, 30)
                print(f"  [{account_uid}] Online slow reconnect ({reconnect_count}) in {wait_time}s")
                await asyncio.sleep(wait_time)
                continue
        
        await asyncio.sleep(reconnect_delay)
                            
async def TcPChaT(account_uid, ip, port, AutHToKen, key, iv, LoGinDaTaUncRypTinG, ready_event, region, reconnect_delay=3):
    """TCP Chat connection لكل حساب - اتصال مستقر مع إعادة اتصال ذكية"""
    print(f"  [{account_uid}] Starting TCP Chat for region: {region}")
    first_connect = True
    reconnect_count = 0
    max_fast_reconnects = 5

    while True:
        try:
            reader, writer = await asyncio.open_connection(ip, int(port))
            reconnect_count = 0
            
            # تسجيل الـ whisper_writer
            with sessions_lock:
                if account_uid in bot_sessions:
                    bot_sessions[account_uid]["whisper_writer"] = writer
                    # إذا كان Online متصل، الحساب جاهز
                    if bot_sessions[account_uid].get("online_writer"):
                        bot_sessions[account_uid]["ready"] = True
            
            bytes_payload = bytes.fromhex(AutHToKen)
            writer.write(bytes_payload)
            await writer.drain()
            
            if first_connect:
                ready_event.set()
                first_connect = False
            
            print(f"  [{account_uid}] Chat connected to {ip}:{port}")
            
            if LoGinDaTaUncRypTinG.Clan_ID:
                clan_id = LoGinDaTaUncRypTinG.Clan_ID
                clan_compiled_data = LoGinDaTaUncRypTinG.Clan_Compiled_Data
                print(f'  [{account_uid}] Bot in Clan: {clan_id}')
                pK = await AuthClan(clan_id, clan_compiled_data, key, iv)
                if writer: 
                    writer.write(pK) 
                    await writer.drain()
            
            while True:
                try:
                    data = await reader.read(9999)
                    if not data:
                        print(f"  [{account_uid}] Chat EOF - Connection closed by server")
                        break
                    
                    if data.hex().startswith("120000"):
                        try:
                            response = await DecodeWhisperMessage(data.hex()[10:])
                            uid = response.Data.uid
                            chat_id = response.Data.Chat_ID
                            XX = response.Data.chat_type
                            inPuTMsG = response.Data.msg.lower()

                            if inPuTMsG in ("hi", "hello", "fen", "/help"):
                                message = f"""[B][C]{get_random_color()}BOT IS ONLINE
[FFFFFF]InStGrAm : @skinz_king"""
                                P = await SEndMsG(response.Data.chat_type, message, uid, chat_id, key, iv)
                                
                                with sessions_lock:
                                    whisper_w = bot_sessions.get(account_uid, {}).get("whisper_writer")
                                if whisper_w:
                                    whisper_w.write(P)
                                    await whisper_w.drain()
                                
                        except Exception as e:
                            pass
                except (ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError) as e:
                    print(f"  [{account_uid}] Chat connection lost: {type(e).__name__}")
                    break
                except Exception as e:
                    print(f"  [{account_uid}] Chat read error: {e}")
                    break

            # تنظيف عند قطع الاتصال
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
            
            with sessions_lock:
                if account_uid in bot_sessions:
                    bot_sessions[account_uid]["whisper_writer"] = None
                    bot_sessions[account_uid]["ready"] = False
            
            print(f"  [{account_uid}] Chat disconnected - Reconnecting... ({reconnect_count + 1})")
                    
        except Exception as e:
            reconnect_count += 1
            
            with sessions_lock:
                if account_uid in bot_sessions:
                    bot_sessions[account_uid]["whisper_writer"] = None
                    bot_sessions[account_uid]["ready"] = False
            
            if reconnect_count <= max_fast_reconnects:
                print(f"  [{account_uid}] Chat reconnect ({reconnect_count}/{max_fast_reconnects}) in {reconnect_delay}s")
            else:
                wait_time = min(reconnect_count, 30)
                print(f"  [{account_uid}] Chat slow reconnect ({reconnect_count}) in {wait_time}s")
                await asyncio.sleep(wait_time)
                continue
        
        await asyncio.sleep(reconnect_delay)


async def MaiiiinE(Uid, Pw, account_index):
    """تشغيل حساب واحد - كل حساب يعمل بشكل مستقل"""
    
    while True:
        try:
            print(f"[Account {account_index}] {Uid} - Generating new token...")
            open_id, access_token = await GeNeRaTeAccEss(Uid, Pw)
            if not open_id or not access_token: 
                print(f"  [{Uid}] ERROR - Invalid Account")
                await asyncio.sleep(10)
                continue
            
            PyL = await EncRypTMajoRLoGin(open_id, access_token)
            MajoRLoGinResPonsE = await MajorLogin(PyL)
            if not MajoRLoGinResPonsE: 
                print(f"  [{Uid}] ERROR - Banned / Not Registered!")
                await asyncio.sleep(10)
                continue
            
            MajoRLoGinauTh = await DecRypTMajoRLoGin(MajoRLoGinResPonsE)
            UrL = MajoRLoGinauTh.url
            region = MajoRLoGinauTh.region
            
            ToKen = MajoRLoGinauTh.token
            TarGeT = MajoRLoGinauTh.account_uid
            key = MajoRLoGinauTh.key
            iv = MajoRLoGinauTh.iv
            timestamp = MajoRLoGinauTh.timestamp
            
            LoGinDaTa = await GetLoginData(UrL, PyL, ToKen)
            if not LoGinDaTa: 
                print(f"  [{Uid}] ERROR - Getting Ports From Login Data!")
                await asyncio.sleep(10)
                continue
                
            LoGinDaTaUncRypTinG = await DecRypTLoGinDaTa(LoGinDaTa)
            OnLinePorTs = LoGinDaTaUncRypTinG.Online_IP_Port
            ChaTPorTs = LoGinDaTaUncRypTinG.AccountIP_Port
            OnLineiP, OnLineporT = OnLinePorTs.split(":")
            ChaTiP, ChaTporT = ChaTPorTs.split(":")
            acc_name = LoGinDaTaUncRypTinG.AccountName
            
            AutHToKen = await xAuThSTarTuP(int(TarGeT), ToKen, int(timestamp), key, iv)
            
            # تسجيل الجلسة في bot_sessions
            with sessions_lock:
                bot_sessions[TarGeT] = {
                    "online_writer": None,
                    "whisper_writer": None,
                    "key": key,
                    "iv": iv,
                    "region": region,
                    "auth_token": AutHToKen,
                    "name": acc_name,
                    "uid": TarGeT,
                    "ready": False,  # يصبح True لما Online + Chat يتصلون
                }
            with busy_lock:
                account_busy[TarGeT] = False
            
            ready_event = asyncio.Event()
            
            task1 = asyncio.create_task(TcPChaT(TarGeT, ChaTiP, ChaTporT, AutHToKen, key, iv, LoGinDaTaUncRypTinG, ready_event, region))
            
            await ready_event.wait()
            await asyncio.sleep(1)
            
            task2 = asyncio.create_task(TcPOnLine(TarGeT, OnLineiP, OnLineporT, key, iv, AutHToKen, region))
            
            print(f"  [{TarGeT}] Bot Online | Name: {acc_name} | Region: {region}")
            
            # انتظار قبل تجديد التوكن (7 ساعات - 5 دقائق)
            await asyncio.sleep(7 * 60 * 60 - 300)
            
            print(f"  [{TarGeT}] Token about to expire - Restarting session...")
            
            # إزالة الجلسة
            with sessions_lock:
                if TarGeT in bot_sessions:
                    del bot_sessions[TarGeT]
            with busy_lock:
                if TarGeT in account_busy:
                    del account_busy[TarGeT]
            
            break
            
        except Exception as e:
            print(f"  [{Uid}] Session Error: {e}")
            print(f"  [{Uid}] Restarting in 10 seconds...")
            await asyncio.sleep(10)


async def StarTinG():
    """تشغيل كل الحسابات بشكل متوازي"""
    accounts = load_accounts()
    
    if not accounts:
        print("[ERROR] No accounts found! Create accounts.txt with format: uid:password")
        print("[INFO] Example:")
        print("  1234567890:your_password_hash_here")
        print("  9876543210:another_password_hash_here")
        return
    
    print(f"\n{'='*50}")
    print(f"  Multi-Account Emote Bot")
    print(f"  Loaded: {len(accounts)} accounts (Max: {MAX_ACCOUNTS})")
    print(f"{'='*50}\n")
    
    # تشغيل معالج الأوامر (مشترك بين كل الحسابات)
    asyncio.create_task(command_checker())
    
    # تشغيل كل الحسابات بشكل متوازي
    tasks = []
    for i, (uid, password) in enumerate(accounts):
        task = asyncio.create_task(MaiiiinE(uid, password, i + 1))
        tasks.append(task)
        await asyncio.sleep(2)  # تأخير 2 ثانية بين كل حساب
    
    # انتظار جميع المهام
    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == '__main__':
    print("Multi-Account Emote Bot - Auto Token Refresh Enabled")
    print(f"Max Accounts: {MAX_ACCOUNTS}")
    print(f"Accounts File: {ACCOUNTS_FILE}")
    print(f"API Port: 9128")
    print(f"{'='*50}")
    asyncio.run(StarTinG())
