from __future__ import annotations

"""
Vex Beyni — JARVIS tarzı ÇOK-ADIMLI orchestrator.

Tek doğal dil mesajı gelir; beyin bir işi bitirene kadar akıl yürütür:
karar ver -> aracı çalıştır -> sonucu gör -> gerekiyorsa devam et -> bitir.
Böylece "siparişi bul VE tracking'i işle" gibi zincirli işler tek mesajla
yapılabilir. Yeni yetenek = registry'ye yeni araç. Model tam serbest karar
verir; elle intent/allowlist yok.

Ek yetenekler:
- Öğrenen hafıza: her konuşmadan kalıcı bilgiyi kendisi çıkarıp kaydeder.
- Öz-farkındalık: kendi kodunu okuyup "nasıl çalışıyorsun" sorusunu cevaplar.
- Sistem durumu: kendi halini doğal dille özetler.
"""

import json
import threading

from app.core.config import CHAT_HISTORY_LIMIT
from app.core.paths import REMINDERS_PATH, TASKS_PATH
from app.services.gemini_service import generate_text, strip_code_fences
from app.services.text_utils import parse_reminder_time_detailed
from app.storage.entity_store import list_items, upsert_item
from app.storage.memory_store import add_rule_from_message, load_memory

MAX_MESSAGE_CHARS = 2000
MAX_BRAIN_STEPS = 5  # bir mesaj için azami araç-zinciri uzunluğu


# ===========================================================================
# ARAÇ HANDLER'LARI
# ===========================================================================

def _h_create_reminder(args, ctx):
    text = (args.get("text") or args.get("title") or "").strip()
    when = (args.get("when") or "").strip()
    remind_at, understood = parse_reminder_time_detailed(when or text or "")
    notes = ["Vex beyni tarafından oluşturuldu."]
    if not understood:
        notes.append("Zaman ifadesi net anlaşılamadı; 1 saat sonrasına kuruldu.")
    reminder = upsert_item(REMINDERS_PATH, {"title": (text or when or "Hatırlatma")[:100],
        "remind_at": remind_at, "status": "active", "notified": False, "notes": notes}, "hatirlatma")
    msg = f"⏰ Hatırlatma kuruldu: {reminder['title']} — {remind_at.replace('T', ' ')}"
    if not understood:
        msg += " (zamanı net anlayamadım, 1 saat sonrasına koydum)"
    return {"user_message": msg, "reminder": reminder}


def _h_create_task(args, ctx):
    title = (args.get("title") or args.get("text") or "").strip()
    if not title:
        return {"user_message": "Görev başlığı anlayamadım, tekrar söyler misin?"}
    task = upsert_item(TASKS_PATH, {"title": title[:120], "status": "açık",
        "priority": args.get("priority", "normal"), "notes": ["Vex beyni tarafından oluşturuldu."]}, "gorev")
    return {"user_message": f"✅ Görev oluşturuldu: {task['title']}", "task": task}


def _h_save_memory(args, ctx):
    text = (args.get("text") or "").strip()
    if not text:
        return {"user_message": "Neyi hafızaya kaydedeyim, biraz açar mısın?"}
    result = add_rule_from_message("bunu unutma: " + text)
    if result.get("success"):
        return {"user_message": f"🧠 Hafızama kaydettim: {result.get('rule')}", "rule": result.get("rule")}
    return {"user_message": result.get("message", "Kaydedemedim.")}


def _h_analyze_screen(args, ctx):
    from app.services.screen_analysis_service import analyze_screen
    result = analyze_screen(args.get("prompt", "") or "Ekranda ne olduğunu analiz et.")
    if result.get("success"):
        return {"user_message": "🖥️ " + (result.get("analysis") or ""), "observation": result.get("analysis")}
    return {"user_message": "Ekranı analiz edemedim: " + result.get("message", "")}


def _h_analyze_site(args, ctx):
    from app.services.site_service import analyze_site
    url = (args.get("url") or "").strip()
    if not url:
        return {"user_message": "Hangi siteyi analiz edeyim? Adresini yazar mısın?"}
    result = analyze_site(url, args.get("prompt", ""))
    if result.get("success"):
        return {"user_message": "🌐 " + (result.get("analysis") or ""), "observation": result.get("analysis")}
    return {"user_message": "Siteyi analiz edemedim: " + result.get("message", "")}


def _h_find_products(args, ctx):
    from app.services.site_service import find_products
    url = (args.get("url") or "").strip()
    if not url:
        return {"user_message": "Hangi sitede ürün arayayım? Adresini ver."}
    result = find_products(url, args.get("query", ""))
    if result.get("success"):
        return {"user_message": "🔎 Bulunan ürünler:\n" + (result.get("formatted_output") or ""),
                "observation": result.get("formatted_output")}
    return {"user_message": "Ürün araması başarısız: " + result.get("message", "")}


def _h_computer_task(args, ctx):
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
            "computer_task_started": True}


def _h_read_self(args, ctx):
    # Öz-farkındalık: kendi kodunu/dosya yapısını okur. Sonuç modele geri
    # beslenir (observation) ki bir sonraki adımda açıklama yapabilsin.
    from app.services import self_knowledge_service as sk
    path = (args.get("path") or "").strip()
    if path:
        result = sk.read_file(path)
        if result.get("success"):
            return {"user_message": f"📄 {result['path']} okundu.",
                    "observation": f"Dosya: {result['path']}\n\n{result['content'][:8000]}"}
        return {"user_message": result.get("message", "Okunamadı."), "observation": result.get("message")}
    subdir = (args.get("subdir") or "").strip()
    listing = sk.list_files(subdir)
    overview = sk.project_overview()
    obs = f"Proje özeti: {overview.get('summary')}\nServisler: {overview.get('services')}\nRoute'lar: {overview.get('routes')}\n\nDosyalar ({listing.get('count')}):\n" + "\n".join(listing.get("files", [])[:120])
    return {"user_message": "📚 Kendi yapımı inceledim.", "observation": obs}


TOOLS: dict[str, dict] = {
    "create_reminder": {"desc": "Hatırlatma kur.", "args": '{"text": "...", "when": "zaman"}', "handler": _h_create_reminder},
    "create_task": {"desc": "Görev/todo oluştur.", "args": '{"title": "...", "priority": "normal|yüksek"}', "handler": _h_create_task},
    "save_memory": {"desc": "Kalıcı bilgi kaydet ('bunu unutma').", "args": '{"text": "..."}', "handler": _h_save_memory},
    "analyze_screen": {"desc": "Ekrana bakıp yorumla.", "args": '{"prompt": "..."}', "handler": _h_analyze_screen},
    "analyze_site": {"desc": "Web sitesi analiz et (URL varsa).", "args": '{"url": "...", "prompt": "..."}', "handler": _h_analyze_site},
    "find_products": {"desc": "Sitede ürün bul (URL varsa).", "args": '{"url": "...", "query": "..."}', "handler": _h_find_products},
    "computer_task": {"desc": "Bilgisayarı kullan: uygulama aç, tıkla, yaz, Shopify/site içinde işlem yap.", "args": '{"instruction": "..."}', "handler": _h_computer_task},
    "read_self": {"desc": "Kendi kodunu/yapını oku ('nasıl çalışıyorsun', 'neler yapabilirsin', 'X dosyasında ne var').", "args": '{"path": "okunacak dosya (opsiyonel)", "subdir": "listelenecek klasör (opsiyonel)"}', "handler": _h_read_self},
}


# ===========================================================================
# YARDIMCILAR
# ===========================================================================

def _display_name(memory):
    user = memory.get("user") or {}
    return str(user.get("preferred_name") or user.get("name") or "").strip() or "Mert"


def _history_block(history, user_name):
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


def _step_prompt(message, history_block, user_name, rules, scratchpad):
    tool_lines = [f'- {n}: {s["desc"]} args: {s["args"]}' for n, s in TOOLS.items()]
    sp = ""
    if scratchpad:
        sp = "\nŞu ana kadar bu istek için yaptıkların (sırayla):\n" + "\n".join(scratchpad) + "\n"
    return (
        f"Sen Vex'sin — {user_name}'in kişisel AI asistanı (JARVIS gibi). "
        f"{user_name}'in isteğini yerine getirmek için ADIM ADIM düşün. Her adımda "
        f"ya bir araç çağır ya da işi bitirip cevap ver.\n\n"
        f"Araçlar:\n" + "\n".join(tool_lines) + "\n"
        f'- reply: İş bitti ya da araç gerekmiyor; {user_name}\'e nihai cevabı ver.\n\n'
        f"Hafızadaki kurallar:\n{rules}\n"
        f"{sp}\n"
        f"SADECE şu JSON'u döndür (Markdown yok):\n"
        f'{{"tool": "araç_veya_reply", "args": {{...}}, "reply": "reply seçtiysen nihai cevap"}}\n\n'
        f"Kurallar:\n- Bir araç sonucunu gördükten sonra gerekiyorsa BAŞKA bir araç çağırabilirsin (zincir).\n"
        f'- İş tamamlandıysa tool="reply" ve tam, yardımcı Türkçe cevap ver.\n'
        f'- Aynı aracı sonuçsuz tekrar çağırma; işe yaramadıysa reply ile durumu açıkla.\n\n'
        f"{history_block}{user_name}: {message}\n"
        f"JSON:"
    )


def _extract_and_learn(message, reply, user_name):
    # Öğrenen hafıza (fire-and-forget): konuşmadan kalıcı bir olgu çıkar, kaydet.
    try:
        prompt = (
            f"Aşağıdaki kısa diyalogda {user_name} hakkında GELECEKTE işe yarayacak "
            f"KALICI bir olgu (tercih, iş bilgisi, isim, kural) paylaşıldı mı?\n"
            f"Sadece JSON döndür: {{\"fact\": \"tek cümlelik kalıcı olgu ya da boş string\"}}\n"
            f"Geçici/önemsiz şeyler için boş bırak.\n\n"
            f"{user_name}: {message}\nVex: {reply}\nJSON:"
        )
        res = generate_text(prompt)
        if not res.get("success"):
            return
        data = json.loads(strip_code_fences(res.get("text") or "{}"))
        fact = (data.get("fact") or "").strip()
        if fact and len(fact) > 4:
            memory = load_memory()
            if fact not in (memory.get("rules") or []):
                add_rule_from_message("bunu unutma: " + fact)
                print(f"[brain] öğrenildi: {fact}")
    except Exception as exc:
        print(f"[brain] öğrenme atlandı: {exc}")


# ===========================================================================
# ANA GİRİŞ — çok adımlı döngü
# ===========================================================================

def ask(message, history=None):
    message = (message or "").strip()
    if not message:
        return {"success": False, "reply": "Bir şey yazmadın gibi görünüyor."}

    memory = load_memory()
    user_name = _display_name(memory)
    rules_list = memory.get("rules", []) or []
    rules = "\n".join(f"- {r}" for r in rules_list) if rules_list else "- (özel kural yok)"
    hist_block = _history_block(history or [], user_name)

    scratchpad: list[str] = []
    tools_used: list[str] = []
    final_reply = None
    steps_taken = 0

    for step in range(1, MAX_BRAIN_STEPS + 1):
        steps_taken = step
        routed = generate_text(_step_prompt(message, hist_block, user_name, rules, scratchpad))
        if not routed.get("success"):
            return {"success": False, "reply": f"⚠️ Şu an beynim çevrimdışı {user_name}. Teknik: {routed.get('message')}",
                    "error": routed.get("message")}
        try:
            decision = json.loads(strip_code_fences(routed.get("text") or ""))
        except Exception:
            final_reply = (routed.get("text") or "").strip() or f"Tamam {user_name}."
            break

        tool = (decision.get("tool") or "reply").strip()
        args = decision.get("args") or {}
        router_reply = (decision.get("reply") or "").strip()

        if tool == "reply" or tool not in TOOLS:
            final_reply = router_reply or f"Buyur {user_name}?"
            break

        ctx = {"user_name": user_name, "memory": memory, "message": message}
        try:
            result = TOOLS[tool]["handler"](args, ctx)
        except Exception as exc:
            final_reply = f"'{tool}' aracını çalıştırırken hata aldım {user_name}: {exc}"
            break

        tools_used.append(tool)
        user_msg = result.get("user_message", "")
        observation = result.get("observation")

        # Bir gözlem döndüyse (ekran/site/ürün/kod) döngü devam edip modelin
        # sonucu yorumlamasına izin verilir. Aksi halde (aksiyon tamamlandı)
        # araç mesajını nihai cevap kabul et.
        if observation:
            scratchpad.append(f"{step}. {tool} -> {str(observation)[:1200]}")
            continue
        else:
            scratchpad.append(f"{step}. {tool} -> {user_msg}")
            final_reply = user_msg
            break
    else:
        final_reply = final_reply or f"{user_name}, birkaç adım denedim ama net sonuca ulaşamadım."

    if final_reply is None:
        final_reply = f"Tamam {user_name}."

    # Öğrenen hafıza — yanıtı bloklamadan arka planda çalışır.
    threading.Thread(target=_extract_and_learn, args=(message, final_reply, user_name), daemon=True).start()

    return {"success": True, "reply": final_reply, "tools_used": tools_used, "steps": steps_taken}


# ===========================================================================
# SİSTEM DURUMU — Vex kendi halini doğal dille özetler
# ===========================================================================

def system_status():
    from app.services import computer_service, scheduler_service
    memory = load_memory()
    user_name = _display_name(memory)
    reminders = [r for r in list_items(REMINDERS_PATH) if r.get("status") == "active" and not r.get("notified")]
    tasks = [t for t in list_items(TASKS_PATH) if t.get("status") != "tamamlandı"]
    comp = computer_service.status()
    sched = scheduler_service.status()
    notifs = scheduler_service.pending_notifications()["notifications"]

    parts = [f"Merhaba {user_name}, işte durum:"]
    parts.append(f"• Bekleyen hatırlatma: {len(reminders)}")
    parts.append(f"• Açık görev: {len(tasks)}")
    parts.append(f"• Bilgisayar kontrol: {'çalışıyor' if comp.get('running') else 'boşta'}")
    parts.append(f"• Proaktif zamanlayıcı: {'aktif' if sched.get('running') else 'kapalı'}")
    if notifs:
        parts.append(f"• 🔔 {len(notifs)} yeni bildirim (zamanı gelen hatırlatma)")
    parts.append(f"• Elimdeki yetenekler: {', '.join(TOOLS.keys())}")

    return {
        "success": True,
        "summary": "\n".join(parts),
        "data": {
            "pending_reminders": len(reminders),
            "open_tasks": len(tasks),
            "computer_running": comp.get("running"),
            "scheduler_running": sched.get("running"),
            "unseen_notifications": len(notifs),
            "capabilities": list(TOOLS.keys()),
        },
    }
