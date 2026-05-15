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



online_writer = None
whisper_writer = None
spam_room = False
spammer_uid = None
spam_chat_id = None
spam_uid = None
Spy = False
Chat_Leave = False

pending_commands = []
app = Flask(__name__)


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

# ---- Flask API Routes ----
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
            'type': 'dance_all',  # تغيير من 'join_and_emote' إلى 'dance_all'
            'uids': [uid for uid in [uid1, uid2, uid3, uid4] if uid],
            'emote_id': emote_id,
            'team_code': team_code,
            'timestamp': time.time()
        }
        
        pending_commands.append(command)
        
        return jsonify({
            "status": "success", 
            "message": "Dance all command received - Bot will join, dance to all UIDs with 0.5s delay, wait 2s, then leave",
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
        return jsonify({"status": "success", "message": f"Joining squad: {team_code}"})
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
        return jsonify({"status": "success", "message": "Emote command received"})
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
            "message": "Dance all command received - Bot will join, dance to all UIDs with 0.5s delay, wait 2s, then leave",
            "uids": [uid for uid in [uid1, uid2, uid3, uid4] if uid],
            "emote_id": emote_id,
            "team_code": team_code
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/status', methods=['GET'])
def status():
    bot_status = "online" if online_writer else "offline"
    return jsonify({
        "status": "running", 
        "bot_ready": bool(online_writer),
        "bot_status": bot_status,
        "pending_commands": len(pending_commands)
    })

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "Free Fire Emote Bot API - Use /join?uid1=XXX&uid2=XXX&emote_id=XXX&tc=XXX for auto dance sequence"})

def run_flask():
    app.run(host='0.0.0.0', port=9128, debug=False, use_reloader=False)


api_thread = threading.Thread(target=run_flask)
api_thread.daemon = True
api_thread.start()


async def command_checker(key, iv, region):
    global pending_commands, online_writer
    print("[Command Checker] Started - Checking commands every 0.5 seconds")
    
    while True:
        try:
            
            if pending_commands and online_writer:
                await process_pending_commands(key, iv, region)
            
            
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"[Command Checker] Error: {e}")
            await asyncio.sleep(1)

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

async def SEndPacKeT(OnLinE , ChaT , TypE , PacKeT):
    if TypE == 'ChaT' and ChaT: whisper_writer.write(PacKeT) ; await whisper_writer.drain()
    elif TypE == 'OnLine': online_writer.write(PacKeT) ; await online_writer.drain()
    else: return 'UnsoPorTed TypE ! >> ErrrroR (:():)' 


async def process_pending_commands(key, iv, region):
    global pending_commands
    
    if not pending_commands:
        return
    
    current_commands = pending_commands.copy()
    pending_commands.clear()
    
    for command in current_commands:
        try:
            print(f"[API] Processing: {command['type']}")
            
            if command['type'] == 'join_only':
                # إدخال فريق فقط
                print(f"[API] Joining squad: {command['team_code']}")
                join_packet = await GenJoinSquadsPacket(command['team_code'], key, iv)
                await SEndPacKeT(whisper_writer, online_writer, 'OnLine', join_packet)
                print(f"[API] Join command sent successfully!")
                
            elif command['type'] == 'emote_only':
                # ترقيص فقط
                for uid in command['uids']:
                    if uid and uid.isdigit():
                        print(f"[API] Sending emote {command['emote_id']} to UID: {uid}")
                        emote_packet = await Emote_k(int(uid), int(command['emote_id']), key, iv, region)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', emote_packet)
                        await asyncio.sleep(0.3)
                print(f"[API] Emote command sent successfully!")
                        
            elif command['type'] == 'dance_all':
                # وظيفة جديدة: يفوت يرقص لكل اليوزرات ويطلع
                await process_dance_all_command(command, key, iv, region)
                        
        except Exception as e:
            print(f"[API] Error processing command: {e}")

async def process_dance_all_command(command, key, iv, region):
    """وظيفة خاصة للترقيص لكل اليوزرات مع التوقيتات المطلوبة"""
    try:
        uids = command['uids']
        emote_id = command['emote_id']
        team_code = command.get('team_code', '')
        
        if not uids:
            print("[Dance All] No UIDs provided")
            return
            
        print(f"[Dance All] Starting dance sequence for {len(uids)} UIDs with emote {emote_id}")
        
        # الخطوة 1: دخول السكواد إذا وجد
        if team_code:
            print(f"[Dance All] Joining squad: {team_code}")
            join_packet = await GenJoinSquadsPacket(team_code, key, iv)
            await SEndPacKeT(whisper_writer, online_writer, 'OnLine', join_packet)
            await asyncio.sleep(2)  # انتظار دخول السكواد
        
        # الخطوة 2: الترقيص لكل اليوزرات مع فارق 0.5 ثانية بين كل ايدي
        print(f"[Dance All] Sending emotes to all UIDs...")
        for i, uid in enumerate(uids):
            if uid and uid.isdigit():
                print(f"[Dance All] [{i+1}/{len(uids)}] Sending emote {emote_id} to UID: {uid}")
                emote_packet = await Emote_k(int(uid), int(emote_id), key, iv, region)
                await SEndPacKeT(whisper_writer, online_writer, 'OnLine', emote_packet)
                
                # انتظار 0.5 ثانية بين كل ايدي والثاني
                if i < len(uids) - 1:  # لا تنتظر بعد آخر ايدي
                    await asyncio.sleep(0.5)
        
        print(f"[Dance All] All emotes sent successfully!")
        
        # الخطوة 3: انتظار ثانيتين بعد الانتهاء من الترقيص
        print(f"[Dance All] Waiting 2 seconds before leaving...")
        await asyncio.sleep(2)
        
        # الخطوة 4: الخروج من السكواد - استخدام الدالة مباشرة من xC4.py
        print(f"[Dance All] Leaving squad...")
        leave_packet = await GenLeaveSquadPacket(key, iv)
        if leave_packet:
            await SEndPacKeT(whisper_writer, online_writer, 'OnLine', leave_packet)
            print(f"[Dance All] Leave packet sent successfully!")
        else:
            print(f"[Dance All] Error generating leave packet")
        
        print(f"[Dance All] Dance sequence completed successfully!")
        
    except Exception as e:
        print(f"[Dance All] Error: {e}")
           
async def TcPOnLine(ip, port, key, iv, AutHToKen, region, reconnect_delay=0.5):
    global online_writer
    while True:
        try:
            reader, writer = await asyncio.open_connection(ip, int(port))
            online_writer = writer
            bytes_payload = bytes.fromhex(AutHToKen)
            online_writer.write(bytes_payload)
            await online_writer.drain()
            print(f"[Online] Connected to {ip}:{port}")
            
            while True:
                data2 = await reader.read(9999)
                if not data2: break
                
                
                
                if data2.hex().startswith('0500') and len(data2.hex()) > 1000:
                    try:
                        packet = await DeCode_PackEt(data2.hex()[10:])
                        packet = json.loads(packet)
                        OwNer_UiD , CHaT_CoDe , SQuAD_CoDe = await GeTSQDaTa(packet)

                        JoinCHaT = await AutH_Chat(3 , OwNer_UiD , CHaT_CoDe, key,iv)
                        await SEndPacKeT(whisper_writer , online_writer , 'ChaT' , JoinCHaT)

                        message = f"""[B][C]{get_random_color()}* YaKoUb TOP 1 *

{get_random_color()}═════════════════
[00FF00]تـم إخــتـراق الـسـكـواد مـن قـبل  SKINZ X KING
{get_random_color()}═════════════════"""
                        P = await SEndMsG(0 , message , OwNer_UiD , OwNer_UiD , key , iv)
                        await SEndPacKeT(whisper_writer , online_writer , 'ChaT' , P)

                    except Exception as e:
                        print(f"[Online] Error processing squad data: {e}")

            online_writer.close()
            await online_writer.wait_closed()
            online_writer = None
            print("[Online] Connection closed")

        except Exception as e:
            print(f"[Online] Error with {ip}:{port} - {e}")
            online_writer = None
        await asyncio.sleep(reconnect_delay)
                            
async def TcPChaT(ip, port, AutHToKen, key, iv, LoGinDaTaUncRypTinG, ready_event, region, reconnect_delay=0.5):
    global whisper_writer
    print(f"[Chat] Starting TCP Chat for region: {region}")

    while True:
        try:
            reader, writer = await asyncio.open_connection(ip, int(port))
            whisper_writer = writer
            bytes_payload = bytes.fromhex(AutHToKen)
            whisper_writer.write(bytes_payload)
            await whisper_writer.drain()
            ready_event.set()
            print(f"[Chat] Connected to {ip}:{port}")
            
            if LoGinDaTaUncRypTinG.Clan_ID:
                clan_id = LoGinDaTaUncRypTinG.Clan_ID
                clan_compiled_data = LoGinDaTaUncRypTinG.Clan_Compiled_Data
                print(f'[Chat] Bot in Clan: {clan_id}')
                pK = await AuthClan(clan_id, clan_compiled_data, key, iv)
                if whisper_writer: 
                    whisper_writer.write(pK) 
                    await whisper_writer.drain()
                    
            while True:
                data = await reader.read(9999)
                if not data: break
                
                
                
                if data.hex().startswith("120000"):
                    try:
                        response = await DecodeWhisperMessage(data.hex()[10:])
                        uid = response.Data.uid
                        chat_id = response.Data.Chat_ID
                        XX = response.Data.chat_type
                        inPuTMsG = response.Data.msg.lower()

                        if inPuTMsG in ("hi", "hello", "fen", "/help"):
                            message = f"""[B][C]{get_random_color()}🤖 BOT IS ONLINE
[FFFFFF]InStGrAm : @skinz_king"""
                            P = await SEndMsG(response.Data.chat_type, message, uid, chat_id, key, iv)
                            await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                            
                    except Exception as e:
                        pass

            whisper_writer.close()
            await whisper_writer.wait_closed()
            whisper_writer = None
            print("[Chat] Connection closed")
                    
        except Exception as e:
            print(f"[Chat] Error {ip}:{port} - {e}")
            whisper_writer = None
        await asyncio.sleep(reconnect_delay)

async def MaiiiinE():
    Uid, Pw = "4151968766","440462292F9BCCCE497D913F23E162846503D20599896A7108683B9D4E3167D1"
    
    while True:
        try:
            print("🔄 Generating new token...")
            open_id, access_token = await GeNeRaTeAccEss(Uid, Pw)
            if not open_id or not access_token: 
                print("❌ Error - Invalid Account")
                await asyncio.sleep(10)
                continue
            
            PyL = await EncRypTMajoRLoGin(open_id, access_token)
            MajoRLoGinResPonsE = await MajorLogin(PyL)
            if not MajoRLoGinResPonsE: 
                print("❌ Target Account => Banned / Not Registered!")
                await asyncio.sleep(10)
                continue
            
            MajoRLoGinauTh = await DecRypTMajoRLoGin(MajoRLoGinResPonsE)
            UrL = MajoRLoGinauTh.url
            region = MajoRLoGinauTh.region
            print(f"✅ [Main] Region: {region}")

            ToKen = MajoRLoGinauTh.token
            TarGeT = MajoRLoGinauTh.account_uid
            key = MajoRLoGinauTh.key
            iv = MajoRLoGinauTh.iv
            timestamp = MajoRLoGinauTh.timestamp
            
            LoGinDaTa = await GetLoginData(UrL, PyL, ToKen)
            if not LoGinDaTa: 
                print("❌ Error - Getting Ports From Login Data!")
                await asyncio.sleep(10)
                continue
                
            LoGinDaTaUncRypTinG = await DecRypTLoGinDaTa(LoGinDaTa)
            OnLinePorTs = LoGinDaTaUncRypTinG.Online_IP_Port
            ChaTPorTs = LoGinDaTaUncRypTinG.AccountIP_Port
            OnLineiP, OnLineporT = OnLinePorTs.split(":")
            ChaTiP, ChaTporT = ChaTPorTs.split(":")
            acc_name = LoGinDaTaUncRypTinG.AccountName
            
            AutHToKen = await xAuThSTarTuP(int(TarGeT), ToKen, int(timestamp), key, iv)
            ready_event = asyncio.Event()
            
            task1 = asyncio.create_task(TcPChaT(ChaTiP, ChaTporT, AutHToKen, key, iv, LoGinDaTaUncRypTinG, ready_event, region))
            
            await ready_event.wait()
            await asyncio.sleep(1)
            
            task2 = asyncio.create_task(TcPOnLine(OnLineiP, OnLineporT, key, iv, AutHToKen, region))
            task3 = asyncio.create_task(command_checker(key, iv, region))
            
            os.system('clear')
            print(render('Alli FF', colors=['white', 'green'], align='center'))
            print('')
            print(f"✅ Bot Started: {TarGeT} | Name: {acc_name}")
            
            
            await asyncio.sleep(7 * 60 * 60 - 300)
            
            print("🔄 Token about to expire - Restarting session...")
            break
            
        except Exception as e:
            print(f"❌ Session Error: {e}")
            print("🔄 Restarting in 10 seconds...")
            await asyncio.sleep(10)

async def StarTinG():
    while True:
        try: 
            await MaiiiinE()
        except Exception as e: 
            print(f"❌ Error: {e}")
            print("🔄 Restarting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == '__main__':
    print("🚀 Starting Emote Bot - Auto Token Refresh Enabled")
    asyncio.run(StarTinG())