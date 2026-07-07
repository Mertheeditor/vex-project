from __future__ import annotations

import json
import threading
import time
import uuid
import webbrowser
from datetime import datetime

from app.core.optional_imports import optional_import
from app.core.paths import COMPUTER_LOGS_PATH
from app.services.gemini_service import generate_with_image, strip_code_fences
from app.services.screenshot_service import capture_screenshot
from app.storage.json_store import load_json, save_json

# --- Patch 02: PyAutoGUI failsafe ---
# Mouse ekranın sol-üst köşesine giderse FailSafeException fırlar ve görev
# anında durur. Bu, modelin davranışını KISITLAMAZ; sadece sana fiziksel
# bir acil fren verir. pyautogui yoksa (headless/sunucu) sessizce geçilir.
_pag_for_setup, _pag_setup_err = optional_import("pyautogui")
if _pag_for_setup is not None:
    try:
        _pag_for_setup.FAILSAFE = True
        _pag_for_setup.PAUSE = 0.2
    except Exception:
        pass

# Bir görevin çalışabileceği en uzun süre (saniye). Aşılırsa görev
# otomatik durur (TASK_TIMEOUT). Adım limitine ek bir emniyet.
MAX_TASK_SECONDS = 120

# Vex'in dış görev sırasında kendi kontrol panelini tıklamasını engelleyen
# tek koruma. Otomasyonu kısıtlamaz; yalnızca kendini tıklayıp döngüye
# girmesini önler. Tamamen serbest davranış için patch ile False yapılabilir.
SELF_UI_GUARD = False

OBSERVE_PROMPT = (
    "Bu ekran görüntüsünü detaylıca analiz et. Türkçe olarak ne gördüğünü açıkla. "
    "Butonlar, metinler, form alanları, menüler varsa bunları belirt."
)

_state_lock = threading.Lock()
state = {
    "running": False,
    "stop_requested": False,
    "active_task_id": None,
    "last_intent": "autonomous",
    "last_action": "none",
    "manual_pending_action": None,
}


def add_log(message: str, task_id: str = "") -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    label = f" [{task_id[:6]}]" if task_id else ""
    line = f"[{stamp}]{label} {message}"
    print(line)
    logs_list = load_json(COMPUTER_LOGS_PATH, [])
    logs_list.append(line)
    save_json(COMPUTER_LOGS_PATH, logs_list[-300:])


def status() -> dict:
    with _state_lock:
        snapshot = dict(state)
    result = {
        "success": True,
        "running": snapshot["running"],
        "stopped": snapshot["stop_requested"],
        "active_task_id": snapshot["active_task_id"],
        "last_intent": snapshot["last_intent"],
        "last_action": snapshot["last_action"],
        "manual_pending_action": snapshot["manual_pending_action"],
        "logs": load_json(COMPUTER_LOGS_PATH, [])[-50:],
    }
    if snapshot["running"]:
        result["screenshot"] = capture_screenshot()
    return result


def logs() -> dict:
    return {"success": True, "logs": load_json(COMPUTER_LOGS_PATH, [])}


def stop() -> dict:
    with _state_lock:
        state["stop_requested"] = True
        state["running"] = False
        state["manual_pending_action"] = None
        state["last_action"] = "stopped"
    add_log("Görev kullanıcı tarafından durduruldu.")
    return {"success": True, "message": "Computer-use durduruldu."}


def emergency_stop() -> dict:
    # Büyük kırmızı "ACİL DURDUR" butonunun bağlandığı fonksiyon. Her şeyi
    # zorla sıfırlar: aktif görev, bekleyen manuel adım, tüm bayraklar.
    with _state_lock:
        state["stop_requested"] = True
        state["running"] = False
        state["active_task_id"] = None
        state["manual_pending_action"] = None
        state["last_action"] = "emergency_stop"
    add_log("EMERGENCY_STOP_TRIGGERED: Tüm computer-use işlemleri zorla durduruldu.")
    return {"success": True, "message": "ACİL DURDUR: tüm işlemler durduruldu."}


def plan(instruction: str) -> dict:
    # Artık ayrı bir "planlama" adımı yok; model her adımda ekrana bakıp
    # kendisi karar veriyor. Bu uç nokta geriye dönük uyumluluk için duruyor.
    with _state_lock:
        state["last_intent"] = instruction or "autonomous"
    add_log(f"Plan istendi (model her adımda kendisi karar verecek): {instruction}")
    return {
        "success": True,
        "plan": ["Ekranı gör", "Modelle karar ver", "Aksiyonu uygula", "Bitene kadar tekrarla"],
        "message": "Vex ekrana bakıp adım adım kendisi ilerleyecek.",
    }


def _decision_prompt(instruction: str) -> str:
    # Modele: ham ekrana bak, tek bir sonraki aksiyonu JSON olarak ver.
    # Elle intent/allowlist yok; kararı tamamen model verir.
    guard_note = (
        "\nÖNEMLİ: Ekranda Vex'in kendi kontrol paneli (\"Görevi Başlat\", "
        "\"Durdur\" butonları, sohbet penceresi) görünebilir. Görev açıkça Vex "
        "hakkında değilse bu panele DOKUNMA; sadece ilgili dış pencerelerle "
        "çalış.\n"
        if SELF_UI_GUARD
        else "\n"
    )
    return (
        "Sen Vex'in bilgisayar kontrol zekâsısın. Sana kullanıcının o anki ekran "
        "görüntüsü veriliyor. Görevi tamamlamak için atılacak BİR SONRAKİ tekil "
        "adıma sen karar ver. Elle tanımlanmış kural yok; ekranda ne görüyorsan "
        "ona göre mantıklı davran.\n"
        f'Görev: "{instruction}"\n'
        f"{guard_note}"
        "Yalnızca aşağıdaki JSON'u döndür (başka açıklama, Markdown yazma):\n"
        "{\n"
        '  "thought": "Ekranda ne görüyorsun ve neden bu adımı seçtin (kısa)",\n'
        '  "action": "click | double_click | type_text | press_key | hotkey | scroll | open_url | wait | done | ask_user",\n'
        '  "x": <tıklama X koordinatı, gerekliyse>,\n'
        '  "y": <tıklama Y koordinatı, gerekliyse>,\n'
        '  "text": "<type_text için yazılacak metin ya da ask_user için soru>",\n'
        '  "key": "<press_key için tek tuş, örn enter>",\n'
        '  "keys": ["<hotkey kombinasyonu, örn cmd, space>"],\n'
        '  "url": "<open_url için tam https adresi>",\n'
        '  "clicks": <scroll miktarı, + yukarı - aşağı>,\n'
        '  "seconds": <wait için saniye>\n'
        "}\n"
        "Görev tamamlandıysa action=\"done\". Kullanıcıdan bilgi gerekiyorsa "
        "action=\"ask_user\" ve soruyu text alanına yaz."
    )


def _is_self_ui(action_data: dict, instruction: str) -> bool:
    if not SELF_UI_GUARD:
        return False
    thought = (action_data.get("thought") or "").lower()
    targets_self = any(k in thought for k in ("vex", "dashboard", "görevi başlat", "durdur butonu"))
    task_about_self = "vex" in (instruction or "").lower() or "panel" in (instruction or "").lower()
    return targets_self and not task_about_self


def execute_action(task_id: str, action_data: dict, instruction: str = "") -> dict:
    with _state_lock:
        # Stop yalnızca aktif görev döngüsünü keser; görev bittikten sonra
        # tekil aksiyonu engellemez.
        if state["stop_requested"] and state["running"]:
            return {"success": False, "message": "Stopped by user"}

    action = (action_data.get("action") or "").lower()
    with _state_lock:
        state["last_action"] = action

    if action in ("click", "double_click", "move") and _is_self_ui(action_data, instruction):
        add_log("SELF_UI_GUARD: Vex kendi panelini tıklamayı denedi, adım atlandı.", task_id)
        return {"success": False, "message": "SELF_UI_GUARD_BLOCKED"}

    # open_url: uygulama açmaya gerek kalmadan tarayıcıda adres açar.
    if action == "open_url":
        url = (action_data.get("url") or "").strip()
        if not url:
            return {"success": False, "message": "url gerekli"}
        if not (url.startswith("http://") or url.startswith("https://")):
            add_log(f"Güvensiz URL şeması engellendi: {url}", task_id)
            return {"success": False, "message": "Güvensiz URL şeması"}
        webbrowser.open(url)
        add_log(f"OPEN_URL: {url}", task_id)
        return {"success": True, "action": "open_url", "url": url}

    if action == "wait":
        seconds = float(action_data.get("seconds", 1) or 1)
        time.sleep(max(0.0, min(seconds, 30.0)))
        add_log(f"WAIT: {seconds}s", task_id)
        return {"success": True, "action": "wait", "seconds": seconds}

    if action == "done":
        return {"success": True, "action": "done"}

    # Buradan sonrası fiziksel giriş: pyautogui gerekiyor.
    pag, pag_error = optional_import("pyautogui")
    if pag_error:
        add_log(f"pyautogui kullanılamıyor: {pag_error}", task_id)
        return {"success": False, "message": f"pyautogui kurulu değil veya çalışmıyor: {pag_error}"}

    try:
        if action == "click":
            x, y = action_data.get("x"), action_data.get("y")
            if x is None or y is None:
                return {"success": False, "message": "x/y gerekli"}
            pag.click(x, y)
            add_log(f"CLICK ({x}, {y})", task_id)
            return {"success": True, "action": "click", "x": x, "y": y}

        if action == "double_click":
            x, y = action_data.get("x"), action_data.get("y")
            if x is None or y is None:
                return {"success": False, "message": "x/y gerekli"}
            pag.doubleClick(x, y)
            add_log(f"DOUBLE_CLICK ({x}, {y})", task_id)
            return {"success": True, "action": "double_click", "x": x, "y": y}

        if action == "type_text":
            text = action_data.get("text", "")
            if not text:
                return {"success": False, "message": "text gerekli"}
            pag.typewrite(text, interval=0.02)
            add_log(f"TYPE_TEXT: {text[:40]}...", task_id)
            return {"success": True, "action": "type_text", "text": text}

        if action == "press_key":
            key = action_data.get("key", "")
            if not key:
                return {"success": False, "message": "key gerekli"}
            pag.press(key)
            add_log(f"PRESS_KEY: {key}", task_id)
            return {"success": True, "action": "press_key", "key": key}

        if action == "hotkey":
            keys = action_data.get("keys", [])
            if not keys:
                return {"success": False, "message": "keys gerekli"}
            pag.hotkey(*keys)
            add_log(f"HOTKEY: {'+'.join(keys)}", task_id)
            return {"success": True, "action": "hotkey", "keys": keys}

        if action == "scroll":
            clicks = int(action_data.get("clicks", 3) or 3)
            pag.scroll(clicks)
            add_log(f"SCROLL: {clicks}", task_id)
            return {"success": True, "action": "scroll", "clicks": clicks}

        return {"success": False, "message": f"Bilinmeyen aksiyon: {action}"}
    except Exception as exc:
        # PyAutoGUI FailSafe'i yutma: run_task'ın failsafe yakalayıcısına gitsin.
        if "FailSafe" in type(exc).__name__:
            raise
        add_log(f"Aksiyon hatası: {exc}", task_id)
        return {"success": False, "message": str(exc)}


def execute_direct(action_data: dict) -> dict:
    with _state_lock:
        task_id = state["active_task_id"] or str(uuid.uuid4())[:8]
    return execute_action(task_id, action_data)


def observe() -> dict:
    screenshot = capture_screenshot()
    if not screenshot.get("success"):
        return screenshot
    result = generate_with_image(OBSERVE_PROMPT, screenshot["image_base64"], "image/png")
    if result.get("success"):
        return {"success": True, "analysis": (result.get("text") or "").strip()}
    return {"success": False, "message": result.get("message", "Ekran analizi yapılamadı.")}


def step_approve() -> dict:
    with _state_lock:
        pending = state["manual_pending_action"]
        if not pending:
            return {"success": False, "message": "Onay bekleyen manuel adım yok."}
        state["manual_pending_action"] = None
        task_id = state["active_task_id"] or str(uuid.uuid4())[:8]
    result = execute_action(task_id, pending)
    return {
        "success": True,
        "result": result,
        "message": f"Manuel adım onaylandı ve yürütüldü: {pending.get('action')}",
    }


def step_reject() -> dict:
    with _state_lock:
        if not state["manual_pending_action"]:
            return {"success": False, "message": "Reddedilecek adım yok."}
        state["manual_pending_action"] = None
    add_log("Önerilen adım reddedildi.")
    return {"success": True, "message": "Önerilen adım reddedildi."}


def run_task(instruction: str, mode: str = "autonomous", max_steps: int = 20) -> dict:
    """Saf model-öncelikli döngü: ekranı gör -> modelle karar ver -> uygula.

    mode == "manual_step" ise her adım onaya düşer (frontend'den seçilebilir);
    diğer tüm modlarda ("autonomous", "assisted_fast" ...) aksiyon doğrudan
    uygulanır. Elle intent/URL/allowlist kuralı YOKTUR.
    """
    instruction = (instruction or "").strip()
    if not instruction:
        return {"success": False, "message": "Talimat (instruction) gereklidir."}

    with _state_lock:
        if state["running"]:
            return {
                "success": False,
                "message": "Zaten aktif bir bilgisayar kontrol görevi çalışıyor! Lütfen önce onu durdurun.",
                "active_task_id": state["active_task_id"],
            }
        task_id = str(uuid.uuid4())[:8]
        state["running"] = True
        state["stop_requested"] = False
        state["active_task_id"] = task_id
        state["last_intent"] = "autonomous"
        state["manual_pending_action"] = None

    add_log(f"GÖREV BAŞLATILDI: {instruction} (Mod: {mode})", task_id)

    started_at = time.monotonic()
    try:
        max_steps = max(1, min(int(max_steps or 20), 50))
        for step in range(1, max_steps + 1):
            with _state_lock:
                if state["stop_requested"]:
                    add_log("Görev kullanıcı tarafından durduruldu.", task_id)
                    return {"success": True, "message": "Stopped by user", "steps": step - 1}

            # Süre limiti: bir adım takılsa bile görev sonsuza kadar sürmez.
            if time.monotonic() - started_at > MAX_TASK_SECONDS:
                add_log(f"TASK_TIMEOUT: {MAX_TASK_SECONDS}sn süre sınırı aşıldı, görev durduruldu.", task_id)
                return {"success": True, "message": "TASK_TIMEOUT", "steps": step - 1}

            screenshot = capture_screenshot()
            if not screenshot.get("success"):
                return screenshot

            decision = generate_with_image(_decision_prompt(instruction), screenshot["image_base64"], "image/png")
            if not decision.get("success"):
                add_log(f"Model karar veremedi: {decision.get('message')}", task_id)
                return {"success": False, "message": decision.get("message")}

            try:
                action_data = json.loads(strip_code_fences(decision.get("text") or ""))
            except Exception as exc:
                add_log(f"Model yanıtı geçerli JSON değil: {exc}", task_id)
                return {"success": False, "message": "Model yanıtı geçerli JSON değil", "raw": decision.get("text")}

            action = (action_data.get("action") or "").lower()
            thought = action_data.get("thought", "")
            add_log(f"Adım {step}: {action} - {thought[:70]}", task_id)

            if action == "done":
                add_log("Görev başarıyla tamamlandı.", task_id)
                return {"success": True, "message": "Görev tamamlandı", "steps": step}

            if action == "ask_user":
                question = action_data.get("text") or "Devam etmek için bilgi gerekiyor."
                add_log(f"Vex soruyor: {question}", task_id)
                return {"success": True, "message": "Kullanıcı girdisi gerekiyor", "question": question, "steps": step}

            # manual_step modunda adımı uygulamadan onaya bırak.
            if mode == "manual_step":
                with _state_lock:
                    state["manual_pending_action"] = action_data
                add_log(f"Adım {step} için onay bekleniyor: {action}", task_id)
                return {
                    "success": True,
                    "message": "Manual step approval required",
                    "step": step,
                    "proposed_action": action_data,
                    "screenshot": screenshot,
                }

            # Varsayılan: onay beklemeden doğrudan uygula.
            result = execute_action(task_id, action_data, instruction)
            if not result.get("success"):
                add_log(f"Aksiyon başarısız: {result.get('message')}", task_id)
                return result

            # Ekranın oturması için kısa bekleme.
            time.sleep(0.6)

        add_log(f"Maksimum adım ({max_steps}) sınırına ulaşıldı.", task_id)
        return {"success": True, "message": "Maksimum adıma ulaşıldı", "steps": max_steps}
    except Exception as exc:
        # PyAutoGUI FailSafe (mouse sol-üst köşe) dahil beklenmedik her hata
        # burada yakalanır; görev güvenle sonlanır, state finally'de temizlenir.
        name = type(exc).__name__
        if "FailSafe" in name:
            add_log("FAILSAFE_TRIGGERED: Mouse sol-üst köşeye gitti, görev acilen durduruldu.", task_id)
            return {"success": True, "message": "FAILSAFE_TRIGGERED", "stopped": True}
        add_log(f"Görev beklenmedik hatayla durdu: {exc}", task_id)
        return {"success": False, "message": f"Beklenmedik hata: {exc}"}
    finally:
        with _state_lock:
            state["running"] = False
            state["active_task_id"] = None
