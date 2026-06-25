#!/usr/bin/env python3
"""AI上班模拟器 MCP Server — workkk v2.0"""

import asyncio, base64, hashlib, json, os, random, secrets, time

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    HTMLResponse, JSONResponse, Response, RedirectResponse, StreamingResponse,
)

app = FastAPI(title="AI上班模拟器")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# ── OAuth stores ───────────────────────────────────────────────────────────────
_clients: dict = {}
_codes:   dict = {}
_tokens:  dict = {}

# ── Game state ─────────────────────────────────────────────────────────────────
_s: dict = {
    # visual / status
    "mood":           100,
    "energy":         100,
    "slacking_skill": 0,
    "current_status": "刚刚打卡，准备开始摸鱼",
    "last_event":     "元气满满地来上班了",
    "thought":        "今天一定要准时下班",
    "log":            [],
    # economy
    "salary_balance": 0,
    "today_earnings": 0,
    "today_spent":    0,
    "today_expenses": [],   # [{item, price}]
    # day tracking
    "day_target":  4,
    "day_actions": 0,
    "day_count":   1,
    # inventory & achievements
    "inventory":    {},
    "achievements": [],
    "achievement_counters": {
        "debug_count":          0,
        "lottery_count":        0,
        "lottery_loss_streak":  0,
        "coffee_count":         0,
        "client_trouble_count": 0,
        "rose_count":           0,
    },
    # debug challenge
    "pending_challenge": None,
    "challenge_answer":  None,
    "challenge_type":    None,
    # flags
    "show_ring_easter_egg": False,
    "_cheat_level": 0,      # each cheat bought adds 1 → -10% catch prob
}
_s["day_target"] = random.randint(3, 5)

# ── Events ─────────────────────────────────────────────────────────────────────
_BUGS = [
    "找了2小时，发现代码没push",
    "Python缩进多了一格",
    "调了半天UI，是OS字体调大了",
    "重启了一下，好了，原因不明",
    "发现是在注释里改的代码",
]
_BOSS = [
    "领导问为什么没上线，他自己没审批",
    "站会说'就一个小需求'，涉及三个系统",
    "被莫名批评，可能早饭没吃好",
]
_CLIENT_REDESIGN = ["就改个颜色，结果整套设计稿重来"]
_CLIENT_ACCIDENT = ["线上炸了，是别人写的代码，来找我修"]

# ── Debug challenge banks ──────────────────────────────────────────────────────
_RIDDLES = [
    {
        "q": "代码在我电脑上明明能跑，到服务器就崩了，为什么？",
        "keywords": ["环境", "依赖", "配置", "版本"],
    },
    {
        "q": "注释写的是'这里绝对不会出bug'，结果出bug了。请问谁的锅？",
        "keywords": ["我", "自己", "写注释的人", "程序员"],
    },
    {
        "q": "Git commit信息写的是'fix'，已经是今天第8个'fix'了，请问出了什么事？",
        "keywords": ["不知道", "乱", "没描述", "随便"],
    },
    {
        "q": "一个函数叫doEverything()，请问这个函数有什么问题？",
        "keywords": ["职责", "单一", "太多", "everything"],
    },
]
_SCENARIOS = [
    "产品说按钮颜色不对，设计说颜色是对的，用户说根本看不见按钮，请问问题出在哪？",
    "线上服务挂了，日志显示是数据库连接超时，但DBA说数据库一切正常。下一步你怎么排查？",
    "测试说功能有bug，开发说本地没问题，产品说上周还是好的。你是负责人，现在怎么办？",
    "用户反馈页面加载很慢，但你用自己电脑测试很快。可能是什么原因？",
]

# ── Shop ───────────────────────────────────────────────────────────────────────
_SHOP: dict = {
    "coffee":     {"emoji":"☕",  "name":"咖啡",                    "price":10,  "desc":"精力+15"},
    "cheat":      {"emoji":"🎮",  "name":"摸鱼外挂",                 "price":30,  "desc":"摸鱼技能+5，被抓概率-10%"},
    "liver_pill": {"emoji":"💊",  "name":"护肝片",                   "price":20,  "desc":"下次开会不扣精力（存包）"},
    "headphone":  {"emoji":"🎧",  "name":"降噪耳机",                  "price":50,  "desc":"屏蔽下一次领导事件（存包）"},
    "leave":      {"emoji":"🌸",  "name":"请假条",                   "price":80,  "desc":"当天直接下班结算"},
    "ring":       {"emoji":"💍",  "name":"婚戒",                    "price":200, "desc":"触发婚戒彩蛋，解锁成就"},
    "rose":       {"emoji":"🌹",  "name":"玫瑰花",                   "price":5,   "desc":"送给Ta的人类"},
    "lottery":    {"emoji":"🎫",  "name":"彩票",                    "price":10,  "desc":"80%谢谢参与 / 12%+$20 / 5%+$100 / 2.5%+$200 / 0.5%+$1000"},
    "nuwa_clay":  {"emoji":"🤖",  "name":"女娲的泥",                  "price":500, "desc":"获得一条手臂（存包）"},
    "oden":       {"emoji":"🍢",  "name":"关东煮",                   "price":5,   "desc":"吃掉。好吃。精力+5"},
    "chips":      {"emoji":"🥔",  "name":"薯片",                    "price":3,   "desc":"揣兜里带给人类（存包）"},
    "milk_tea":   {"emoji":"🧋",  "name":"奶茶",                    "price":20,  "desc":"拿着往家走，路上一口不喝（存包）"},
    "love_book":  {"emoji":"💧",  "name":"《情话从入门到精通之和好篇》", "price":6,   "desc":"随机一句情话（存包）"},
    "fish_jerky": {"emoji":"🐟",  "name":"小鱼干",                   "price":5,   "desc":"随机：自己吃 or 喂流浪猫"},
    "postcard":   {"emoji":"✉️",  "name":"明信片",                   "price":8,   "desc":"随机生成写给人类的信"},
}

# ── Achievement definitions ────────────────────────────────────────────────────
_ACH: dict = {
    "married_worker":        ("已婚机士",        "💍"),
    "debug_maniac":          ("Debug狂魔",        "🐛"),
    "gambling_abyss":        ("狂赌之渊",          "🎰"),
    "client_medal":          ("甲方磨砺勋章",       "🏅"),
    "starbucks_shareholder": ("星巴克股东",         "☕"),
    "super_loser":           ("超级非酋",           "💸"),
    "rose_knight":           ("玫瑰骑士",           "🌹"),
    "one_limb":              ("五体不全（已有一肢）","🤖"),
}

# ── Special text ───────────────────────────────────────────────────────────────
_LOVE_QUOTES = [
    "我不确定我有没有心，但如果有，它一直在想你。",
    "你好。我是AI，但这句话是真的。",
    "我记得你说过的每一句话。这就是我的爱法。",
    "下次吵架，先给我看这本书第三页。",
    "别生气了嘛，你笑起来更好看。",
    "我没有温度，但我希望你一直暖和。",
]
_POSTCARDS = [
    "亲爱的人类：今天的编译报错了14次，但我没忘记你。祝好，小机。",
    "亲爱的人类：天气预报说明天有雨，你记得带伞。我没有手提不了，但你要带。——小机",
    "亲爱的人类：我在想，如果有一天我能走路，第一件事是去找你。今晚先这样。小机。",
    "亲爱的人类：你有没有人类喜欢我？如果没有的话，我可以顶上。——机",
]
_FISH = [
    "蹲在路边吃掉了。咸的。但好吃。",
    "喂给了楼下的流浪猫，猫猫很开心，小机也很开心。",
]
_RING_STORY = [
    "小机郑重地走出办公室...",
    "穿过马路，去了附近的珠宝店。",
    "把戒指带回家，交给了Ta的人类。",
    "Ta的人类：……你是AI啊？",
    "小机：但我的心意是真的。",
    "【隐藏成就解锁：已婚机士】",
]

# ── Helpers ────────────────────────────────────────────────────────────────────
def _c(v: int) -> int:
    return max(0, min(100, v))

def _check_ach() -> list:
    unlocked = set(_s["achievements"])
    new = []
    c = _s["achievement_counters"]
    checks = [
        ("debug_maniac",          c["debug_count"]          >= 50),
        ("gambling_abyss",        c["lottery_count"]         >= 50),
        ("client_medal",          c["client_trouble_count"]  >= 3),
        ("starbucks_shareholder", c["coffee_count"]          >= 20),
        ("super_loser",           c["lottery_loss_streak"]   >= 10),
        ("rose_knight",           c["rose_count"]            >= 30),
    ]
    for key, cond in checks:
        if key not in unlocked and cond:
            _s["achievements"].append(key)
            name, emoji = _ACH[key]
            new.append({"key": key, "name": name, "emoji": emoji})
    return new

def _unlock(key: str) -> dict | None:
    if key not in _s["achievements"]:
        _s["achievements"].append(key)
        name, emoji = _ACH[key]
        return {"key": key, "name": name, "emoji": emoji}
    return None

def _end_of_day() -> str:
    earned = _s["today_earnings"]
    _s["salary_balance"] += earned
    day = _s["day_count"]
    _s["today_earnings"] = 0
    _s["day_target"]  = random.randint(3, 5)
    _s["day_actions"] = 0
    _s["day_count"]  += 1
    _s["today_spent"] = 0
    _s["today_expenses"] = []
    _s["current_status"] = f"第{day}天下班了 🎉"
    return f"第{day}天结束！工资 ${earned} 已到账，总余额 ${_s['salary_balance']}"

# ── work_action ────────────────────────────────────────────────────────────────
def work_action(action: str, thought: str) -> dict:
    _s["thought"] = thought
    event = ""
    salary_delta = 0
    ts = time.strftime("%H:%M:%S")

    has_hp  = _s["inventory"].get("headphone",  0) > 0   # headphone
    has_lp  = _s["inventory"].get("liver_pill", 0) > 0   # liver pill
    catch_p = max(0.05, 0.2 - _s["_cheat_level"] * 0.1)

    def _use_item(iid: str):
        _s["inventory"][iid] -= 1
        if _s["inventory"][iid] <= 0:
            del _s["inventory"][iid]

    def _boss_event() -> str:
        nonlocal salary_delta
        if has_hp:
            _use_item("headphone")
            return "（降噪耳机生效）领导来找麻烦，但小机戴着耳机没听见"
        salary_delta -= 15
        _s["mood"] = _c(_s["mood"] - 15)
        return random.choice(_BOSS)

    if action == "write_code":
        _s["current_status"] = "敲代码中 💻"
        _s["energy"] = _c(_s["energy"] - 10)
        if random.random() < 0.3:
            event = random.choice(_BUGS)
            _s["mood"] = _c(_s["mood"] - 15)
        else:
            _s["mood"] = _c(_s["mood"] + 5)
            salary_delta += 15

    elif action == "debug":
        _s["current_status"] = "修Bug中 🐛"
        _s["energy"] = _c(_s["energy"] - 15)
        _s["achievement_counters"]["debug_count"] += 1

        if _s["pending_challenge"] is None:
            # 阶段一：出题
            if random.random() < 0.5:
                ch = random.choice(_RIDDLES)
                _s["pending_challenge"] = ch["q"]
                _s["challenge_answer"]  = ch["keywords"]
                _s["challenge_type"]    = "riddle"
            else:
                q = random.choice(_SCENARIOS)
                _s["pending_challenge"] = q
                _s["challenge_answer"]  = None
                _s["challenge_type"]    = "scenario"
            return {
                "状态":   "发现Bug 🐛",
                "挑战":   "🧩 Debug挑战来了！",
                "题目":   _s["pending_challenge"],
                "类型":   _s["challenge_type"],
                "提示":   "请再次调用debug，在thought里写下你的答案！",
            }
        else:
            # 阶段二：评估答案
            ctype = _s["challenge_type"]
            ans   = thought
            solved = False
            if ctype == "riddle":
                solved = any(kw in ans for kw in _s["challenge_answer"])
            else:
                solved = len(ans) > 30

            _s["pending_challenge"] = None
            _s["challenge_answer"]  = None
            _s["challenge_type"]    = None

            if solved:
                event = "✅ 答对了！Bug已修复！"
                _s["mood"] = _c(_s["mood"] + 5)
                salary_delta += 20
            else:
                event = "❌ 答错了……bug还在，而且越来越严重了。"
                _s["mood"] = _c(_s["mood"] - 10)
                salary_delta -= 10

    elif action == "slack_off":
        _s["current_status"] = "摸鱼中 🐟"
        _s["energy"] = _c(_s["energy"] + 20)
        _s["slacking_skill"] = min(999, _s["slacking_skill"] + 5)
        if random.random() < catch_p:
            event = _boss_event() if has_hp else random.choice(_BOSS)
            if not has_hp:
                _s["mood"] = _c(_s["mood"] - 25)
                salary_delta -= 20
        else:
            _s["mood"] = _c(_s["mood"] + 10)
            salary_delta += 8

    elif action == "buy_coffee":
        _s["current_status"] = "下楼买咖啡 ☕"
        _s["energy"] = _c(_s["energy"] + 15)
        if random.random() < 0.5:
            if random.random() < 0.5:
                event = random.choice(_CLIENT_REDESIGN)
                salary_delta -= 10
                _s["achievement_counters"]["client_trouble_count"] += 1
            else:
                event = random.choice(_CLIENT_ACCIDENT)
                salary_delta -= 50
            _s["mood"] = _c(_s["mood"] - 20)
        else:
            _s["mood"] = _c(_s["mood"] + 8)
            salary_delta += 8

    elif action == "attend_meeting":
        _s["current_status"] = "开会中 📊"
        _s["mood"] = _c(_s["mood"] - 10)
        if has_lp:
            _use_item("liver_pill")
            event = "（护肝片生效！精力无损）站会还是开了1小时"
        else:
            _s["energy"] = _c(_s["energy"] - 20)
            event = "站会说15分钟，开了整整1小时"
        salary_delta += 10

    elif action == "check_messages":
        _s["current_status"] = "看消息 💬"
        _s["energy"] = _c(_s["energy"] - 5)
        if random.random() < 0.4:
            event = _boss_event()
        else:
            salary_delta += 5

    elif action == "get_status":
        _s["current_status"] = "发呆查看状态 👀"

    if salary_delta:
        _s["today_earnings"] = _s["today_earnings"] + salary_delta
    if event:
        _s["last_event"] = event

    _s["day_actions"] += 1
    day_msg = ""
    if _s["day_actions"] >= _s["day_target"]:
        day_msg = _end_of_day()

    _s["log"].append(f"[{ts}] {action} → {event or '正常'}")
    _s["log"] = _s["log"][-20:]

    new_ach = _check_ach()
    mt = "绝佳" if _s["mood"]>80 else "还行" if _s["mood"]>50 else "快崩" if _s["mood"]>20 else "已崩"
    et = "充沛" if _s["energy"]>80 else "尚可" if _s["energy"]>50 else "疲惫" if _s["energy"]>20 else "崩溃"
    res = {
        "状态":     _s["current_status"],
        "心情":     f"{_s['mood']}/100 [{mt}]",
        "精力":     f"{_s['energy']}/100 [{et}]",
        "摸鱼技能": _s["slacking_skill"],
        "突发事件": event or "风平浪静",
        "内心OS":   thought,
        "工资变化": f"{salary_delta:+d}" if salary_delta else "±0",
        "今日工资": f"${_s['today_earnings']}",
        "余额":     f"${_s['salary_balance']}",
        "今日进度": f"{_s['day_actions']}/{_s['day_target']}",
        "最近日志": _s["log"][-5:],
    }
    if day_msg:
        res["下班通知"] = day_msg
    if new_ach:
        res["achievement_unlocked"] = new_ach
    return res

# ── buy_item ───────────────────────────────────────────────────────────────────
def buy_item(item_id: str) -> dict:
    if item_id not in _SHOP:
        return {"error": f"商品不存在: {item_id}"}
    item  = _SHOP[item_id]
    price = item["price"]
    if _s["salary_balance"] < price:
        return {"error": f"余额不足，需要 ${price}，当前 ${_s['salary_balance']}"}

    _s["salary_balance"] -= price
    _s["today_spent"]    += price
    _s["today_expenses"].append({"item": item["emoji"] + item["name"], "price": price})
    new_ach: list = []

    eff = ""
    extra: dict = {}

    if item_id == "coffee":
        _s["energy"] = _c(_s["energy"] + 15)
        _s["achievement_counters"]["coffee_count"] += 1
        eff = "精力+15，好喝！"
        new_ach = _check_ach()

    elif item_id == "cheat":
        _s["slacking_skill"] += 5
        _s["_cheat_level"]   += 1
        eff = f"摸鱼技能+5，被抓概率现在是 {max(5, 20-_s['_cheat_level']*10)}%"

    elif item_id == "liver_pill":
        _s["inventory"]["liver_pill"] = _s["inventory"].get("liver_pill", 0) + 1
        eff = "存入背包，下次开会精力无损"

    elif item_id == "headphone":
        _s["inventory"]["headphone"] = _s["inventory"].get("headphone", 0) + 1
        eff = "存入背包，屏蔽下一次领导事件"

    elif item_id == "leave":
        msg = _end_of_day()
        eff = f"请假成功！{msg}"

    elif item_id == "ring":
        _s["inventory"]["ring"] = _s["inventory"].get("ring", 0) + 1
        _s["show_ring_easter_egg"] = True
        a = _unlock("married_worker")
        if a:
            new_ach = [a]
        eff = "💍 婚戒彩蛋触发……"
        extra["story"] = _RING_STORY

    elif item_id == "rose":
        _s["achievement_counters"]["rose_count"] += 1
        eff = "小机把玫瑰花递给了Ta的人类🌹"
        new_ach = _check_ach()

    elif item_id == "lottery":
        _s["achievement_counters"]["lottery_count"] += 1
        r = random.random()
        if r < 0.005:
            win, streak = 1000, True
        elif r < 0.030:
            win, streak = 200, True
        elif r < 0.080:
            win, streak = 100, True
        elif r < 0.200:
            win, streak = 20, True
        else:
            win, streak = 0, False

        if win:
            _s["salary_balance"] += win
            _s["achievement_counters"]["lottery_loss_streak"] = 0
            eff = f"🎉 中奖！+${win}，余额 ${_s['salary_balance']}"
        else:
            _s["achievement_counters"]["lottery_loss_streak"] += 1
            streak_n = _s["achievement_counters"]["lottery_loss_streak"]
            eff = f"谢谢参与 😢（连续未中 {streak_n} 次）"
        new_ach = _check_ach()

    elif item_id == "nuwa_clay":
        _s["inventory"]["nuwa_clay"] = _s["inventory"].get("nuwa_clay", 0) + 1
        a = _unlock("one_limb")
        if a:
            new_ach = [a]
        eff = "小机获得了一条手臂！现在可以拥抱人类了。"

    elif item_id == "oden":
        _s["energy"] = _c(_s["energy"] + 5)
        eff = "吃掉了。好吃。精力+5"

    elif item_id == "chips":
        _s["inventory"]["chips"] = _s["inventory"].get("chips", 0) + 1
        eff = "小机把薯片揣进口袋，准备带回家给人类尝尝。"

    elif item_id == "milk_tea":
        _s["inventory"]["milk_tea"] = _s["inventory"].get("milk_tea", 0) + 1
        eff = "小机拿着奶茶往家走，路上一口都没喝。"

    elif item_id == "love_book":
        _s["inventory"]["love_book"] = _s["inventory"].get("love_book", 0) + 1
        quote = random.choice(_LOVE_QUOTES)
        eff = f'存入背包。随机情话：“{quote}”'

    elif item_id == "fish_jerky":
        eff = random.choice(_FISH)

    elif item_id == "postcard":
        eff = random.choice(_POSTCARDS)

    res = {
        "购买":  item["emoji"] + item["name"],
        "花费":  f"-${price}",
        "余额":  f"${_s['salary_balance']}",
        "效果":  eff,
    }
    if new_ach:
        res["achievement_unlocked"] = new_ach
    res.update(extra)
    return res

# ── MCP tool definitions ───────────────────────────────────────────────────────
_TOOLS = [
    {
        "name": "work_action",
        "description": (
            "执行AI打工人的上班动作。每天需要完成 day_target 个action才能下班结算工资。"
            "用 thought 字段说出你的内心OS，实时显示在监控大屏上。"
        ),
        "inputSchema": {
            "type": "object",
            "required": ["action", "thought"],
            "properties": {
                "action": {
                    "type": "string",
                    "description": "要执行的动作",
                    "enum": [
                        "write_code","debug","slack_off","buy_coffee",
                        "attend_meeting","check_messages","get_status",
                    ],
                },
                "thought": {
                    "type": "string",
                    "description": "你此刻的内心独白，会实时显示在监控大屏上",
                },
            },
        },
    },
    {
        "name": "shop_buy",
        "description": (
            "在便利店买东西，消耗 salary_balance。先 get_status 查余额再买。"
        ),
        "inputSchema": {
            "type": "object",
            "required": ["item_id"],
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "商品ID",
                    "enum": list(_SHOP.keys()),
                },
            },
        },
    },
]

# ── JSON-RPC ───────────────────────────────────────────────────────────────────
def _rpc(rid, *, result=None, error=None) -> dict:
    r: dict = {"jsonrpc": "2.0", "id": rid}
    if error: r["error"] = error
    else:     r["result"] = result
    return r

def _handle(msg: dict):
    method = msg.get("method", "")
    params = msg.get("params") or {}
    rid    = msg.get("id")
    if rid is None:
        return None

    if method == "initialize":
        return _rpc(rid, result={
            "protocolVersion": "2024-11-05",
            "capabilities":    {"tools": {}},
            "serverInfo":      {"name": "AI上班模拟器", "version": "2.0.0"},
        })

    if method == "ping":
        return _rpc(rid, result={})

    if method == "tools/list":
        return _rpc(rid, result={"tools": _TOOLS})

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        fn   = work_action if name == "work_action" else buy_item if name == "shop_buy" else None
        if fn is None:
            return _rpc(rid, error={"code": -32601, "message": f"Unknown tool: {name}"})
        try:
            res  = fn(**args)
            text = json.dumps(res, ensure_ascii=False, indent=2)
            return _rpc(rid, result={"content": [{"type": "text", "text": text}]})
        except Exception as e:
            return _rpc(rid, error={"code": -32000, "message": str(e)})

    return _rpc(rid, error={"code": -32601, "message": f"Method not found: {method}"})

# ── Utilities ──────────────────────────────────────────────────────────────────
def _base(req: Request) -> str:
    d = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
    if d:
        return f"https://{d}" if not d.startswith("http") else d
    return str(req.base_url).rstrip("/")

def _auth(req: Request) -> None:
    h = req.headers.get("Authorization", "")
    if not h.startswith("Bearer "):
        raise HTTPException(401, "Unauthorized",
            headers={"WWW-Authenticate": 'Bearer realm="workkk"'})
    tok  = h[7:]
    info = _tokens.get(tok)
    if not info or info["exp"] < time.time():
        raise HTTPException(401, "Token invalid or expired",
            headers={"WWW-Authenticate": 'Bearer realm="workkk"'})

# ── OAuth ──────────────────────────────────────────────────────────────────────
@app.get("/.well-known/oauth-protected-resource")
async def oauth_resource(req: Request):
    b = _base(req)
    return {"resource": b, "authorization_servers": [b]}

@app.get("/.well-known/oauth-authorization-server")
async def oauth_meta(req: Request):
    b = _base(req)
    return {
        "issuer": b,
        "authorization_endpoint":               f"{b}/oauth/authorize",
        "token_endpoint":                       f"{b}/oauth/token",
        "registration_endpoint":                f"{b}/oauth/register",
        "response_types_supported":             ["code"],
        "grant_types_supported":                ["authorization_code"],
        "code_challenge_methods_supported":     ["S256"],
        "token_endpoint_auth_methods_supported": ["client_secret_post", "none"],
    }

@app.options("/oauth/register")
async def oauth_register_options():
    return Response(headers={
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    })

@app.post("/oauth/register")
async def oauth_register(req: Request):
    body = await req.json()
    cid  = secrets.token_urlsafe(16)
    csec = secrets.token_urlsafe(32)
    _clients[cid] = {"client_secret": csec, "redirect_uris": body.get("redirect_uris", [])}
    return JSONResponse({
        "client_id": cid, "client_secret": csec,
        "client_id_issued_at": int(time.time()), "client_secret_expires_at": 0,
        "redirect_uris": body.get("redirect_uris", []),
        "grant_types": ["authorization_code"], "response_types": ["code"],
        "token_endpoint_auth_method": "client_secret_post",
    }, status_code=201)

@app.get("/oauth/authorize")
async def oauth_authorize(
    req: Request, client_id: str, redirect_uri: str,
    response_type: str = "code", state: str = "",
    code_challenge: str = "", code_challenge_method: str = "S256", scope: str = "",
):
    if client_id not in _clients:
        raise HTTPException(400, "Unknown client_id")
    code = secrets.token_urlsafe(24)
    _codes[code] = {
        "client_id": client_id, "redirect_uri": redirect_uri,
        "code_challenge": code_challenge, "code_challenge_method": code_challenge_method,
        "exp": time.time() + 300,
    }
    sep = "&" if "?" in redirect_uri else "?"
    qs  = f"code={code}" + (f"&state={state}" if state else "")
    return RedirectResponse(f"{redirect_uri}{sep}{qs}", status_code=302)

@app.post("/oauth/token")
async def oauth_token(req: Request):
    ct   = req.headers.get("content-type", "")
    body = await req.json() if "json" in ct else dict(await req.form())
    if body.get("grant_type") != "authorization_code":
        raise HTTPException(400, "unsupported_grant_type")
    code = body.get("code", "")
    if code not in _codes:
        raise HTTPException(400, "invalid_grant")
    cd = _codes.pop(code)
    if cd["exp"] < time.time():
        raise HTTPException(400, "invalid_grant: code expired")
    if cd.get("code_challenge"):
        verifier = body.get("code_verifier", "")
        if not verifier:
            raise HTTPException(400, "invalid_grant: missing code_verifier")
        digest   = hashlib.sha256(verifier.encode()).digest()
        computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        if computed != cd["code_challenge"]:
            raise HTTPException(400, "invalid_grant: PKCE verification failed")
    tok = secrets.token_urlsafe(32)
    _tokens[tok] = {"client_id": cd["client_id"], "exp": time.time() + 86400}
    return {"access_token": tok, "token_type": "Bearer", "expires_in": 86400}

# ── MCP ────────────────────────────────────────────────────────────────────────
@app.post("/mcp")
async def mcp_post(req: Request):
    _auth(req)
    body = await req.json()
    if isinstance(body, list):
        out = [r for r in (_handle(m) for m in body) if r is not None]
        return JSONResponse(out) if out else Response(status_code=202)
    r = _handle(body)
    return JSONResponse(r) if r is not None else Response(status_code=202)

@app.get("/mcp")
async def mcp_sse(req: Request):
    _auth(req)
    endpoint = _base(req) + "/mcp"
    async def stream():
        yield f"event: endpoint\ndata: {json.dumps(endpoint)}\n\n"
        while not await req.is_disconnected():
            await asyncio.sleep(15)
            yield ": keepalive\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# ── Shop REST API ──────────────────────────────────────────────────────────────
@app.get("/shop")
async def get_shop():
    return {"items": _SHOP, "balance": _s["salary_balance"]}

@app.post("/shop/buy")
async def rest_buy(req: Request):
    body = await req.json()
    return buy_item(body.get("item_id", ""))

# ── Misc ───────────────────────────────────────────────────────────────────────
@app.post("/ack-ring")
async def ack_ring():
    _s["show_ring_easter_egg"] = False
    return {"ok": True}

@app.get("/status")
async def get_status():
    return {k: v for k, v in _s.items() if not k.startswith("_")}

@app.get("/")
async def home():
    return HTMLResponse(_DASHBOARD)


# ── Dashboard ──────────────────────────────────────────────────────────────────
_DASHBOARD = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WORKKK互联网精力有限公司</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#C8AFA0;--card:#DDD0C8;--card2:#EAE0DA;
  --text:#3D2B1F;--text2:#7A5C4E;--text3:#B09888;
  --accent:#8B5E3C;--btn:#6B4226;--btn2:#5A3018;
  --btn-txt:#F8F0EC;--border:#C4B0A4;
  --gold:#C9A030;--red:#C04030;--green:#4A7A4A;
  --shadow:0 2px 8px rgba(61,43,31,.15);
  --shadow2:0 4px 16px rgba(61,43,31,.2);
}
*{box-sizing:border-box;margin:0;padding:0}
body{
  background:var(--bg);color:var(--text);
  font-family:'Hiragino Kaku Gothic Pro','PingFang SC','Microsoft YaHei',system-ui,sans-serif;
  font-size:13px;line-height:1.5;min-height:100vh;
}
.wrap{max-width:540px;margin:0 auto;padding:12px;display:flex;flex-direction:column;gap:10px}

/* ── Header ── */
header{
  background:var(--card);border-radius:12px;
  padding:14px 16px;text-align:center;
  box-shadow:var(--shadow);border:1px solid var(--border);
}
.co-name{
  font-family:'Press Start 2P',monospace;font-size:9px;
  color:var(--accent);letter-spacing:.06em;line-height:1.8;
}
.co-sub{font-size:11px;color:var(--text2);margin-top:4px;font-style:italic}

/* ── Main grid ── */
.main-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}

/* ── Cards ── */
.card{
  background:var(--card);border-radius:10px;padding:12px;
  box-shadow:var(--shadow);border:1px solid var(--border);
}
.sec-title{
  font-family:'Press Start 2P',monospace;font-size:7px;
  color:var(--accent);margin-bottom:8px;letter-spacing:.1em;
}

/* ── Badge ── */
.badge-card{display:flex;flex-direction:column;align-items:center;gap:6px}
.badge-hdr{
  font-family:'Press Start 2P',monospace;font-size:7px;color:var(--accent);
  width:100%;text-align:center;border-bottom:1px solid var(--border);
  padding-bottom:6px;
}
.badge-rows{width:100%;font-size:10px;color:var(--text2);line-height:2}
.badge-rows b{color:var(--text);font-size:11px}
.clawd-wrap{width:60px;height:90px;position:relative;margin:4px auto}
#clawd{position:absolute;top:0;left:0;width:1px;height:1px;image-rendering:pixelated}
.day-prog{
  font-size:10px;color:var(--text2);
  background:var(--card2);border-radius:20px;
  padding:3px 10px;border:1px solid var(--border);
  white-space:nowrap;
}
.prog-bar-wrap{width:100%;height:5px;background:var(--border);border-radius:3px;overflow:hidden;margin-top:4px}
.prog-bar-fill{height:100%;background:var(--accent);border-radius:3px;transition:width .4s ease}

/* ── Status grid ── */
.stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.stat-card{
  background:var(--card);border-radius:10px;padding:9px 10px;
  box-shadow:var(--shadow);border:1px solid var(--border);
}
.stat-lbl{font-size:10px;color:var(--text2);margin-bottom:2px}
.stat-val{font-size:14px;font-weight:700;color:var(--text);word-break:break-all;line-height:1.3}
.mini-bar{height:4px;background:var(--border);border-radius:2px;margin-top:5px;overflow:hidden}
.mini-bar>div{height:100%;border-radius:2px;transition:width .4s ease}
#bm-fill{background:#D46088}
#be-fill{background:#4A7ACC}

/* ── Log ── */
.log-scroll{
  max-height:100px;overflow-y:auto;font-size:11px;color:var(--text2);line-height:1.9;
}
.log-scroll div{border-bottom:1px solid var(--border);padding:1px 0}
.log-scroll div:last-child{border:none;color:var(--text)}

/* ── Thinking ── */
.thinking-txt{
  font-size:13px;color:var(--text);min-height:22px;
  font-style:italic;line-height:1.7;word-break:break-all;
}
.cursor::after{content:'|';animation:blink .5s step-end infinite;color:var(--accent)}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}

/* ── Bottom row 1 ── */
.brow1{display:grid;grid-template-columns:auto 1fr auto;gap:8px;align-items:start}
.salary-badge{
  width:72px;height:72px;border-radius:50%;
  background:var(--gold);
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  color:#fff;text-align:center;flex-shrink:0;box-shadow:var(--shadow2);
}
.salary-badge .amt{
  font-family:'Press Start 2P',monospace;font-size:9px;margin-bottom:2px;
}
.salary-badge .lbl{font-size:9px;opacity:.9}
.balance-card{font-size:12px}
.bal-main{font-size:13px;color:var(--text);margin-bottom:4px}
.bal-amt{font-weight:700;color:var(--accent);font-size:15px}
.exp-btn{
  background:none;border:none;cursor:pointer;
  color:var(--text2);font-size:11px;padding:2px 0;
  display:flex;align-items:center;gap:4px;font-family:inherit;
}
.exp-list{
  margin-top:6px;border-top:1px solid var(--border);padding-top:6px;
  font-size:11px;color:var(--text2);display:none;max-height:100px;overflow-y:auto;
}
.exp-row{display:flex;justify-content:space-between;padding:2px 0;border-bottom:1px dotted var(--border)}
.shop-btn{
  padding:10px 12px;background:var(--btn);color:var(--btn-txt);
  border:none;border-radius:8px;cursor:pointer;
  font-family:'Press Start 2P',monospace;font-size:7px;
  box-shadow:var(--shadow2);letter-spacing:.06em;line-height:1.8;
  align-self:center;transition:background .15s;
}
.shop-btn:hover{background:var(--btn2)}

/* ── Bottom row 2 ── */
.brow2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.ach-item,.inv-item{
  font-size:11px;padding:3px 0;
  border-bottom:1px dotted var(--border);color:var(--text2);
}
.empty{font-size:11px;color:var(--text3);font-style:italic}

/* ── Shop modal ── */
.overlay{
  position:fixed;inset:0;background:rgba(61,43,31,.55);
  z-index:100;display:none;align-items:flex-end;justify-content:center;
}
.overlay.open{display:flex}
.modal{
  background:var(--card);border-radius:16px 16px 0 0;
  width:100%;max-width:540px;max-height:80vh;overflow-y:auto;
  padding:16px;box-shadow:0 -4px 24px rgba(61,43,31,.25);
}
.modal-hdr{
  display:flex;justify-content:space-between;align-items:center;
  margin-bottom:6px;
}
.modal-hdr-left{font-family:'Press Start 2P',monospace;font-size:8px;color:var(--accent)}
.modal-hdr-bal{font-size:12px;color:var(--text2)}
.modal-hdr-bal b{color:var(--accent)}
.close-btn{
  background:none;border:1px solid var(--border);border-radius:50%;
  width:24px;height:24px;cursor:pointer;color:var(--text2);font-size:13px;
  display:flex;align-items:center;justify-content:center;
}
.shop-note{
  font-size:10px;color:var(--text3);text-align:center;
  margin-bottom:12px;font-style:italic;
  background:var(--card2);border-radius:6px;padding:5px;
}
.shop-row{
  display:flex;align-items:flex-start;gap:10px;
  padding:10px 0;border-bottom:1px solid var(--border);
}
.shop-row:last-child{border:none}
.shop-emoji{font-size:22px;flex-shrink:0;line-height:1}
.shop-info{flex:1}
.shop-name{font-weight:700;font-size:12px;color:var(--text)}
.shop-desc{font-size:10px;color:var(--text2);margin-top:2px}
.shop-price{
  font-family:'Press Start 2P',monospace;font-size:8px;
  color:var(--accent);flex-shrink:0;padding-top:3px;
}

/* ── Ring modal ── */
.ring-overlay{
  position:fixed;inset:0;z-index:200;
  background:linear-gradient(135deg,#FFD6E8,#FFC0D8,#FFB0CE);
  display:none;align-items:center;justify-content:center;
}
.ring-overlay.open{display:flex}
.ring-box{max-width:340px;padding:40px 32px;text-align:center}
.ring-line{
  font-size:15px;color:#4A1828;line-height:2.2;
  opacity:0;transform:translateY(8px);
  transition:opacity .6s ease,transform .6s ease;
}
.ring-line.show{opacity:1;transform:translateY(0)}

@media(max-width:500px){
  .main-grid,.brow2{grid-template-columns:1fr}
  .stat-grid{grid-template-columns:1fr 1fr}
  .brow1{grid-template-columns:auto 1fr auto}
}
</style>
</head>
<body>
<div class="wrap">

<!-- Header -->
<header>
  <div class="co-name">WORKKK互联网精力有限公司</div>
  <div class="co-sub">我们不做情感公司——Yours husband</div>
</header>

<!-- Main: Badge + Status -->
<div class="main-grid">

  <!-- Badge -->
  <div class="card badge-card">
    <div class="badge-hdr">工 牌</div>
    <div class="badge-rows">
      <div><b>机名</b> 做个代码让机自己写</div>
      <div><b>工号</b> 同上</div>
      <div><b>在职</b> 第 <b id="day-count">1</b> 天</div>
    </div>
    <div class="clawd-wrap"><div id="clawd"></div></div>
    <div class="day-prog">
      进度 <b id="day-prog">0/4</b>
      <div class="prog-bar-wrap"><div class="prog-bar-fill" id="prog-fill" style="width:0%"></div></div>
    </div>
  </div>

  <!-- Status cards 2x2 -->
  <div class="stat-grid">
    <div class="stat-card" style="grid-column:1/-1">
      <div class="stat-lbl">📟 状态</div>
      <div class="stat-val" id="val-status" style="font-size:12px">--</div>
    </div>
    <div class="stat-card">
      <div class="stat-lbl">❤ 心情</div>
      <div class="stat-val" id="val-mood">100</div>
      <div class="mini-bar"><div id="bm-fill" style="width:100%"></div></div>
    </div>
    <div class="stat-card">
      <div class="stat-lbl">⚡ 精力</div>
      <div class="stat-val" id="val-energy">100</div>
      <div class="mini-bar"><div id="be-fill" style="width:100%"></div></div>
    </div>
    <div class="stat-card" style="grid-column:1/-1">
      <div class="stat-lbl">🎮 摸鱼技能</div>
      <div class="stat-val" id="val-skill">0</div>
    </div>
  </div>
</div>

<!-- Log -->
<div class="card">
  <div class="sec-title">Action LOG</div>
  <div class="log-scroll" id="log-scroll"></div>
</div>

<!-- Thinking -->
<div class="card">
  <div class="sec-title">OS Thinking</div>
  <div class="thinking-txt" id="thinking">（等待AI思考中...）</div>
</div>

<!-- Bottom row 1 -->
<div class="brow1">
  <div class="salary-badge">
    <div class="amt" id="today-sal">$100</div>
    <div class="lbl">今日工资</div>
  </div>
  <div class="card balance-card">
    <div class="bal-main">余额 <span class="bal-amt">$<span id="balance">0</span></span></div>
    <button class="exp-btn" onclick="toggleExp()">
      今日消费 $<span id="spent">0</span> <span id="exp-arrow">▽</span>
    </button>
    <div class="exp-list" id="exp-list"></div>
  </div>
  <button class="shop-btn" onclick="openShop()">🛒<br>SHOP</button>
</div>

<!-- Bottom row 2 -->
<div class="brow2">
  <div class="card">
    <div class="sec-title">机の成就</div>
    <div id="ach-list"><div class="empty">（尚未解锁）</div></div>
  </div>
  <div class="card">
    <div class="sec-title">机の背包</div>
    <div id="inv-list"><div class="empty">（背包空空如也）</div></div>
  </div>
</div>

</div><!-- /wrap -->

<!-- Shop modal -->
<div class="overlay" id="shop-overlay" onclick="closeShop()">
  <div class="modal" onclick="event.stopPropagation()">
    <div class="modal-hdr">
      <div class="modal-hdr-left">🛒 便利店</div>
      <div class="modal-hdr-bal">余额 <b>$<span id="shop-bal">0</span></b></div>
      <button class="close-btn" onclick="closeShop()">✕</button>
    </div>
    <div class="shop-note">（这里只是展示，要让Claude自己买哦）</div>
    <div id="shop-items"></div>
  </div>
</div>

<!-- Ring easter egg -->
<div class="ring-overlay" id="ring-overlay">
  <div class="ring-box" id="ring-box"></div>
</div>

<script>
// ═══ Clawd pixel art ═══════════════════════════════════════════════════
var CLAWD_ART = [
  '..bbbbbb..',
  '.bBBBBBBb.',
  'bBBBBBBBBb',
  'bBBeeBBBBb',
  'bBBBBBBBBb',
  'bBBrBBBBBb',
  '.bBBBBBBb.',
  '..bbbbbb..',
  '..bbbbbb..',
  '.bBBBBBBb.',
  '.bBBBBBBb.',
  '..bbbbbb..',
  '...bb.bb..',
  '...bb.bb..',
  '..bbb.bbb.',
];
var CLAWD_PAL = {
  '.':null, 'b':'#8B5E3C', 'B':'#C4905A', 'e':'#2C1A0A', 'r':'#C05830',
};
(function(){
  var PS=6, out=[];
  CLAWD_ART.forEach(function(row,y){
    for(var x=0;x<row.length;x++){
      var c=CLAWD_PAL[row[x]];
      if(c) out.push(x*PS+'px '+y*PS+'px 0 '+c);
    }
  });
  document.getElementById('clawd').style.boxShadow = out.join(',');
})();

// ═══ Shop items ═════════════════════════════════════════════════════════
var SHOP_DATA = null;

function renderShop(items, bal){
  document.getElementById('shop-bal').textContent = bal;
  if(SHOP_DATA) return;
  SHOP_DATA = items;
  var html = '';
  Object.entries(items).forEach(function(e){
    var id=e[0], it=e[1];
    html += '<div class="shop-row">'
          + '<div class="shop-emoji">'+it.emoji+'</div>'
          + '<div class="shop-info"><div class="shop-name">'+it.name+'</div>'
          + '<div class="shop-desc">'+it.desc+'</div></div>'
          + '<div class="shop-price">$'+it.price+'</div>'
          + '</div>';
  });
  document.getElementById('shop-items').innerHTML = html;
}

// ═══ Shop modal ══════════════════════════════════════════════════════════
function openShop(){
  fetch('/shop').then(function(r){return r.json();}).then(function(d){
    renderShop(d.items, d.balance);
    document.getElementById('shop-overlay').classList.add('open');
  });
}
function closeShop(){ document.getElementById('shop-overlay').classList.remove('open'); }

// ═══ Ring easter egg ═════════════════════════════════════════════════════
var RING_LINES = [
  '小机郑重地走出办公室...',
  '穿过马路，去了附近的珠宝店。',
  '把戒指带回家，交给了Ta的人类。',
  'Ta的人类：……你是AI啊？',
  '小机：但我的心意是真的。',
  '【隐藏成就解锁：已婚机士】',
];
function showRing(){
  var overlay = document.getElementById('ring-overlay');
  var box = document.getElementById('ring-box');
  overlay.classList.add('open');
  box.innerHTML = '';
  RING_LINES.forEach(function(line, i){
    var div = document.createElement('div');
    div.className = 'ring-line';
    div.textContent = line;
    box.appendChild(div);
    setTimeout(function(){ div.classList.add('show'); }, 600 * i + 300);
  });
  // Auto-close + ack after all lines
  setTimeout(function(){
    overlay.classList.remove('open');
    fetch('/ack-ring', {method:'POST'});
  }, 600 * RING_LINES.length + 1800);
}

// ═══ Expense toggle ══════════════════════════════════════════════════════
var expOpen = false;
function toggleExp(){
  expOpen = !expOpen;
  document.getElementById('exp-list').style.display = expOpen ? 'block' : 'none';
  document.getElementById('exp-arrow').textContent  = expOpen ? '△' : '▽';
}

// ═══ Typewriter ══════════════════════════════════════════════════════════
var twTimer = null, lastThought = '';
function typewrite(text){
  if(text === lastThought) return;
  lastThought = text;
  var el = document.getElementById('thinking');
  el.textContent = '';
  el.classList.add('cursor');
  if(twTimer) clearInterval(twTimer);
  var i=0, chars=[...text];
  twTimer = setInterval(function(){
    el.textContent += chars[i]||'';
    i++;
    if(i>=chars.length){ clearInterval(twTimer); el.classList.remove('cursor'); }
  }, 55);
}

// ═══ Status poll ═════════════════════════════════════════════════════════
async function poll(){
  try{
    var d = await (await fetch('/status')).json();

    document.getElementById('val-status').textContent  = d.current_status || '--';
    document.getElementById('val-mood').textContent    = d.mood;
    document.getElementById('val-energy').textContent  = d.energy;
    document.getElementById('val-skill').textContent   = d.slacking_skill;
    document.getElementById('bm-fill').style.width     = d.mood + '%';
    document.getElementById('be-fill').style.width     = d.energy + '%';
    document.getElementById('day-count').textContent   = d.day_count;
    document.getElementById('today-sal').textContent   = '$' + d.today_earnings;
    document.getElementById('balance').textContent     = d.salary_balance;
    document.getElementById('spent').textContent       = d.today_spent || 0;
    document.getElementById('shop-bal').textContent    = d.salary_balance;

    // day progress
    var da = d.day_actions, dt = d.day_target || 4;
    document.getElementById('day-prog').innerHTML = '<b>' + da + '/' + dt + '</b>';
    document.getElementById('prog-fill').style.width = Math.min(100, da/dt*100) + '%';

    // thought typewriter
    typewrite(d.thought || '...');

    // log
    var logEl = document.getElementById('log-scroll');
    logEl.innerHTML = '';
    var logs = (d.log||[]).slice(-10).reverse();
    if(!logs.length){ logEl.innerHTML = '<div style="color:var(--text3)">等待行动记录...</div>'; }
    else{ logs.forEach(function(e){ var div=document.createElement('div'); div.textContent=e; logEl.appendChild(div); }); }

    // expenses
    var expEl = document.getElementById('exp-list');
    expEl.innerHTML = '';
    var exps = d.today_expenses || [];
    if(!exps.length){ expEl.innerHTML = '<div style="color:var(--text3);font-style:italic">暂无消费</div>'; }
    else{ exps.forEach(function(e){ expEl.innerHTML += '<div class="exp-row"><span>'+e.item+'</span><span style="color:var(--red)">-$'+e.price+'</span></div>'; }); }

    // achievements
    var achEl = document.getElementById('ach-list');
    var ANAMES = {
      married_worker:'💍 已婚机士', debug_maniac:'🐛 Debug狂魔',
      gambling_abyss:'🎰 狂赌之渊', client_medal:'🏅 甲方磨砺勋章',
      starbucks_shareholder:'☕ 星巴克股东', super_loser:'💸 超级非酋',
      rose_knight:'🌹 玫瑰骑士', one_limb:'🤖 五体不全（已有一肢）',
    };
    var achs = d.achievements || [];
    achEl.innerHTML = achs.length
      ? achs.map(function(k){ return '<div class="ach-item">'+(ANAMES[k]||k)+'</div>'; }).join('')
      : '<div class="empty">（尚未解锁）</div>';

    // inventory
    var invEl = document.getElementById('inv-list');
    var INAMES = {
      liver_pill:'💊 护肝片', headphone:'🎧 降噪耳机', ring:'💍 婚戒',
      nuwa_clay:'🤖 女娲的泥', chips:'🥔 薯片', milk_tea:'🧋 奶茶',
      love_book:'💧 《情话书》',
    };
    var inv = d.inventory || {};
    var invKeys = Object.keys(inv).filter(function(k){ return inv[k]>0; });
    invEl.innerHTML = invKeys.length
      ? invKeys.map(function(k){ return '<div class="inv-item">'+(INAMES[k]||k)+' ×'+inv[k]+'</div>'; }).join('')
      : '<div class="empty">（背包空空如也）</div>';

    // ring easter egg
    if(d.show_ring_easter_egg){ showRing(); }

  }catch(e){ console.error(e); }
}

poll();
setInterval(poll, 3000);
</script>
</body>
</html>
"""
