from __future__ import annotations

"""
Vex Beyni (Brain) — JARVIS tarzı merkezi orchestrator.
Tek doğal dil mesajı gelir; beyin kayıtlı ARAÇLARDAN hangisinin
çalıştırılacağına LLM ile karar verir. Yeni yetenek = yeni araç.
SDK'ya bağımlı native function-calling yerine JSON-router deseni kullanılır.
"""

import json
import threading

from app.core.config import CHAT_HISTORY_LIMIT
from app.core.paths import REMINDERS_PATH, TASKS_PATH
from app.services.gemini_service import generate_text, strip_code_fences
from app.services.text_utils import parse_reminder_time_detailed
from app.storage.entity_store import upsert_item
from app.storage.memory_store import add_rule_from_message, load_memory

MAX_MESSAGE_CHARS = 2000


def _h_create_reminder(args: dict, ctx: dict) -> dict:
    text = (args.get("text") or args.get("title") or "").strip()
    when = (args.get("when") or "").strip()
    remind_at, understood = parse_reminder_time_detailed(when or text or "")
    notes = ["Vex beyni tarafından oluşturuldu."]
    if not understood:
        notes.append("Zaman ifadesi net anlaşılamadı; 1 saat sonrasına kuruldu.")
    reminder = upsert_item(
        REMINDERS_PATH,
        {"title": (text or when or "Hatırlatma")[:100], "remind_at": remind_at,
         "status": "active", "notified": False, "notes": notes},
        "hatirlatma",
    )
    msg = f"⏰ Hatırlatma kuruldu: {reminder['title']} — {remind_at.replace('T', ' ')}"
    if not understood:
        msg += " (zamanı net anlayamadım, 1 saat sonrasına koydum)"
    return {"user_message": msg, "reminder": reminder}


def _h_create_task(args: dict, ctx: dict) -> dict:
    title = (args.get("title") or args.get("text") or "").strip()
    if not title:
        return {"user_message": "Görev başlığı anlayamadım, tekrar söyler misin?"}
    task = upsert_item(
        TASKS_PATH,
        {"title": title[:120], "status": "açık", "priority": args.get("priority", "normal"),
         "notes": ["Vex beyni tarafından oluşturuldu."]},
        "gorev",
    )
    return {"user_message": f"✅ Görev oluşturuldu: {task['title']}", "task": task}


def _h_save_memory(args: dict, ctx: dict) -> dict:
    text = (args.get("text") or "").strip()
    if not text:
        return {"user_message": "Neyi hafızaya kaydedeyim, biraz açar mısın?"}
    result = add_rule_from_message("bunu unutma: " + text)
    if result.get("success"):
        return {"user_message": f"🧠 Hafızama kaydettim: {result.get('rule')}", "rule": result.get("rule")}
    return {"user_message": result.get("message", "Kaydedemedim.")}


def _h_analyze_screen(args: dict, ctx: dict) -> dict:
    from app.services.screen_analysis_service import analyze_screen
    result = analyze_screen(args.get("prompt", "") or "Ekranda ne olduğunu analiz et.")
    if result.get("success"):
        return {"user_message": "🖥️ " + (result.get("analysis") or ""), "analysis": result.get("analysis")}
    return {"user_message": "Ekranı analiz edemedim: " + result.get("message", "")}


def _h_analyze_site(args: dict, ctx: dict) -> dict:
    from app.services.site_service import analyze_site
    url = (args.get("url") or "").strip()
    if not url:
        return {"user_message": "Hangi siteyi analiz edeyim? Adresini yazar mısın?"}
    result = analyze_site(url, args.get("prompt", ""))
    if result.get("success"):
        return {"user_message": "🌐 " + (result.get("analysis") or ""), "analysis": result.get("analysis")}
    return {"user_message": "Siteyi analiz edemedim: " + result.get("message", "")}


def _h_find_products(args: dict, ctx: dict) -> dict:
    from app.services.site_service import find_products
    url = (args.get("url") or "").strip()
    if not url:
        return {"user_message": "Hangi sitede ürün arayayım? Adresini ver."}
    result = find_products(url, args.get("query", ""))
    if result.get("success"):
        return {"user_message": "🔎 Bulunan ürünler:\n" + (result.get("formatted_output") or ""), "products": result.get("products")}
    return {"user_message": "Ürün araması başarısız: " + result.get("message", "")}


def _h_computer_task(args: dict, ctx: dict) -> dict:
    from app.services import computer_service
    instruction = (args.get("instruction") or args.get("task") or "").strip()
    if not instruction:
        return {"user_message": "Bilgisayarda ne yapmamı istiyorsun? Görevi biraz açar mısın?"}
    if computer_service.state.get("running"):
        return {"user_message": "Şu an zaten bir bilgisayar görevi çalışıyor. Önce onu durdurmamı ister misin?"}
    mode = args.get("mode", "autonomous")
    try:
        max_steps = int(args.get("max_steps", 20))
    except Exception:
        max_steps = 20
    threading.Thread(target=computer_service.run_task, args=(instruction, mode, max_steps), daemon=True).start()
    return {"user_message": f"🖱️ Görevi başlattım: \"{instruction}\". Bilgisayar Kontrol sekmesinden takip edebilir, istediğin an ACİL DURDUR ile kesebilirsin.",
            "computer_task_started": True, "instruction": instruction}


TOOLS: dict[str, dict] = {
    "create_reminder": {"desc": "Hatırlatma kur. 'bana X'i hatırlat', 'yarın 15:00'te ...' derse.",
                        "args": '{"text": "ne hatırlatılacak", "when": "zaman ifadesi"}', "handler": _h_create_reminder},
    "create_task": {"desc": "Yeni görev/todo oluştur. 'şunu görev olarak ekle', 'yapılacaklara ekle'.",
                   "args": '{"title": "görev başlığı", "priority": "normal|yüksek"}', "handler": _h_create_task},
    "save_memory": {"desc": "Kalıcı bilgi/kural kaydet. 'bunu unutma', 'hafızana yaz'.",
                   "args": '{"text": "kaydedilecek kalıcı bilgi"}', "handler": _h_save_memory},
    "analyze_screen": {"desc": "Ekran görüntüsü alıp yorumla. 'ekranıma bak', 'bu hata ne'.",
                      "args": '{"prompt": "neye bakılacağı"}', "handler": _h_analyze_screen},
    "analyze_site": {"desc": "Web sitesi analiz et. Mesajda URL varsa ve analiz isteniyorsa.",
                    "args": '{"url": "site adresi", "prompt": "neye bakılacağı"}', "handler": _h_analyze_site},
    "find_products": {"desc": "Bir sitede ürün linkleri bul. Mesajda URL varsa.",
                     "args": '{"url": "site adresi", "query": "aranan ürün"}', "handler": _h_find_products},
    "computer_task": {"desc": "Bilgisayarı kullan: uygulama aç, tıkla, yaz, Shopify/site içinde işlem yap.",
                     "args": '{"instruction": "yapılacak işin tarifi"}', "handler": _h_computer_task},
}


def _display_name(memory: dict) -> str:
    user = memory.get("user") or {}
    return str(user.get("preferred_name") or user.get("name") or "").strip() or "Mert"


def _history_block(history: list, user_name: str) -> str:
    if not history:
        return ""
    lines = []
    for item in history[-CHAT_HISTORY_LIMIT:]:
        sender = (getattr(item, "sender", None) or (item.get("sender") if isinstance(item, dict) else "") or "").strip()
        text = (getattr(item, "text", None) or (item.get("text") if isinstance(item, dict) else "") or "").strip()
        if not text:
            continue
        speaker = user_name if sender in ("Sen", user_name) else "Vex"
        if len(text) > MAX_MESSAGE_CHARS:
            text = text[:MAX_MESSAGE_CHARS] + " …"
        lines.append(f"{speaker}: {text}")
    return ("Önceki konuşma:\n" + "\n".join(lines) + "\n\n") if lines else ""


def _routing_prompt(message: str, history_block: str, user_name: str, rules: str) -> str:
    tool_lines = [f'- {name}: {spec["desc"]} args: {spec["args"]}' for name, spec in TOOLS.items()]
    return (
        f"Sen Vex'sin — {user_name}'in kişisel AI asistanı (JARVIS gibi). "
        f"{user_name}'in doğal dil isteğini anlayıp ya doğrudan cevap ver ya da doğru aracı çalıştır.\n\n"
        f"Araçlar:\n" + "\n".join(tool_lines) + "\n"
        f'- reply: Hiçbiri gerekmiyorsa; sohbet, açıklama, bilgi, soru-cevap.\n\n'
        f"Hafızadaki kurallar:\n{rules}\n\n"
        f"SADECE şu JSON'u döndür (Markdown yok):\n"
        f'{{"tool": "araç_adı_veya_reply", "args": {{...}}, "reply": "kullanıcıya gösterilecek cevap"}}\n\n'
        f"Kurallar:\n- Net aksiyon yoksa tool=\"reply\".\n"
        f'- tool="reply" ise "reply" TAM ve yardımcı Türkçe cevap olsun.\n'
        f'- Araç seçtiysen "reply" kısa onay olsun ({user_name}\'e hitap et).\n'
        f'- Emin değilsen aksiyon uydurma; reply ile sor.\n\n'
        f"{history_block}{user_name}: {message}\nJSON:"
    )


def ask(message: str, history: list | None = None) -> dict:
    message = (message or "").strip()
    if not message:
        return {"success": False, "reply": "Bir şey yazmadın gibi görünüyor."}
    memory = load_memory()
    user_name = _display_name(memory)
    rules_list = memory.get("rules", []) or []
    rules = "\n".join(f"- {r}" for r in rules_list) if rules_list else "- (özel kural yok)"
    hist_block = _history_block(history or [], user_name)
    routed = generate_text(_routing_prompt(message, hist_block, user_name, rules))
    if not routed.get("success"):
        return {"success": False, "reply": f"⚠️ Şu an beynim çevrimdışı {user_name}. Teknik: {routed.get('message')}",
                "error": routed.get("message")}
    try:
        decision = json.loads(strip_code_fences(routed.get("text") or ""))
    except Exception:
        fallback = (routed.get("text") or "").strip() or f"Tamam {user_name}."
        return {"success": True, "reply": fallback, "tool": "reply"}
    tool = (decision.get("tool") or "reply").strip()
    args = decision.get("args") or {}
    router_reply = (decision.get("reply") or "").strip()
    if tool == "reply" or tool not in TOOLS:
        return {"success": True, "reply": router_reply or f"Buyur {user_name}?", "tool": "reply"}
    ctx = {"user_name": user_name, "memory": memory, "message": message}
    try:
        result = TOOLS[tool]["handler"](args, ctx)
    except Exception as exc:
        return {"success": False, "reply": f"'{tool}' aracını çalıştırırken hata aldım {user_name}: {exc}",
                "tool": tool, "error": str(exc)}
    return {"success": True, "reply": result.get("user_message") or router_reply or "Tamam.", "tool": tool, "result": result}
