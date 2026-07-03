import { useEffect, useRef, useState } from "react";
import "./App.css";

type Message = {
  id: number;
  sender: "Vex" | "Sen";
  text: string;
};

type MemorySaveResult = {
  success: boolean;
  message: string;
  rule?: string;
};

type MemoryData = {
  user?: {
    name?: string;
    preferred_name?: string;
  };
  assistant?: {
    name?: string;
    role?: string;
    tone?: string;
  };
  project?: {
    name?: string;
    motto?: string;
    cost_principle?: string;
    interface_principle?: string;
    development_machine?: string;
    target_platforms?: string[];
  };
  ai?: {
    primary_model_provider?: string;
    fallback_strategy?: string;
  };
  work_domains?: string[];
  rules?: string[];
};

type ProjectData = {
  id: string;
  name: string;
  type: string;
  status: string;
  description: string;
  main_goals: string[];
  notes: string[];
};

type ProjectFromChatResult = {
  success: boolean;
  message: string;
  project?: ProjectData;
  projects?: ProjectData[];
  source_message?: string;
};

type TaskData = {
  id: string;
  title: string;
  project_id: string;
  status: string;
  priority: string;
  description: string;
  notes: string[];
};

type TaskFromChatResult = {
  success: boolean;
  message: string;
  task?: TaskData;
  tasks?: TaskData[];
  source_message?: string;
};

type ApprovalData = {
  id: string;
  title: string;
  project_id: string;
  action_type: string;
  risk_level: string;
  status: string;
  description: string;
  payload: Record<string, unknown>;
  notes: string[];
};

type ApprovalFromChatResult = {
  success: boolean;
  message: string;
  approval?: ApprovalData;
  approvals?: ApprovalData[];
  source_message?: string;
};

type ReminderData = {
  id: string;
  title: string;
  remind_at: string;
  project_id: string;
  task_id: string;
  status: string;
  notified: boolean;
  notes: string[];
};

type OutputData = {
  id: string;
  title: string;
  project_id: string;
  task_id: string;
  output_type: string;
  content: string;
  status: string;
  notes: string[];
};

type OutputFromChatResult = {
  success: boolean;
  message: string;
  output?: OutputData | null;
  outputs?: OutputData[];
};

type ActiveView = "dashboard" | "chat" | "memory" | "projects" | "tasks" | "approvals" | "outputs" | "reminders" | "evolution" | "computer";
type BackendStatus = "checking" | "online" | "offline";

type WorkspaceSummary = {
  success: boolean;
  active_project?: ProjectData | null;
  active_project_id?: string;
  counts: {
    active_projects: number;
    open_tasks: number;
    high_priority_tasks: number;
    pending_approvals: number;
    outputs?: number;
    preferences?: number;
  };
  active_projects: ProjectData[];
  open_tasks: TaskData[];
  high_priority_tasks: TaskData[];
  pending_approvals: ApprovalData[];
  outputs?: OutputData[];
  suggested_next_step: string;
};

type ActiveProjectResponse = {
  success: boolean;
  message?: string;
  project_id: string;
  project: ProjectData | null;
};

type ActiveTaskResponse = {
  success: boolean;
  message?: string;
  task_id: string;
  task: TaskData | null;
};

type ActiveProjectDetail = {
  success: boolean;
  has_active_project: boolean;
  project_id: string;
  project: ProjectData | null;
  tasks: TaskData[];
  open_tasks: TaskData[];
  high_priority_tasks: TaskData[];
  approvals: ApprovalData[];
  pending_approvals: ApprovalData[];
  outputs: OutputData[];
  counts?: {
    tasks: number;
    open_tasks: number;
    high_priority_tasks: number;
    approvals: number;
    pending_approvals: number;
    outputs?: number;
  };
  suggested_next_step: string;
};

function App() {
  const [activeView, setActiveView] = useState<ActiveView>("dashboard");
  const [input, setInput] = useState("");
  
  // Evrim Ajanı State'leri
  const [evolutionPrompt, setEvolutionPrompt] = useState("");
  const [evolutionLogs, setEvolutionLogs] = useState<string[]>([]);
  const [isEvolutionRunning, setIsEvolutionRunning] = useState(false);
  const [pendingEvolutionActions, setPendingEvolutionActions] = useState<any[]>([]);
  const [isSending, setIsSending] = useState(false);

  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const [backendMessage, setBackendMessage] = useState("Backend kontrol ediliyor...");

  const [workspaceSummary, setWorkspaceSummary] = useState<WorkspaceSummary | null>(null);
  const [isWorkspaceLoading, setIsWorkspaceLoading] = useState(false);

  const [activeProject, setActiveProject] = useState<ProjectData | null>(null);
  const [activeProjectId, setActiveProjectId] = useState("");

  const [activeTask, setActiveTask] = useState<TaskData | null>(null);
  const [activeTaskId, setActiveTaskId] = useState("");

  const [suggestedTaskId, setSuggestedTaskId] = useState("");
  const [activeProjectDetail, setActiveProjectDetail] = useState<ActiveProjectDetail | null>(null);
  const [isActiveProjectDetailLoading, setIsActiveProjectDetailLoading] = useState(false);

  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState("Lokal mikrofon hazır");
  const [voiceReplyEnabled, setVoiceReplyEnabled] = useState(true);
  const [autoSendVoiceEnabled, setAutoSendVoiceEnabled] = useState(true);

  const [memoryData, setMemoryData] = useState<MemoryData | null>(null);
  const [isMemoryLoading, setIsMemoryLoading] = useState(false);

  const [projects, setProjects] = useState<ProjectData[]>([]);
  const [isProjectsLoading, setIsProjectsLoading] = useState(false);

  const [tasks, setTasks] = useState<TaskData[]>([]);
  const [isTasksLoading, setIsTasksLoading] = useState(false);

  const [approvals, setApprovals] = useState<ApprovalData[]>([]);
  const [isApprovalsLoading, setIsApprovalsLoading] = useState(false);

  const [outputs, setOutputs] = useState<OutputData[]>([]);
  const [isOutputsLoading, setIsOutputsLoading] = useState(false);

  const [reminders, setReminders] = useState<ReminderData[]>([]);
  const [isRemindersLoading, setIsRemindersLoading] = useState(false);
  const [showProjectForm, setShowProjectForm] = useState(false);

  const [computerScreenshot, setComputerScreenshot] = useState<string | null>(null);
  const [computerScreenshotTime, setComputerScreenshotTime] = useState<string>("");
  const [computerAnalysis, setComputerAnalysis] = useState<string>("");
  const [computerTaskInput, setComputerTaskInput] = useState("");
  const [computerMode, setComputerMode] = useState("assisted_fast");
  const [computerLastResult, setComputerLastResult] = useState<any>(null);
  const [computerLogs, setComputerLogs] = useState<string[]>([]);
  const [computerUseRunning, setComputerUseRunning] = useState(false);
  const [currentComputerTaskId, setCurrentComputerTaskId] = useState<string | null>(null);
  const [lastComputerIntent, setLastComputerIntent] = useState<string>("unknown");
  const [lastComputerAction, setLastComputerAction] = useState<string>("none");
  const [manualPendingAction, setManualPendingAction] = useState<any>(null);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [projectType, setProjectType] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [projectGoals, setProjectGoals] = useState("");
  const [projectNotes, setProjectNotes] = useState("");

  const isBusyRef = useRef(false);
  const isRecordingRef = useRef(false);
  const isTranscribingRef = useRef(false);
  const isSendingRef = useRef(false);
  const isCheckingBackendRef = useRef(false);

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      sender: "Vex",
      text: "Hazırım Mert. Artık mikrofonu başlatıp durdurarak konuşmanı dinleyebiliyorum, backend durumunu takip ediyorum ve sohbetten proje oluşturabiliyorum.",
    },
  ]);
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    checkBackendHealth({ force: true });

    // VEX_REMINDER_INTERVAL_START
    checkDueReminders();
    const vexReminderInterval = window.setInterval(() => {
      checkDueReminders();
    }, 15000);
    // VEX_REMINDER_INTERVAL_END

    loadActiveProject();
    loadActiveTask();
    loadActiveProjectDetail();
    loadWorkspaceSummary();

    const backendHealthInterval = window.setInterval(() => {
      checkBackendHealth();
    }, 7000);

    return () => {
      window.clearInterval(backendHealthInterval);
      window.clearInterval(vexReminderInterval);
    };
  }, []);

  // Evrim status ve log izleme
  useEffect(() => {
    let intervalId: number | undefined;

    if (activeView === "evolution" || isEvolutionRunning) {
      loadEvolutionLogs();
      checkEvolutionStatus();
      loadPendingEvolutionActions();

      intervalId = window.setInterval(() => {
        loadEvolutionLogs();
        checkEvolutionStatus();
        loadPendingEvolutionActions();
      }, 1000);
    }

    return () => {
      if (intervalId !== undefined) {
        window.clearInterval(intervalId);
      }
    };
  }, [activeView, isEvolutionRunning]);

  // Bilgisayar Kontrol durum ve log izleme
  useEffect(() => {
    let intervalId: number;
    if (activeView === "computer" || computerUseRunning) {
      // Initial load
      pollComputerStatus();
      loadComputerLogs();

      // Polling
      intervalId = window.setInterval(() => {
        pollComputerStatus();
        loadComputerLogs();
      }, 1000);
    }
    return () => {
      if (intervalId) {
        window.clearInterval(intervalId);
      }
    };
  }, [activeView, computerUseRunning]);

  async function pollComputerStatus() {
    try {
      const response = await fetch("http://127.0.0.1:8000/computer/status");
      if (response.ok) {
        const data = await response.json();
        setComputerUseRunning(data.running);
        setCurrentComputerTaskId(data.active_task_id);
        setLastComputerIntent(data.last_intent);
        setLastComputerAction(data.last_action);
        setManualPendingAction(data.manual_pending_action);
        
        // Also update screenshot if running
        if (data.screenshot && data.screenshot.success) {
          setComputerScreenshot(data.screenshot.image_base64);
          setComputerScreenshotTime(data.screenshot.timestamp);
        }
      }
    } catch (e) {
      console.error("Computer status hatası:", e);
    }
  }


  async function loadComputerLogs() {
    try {
      const response = await fetch("http://127.0.0.1:8000/computer/logs");
      if (response.ok) {
        const data = await response.json();
        setComputerLogs(data.logs || []);
      }
    } catch (e) {
      console.error("Computer use logları alınamadı:", e);
    }
  }

  function setBusyState(value: boolean) {
    isBusyRef.current = value;
  }


  async function loadEvolutionLogs() {
    try {
      const response = await fetch("http://127.0.0.1:8000/evolution/logs");
      if (response.ok) {
        const data = await response.json();
        setEvolutionLogs(data.logs || []);
      }
    } catch (e) {
      console.error("Evrim logları alınamadı:", e);
    }
  }

  async function checkEvolutionStatus() {
    try {
      const response = await fetch("http://127.0.0.1:8000/evolution/status");
      if (response.ok) {
        const data = await response.json();
        setIsEvolutionRunning(Boolean(data.running));
      }
    } catch (e) {
      console.error("Evrim durumu alınamadı:", e);
    }
  }

  async function loadPendingEvolutionActions() {
    try {
      const response = await fetch("http://127.0.0.1:8000/evolution/pending-actions");
      if (response.ok) {
        const data = await response.json();
        setPendingEvolutionActions(data.pending_actions || []);
      }
    } catch (e) {
      console.error("Bekleyen evrim işlemleri alınamadı:", e);
    }
  }

  async function approveEvolutionAction(actionId: string) {
    try {
      const response = await fetch(`http://127.0.0.1:8000/evolution/approve-action/${actionId}`, {
        method: "POST",
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        alert(data.message || "İşlem onaylanamadı.");
        return;
      }

      await loadPendingEvolutionActions();
      await loadEvolutionLogs();
      await checkEvolutionStatus();
    } catch (e) {
      console.error("İşlem onaylama hatası:", e);
      alert("İşlem onaylanamadı. Backend çalışıyor mu kontrol edelim.");
    }
  }

  async function rejectEvolutionAction(actionId: string) {
    try {
      const response = await fetch(`http://127.0.0.1:8000/evolution/reject-action/${actionId}`, {
        method: "POST",
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        alert(data.message || "İşlem reddedilemedi.");
        return;
      }

      await loadPendingEvolutionActions();
      await loadEvolutionLogs();
      await checkEvolutionStatus();
    } catch (e) {
      console.error("İşlem reddetme hatası:", e);
      alert("İşlem reddedilemedi. Backend çalışıyor mu kontrol edelim.");
    }
  }

  async function startEvolution() {
    if (!evolutionPrompt.trim() || isEvolutionRunning) {
      return;
    }

    setIsEvolutionRunning(true);
    setEvolutionLogs([]);

    try {
      await fetch("http://127.0.0.1:8000/evolution/reset-logs", { method: "POST" });

      const response = await fetch("http://127.0.0.1:8000/evolution/prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: evolutionPrompt }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        alert(data.message || "Evrim başlatılamadı.");
        setIsEvolutionRunning(false);
        return;
      }

      setEvolutionPrompt("");
      await loadEvolutionLogs();
      await loadPendingEvolutionActions();
    } catch (e) {
      console.error("Evrim hatası:", e);
      setIsEvolutionRunning(false);
      alert("Evrim başlatılamadı. Backend çalışıyor mu kontrol edelim.");
    }
  }

  function updateRecording(value: boolean) {
    isRecordingRef.current = value;
    setIsRecording(value);
  }

  function updateTranscribing(value: boolean) {
    isTranscribingRef.current = value;
    setIsTranscribing(value);
  }

  function updateSending(value: boolean) {
    isSendingRef.current = value;
    setIsSending(value);
  }

  async function checkBackendHealth(options?: { force?: boolean }) {
    if (isCheckingBackendRef.current && !options?.force) {
      return;
    }

    isCheckingBackendRef.current = true;

    if (backendStatus !== "online") {
      setBackendStatus("checking");
    }

    setBackendMessage("Backend bağlantısı kontrol ediliyor...");

    try {
      let response = await fetch("http://127.0.0.1:8000/health", {
        method: "GET",
        cache: "no-store",
      });

      if (!response.ok) {
        response = await fetch("http://127.0.0.1:8000/", {
          method: "GET",
          cache: "no-store",
        });
      }

      if (!response.ok) {
        throw new Error(`Backend cevap verdi ama sağlıklı değil: ${response.status}`);
      }

      setBackendStatus("online");
      setBackendMessage("Backend bağlı ve çalışıyor.");
    } catch (error) {
      console.error("Backend health check hatası:", error);
      setBackendStatus("offline");
      setBackendMessage("Backend kapalı veya ulaşılamıyor.");
    } finally {
      isCheckingBackendRef.current = false;
    }
  }

  function getBackendLabel() {
    if (backendStatus === "online") return "Backend: Bağlı";
    if (backendStatus === "offline") return "Backend: Kapalı";
    return "Backend: Kontrol Ediliyor";
  }

  function getActiveViewLabel() {
    if (activeView === "dashboard") return "Dashboard";
    if (activeView === "chat") return "Genel sohbet";
    if (activeView === "memory") return "Hafıza merkezi";
    if (activeView === "projects") return "Proje merkezi";
    if (activeView === "tasks") return "Görev merkezi";
    if (activeView === "approvals") return "Onay Merkezi";
    if (activeView === "outputs") return "Çıktılar";
    if (activeView === "reminders") return "Hatırlatmalar";
    if (activeView === "evolution") return "Evrim Merkezi";
    if (activeView === "computer") return "Bilgisayar Kontrol";
    return "Vex";
  }

  function slugify(text: string) {
    return text
      .toLocaleLowerCase("tr-TR")
      .replace(/ı/g, "i")
      .replace(/ğ/g, "g")
      .replace(/ü/g, "u")
      .replace(/ş/g, "s")
      .replace(/ö/g, "o")
      .replace(/ç/g, "c")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function splitLines(text: string) {
    return text
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
  }

  function cleanTranscribedText(text: string) {
    return text
      .replace(/\bveks\b/gi, "Vex")
      .replace(/\bvekiz\b/gi, "Vex")
      .replace(/\bvekiş\b/gi, "Vex")
      .replace(/\bvexx\b/gi, "Vex")
      .trim();
  }

  function cleanTextForSpeech(text: string) {
    return text
      .replace(/\*\*/g, "")
      .replace(/```[\s\S]*?```/g, "Kod bloğunu ekranda gösteriyorum.")
      .replace(/`/g, "")
      .replace(/https?:\/\/\S+/g, "bir bağlantı")
      .trim();
  }



  function speakText(text: string) {
    if (!voiceReplyEnabled) {
      return;
    }

    if (!("speechSynthesis" in window)) {
      setVoiceStatus("Sesli okuma bu ortamda desteklenmiyor.");
      return;
    }

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(cleanTextForSpeech(text));
    utterance.lang = "tr-TR";
    utterance.rate = 1;
    utterance.pitch = 1;

    const voices = window.speechSynthesis.getVoices();
    const turkishVoice =
      voices.find((voice) => voice.lang.toLowerCase().startsWith("tr")) ??
      voices.find((voice) => voice.lang.toLowerCase().includes("tr")) ??
      null;

    if (turkishVoice) {
      utterance.voice = turkishVoice;
    }

    utterance.onstart = () => {
      setVoiceStatus("Vex sesli cevap veriyor...");
    };

    utterance.onend = () => {
      setVoiceStatus("Sesli cevap tamamlandı.");
    };

    utterance.onerror = () => {
      setVoiceStatus("Sesli okuma sırasında hata oluştu.");
    };

    window.speechSynthesis.speak(utterance);
  }

  function stopSpeaking() {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      setVoiceStatus("Sesli cevap durduruldu.");
    }
  }

  function shouldSaveToMemory(text: string) {
    const lowerText = text.toLocaleLowerCase("tr-TR");

    return (
      lowerText.includes("hafızana yaz") ||
      lowerText.includes("hafızaya yaz") ||
      lowerText.includes("bunu unutma") ||
      lowerText.includes("unutma")
    );
  }

  function extractFirstUrl(text: string) {
    const match = text.match(/https?:\/\/[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s]*/);

    if (!match) return "";

    return match[0].replace(/[),.;]+$/, "");
  }

  function shouldCreateShopifyContentFromChat(text: string) {
    const lowerText = text.toLocaleLowerCase("tr-TR");

    return (
      lowerText.includes("shopify") &&
      (
        lowerText.includes("ürün") ||
        lowerText.includes("urun") ||
        lowerText.includes("başlık") ||
        lowerText.includes("baslik") ||
        lowerText.includes("açıklama") ||
        lowerText.includes("aciklama") ||
        lowerText.includes("seo") ||
        lowerText.includes("meta") ||
        lowerText.includes("içerik") ||
        lowerText.includes("icerik") ||
        lowerText.includes("hazırla") ||
        lowerText.includes("hazirla")
      )
    );
  }

  function shouldFindProductsOnSiteFromChat(text: string) {
    const lowerText = text.toLocaleLowerCase("tr-TR");
    const url = extractFirstUrl(text);

    if (!url) return false;

    return (
      lowerText.includes("ürünü bul") ||
      lowerText.includes("urunu bul") ||
      lowerText.includes("ürününü bul") ||
      lowerText.includes("urununu bul") ||
      lowerText.includes("ürün bul") ||
      lowerText.includes("urun bul") ||
      lowerText.includes("bulabilir misin") ||
      lowerText.includes("bulur musun") ||
      lowerText.includes("bul bana") ||
      lowerText.includes("sitede bul") ||
      lowerText.includes("sitede ara") ||
      lowerText.includes("bu sitede") ||
      lowerText.includes("şu sitede") ||
      lowerText.includes("su sitede") ||
      lowerText.includes("sitesinde") ||
      lowerText.includes("çekçe sitede") ||
      lowerText.includes("cekce sitede") ||
      lowerText.includes("almanca sitede")
    );
  }

  function shouldAnalyzeSiteFromChat(text: string) {
    const lowerText = text.toLocaleLowerCase("tr-TR");
    const url = extractFirstUrl(text);

    if (!url) return false;

    return (
      lowerText.includes("siteyi analiz et") ||
      lowerText.includes("url analiz") ||
      lowerText.includes("seo analiz") ||
      lowerText.includes("seo'yu analiz") ||
      lowerText.includes("bu siteyi incele") ||
      lowerText.includes("bu siteyi analiz et") ||
      lowerText.includes("tasarımını analiz et") ||
      lowerText.includes("tasarimini analiz et") ||
      lowerText.includes("site analizi")
    );
  }

  function shouldCreateReminderFromChat(text: string) {
    const lowerText = text.toLocaleLowerCase("tr-TR");

    return (
      lowerText.includes("hatırlat") ||
      lowerText.includes("hatirlat") ||
      lowerText.includes("beni uyar") ||
      lowerText.includes("alarm kur") ||
      lowerText.includes("dakika sonra") ||
      lowerText.includes("saat sonra")
    );
  }

  function shouldAnalyzeScreenFromChat(text: string) {
    const lowerText = text.toLocaleLowerCase("tr-TR");

    return (
      lowerText.includes("ekran") ||
      lowerText.includes("screen") ||
      lowerText.includes("görüntü") ||
      lowerText.includes("goruntu") ||
      lowerText.includes("bu hatayı") ||
      lowerText.includes("bu hatayi") ||
      lowerText.includes("bu tasarımı") ||
      lowerText.includes("bu tasarimi")
    );
  }

  function shouldCreateProjectFromChat(text: string) {
    const lowerText = text.toLocaleLowerCase("tr-TR");

    const hasProjectWord = lowerText.includes("proje");
    const hasCreateIntent =
      lowerText.includes("oluştur") ||
      lowerText.includes("olustur") ||
      lowerText.includes("aç") ||
      lowerText.includes("ac") ||
      lowerText.includes("ekle") ||
      lowerText.includes("kaydet");

    return hasProjectWord && hasCreateIntent;
  }

  function shouldCreateTaskFromChat(text: string) {
    const lowerText = text.toLocaleLowerCase("tr-TR");

    const hasTaskWord =
      lowerText.includes("görev") ||
      lowerText.includes("gorev") ||
      lowerText.includes("task") ||
      lowerText.includes("yapılacak") ||
      lowerText.includes("yapilacak");

    const hasCreateIntent =
      lowerText.includes("ekle") ||
      lowerText.includes("oluştur") ||
      lowerText.includes("olustur") ||
      lowerText.includes("kaydet") ||
      lowerText.includes("not al");

    return hasTaskWord && hasCreateIntent;
  }

  function shouldSaveOutputFromChat(text: string) {
    const lowerText = text.toLocaleLowerCase("tr-TR");

    return (
      lowerText.includes("bunu kaydet") ||
      lowerText.includes("çıktı olarak kaydet") ||
      lowerText.includes("cikti olarak kaydet") ||
      lowerText.includes("taslak olarak kaydet") ||
      lowerText.includes("proje çıktısı yap") ||
      lowerText.includes("proje ciktisi yap")
    );
  }

  function shouldCompleteActiveTaskFromChat(text: string) {
    const lowerText = text.toLocaleLowerCase("tr-TR");

    return (
      lowerText.includes("bu görevi kapat") ||
      lowerText.includes("bu gorevi kapat") ||
      lowerText.includes("görevi kapat") ||
      lowerText.includes("gorevi kapat") ||
      lowerText.includes("görevi tamamla") ||
      lowerText.includes("gorevi tamamla") ||
      lowerText.includes("tamamlandı olarak işaretle") ||
      lowerText.includes("tamamlandi olarak isaretle") ||
      lowerText.includes("evet kapat") ||
      lowerText.includes("tamam kapat") ||
      lowerText.includes("kapatabilirsin") ||
      lowerText.includes("evet görevi kapat") ||
      lowerText.includes("evet gorevi kapat")
    );
  }

  function shouldActivateSuggestedTaskFromChat(text: string) {
    const lowerText = text.toLocaleLowerCase("tr-TR");

    return (
      lowerText.includes("evet onu aktif yap") ||
      lowerText.includes("onu aktif yap") ||
      lowerText.includes("sıradaki görevi aktif yap") ||
      lowerText.includes("siradaki gorevi aktif yap") ||
      lowerText.includes("bunu aktif görev yap") ||
      lowerText.includes("bunu aktif gorev yap") ||
      lowerText.includes("o görevden devam edelim") ||
      lowerText.includes("o gorevden devam edelim")
    );
  }

  function shouldCreateApprovalFromChat(text: string) {
    const lowerText = text.toLocaleLowerCase("tr-TR");

    const riskyWords = [
      "canlıya al",
      "canliya al",
      "yayına al",
      "yayina al",
      "yayınla",
      "yayinla",
      "shopify’da",
      "shopify'da",
      "shopifyda",
      "ürünü güncelle",
      "urunu guncelle",
      "fiyat değiştir",
      "fiyat degistir",
      "sil",
      "mail gönder",
      "mail gonder",
      "e-posta gönder",
      "email gönder",
      "dosya sil"
    ];

    return riskyWords.some((word) => lowerText.includes(word));
  }

  async function saveMessageToMemory(text: string): Promise<MemorySaveResult | null> {
    const response = await fetch("http://127.0.0.1:8000/memory/rules/from-chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: text,
      }),
    });

    if (!response.ok) {
      throw new Error("Hafıza endpoint'i cevap vermedi.");
    }

    return response.json();
  }

  async function createShopifyContentFromChat(text: string) {
    const response = await fetch("http://127.0.0.1:8000/shopify/content-from-chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: text,
        project_id: activeProjectId,
        task_id: activeTaskId,
        language: "English",
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Shopify içerik endpoint hatası: HTTP ${response.status}: ${errorText}`);
    }

    return response.json();
  }

  function buildShopifyContentReply(result: any) {
    if (!result.success) {
      return result.message || "Shopify içeriğini hazırlayamadım Mert.";
    }

    if (result.formatted_output) {
      return result.formatted_output;
    }

    return "Shopify içerik paketi hazırlandı ama formatlı çıktı boş döndü.";
  }

  async function findProductsOnSiteFromChat(text: string) {
    const url = extractFirstUrl(text);

    const controller = new AbortController();
    // 90 seconds timeout because backend crawls multiple pages and might take a long time
    const timeoutId = setTimeout(() => controller.abort(), 90000);

    try {
      const response = await fetch("http://127.0.0.1:8000/site/find-products", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url,
          query: text,
          language: "Turkish",
          max_pages: 15,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Site ürün bulma endpoint hatası: HTTP ${response.status}: ${errorText}`);
      }

      return response.json();
    } catch (error: unknown) {
      clearTimeout(timeoutId);
      if (error instanceof DOMException && error.name === "AbortError") {
        throw new Error("İstek zaman aşımına uğradı. Site çok yavaş yanıt verdi veya bot koruması kullanıyor olabilir.");
      }
      throw error;
    }
  }

  function buildProductFinderReply(result: any) {
    if (!result.success) {
      return result.message || "Sitede ürün araması yapamadım Mert.";
    }

    return result.formatted_output || "Ürün araması tamamlandı ama formatlı çıktı boş döndü.";
  }

  async function analyzeSiteFromChat(text: string) {
    const url = extractFirstUrl(text);

    const response = await fetch("http://127.0.0.1:8000/site/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url,
        prompt: text,
      }),
    });

    if (!response.ok) {
      throw new Error("Site analiz endpoint'i cevap vermedi.");
    }

    return response.json();
  }

  function buildSiteAnalysisReply(result: { success: boolean; analysis?: string; message?: string }) {
    if (!result.success) {
      return result.message || "Siteyi analiz edemedim Mert. URL doğru mu kontrol edelim.";
    }

    return `Site Analizi:\n\n${result.analysis || "Siteyi analiz ettim ama anlamlı bir çıktı oluşmadı."}`;
  }

  async function analyzeScreenFromChat(text: string) {
    const response = await fetch("http://127.0.0.1:8000/screen/capture-and-analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        prompt: text,
      }),
    });

    if (!response.ok) {
      throw new Error("Ekran analiz endpoint'i cevap vermedi.");
    }

    return response.json();
  }

  function buildScreenAnalysisReply(result: { success: boolean; analysis?: string; message?: string }) {
    if (!result.success) {
      return result.message || "Ekranı analiz edemedim Mert. macOS ekran kaydı iznini kontrol edelim.";
    }

    return `Ekran Analizi:\n\n${result.analysis || "Ekranı analiz ettim ama anlamlı bir çıktı oluşmadı."}`;
  }

  async function createProjectFromChat(text: string): Promise<ProjectFromChatResult> {
    const response = await fetch("http://127.0.0.1:8000/projects/from-chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: text,
      }),
    });

    if (!response.ok) {
      throw new Error("Sohbetten proje oluşturma endpoint'i cevap vermedi.");
    }

    return response.json();
  }

  async function createTaskFromChat(text: string): Promise<TaskFromChatResult> {
    const response = await fetch("http://127.0.0.1:8000/tasks/from-chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: text,
        project_id: activeProjectId,
      }),
    });

    if (!response.ok) {
      throw new Error("Sohbetten görev oluşturma endpoint'i cevap vermedi.");
    }

    return response.json();
  }

  async function createReminderFromChat(text: string) {
    const response = await fetch("http://127.0.0.1:8000/reminders/from-chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: text,
        project_id: activeProjectId,
        task_id: activeTaskId,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Hatırlatma endpoint hatası: HTTP ${response.status}: ${errorText}`);
    }

    return response.json();
  }

  function buildReminderCreatedReply(result: any) {
    if (!result.success) {
      return result.message || "Hatırlatmayı oluşturamadım Mert.";
    }

    const reminder = result.reminder;

    if (!reminder) {
      return "Hatırlatmayı oluşturdum ama detay boş döndü Mert.";
    }

    return `Tamam Mert, hatırlatmayı kurdum.

Başlık: ${reminder.title}
Zaman: ${reminder.remind_at}
Proje: ${reminder.project_id || "Genel"}
Görev: ${reminder.task_id || "Bağlı görev yok"}

Zamanı geldiğinde Vex açık olduğu sürece seni uyaracağım.`;
  }

  async function createApprovalFromChat(text: string): Promise<ApprovalFromChatResult> {
    const response = await fetch("http://127.0.0.1:8000/approvals/from-chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: text,
        project_id: activeProjectId,
      }),
    });

    if (!response.ok) {
      throw new Error("Sohbetten onay isteği oluşturma endpoint'i cevap vermedi.");
    }

    return response.json();
  }

  function buildProjectCreatedReply(result: ProjectFromChatResult) {
    if (!result.success) {
      return result.message || "Projeyi oluşturamadım Mert. Backend tarafını kontrol edelim.";
    }

    const project = result.project;

    if (!project) {
      return "Projeyi oluşturdum Mert ama proje detayları boş döndü. Projeler panelinden kontrol edelim.";
    }

    const goals =
      project.main_goals?.length > 0
        ? project.main_goals.map((goal) => `- ${goal}`).join("\n")
        : "- İlk hedefleri sonra netleştireceğiz.";

    return `Tamam Mert, projeyi oluşturdum: ${project.name}

Tip: ${project.type}
Durum: ${project.status}

Açıklama:
${project.description || "Açıklama daha sonra netleştirilecek."}

Ana hedefler:
${goals}

Projeler panelinden de görebilirsin.`;
  }

  function buildTaskCreatedReply(result: TaskFromChatResult) {
    if (!result.success) {
      return result.message || "Görevi oluşturamadım Mert. Backend tarafını kontrol edelim.";
    }

    const task = result.task;

    if (!task) {
      return "Görevi oluşturdum Mert ama görev detayları boş döndü. Görevler panelinden kontrol edelim.";
    }

    return `Tamam Mert, görevi ekledim: ${task.title}

Proje: ${task.project_id || "Genel"}
Durum: ${task.status}
Öncelik: ${task.priority}

Açıklama:
${task.description || "Açıklama daha sonra netleştirilecek."}

Görevler panelinden takip edebilirsin.`;
  }

  function buildApprovalCreatedReply(result: ApprovalFromChatResult) {
    if (!result.success) {
      return result.message || "Onay isteği oluşturamadım Mert. Backend tarafını kontrol edelim.";
    }

    const approval = result.approval;

    if (!approval) {
      return "Onay isteğini oluşturdum Mert ama detaylar boş döndü. Onay Merkezi’nden kontrol edelim.";
    }

    return `Tamam Mert, bu işlem riskli olduğu için direkt yapmadım ve Onay Merkezi’ne aldım.

Onay: ${approval.title}
Proje: ${approval.project_id || "Genel"}
İşlem tipi: ${approval.action_type}
Risk: ${approval.risk_level}
Durum: ${approval.status}

Açıklama:
${approval.description || "Açıklama yok."}

Onay Merkezi’nden onaylayabilir veya reddedebilirsin.`;
  }

  async function loadWorkspaceSummary() {
    setIsWorkspaceLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/workspace/summary");

      if (!response.ok) {
        throw new Error("Workspace özeti yüklenemedi.");
      }

      const data = await response.json();
      setWorkspaceSummary(data);

      if (data?.active_project) {
        setActiveProject(data.active_project);
        setActiveProjectId(data.active_project_id ?? data.active_project.id ?? "");
      }
    } catch (error) {
      console.error(error);
      setWorkspaceSummary(null);
    } finally {
      setIsWorkspaceLoading(false);
    }
  }

  async function loadActiveProject() {
    try {
      const response = await fetch("http://127.0.0.1:8000/workspace/active-project");

      if (!response.ok) {
        throw new Error("Aktif proje yüklenemedi.");
      }

      const data: ActiveProjectResponse = await response.json();

      setActiveProject(data.project);
      setActiveProjectId(data.project_id || "");
    } catch (error) {
      console.error(error);
      setActiveProject(null);
      setActiveProjectId("");
    }
  }

  async function loadActiveTask() {
    try {
      const response = await fetch("http://127.0.0.1:8000/workspace/active-task");

      if (!response.ok) {
        throw new Error("Aktif görev yüklenemedi.");
      }

      const data: ActiveTaskResponse = await response.json();

      setActiveTask(data.task);
      setActiveTaskId(data.task_id || "");
    } catch (error) {
      console.error(error);
      setActiveTask(null);
      setActiveTaskId("");
    }
  }

  async function setTaskAsActive(taskId: string) {
    try {
      const response = await fetch("http://127.0.0.1:8000/workspace/active-task", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          task_id: taskId,
        }),
      });

      if (!response.ok) {
        throw new Error("Aktif görev güncellenemedi.");
      }

      const data: ActiveTaskResponse = await response.json();

      if (!data.success) {
        alert(data.message ?? "Aktif görev güncellenemedi.");
        return;
      }

      setActiveTask(data.task);
      setActiveTaskId(data.task_id || "");

      await loadTasks();
      await loadWorkspaceSummary();
      await checkBackendHealth({ force: true });
    } catch (error) {
      console.error(error);
      alert("Aktif görev güncellenemedi. Backend çalışıyor mu kontrol edelim.");
    }
  }

  async function loadActiveProjectDetail() {
    setIsActiveProjectDetailLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/workspace/active-project/detail");

      if (!response.ok) {
        throw new Error("Aktif proje detayı yüklenemedi.");
      }

      const data: ActiveProjectDetail = await response.json();
      setActiveProjectDetail(data);

      if (data.project) {
        setActiveProject(data.project);
        setActiveProjectId(data.project_id || data.project.id || "");
      }
    } catch (error) {
      console.error(error);
      setActiveProjectDetail(null);
    } finally {
      setIsActiveProjectDetailLoading(false);
    }
  }

  async function setProjectAsActive(projectId: string) {
    try {
      const response = await fetch("http://127.0.0.1:8000/workspace/active-project", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          project_id: projectId,
        }),
      });

      if (!response.ok) {
        throw new Error("Aktif proje güncellenemedi.");
      }

      const data: ActiveProjectResponse = await response.json();

      if (!data.success) {
        alert(data.message ?? "Aktif proje güncellenemedi.");
        return;
      }

      setActiveProject(data.project);
      setActiveProjectId(data.project_id || "");

      await loadActiveProjectDetail();
      await loadWorkspaceSummary();
      await loadProjects();
      await checkBackendHealth({ force: true });
    } catch (error) {
      console.error(error);
      alert("Aktif proje güncellenemedi. Backend çalışıyor mu kontrol edelim.");
    }
  }

  async function loadMemory() {
    updateTranscribing(false);
    setIsMemoryLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/memory");

      if (!response.ok) {
        throw new Error("Hafıza yüklenemedi.");
      }

      const data = await response.json();
      setMemoryData(data);
    } catch (error) {
      console.error(error);
      setMemoryData(null);
    } finally {
      setIsMemoryLoading(false);
    }
  }

  async function loadProjects() {
    setIsProjectsLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/projects");

      if (!response.ok) {
        throw new Error("Projeler yüklenemedi.");
      }

      const data = await response.json();
      setProjects(data);
    } catch (error) {
      console.error(error);
      setProjects([]);
    } finally {
      setIsProjectsLoading(false);
    }
  }

  async function loadTasks() {
    setIsTasksLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/tasks");

      if (!response.ok) {
        throw new Error("Görevler yüklenemedi.");
      }

      const data = await response.json();
      setTasks(data);
    } catch (error) {
      console.error(error);
      setTasks([]);
    } finally {
      setIsTasksLoading(false);
    }
  }

  async function loadApprovals() {
    setIsApprovalsLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/approvals");

      if (!response.ok) {
        throw new Error("Onaylar yüklenemedi.");
      }

      const data = await response.json();
      setApprovals(data);
    } catch (error) {
      console.error(error);
      setApprovals([]);
    } finally {
      setIsApprovalsLoading(false);
    }
  }

  async function loadOutputs() {
    setIsOutputsLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/outputs");

      if (!response.ok) {
        throw new Error("Çıktılar yüklenemedi.");
      }

      const data = await response.json();
      setOutputs(data);
    } catch (error) {
      console.error(error);
      setOutputs([]);
    } finally {
      setIsOutputsLoading(false);
    }
  }

  async function loadReminders() {
    setIsRemindersLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/reminders");

      if (!response.ok) {
        throw new Error("Hatırlatmalar yüklenemedi.");
      }

      const data = await response.json();
      setReminders(data);
    } catch (error) {
      console.error(error);
      setReminders([]);
    } finally {
      setIsRemindersLoading(false);
    }
  }


  async function checkDueReminders() {
    try {
      const response = await fetch("http://127.0.0.1:8000/reminders/due", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          mark_as_notified: true,
        }),
      });

      if (!response.ok) {
        return;
      }

      const data = await response.json();
      const dueReminders: ReminderData[] = data?.due_reminders ?? [];

      if (dueReminders.length === 0) {
        return;
      }

      const reminderText = dueReminders
        .map((reminder) => `• ${reminder.title}`)
        .join("\n");

      const alertText =
        dueReminders.length === 1
          ? `Mert, şunu hatırlatmamı istemiştin: ${dueReminders[0].title}`
          : `Mert, hatırlatmamı istediğin birkaç şeyin zamanı geldi:\n\n${reminderText}`;

      const reminderMessage: Message = {
        id: Date.now() + 3,
        sender: "Vex",
        text: alertText,
      };

      setMessages((currentMessages) => [...currentMessages, reminderMessage]);

      try {
        await loadReminders();
      } catch (loadError) {
        console.error("Hatırlatmalar yenilenemedi:", loadError);
      }

      speakText(alertText);
    } catch (error) {
      console.error("Hatırlatma zamanı kontrol hatası:", error);
    }
  }

  async function deleteReminder(reminderId: string) {
    try {
      const response = await fetch(`http://127.0.0.1:8000/reminders/${reminderId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error("Hatırlatma silinemedi.");
      }

      await loadReminders();
    } catch (error) {
      console.error(error);
      alert("Hatırlatma silinemedi. Backend çalışıyor mu kontrol edelim.");
    }
  }

  async function createProject() {
    const cleanName = projectName.trim();

    if (!cleanName || isCreatingProject) {
      return;
    }

    setIsCreatingProject(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/projects", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          id: slugify(cleanName),
          name: cleanName,
          type: projectType.trim() || "Genel proje",
          status: "aktif",
          description: projectDescription.trim(),
          main_goals: splitLines(projectGoals),
          notes: splitLines(projectNotes),
        }),
      });

      if (!response.ok) {
        throw new Error("Proje oluşturulamadı.");
      }

      setProjectName("");
      setProjectType("");
      setProjectDescription("");
      setProjectGoals("");
      setProjectNotes("");
      setShowProjectForm(false);

      await loadProjects();
      await checkBackendHealth({ force: true });
    } catch (error) {
      console.error(error);
      alert("Proje oluşturulamadı. Backend çalışıyor mu kontrol edelim.");
    } finally {
      setIsCreatingProject(false);
    }
  }

  async function deleteProject(projectId: string) {
    try {
      const response = await fetch(`http://127.0.0.1:8000/projects/${projectId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error("Proje silinemedi.");
      }

      await loadProjects();
      await checkBackendHealth({ force: true });
    } catch (error) {
      console.error(error);
      alert("Proje silinemedi. Backend çalışıyor mu kontrol edelim.");
    }
  }

  async function completeTask(taskId: string) {
    try {
      const response = await fetch(`http://127.0.0.1:8000/tasks/${taskId}/complete`, {
        method: "PATCH",
      });

      if (!response.ok) {
        throw new Error("Görev tamamlanamadı.");
      }

      await loadTasks();
      await checkBackendHealth({ force: true });
    } catch (error) {
      console.error(error);
      alert("Görev tamamlanamadı. Backend çalışıyor mu kontrol edelim.");
    }
  }

  async function deleteTask(taskId: string) {
    try {
      const response = await fetch(`http://127.0.0.1:8000/tasks/${taskId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error("Görev silinemedi.");
      }

      await loadTasks();
      await checkBackendHealth({ force: true });
    } catch (error) {
      console.error(error);
      alert("Görev silinemedi. Backend çalışıyor mu kontrol edelim.");
    }
  }

  async function approveApproval(approvalId: string) {
    try {
      const response = await fetch(`http://127.0.0.1:8000/approvals/${approvalId}/approve`, {
        method: "PATCH",
      });

      if (!response.ok) {
        throw new Error("Onay isteği onaylanamadı.");
      }

      await loadApprovals();
      await checkBackendHealth({ force: true });
    } catch (error) {
      console.error(error);
      alert("Onay isteği onaylanamadı. Backend çalışıyor mu kontrol edelim.");
    }
  }

  async function rejectApproval(approvalId: string) {
    try {
      const response = await fetch(`http://127.0.0.1:8000/approvals/${approvalId}/reject`, {
        method: "PATCH",
      });

      if (!response.ok) {
        throw new Error("Onay isteği reddedilemedi.");
      }

      await loadApprovals();
      await checkBackendHealth({ force: true });
    } catch (error) {
      console.error(error);
      alert("Onay isteği reddedilemedi. Backend çalışıyor mu kontrol edelim.");
    }
  }

  async function deleteApproval(approvalId: string) {
    try {
      const response = await fetch(`http://127.0.0.1:8000/approvals/${approvalId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error("Onay isteği silinemedi.");
      }

      await loadApprovals();
      await checkBackendHealth({ force: true });
    } catch (error) {
      console.error(error);
      alert("Onay isteği silinemedi. Backend çalışıyor mu kontrol edelim.");
    }
  }

  async function saveLastAssistantOutput() {
    const lastVexMessage = [...messages]
      .reverse()
      .find((message) => message.sender === "Vex" && message.text.trim());

    if (!lastVexMessage) {
      return {
        success: false,
        message: "Kaydedilecek Vex çıktısı bulunamadı.",
        output: null,
      } as OutputFromChatResult;
    }

    const response = await fetch("http://127.0.0.1:8000/outputs/from-chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        title: activeTask?.title || activeProject?.name || "Sohbet çıktısı",
        output_type: "genel",
        content: lastVexMessage.text,
      }),
    });

    if (!response.ok) {
      throw new Error("Çıktı kaydetme endpoint'i cevap vermedi.");
    }

    return response.json();
  }

  async function completeActiveTaskFromChat() {
    if (!activeTaskId) {
      return {
        success: false,
        message: "Aktif görev seçili değil.",
        task: null,
      };
    }

    const response = await fetch(`http://127.0.0.1:8000/tasks/${activeTaskId}/complete`, {
      method: "PATCH",
    });

    if (!response.ok) {
      throw new Error("Aktif görev tamamlanamadı.");
    }

    return response.json();
  }

  async function deleteOutput(outputId: string) {
    try {
      const response = await fetch(`http://127.0.0.1:8000/outputs/${outputId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error("Çıktı silinemedi.");
      }

      await loadOutputs();
      await loadWorkspaceSummary();
      await loadActiveProjectDetail();
      await checkBackendHealth({ force: true });
    } catch (error) {
      console.error(error);
      alert("Çıktı silinemedi. Backend çalışıyor mu kontrol edelim.");
    }
  }

  // Dummy reference to bypass strict TS rules
  if (false as boolean) {
    console.log(startVoiceRecording, stopVoiceRecordingAndTranscribe);
  }

  async function startVoiceRecording() {
    if (isRecordingRef.current || isSendingRef.current || isTranscribingRef.current) {
      return;
    }

    if (backendStatus === "offline") {
      alert("Backend kapalı görünüyor. Önce backend’i başlatalım.");
      return;
    }

    stopSpeaking();
    setBusyState(true);
    updateRecording(true);
    setVoiceStatus("Mikrofon kaydı başladı. Konuşabilirsin.");

    try {
      const response = await fetch("http://127.0.0.1:8000/speech/record/start", {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("Kayıt başlatılamadı.");
      }

      const data = await response.json();

      if (!data?.success) {
        updateRecording(false);
        setBusyState(false);
        setVoiceStatus(data?.message ?? "Kayıt başlatılamadı.");
        alert(data?.message ?? "Kayıt başlatılamadı.");
      }
    } catch (error) {
      console.error(error);
      updateRecording(false);
      setBusyState(false);
      setVoiceStatus("Kayıt başlatılamadı.");
      alert("Kayıt başlatılamadı. Backend açık mı kontrol edelim.");
      await checkBackendHealth({ force: true });
    }
  }

  async function stopVoiceRecordingAndTranscribe() {
    if (!isRecordingRef.current || isTranscribingRef.current) {
      return;
    }

    updateRecording(false);
    updateTranscribing(true);
    setBusyState(true);
    setVoiceStatus("Kayıt durduruldu. Whisper yazıya çeviriyor...");

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/speech/record/stop-and-transcribe",
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        throw new Error("Kayıt durdurulamadı veya yazıya çevrilemedi.");
      }

      const data = await response.json();

      if (data?.success && data?.text) {
        const cleanedText = cleanTranscribedText(data.text);
        setInput(cleanedText);
        setVoiceStatus(`Ses metne çevrildi: ${cleanedText}`);

        if (autoSendVoiceEnabled) {
          setVoiceStatus(`Ses metne çevrildi ve gönderiliyor: ${cleanedText}`);
          await sendMessage(cleanedText);
        }
      } else {
        setVoiceStatus(data?.message ?? "Ses algılandı ama metin çıkarılamadı.");
        alert(data?.message ?? "Ses algılandı ama metin çıkarılamadı.");
      }
    } catch (error) {
      console.error(error);
      setVoiceStatus("Ses yazıya çevrilemedi.");
      alert("Ses yazıya çevrilemedi. Backend açık mı kontrol edelim.");
    } finally {
      updateTranscribing(false);
      setBusyState(false);
      await checkBackendHealth({ force: true });
    }
  }


  async function listenAndTranscribe() {
    if (isRecordingRef.current || isSendingRef.current || isTranscribingRef.current) {
      return;
    }

    if (backendStatus === "offline") {
      alert("Backend kapalı görünüyor. Önce backend’i başlatalım.");
      return;
    }

    stopSpeaking();
    setBusyState(true);
    updateRecording(true);
    setVoiceStatus("Dinliyorum... Konuşman bitince otomatik duracağım.");

    try {
      const response = await fetch("http://127.0.0.1:8000/speech/listen-and-transcribe", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          max_seconds: 20,
          silence_seconds: 0.45,
          peak_threshold: 0.06,
          average_threshold: 0.008,
        }),
      });

      updateRecording(false);
      updateTranscribing(true);
      setVoiceStatus("Konuşma bitti. Whisper yazıya çeviriyor...");

      if (!response.ok) {
        throw new Error("Otomatik dinleme yazıya çevrilemedi.");
      }

      const data = await response.json();

      if (data?.success && data?.text) {
        const cleanedText = cleanTranscribedText(data.text);
        setInput(cleanedText);
        setVoiceStatus(`Ses metne çevrildi: ${cleanedText}`);

        if (autoSendVoiceEnabled) {
          setVoiceStatus(`Ses metne çevrildi ve gönderiliyor: ${cleanedText}`);
          await sendMessage(cleanedText);
        }
      } else {
        setVoiceStatus(data?.message ?? "Ses algılandı ama metin çıkarılamadı.");
        alert(data?.message ?? "Ses algılandı ama metin çıkarılamadı.");
      }
    } catch (error) {
      console.error(error);
      setVoiceStatus("Otomatik ses algılama hata verdi.");
      alert("Ses yazıya çevrilemedi. Backend açık mı kontrol edelim.");
    } finally {
      updateRecording(false);
      updateTranscribing(false);
      setBusyState(false);
      await checkBackendHealth({ force: true });
    }
  }

  function openDashboardView() {
    setActiveView("dashboard");
    loadActiveProject();
    loadActiveTask();
    loadActiveProjectDetail();
    loadWorkspaceSummary();
  }

  function openMemoryView() {
    setActiveView("memory");
    loadMemory();
  }

  function openProjectsView() {
    setActiveView("projects");
    loadActiveProject();
    loadActiveTask();
    loadProjects();
  }

  function openTasksView() {
    setActiveView("tasks");
    loadActiveTask();
    loadTasks();
  }

  function openApprovalsView() {
    setActiveView("approvals");
    loadApprovals();
  }

  function openOutputsView() {
    setActiveView("outputs");
    loadOutputs();
  }

  function openRemindersView() {
    setActiveView("reminders");
    loadReminders();
  }

  async function sendMessage(messageOverride?: string) {
    const cleanInput = (messageOverride ?? input).trim();

    if (!cleanInput || isSendingRef.current || (isRecordingRef.current && !messageOverride)) {
      return;
    }

    if (backendStatus === "offline") {
      alert("Backend kapalı görünüyor. Mesaj göndermek için backend’i başlatmamız gerekiyor.");
      return;
    }

    const userMessage: Message = {
      id: Date.now(),
      sender: "Sen",
      text: cleanInput,
    };

    setMessages((currentMessages) => [...currentMessages, userMessage]);
    setInput("");
    stopSpeaking();
    updateSending(true);
    setBusyState(true);
    setIsTyping(true);

    const historyForBackend = messages.map((message) => ({
      sender: message.sender,
      text: message.text,
    }));

      if (shouldFindProductsOnSiteFromChat(cleanInput)) {
        try {
          const productFinderResult = await findProductsOnSiteFromChat(cleanInput);
          const productFinderReplyText = buildProductFinderReply(productFinderResult);
          const productFinderReply: Message = {
            id: Date.now() + 2,
            sender: "Vex",
            text: productFinderReplyText,
          };
          setMessages((currentMessages) => [...currentMessages, productFinderReply]);
          speakText(productFinderReplyText);
        } catch (error) {
          const errorReply: Message = {
            id: Date.now() + 2,
            sender: "Vex",
            text: `Ürün araması yaparken hata aldım Mert: ${error instanceof Error ? error.message : String(error)}`,
          };
          setMessages((currentMessages) => [...currentMessages, errorReply]);
        } finally {
          setIsTyping(false);
          updateSending(false);
          setBusyState(false);
        }
        return;
      }

      if (shouldCreateShopifyContentFromChat(cleanInput)) {
        try {
          const shopifyResult = await createShopifyContentFromChat(cleanInput);
          const shopifyReplyText = buildShopifyContentReply(shopifyResult);
          const shopifyReply: Message = {
            id: Date.now() + 2,
            sender: "Vex",
            text: shopifyReplyText,
          };
          setMessages((currentMessages) => [...currentMessages, shopifyReply]);
          speakText(shopifyReplyText);
        } catch (error) {
          const errorReply: Message = {
            id: Date.now() + 2,
            sender: "Vex",
            text: `Shopify içeriği hazırlarken hata aldım Mert: ${error instanceof Error ? error.message : String(error)}`,
          };
          setMessages((currentMessages) => [...currentMessages, errorReply]);
        } finally {
          setIsTyping(false);
          updateSending(false);
          setBusyState(false);
        }
        return;
      }

      if (shouldAnalyzeSiteFromChat(cleanInput)) {
        try {
          const siteResult = await analyzeSiteFromChat(cleanInput);
          const siteReplyText = buildSiteAnalysisReply(siteResult);
          const siteReply: Message = {
            id: Date.now() + 2,
            sender: "Vex",
            text: siteReplyText,
          };
          setMessages((currentMessages) => [...currentMessages, siteReply]);
          speakText(siteReplyText);
        } catch (error) {
          const errorReply: Message = {
            id: Date.now() + 2,
            sender: "Vex",
            text: `Site analizi yaparken hata aldım Mert: ${error instanceof Error ? error.message : String(error)}`,
          };
          setMessages((currentMessages) => [...currentMessages, errorReply]);
        } finally {
          setIsTyping(false);
          updateSending(false);
          setBusyState(false);
        }
        return;
      }

      if (shouldAnalyzeScreenFromChat(cleanInput)) {
        try {
          const screenResult = await analyzeScreenFromChat(cleanInput);
          const screenReplyText = buildScreenAnalysisReply(screenResult);
          const screenReply: Message = {
            id: Date.now() + 2,
            sender: "Vex",
            text: screenReplyText,
          };
          setMessages((currentMessages) => [...currentMessages, screenReply]);
          speakText(screenReplyText);
        } catch (error) {
          const errorReply: Message = {
            id: Date.now() + 2,
            sender: "Vex",
            text: `Ekran analizi yaparken hata aldım Mert: ${error instanceof Error ? error.message : String(error)}`,
          };
          setMessages((currentMessages) => [...currentMessages, errorReply]);
        } finally {
          setIsTyping(false);
          updateSending(false);
          setBusyState(false);
        }
        return;
      }

    try {
      // VEX_HARD_REMINDER_ROUTE_START
      const hardReminderText = cleanInput.toLocaleLowerCase("tr-TR");
      const isHardReminderCommand =
        hardReminderText.includes("hatırlat") ||
        hardReminderText.includes("hatirlat") ||
        hardReminderText.includes("beni uyar") ||
        hardReminderText.includes("alarm kur") ||
        hardReminderText.includes("dakika sonra") ||
        hardReminderText.includes("saat sonra");

      if (isHardReminderCommand) {
        try {
          const response = await fetch("http://127.0.0.1:8000/reminders/from-chat", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              message: cleanInput,
              project_id: activeProjectId,
              task_id: activeTaskId,
            }),
          });

          const rawText = await response.text();

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${rawText}`);
          }

          const reminderResult = JSON.parse(rawText);
          const reminder = reminderResult.reminder;

          const reminderReplyText =
            reminderResult.success && reminder
              ? `Tamam Mert, hatırlatmayı kurdum.

Başlık: ${reminder.title}
Zaman: ${reminder.remind_at}
Proje: ${reminder.project_id || "Genel"}
Görev: ${reminder.task_id || "Bağlı görev yok"}

Zamanı geldiğinde Vex açık olduğu sürece seni uyaracağım.`
              : reminderResult.message || "Hatırlatmayı oluşturamadım Mert.";

          const reminderReply: Message = {
            id: Date.now() + 2,
            sender: "Vex",
            text: reminderReplyText,
          };

          setMessages((currentMessages) => [...currentMessages, reminderReply]);

          try {
            await loadReminders();
          } catch (loadError) {
            console.error("Hatırlatma listesi yenilenemedi:", loadError);
          }

          speakText(reminderReplyText);
          return;
        } catch (error) {
          console.error("Hatırlatma route hatası:", error);

          const errorText = `Hatırlatmayı oluştururken teknik hata aldım Mert: ${
            error instanceof Error ? error.message : String(error)
          }`;

          const errorReply: Message = {
            id: Date.now() + 2,
            sender: "Vex",
            text: errorText,
          };

          setMessages((currentMessages) => [...currentMessages, errorReply]);
          speakText(errorText);
          return;
        }
      }
      // VEX_HARD_REMINDER_ROUTE_END
      if (shouldCreateReminderFromChat(cleanInput)) {
        try {
          const reminderResult = await createReminderFromChat(cleanInput);
          const reminderReplyText = buildReminderCreatedReply(reminderResult);

          const reminderReply: Message = {
            id: Date.now() + 2,
            sender: "Vex",
            text: reminderReplyText,
          };

          setMessages((currentMessages) => [...currentMessages, reminderReply]);

          await loadReminders();
          speakText(reminderReplyText);
          return;
        } catch (error) {
          console.error("Hatırlatma oluşturma hatası:", error);

          const errorText = `Hatırlatmayı oluştururken teknik hata aldım Mert: ${
            error instanceof Error ? error.message : String(error)
          }`;

          const errorReply: Message = {
            id: Date.now() + 2,
            sender: "Vex",
            text: errorText,
          };

          setMessages((currentMessages) => [...currentMessages, errorReply]);
          speakText(errorText);
          return;
        }
      }

      if (shouldActivateSuggestedTaskFromChat(cleanInput)) {
        if (!suggestedTaskId) {
          const noSuggestedTaskReply: Message = {
            id: Date.now() + 2,
            sender: "Vex",
            text: "Şu an aktif yapabileceğim önerilmiş bir görev yok Mert. Görevler panelinden bir görevi aktif seçebiliriz.",
          };

          setMessages((currentMessages) => [...currentMessages, noSuggestedTaskReply]);
          speakText(noSuggestedTaskReply.text);
          return;
        }

        await setTaskAsActive(suggestedTaskId);

        const activatedTaskReply: Message = {
          id: Date.now() + 2,
          sender: "Vex",
          text: "Tamam Mert, önerdiğim görevi aktif görev yaptım. Şimdi bu işten devam edebiliriz.",
        };

        setMessages((currentMessages) => [...currentMessages, activatedTaskReply]);
        setSuggestedTaskId("");
        speakText(activatedTaskReply.text);
        return;
      }

      if (shouldCompleteActiveTaskFromChat(cleanInput)) {
        const completeTaskResult = await completeActiveTaskFromChat();

        const completedTask = completeTaskResult.task;

        const remainingOpenTasks = completeTaskResult.tasks?.filter(
          (task: TaskData) => task.status !== "tamamlandı"
        ) ?? [];

        const suggestedTask = remainingOpenTasks.find(
          (task: TaskData) => task.project_id === activeProjectId
        ) ?? remainingOpenTasks[0];

        setSuggestedTaskId(suggestedTask?.id ?? "");

        const completeReplyText = completeTaskResult.success && completedTask
          ? `Tamam Mert, aktif görevi tamamlandı olarak işaretledim.

Görev: ${completedTask.title}
Proje: ${completedTask.project_id || "Genel"}
Durum: ${completedTask.status}

${
  suggestedTask
    ? `Sırada şu görev var: ${suggestedTask.title}

İstersen bunu aktif görev yapıp buradan devam edebiliriz.`
    : "Şu an açık görev görünmüyor. İstersen aktif proje için yeni bir görev oluşturabiliriz."
}`
          : completeTaskResult.message || "Aktif görevi kapatamadım Mert.";

        const completeReply: Message = {
          id: Date.now() + 2,
          sender: "Vex",
          text: completeReplyText,
        };

        setMessages((currentMessages) => [...currentMessages, completeReply]);

        await loadActiveTask();
        await loadTasks();
        await loadWorkspaceSummary();
        await loadActiveProjectDetail();
        speakText(completeReplyText);
        return;
      }

      if (shouldSaveOutputFromChat(cleanInput)) {
        const outputResult = await saveLastAssistantOutput();

        const outputReplyText = outputResult.success && outputResult.output
          ? `Tamam Mert, son çıktıyı kaydettim.

Başlık: ${outputResult.output.title}
Proje: ${outputResult.output.project_id || "Genel"}
Görev: ${outputResult.output.task_id || "Bağlı görev yok"}
Tür: ${outputResult.output.output_type}
Durum: ${outputResult.output.status}

Çıktılar panelinden görebilirsin.${
  activeTaskId
    ? "\n\nBu çıktı aktif görevi karşılıyorsa bana “evet kapat” diyebilirsin; görevi tamamlandı yaparım."
    : ""
}`
          : outputResult.message || "Çıktıyı kaydedemedim Mert.";

        const outputReply: Message = {
          id: Date.now() + 2,
          sender: "Vex",
          text: outputReplyText,
        };

        setMessages((currentMessages) => [...currentMessages, outputReply]);

        await loadOutputs();
        await loadWorkspaceSummary();
        await loadActiveProjectDetail();
        speakText(outputReplyText);
        return;
      }

      if (shouldCreateApprovalFromChat(cleanInput)) {
        const approvalResult = await createApprovalFromChat(cleanInput);
        const approvalReplyText = buildApprovalCreatedReply(approvalResult);

        const approvalReply: Message = {
          id: Date.now() + 2,
          sender: "Vex",
          text: approvalReplyText,
        };

        setMessages((currentMessages) => [...currentMessages, approvalReply]);

        await loadApprovals();
        speakText(approvalReplyText);
        return;
      }

      if (shouldCreateProjectFromChat(cleanInput)) {
        const projectResult = await createProjectFromChat(cleanInput);
        const projectReplyText = buildProjectCreatedReply(projectResult);

        const projectReply: Message = {
          id: Date.now() + 2,
          sender: "Vex",
          text: projectReplyText,
        };

        setMessages((currentMessages) => [...currentMessages, projectReply]);

        await loadProjects();
        speakText(projectReplyText);
        return;
      }

      if (shouldCreateTaskFromChat(cleanInput)) {
        const taskResult = await createTaskFromChat(cleanInput);
        const taskReplyText = buildTaskCreatedReply(taskResult);

        const taskReply: Message = {
          id: Date.now() + 2,
          sender: "Vex",
          text: taskReplyText,
        };

        setMessages((currentMessages) => [...currentMessages, taskReply]);

        await loadTasks();
        speakText(taskReplyText);
        return;
      }

      let memoryMessage: Message | null = null;

      if (shouldSaveToMemory(cleanInput)) {
        const memoryResult = await saveMessageToMemory(cleanInput);

        if (memoryResult?.success) {
          memoryMessage = {
            id: Date.now() + 1,
            sender: "Vex",
            text: memoryResult.rule
              ? `Tamam Mert, bunu hafızama ekledim: "${memoryResult.rule}"`
              : "Tamam Mert, bu bilgiyi hafızama ekledim.",
          };
        } else {
          memoryMessage = {
            id: Date.now() + 1,
            sender: "Vex",
            text:
              memoryResult?.message ??
              "Bu mesajı hafızaya eklemeye çalıştım ama net bir kural çıkaramadım.",
          };
        }
      }

      const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: cleanInput,
          history: historyForBackend,
        }),
      });

      if (!response.ok) {
        throw new Error("Backend cevap vermedi.");
      }

      const data = await response.json();

      const vexReply: Message = {
        id: Date.now() + 2,
        sender: "Vex",
        text: data.reply ?? "Backend cevap verdi ama reply alanı boş geldi.",
      };

      setMessages((currentMessages) => {
        if (memoryMessage) {
          return [...currentMessages, memoryMessage, vexReply];
        }

        return [...currentMessages, vexReply];
      });

      speakText(vexReply.text);
    } catch (error) {
      const errorReply: Message = {
        id: Date.now() + 3,
        sender: "Vex",
        text: `Mesaj gönderirken teknik hata aldım Mert: ${
          error instanceof Error ? error.message : String(error)
        }`,
      };

      setMessages((currentMessages) => [...currentMessages, errorReply]);
      console.error(error);
    } finally {
      updateSending(false);
      setBusyState(false);
      setIsTyping(false);
      await checkBackendHealth({ force: true });
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">V</div>
          <div>
            <h1>Vex</h1>
            <p>AI Workspace</p>
          </div>
        </div>

        <nav className="nav-list">
          <button
            className={`nav-item ${activeView === "dashboard" ? "active" : ""}`}
            onClick={openDashboardView}
          >
            Dashboard
          </button>

          <button
            className={`nav-item ${activeView === "chat" ? "active" : ""}`}
            onClick={() => setActiveView("chat")}
          >
            Genel Sohbet
          </button>

          <button
            className={`nav-item ${activeView === "projects" ? "active" : ""}`}
            onClick={openProjectsView}
          >
            Projeler
          </button>

          <button
            className={`nav-item ${activeView === "tasks" ? "active" : ""}`}
            onClick={openTasksView}
          >
            Görevler
          </button>

          <button className="nav-item">Shopify</button>
          <button className="nav-item">Tasarım</button>
          <button className="nav-item">Dosyalar</button>

          <button
            className={`nav-item ${activeView === "memory" ? "active" : ""}`}
            onClick={openMemoryView}
          >
            Hafıza
          </button>

          <button
            className={`nav-item ${activeView === "approvals" ? "active" : ""}`}
            onClick={openApprovalsView}
          >
            Onay Merkezi
          </button>

          <button
            className={`nav-item ${activeView === "outputs" ? "active" : ""}`}
            onClick={openOutputsView}
          >
            Çıktılar
          </button>

          <button
            className={`nav-item ${activeView === "reminders" ? "active" : ""}`}
            onClick={openRemindersView}
          >
            Hatırlatmalar
          </button>

          <button
            className={`nav-item ${activeView === "evolution" ? "active" : ""}`}
            onClick={() => setActiveView("evolution")}
          >
            Kendi Kendine Gelişim (Evrim)
          </button>

          <button
            className={`nav-item ${activeView === "computer" ? "active" : ""}`}
            onClick={() => setActiveView("computer")}
          >
            Bilgisayar Kontrol
          </button>
        </nav>
      </aside>

      <section className="chat-area">

        {activeView === "dashboard" ? (
          <>
            <header className="topbar">
              <div>
                <p className="eyebrow">Vex çalışma alanı</p>
                <h2>Dashboard</h2>
              </div>
              <div className="topbar-actions">
                <button
                  className="small-action-button"
                  onClick={() => {
                    loadActiveProjectDetail();
                    loadWorkspaceSummary();
                  }}
                >
                  Yenile
                </button>

                <span className={`status-pill backend-${backendStatus === "checking" ? "online" : backendStatus}`}>
                  {getBackendLabel()}
                </span>
              </div>
            </header>

            <div className="projects-page">
              {isWorkspaceLoading ? (
                <div className="panel-card">
                  <strong>Dashboard yükleniyor...</strong>
                </div>
              ) : workspaceSummary ? (
                <>
                  <div className="memory-grid">
                    <div className="memory-card">
                      <p className="panel-label">Şu an üzerinde çalışılan proje</p>
                      <h3>{activeProject?.name ?? "Seçilmedi"}</h3>
                      <p>{activeProject?.type ?? "Projeler panelinden aktif proje seçebilirsin."}</p>
                    </div>

                    <div className="memory-card">
                      <p className="panel-label">Aktif projeler</p>
                      <h3>{workspaceSummary.counts.active_projects}</h3>
                    </div>

                    <div className="memory-card">
                      <p className="panel-label">Açık görevler</p>
                      <h3>{workspaceSummary.counts.open_tasks}</h3>
                    </div>

                    <div className="memory-card">
                      <p className="panel-label">Yüksek öncelik</p>
                      <h3>{workspaceSummary.counts.high_priority_tasks}</h3>
                    </div>

                    <div className="memory-card">
                      <p className="panel-label">Bekleyen onay</p>
                      <h3>{workspaceSummary.counts.pending_approvals}</h3>
                    </div>

                    <div className="memory-card">
                      <p className="panel-label">Kaydedilen çıktılar</p>
                      <h3>{workspaceSummary.counts.outputs ?? 0}</h3>
                    </div>
                  </div>

                  <div className="memory-section">
                    <div className="memory-section-header">
                      <div>
                        <p className="eyebrow">Önerilen sonraki adım</p>
                        <h3>{workspaceSummary.suggested_next_step}</h3>
                      </div>
                    </div>
                  </div>


                  <div className="memory-section">
                    <div className="memory-section-header">
                      <div>
                        <p className="eyebrow">Aktif proje çalışma alanı</p>
                        <h3>{activeProject?.name ?? "Aktif proje seçilmedi"}</h3>
                      </div>

                      <button className="small-action-button" onClick={openProjectsView}>
                        Proje Seç
                      </button>
                    </div>

                    {isActiveProjectDetailLoading ? (
                      <p className="panel-label">Aktif proje detayı yükleniyor...</p>
                    ) : activeProjectDetail?.has_active_project ? (
                      <>
                        <p className="project-description">
                          {activeProjectDetail.project?.description}
                        </p>

                        <div className="memory-grid">
                          <div className="memory-card">
                            <p className="panel-label">Bu projedeki açık görevler</p>
                            <h3>{activeProjectDetail.counts?.open_tasks ?? 0}</h3>
                          </div>

                          <div className="memory-card">
                            <p className="panel-label">Yüksek öncelikli görevler</p>
                            <h3>{activeProjectDetail.counts?.high_priority_tasks ?? 0}</h3>
                          </div>

                          <div className="memory-card">
                            <p className="panel-label">Bekleyen onaylar</p>
                            <h3>{activeProjectDetail.counts?.pending_approvals ?? 0}</h3>
                          </div>
                        </div>

                        <div className="project-section">
                          <p className="panel-label">Vex’in önerdiği sonraki adım</p>
                          <p>{activeProjectDetail.suggested_next_step}</p>
                        </div>

                        <div className="project-grid">
                          <div className="project-card">
                            <div className="project-card-header">
                              <div>
                                <p className="panel-label">Aktif proje görevleri</p>
                                <h3>Öncelikli işler</h3>
                              </div>
                              <button className="small-action-button" onClick={openTasksView}>
                                Görevlere Git
                              </button>
                            </div>

                            <div className="project-section">
                              {activeProjectDetail.high_priority_tasks.length > 0 ? (
                                <ul>
                                  {activeProjectDetail.high_priority_tasks.slice(0, 5).map((task) => (
                                    <li key={task.id}>
                                      {task.title} — {task.priority}
                                    </li>
                                  ))}
                                </ul>
                              ) : activeProjectDetail.open_tasks.length > 0 ? (
                                <ul>
                                  {activeProjectDetail.open_tasks.slice(0, 5).map((task) => (
                                    <li key={task.id}>
                                      {task.title} — {task.status}
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <p className="panel-label">Bu proje için açık görev yok.</p>
                              )}
                            </div>
                          </div>

                          <div className="project-card">
                            <div className="project-card-header">
                              <div>
                                <p className="panel-label">Aktif proje onayları</p>
                                <h3>Bekleyen kararlar</h3>
                              </div>
                              <button className="small-action-button" onClick={openApprovalsView}>
                                Onaylara Git
                              </button>
                            </div>

                            <div className="project-section">
                              {activeProjectDetail.pending_approvals.length > 0 ? (
                                <ul>
                                  {activeProjectDetail.pending_approvals.slice(0, 5).map((approval) => (
                                    <li key={approval.id}>
                                      {approval.title} — {approval.risk_level}
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <p className="panel-label">Bu proje için bekleyen onay yok.</p>
                              )}
                            </div>
                          </div>

                          <div className="project-card">
                            <div className="project-card-header">
                              <div>
                                <p className="panel-label">Aktif proje çıktıları</p>
                                <h3>Kaydedilen taslaklar</h3>
                              </div>
                              <button className="small-action-button" onClick={openOutputsView}>
                                Çıktılara Git
                              </button>
                            </div>

                            <div className="project-section">
                              {activeProjectDetail.outputs?.length > 0 ? (
                                <ul>
                                  {activeProjectDetail.outputs.slice(0, 5).map((output) => (
                                    <li key={output.id}>
                                      {output.title} — {output.output_type} / {output.status}
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <p className="panel-label">Bu proje için kayıtlı çıktı yok.</p>
                              )}
                            </div>
                          </div>
                        </div>
                      </>
                    ) : (
                      <p className="panel-label">
                        Aktif proje seçilmedi. Projeler panelinden bir projeyi aktif yapabilirsin.
                      </p>
                    )}
                  </div>


                  <div className="project-grid">
                    <div className="project-card">
                      <div className="project-card-header">
                        <div>
                          <p className="panel-label">Öncelikli görevler</p>
                          <h3>Bugün bakılacak işler</h3>
                        </div>
                        <button className="small-action-button" onClick={openTasksView}>
                          Görevlere Git
                        </button>
                      </div>

                      <div className="project-section">
                        {workspaceSummary.high_priority_tasks.length > 0 ? (
                          <ul>
                            {workspaceSummary.high_priority_tasks.slice(0, 5).map((task) => (
                              <li key={task.id}>
                                {task.title} — {task.project_id || "Genel"} / {task.priority}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="panel-label">Yüksek öncelikli açık görev yok.</p>
                        )}
                      </div>
                    </div>

                    <div className="project-card">
                      <div className="project-card-header">
                        <div>
                          <p className="panel-label">Bekleyen onaylar</p>
                          <h3>Riskli işlemler</h3>
                        </div>
                        <button className="small-action-button" onClick={openApprovalsView}>
                          Onaylara Git
                        </button>
                      </div>

                      <div className="project-section">
                        {workspaceSummary.pending_approvals.length > 0 ? (
                          <ul>
                            {workspaceSummary.pending_approvals.slice(0, 5).map((approval) => (
                              <li key={approval.id}>
                                {approval.title} — {approval.risk_level}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="panel-label">Bekleyen onay yok.</p>
                        )}
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="panel-card">
                  <strong>Dashboard yüklenemedi.</strong>
                  <p className="panel-label">Backend çalışıyor mu kontrol edelim.</p>
                </div>
              )}
            </div>
          </>
        ) : null}

        {activeView === "chat" ? (
          <>
            <header className="topbar">
              <div>
                <p className="eyebrow">Kişisel yapay zeka iş arkadaşın</p>
                <h2>Vex ile sohbet et</h2>
              </div>

              <div className="topbar-actions">
                <button
                  className="small-action-button"
                  type="button"
                  onClick={() => setAutoSendVoiceEnabled((value) => !value)}
                >
                  Otomatik Gönder: {autoSendVoiceEnabled ? "Açık" : "Kapalı"}
                </button>

                <button
                  className="small-action-button"
                  type="button"
                  onClick={() => setVoiceReplyEnabled((value) => !value)}
                >
                  Sesli Cevap: {voiceReplyEnabled ? "Açık" : "Kapalı"}
                </button>

                <button
                  className="small-action-button"
                  type="button"
                  onClick={stopSpeaking}
                >
                  Sesi Durdur
                </button>

                <span className={`status-pill backend-${backendStatus === "checking" ? "online" : backendStatus}`}>
                  {getBackendLabel()}
                </span>

                <span className="status-pill">
                  {isRecording
                    ? "Kayıt alınıyor..."
                    : isTranscribing
                      ? "Yazıya çevriliyor..."
                      : "Otomatik dinleme aktif"}
                </span>
              </div>
            </header>

            <div className="conversation">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`message ${message.sender === "Sen" ? "user" : "assistant"}`}
                >
                  <span>{message.sender}</span>
                  <p>{message.text}</p>
                </div>
              ))}
              {isTyping ? (
                <div className="message assistant">
                  <span>Vex</span>
                  <p className="typing-indicator">yazıyor<span className="typing-dots">...</span></p>
                </div>
              ) : null}
            </div>

            <div className="composer">
              <button
                className={`mic-button ${isRecording ? "recording" : ""}`}
                type="button"
                onClick={listenAndTranscribe}
                disabled={isSending || isTranscribing || backendStatus === "offline"}
                title="Konuş; sessizlikte otomatik durur"
              >
                {isRecording ? "Dinliyor..." : isTranscribing ? "Çevriliyor..." : "Mikrofon"}
              </button>

              <input
                placeholder="Vex'e bir şey yaz veya mikrofonla konuş..."
                value={input}
                disabled={isSending || isRecording || isTranscribing}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    sendMessage();
                  }
                }}
              />

              <button
                onClick={() => sendMessage()}
                disabled={
                  isSending ||
                  isRecording ||
                  isTranscribing ||
                  backendStatus === "offline"
                }
              >
                {isSending ? "Düşünüyor..." : "Gönder"}
              </button>
            </div>
          </>
        ) : null}

        {activeView === "memory" ? (
          <>
            <header className="topbar">
              <div>
                <p className="eyebrow">Kalıcı hafıza merkezi</p>
                <h2>Vex Hafızası</h2>
              </div>
              <button className="small-action-button" onClick={loadMemory}>
                Yenile
              </button>
            </header>

            <div className="memory-page">
              {isMemoryLoading ? (
                <div className="panel-card">
                  <strong>Hafıza yükleniyor...</strong>
                </div>
              ) : memoryData ? (
                <>
                  <div className="memory-grid">
                    <div className="memory-card">
                      <p className="panel-label">Kullanıcı</p>
                      <h3>{memoryData.user?.preferred_name ?? "Bilinmiyor"}</h3>
                    </div>

                    <div className="memory-card">
                      <p className="panel-label">Asistan</p>
                      <h3>{memoryData.assistant?.name ?? "Vex"}</h3>
                      <p>{memoryData.assistant?.role}</p>
                    </div>

                    <div className="memory-card">
                      <p className="panel-label">Proje mottosu</p>
                      <h3>{memoryData.project?.motto}</h3>
                    </div>

                    <div className="memory-card">
                      <p className="panel-label">Ana model</p>
                      <h3>{memoryData.ai?.primary_model_provider}</h3>
                    </div>
                  </div>

                  <div className="memory-section">
                    <div className="memory-section-header">
                      <div>
                        <p className="eyebrow">Kurallar</p>
                        <h3>Vex’in hatırladığı kurallar</h3>
                      </div>
                      <span className="status-pill">
                        {memoryData.rules?.length ?? 0} kural
                      </span>
                    </div>

                    <div className="rule-list">
                      {memoryData.rules?.map((rule, index) => (
                        <div className="rule-item" key={`${rule}-${index}`}>
                          <span>{index + 1}</span>
                          <p>{rule}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <div className="panel-card">
                  <strong>Hafıza yüklenemedi.</strong>
                  <p className="panel-label">
                    Backend’in çalıştığından emin olalım.
                  </p>
                </div>
              )}
            </div>
          </>
        ) : null}

        {activeView === "projects" ? (
          <>
            <header className="topbar">
              <div>
                <p className="eyebrow">Proje merkezi</p>
                <h2>Vex Projeleri</h2>
              </div>
              <div className="topbar-actions">
                <button
                  className="small-action-button"
                  onClick={() => setShowProjectForm((value) => !value)}
                >
                  {showProjectForm ? "Formu Kapat" : "Yeni Proje"}
                </button>
                <button className="small-action-button" onClick={loadProjects}>
                  Yenile
                </button>
              </div>
            </header>

            <div className="projects-page">
              {showProjectForm ? (
                <div className="project-form">
                  <div>
                    <p className="eyebrow">Yeni proje</p>
                    <h3>Vex’e yeni proje ekle</h3>
                  </div>

                  <div className="form-grid">
                    <label>
                      Proje adı
                      <input
                        value={projectName}
                        onChange={(event) => setProjectName(event.target.value)}
                        placeholder="Örn: Yeni Shopify Sitesi"
                      />
                    </label>

                    <label>
                      Proje tipi
                      <input
                        value={projectType}
                        onChange={(event) => setProjectType(event.target.value)}
                        placeholder="Örn: E-ticaret / Shopify"
                      />
                    </label>
                  </div>

                  <label>
                    Açıklama
                    <textarea
                      value={projectDescription}
                      onChange={(event) => setProjectDescription(event.target.value)}
                      placeholder="Bu proje ne için oluşturuluyor?"
                    />
                  </label>

                  <label>
                    Ana hedefler
                    <textarea
                      value={projectGoals}
                      onChange={(event) => setProjectGoals(event.target.value)}
                      placeholder={"Her satıra bir hedef yaz\nÖrn: Global site yapısı kurulacak"}
                    />
                  </label>

                  <label>
                    Notlar
                    <textarea
                      value={projectNotes}
                      onChange={(event) => setProjectNotes(event.target.value)}
                      placeholder={"Her satıra bir not yaz\nÖrn: Tasarım modern ve premium olacak"}
                    />
                  </label>

                  <div className="form-actions">
                    <button
                      className="small-action-button"
                      onClick={createProject}
                      disabled={isCreatingProject}
                    >
                      {isCreatingProject ? "Kaydediliyor..." : "Projeyi Kaydet"}
                    </button>
                  </div>
                </div>
              ) : null}

              {isProjectsLoading ? (
                <div className="panel-card">
                  <strong>Projeler yükleniyor...</strong>
                </div>
              ) : projects.length > 0 ? (
                <div className="project-grid">
                  {projects.map((project) => (
                    <div className="project-card" key={project.id}>
                      <div className="project-card-header">
                        <div>
                          <p className="panel-label">{project.type}</p>
                          <h3>{project.name}</h3>
                        </div>

                        <div className="project-card-actions">
                          {activeProjectId === project.id ? (
                            <span className="status-pill">Aktif Proje</span>
                          ) : (
                            <button
                              className="small-action-button"
                              type="button"
                              onClick={() => setProjectAsActive(project.id)}
                            >
                              Aktif Yap
                            </button>
                          )}

                          <span className="status-pill">{project.status}</span>

                          <button
                            className="danger-button"
                            type="button"
                            onClick={() => deleteProject(project.id)}
                          >
                            Sil
                          </button>
                        </div>
                      </div>

                      <p className="project-description">{project.description}</p>

                      <div className="project-section">
                        <p className="panel-label">Ana hedefler</p>
                        <ul>
                          {project.main_goals.map((goal, index) => (
                            <li key={`${project.id}-goal-${index}`}>{goal}</li>
                          ))}
                        </ul>
                      </div>

                      <div className="project-section">
                        <p className="panel-label">Notlar</p>
                        <ul>
                          {project.notes.map((note, index) => (
                            <li key={`${project.id}-note-${index}`}>{note}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="panel-card">
                  <strong>Henüz proje yok.</strong>
                  <p className="panel-label">
                    Backend’de projects.json dosyasını kontrol edelim.
                  </p>
                </div>
              )}
            </div>
          </>
        ) : null}

        {activeView === "tasks" ? (
          <>
            <header className="topbar">
              <div>
                <p className="eyebrow">Görev merkezi</p>
                <h2>Vex Görevleri</h2>
              </div>
              <div className="topbar-actions">
                <button className="small-action-button" onClick={loadTasks}>
                  Yenile
                </button>
              </div>
            </header>

            <div className="projects-page">
              {isTasksLoading ? (
                <div className="panel-card">
                  <strong>Görevler yükleniyor...</strong>
                </div>
              ) : tasks.length > 0 ? (
                <div className="project-grid">
                  {tasks.map((task) => (
                    <div className="project-card" key={task.id}>
                      <div className="project-card-header">
                        <div>
                          <p className="panel-label">
                            {task.project_id ? `Proje: ${task.project_id}` : "Genel görev"}
                          </p>
                          <h3>{task.title}</h3>
                        </div>

                        <div className="project-card-actions">
                          {activeTaskId === task.id ? (
                            <span className="status-pill">Aktif Görev</span>
                          ) : (
                            <button
                              className="small-action-button"
                              type="button"
                              onClick={() => setTaskAsActive(task.id)}
                            >
                              Aktif Yap
                            </button>
                          )}

                          <span className="status-pill">{task.priority}</span>
                          <span className="status-pill">{task.status}</span>

                          {task.status !== "tamamlandı" ? (
                            <button
                              className="small-action-button"
                              type="button"
                              onClick={() => completeTask(task.id)}
                            >
                              Tamamla
                            </button>
                          ) : null}

                          <button
                            className="danger-button"
                            type="button"
                            onClick={() => deleteTask(task.id)}
                          >
                            Sil
                          </button>
                        </div>
                      </div>

                      <p className="project-description">
                        {task.description || "Açıklama yok."}
                      </p>

                      {task.notes?.length > 0 ? (
                        <div className="project-section">
                          <p className="panel-label">Notlar</p>
                          <ul>
                            {task.notes.map((note, index) => (
                              <li key={`${task.id}-note-${index}`}>{note}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="panel-card">
                  <strong>Henüz görev yok.</strong>
                  <p className="panel-label">
                    Sohbette “Bilsanpack için şu işi görev olarak ekle” diyebilirsin.
                  </p>
                </div>
              )}
            </div>
          </>
        ) : null}


        {activeView === "approvals" ? (
          <>
            <header className="topbar">
              <div>
                <p className="eyebrow">Onay merkezi</p>
                <h2>Bekleyen Onaylar</h2>
              </div>
              <div className="topbar-actions">
                <button className="small-action-button" onClick={loadApprovals}>
                  Yenile
                </button>
              </div>
            </header>

            <div className="projects-page">
              {isApprovalsLoading ? (
                <div className="panel-card">
                  <strong>Onaylar yükleniyor...</strong>
                </div>
              ) : approvals.length > 0 ? (
                <div className="project-grid">
                  {approvals.map((approval) => (
                    <div className="project-card" key={approval.id}>
                      <div className="project-card-header">
                        <div>
                          <p className="panel-label">
                            {approval.project_id ? `Proje: ${approval.project_id}` : "Genel onay"}
                          </p>
                          <h3>{approval.title}</h3>
                        </div>

                        <div className="project-card-actions">
                          <span className="status-pill">{approval.risk_level}</span>
                          <span className="status-pill">{approval.status}</span>

                          {approval.status === "bekliyor" ? (
                            <>
                              <button
                                className="small-action-button"
                                type="button"
                                onClick={() => approveApproval(approval.id)}
                              >
                                Onayla
                              </button>

                              <button
                                className="danger-button"
                                type="button"
                                onClick={() => rejectApproval(approval.id)}
                              >
                                Reddet
                              </button>
                            </>
                          ) : null}

                          <button
                            className="danger-button"
                            type="button"
                            onClick={() => deleteApproval(approval.id)}
                          >
                            Sil
                          </button>
                        </div>
                      </div>

                      <p className="project-description">
                        {approval.description || "Açıklama yok."}
                      </p>

                      <div className="project-section">
                        <p className="panel-label">İşlem tipi</p>
                        <ul>
                          <li>{approval.action_type}</li>
                        </ul>
                      </div>

                      {approval.payload && Object.keys(approval.payload).length > 0 ? (
                        <div className="project-section">
                          <p className="panel-label">İşlem detayları</p>
                          <pre className="payload-preview">
                            {JSON.stringify(approval.payload, null, 2)}
                          </pre>
                        </div>
                      ) : null}

                      {approval.notes?.length > 0 ? (
                        <div className="project-section">
                          <p className="panel-label">Notlar</p>
                          <ul>
                            {approval.notes.map((note, index) => (
                              <li key={`${approval.id}-note-${index}`}>{note}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="panel-card">
                  <strong>Bekleyen onay yok.</strong>
                  <p className="panel-label">
                    Riskli işlemler burada Mert onayı bekleyecek.
                  </p>
                </div>
              )}
            </div>
          </>
        ) : null}


        {activeView === "outputs" ? (
          <>
            <header className="topbar">
              <div>
                <p className="eyebrow">Proje çıktıları</p>
                <h2>Kaydedilen Çıktılar</h2>
              </div>
              <div className="topbar-actions">
                <button className="small-action-button" onClick={loadOutputs}>
                  Yenile
                </button>
              </div>
            </header>

            <div className="projects-page">
              {isOutputsLoading ? (
                <div className="panel-card">
                  <strong>Çıktılar yükleniyor...</strong>
                </div>
              ) : outputs.length > 0 ? (
                <div className="project-grid">
                  {outputs.map((output) => (
                    <div className="project-card" key={output.id}>
                      <div className="project-card-header">
                        <div>
                          <p className="panel-label">
                            {output.project_id ? `Proje: ${output.project_id}` : "Genel çıktı"}
                          </p>
                          <h3>{output.title}</h3>
                        </div>

                        <div className="project-card-actions">
                          <span className="status-pill">{output.output_type}</span>
                          <span className="status-pill">{output.status}</span>

                          <button
                            className="danger-button"
                            type="button"
                            onClick={() => deleteOutput(output.id)}
                          >
                            Sil
                          </button>
                        </div>
                      </div>

                      <div className="project-section">
                        <p className="panel-label">Bağlı görev</p>
                        <ul>
                          <li>{output.task_id || "Bağlı görev yok"}</li>
                        </ul>
                      </div>

                      <div className="project-section">
                        <p className="panel-label">İçerik</p>
                        <pre className="payload-preview">{output.content}</pre>
                      </div>

                      {output.notes?.length > 0 ? (
                        <div className="project-section">
                          <p className="panel-label">Notlar</p>
                          <ul>
                            {output.notes.map((note, index) => (
                              <li key={`${output.id}-note-${index}`}>{note}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="panel-card">
                  <strong>Henüz kayıtlı çıktı yok.</strong>
                  <p className="panel-label">
                    Vex bir metin ürettikten sonra “bunu kaydet” diyebilirsin.
                  </p>
                </div>
              )}
            </div>
          </>
        ) : null}


        {activeView === "reminders" ? (
          <>
            <header className="topbar">
              <div>
                <p className="eyebrow">Alarm ve hatırlatma sistemi</p>
                <h2>Hatırlatmalar</h2>
              </div>
              <div className="topbar-actions">
                <button className="small-action-button" onClick={loadReminders}>
                  Yenile
                </button>
              </div>
            </header>

            <div className="projects-page">
              {isRemindersLoading ? (
                <div className="panel-card">
                  <strong>Hatırlatmalar yükleniyor...</strong>
                </div>
              ) : reminders.length > 0 ? (
                <div className="project-grid">
                  {reminders.map((reminder) => (
                    <div className="project-card" key={reminder.id}>
                      <div className="project-card-header">
                        <div>
                          <p className="panel-label">
                            {reminder.project_id ? `Proje: ${reminder.project_id}` : "Genel hatırlatma"}
                          </p>
                          <h3>{reminder.title}</h3>
                        </div>

                        <div className="project-card-actions">
                          <span className="status-pill">{reminder.status}</span>
                          <span className="status-pill">{reminder.notified ? "bildirildi" : "bekliyor"}</span>

                          <button
                            className="danger-button"
                            type="button"
                            onClick={() => deleteReminder(reminder.id)}
                          >
                            Sil
                          </button>
                        </div>
                      </div>

                      <div className="project-section">
                        <p className="panel-label">Zaman</p>
                        <ul>
                          <li>{reminder.remind_at}</li>
                        </ul>
                      </div>

                      <div className="project-section">
                        <p className="panel-label">Bağlantı</p>
                        <ul>
                          <li>Görev: {reminder.task_id || "Bağlı görev yok"}</li>
                        </ul>
                      </div>

                      {reminder.notes?.length > 0 ? (
                        <div className="project-section">
                          <p className="panel-label">Notlar</p>
                          <ul>
                            {reminder.notes.map((note, index) => (
                              <li key={`${reminder.id}-note-${index}`}>{note}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="panel-card">
                  <strong>Henüz hatırlatma yok.</strong>
                  <p className="panel-label">
                    “30 dakika sonra beni uyar” veya “saat 18:00’de bunu hatırlat” diyebilirsin.
                  </p>
                </div>
              )}
            </div>
          </>
        ) : null}

        {activeView === "evolution" ? (
          <>
            <header className="topbar">
              <div>
                <p className="eyebrow">Yapay Zeka ile Kendi Kendine Gelişen Dashboard</p>
                <h2>Sistem Geliştirici (Evrim Merkezi)</h2>
              </div>
              <div className="topbar-actions">
                <span className={`status-pill backend-${isEvolutionRunning ? "offline" : "online"}`}>
                  {isEvolutionRunning ? "Evrim Çalışıyor..." : "Evrim Hazır"}
                </span>
                <span className="status-pill backend-online" style={{ background: "rgba(16, 151, 65, 0.2)", color: "#109741" }}>
                  GÜVENLİ MOD AKTİF
                </span>
              </div>
            </header>

            <div className="projects-page">
              {/* Onay Bekleyen İşlemler Kartı */}
              {pendingEvolutionActions.length > 0 ? (
                <div className="panel-card" style={{ marginBottom: "20px", border: "1px solid #ffcc00", background: "rgba(255, 204, 0, 0.05)" }}>
                  <p className="panel-label" style={{ color: "#ffcc00", fontWeight: "bold", fontSize: "14px" }}>⚠️ KULLANICI ONAYI BEKLEYEN İŞLEM</p>
                  <p style={{ fontSize: "13px", color: "#aeb7c8", marginBottom: "15px" }}>
                    Güvenli Geliştirici Modu devrede. Vex'in aşağıdaki kritik eylemi gerçekleştirmesi için onayınız gerekiyor:
                  </p>
                  
                  {pendingEvolutionActions.map((action) => (
                    <div key={action.id} style={{ background: "rgba(0,0,0,0.3)", borderRadius: "8px", padding: "15px", marginBottom: "15px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "10px" }}>
                        <strong>Tip: <span style={{ color: "#ffcc00" }}>{action.action_type}</span></strong>
                        <span className="status-pill" style={{ background: "rgba(224, 94, 94, 0.2)", color: "#ff4d4d" }}>Risk: {action.risk_level}</span>
                      </div>
                      
                      {action.reason && (
                        <p style={{ fontSize: "13px", color: "#f5f7fb", marginBottom: "10px" }}>
                          <strong>Vex'in Gerekçesi:</strong> {action.reason}
                        </p>
                      )}

                      {action.target_path && (
                        <p style={{ fontSize: "13px", color: "#8d96aa", marginBottom: "10px", fontFamily: "Courier, monospace" }}>
                          <strong>Dosya:</strong> {action.target_path}
                        </p>
                      )}

                      {action.command && (
                        <pre style={{ background: "#000", padding: "10px", borderRadius: "5px", fontSize: "12px", color: "#00ff66", overflowX: "auto" }}>
                          <code>{action.command}</code>
                        </pre>
                      )}

                      {action.replacement && (
                        <div style={{ marginTop: "10px" }}>
                          <p style={{ fontSize: "12px", color: "#8d96aa", marginBottom: "5px" }}><strong>Yapılacak Değişiklik:</strong></p>
                          <pre style={{ background: "rgba(16,151,65,0.08)", padding: "10px", borderRadius: "5px", fontSize: "11px", color: "#16c766", overflowX: "auto", borderLeft: "3px solid #16c766" }}>
                            <code>{action.replacement}</code>
                          </pre>
                        </div>
                      )}

                      {action.after_content && (
                        <div style={{ marginTop: "10px" }}>
                          <p style={{ fontSize: "12px", color: "#8d96aa", marginBottom: "5px" }}><strong>Yazılacak Yeni İçerik:</strong></p>
                          <pre style={{ background: "rgba(16,151,65,0.08)", padding: "10px", borderRadius: "5px", fontSize: "11px", color: "#16c766", overflowX: "auto", borderLeft: "3px solid #16c766", maxHeight: "150px" }}>
                            <code>{action.after_content}</code>
                          </pre>
                        </div>
                      )}

                      <div style={{ display: "flex", gap: "10px", marginTop: "15px" }}>
                        <button
                          onClick={() => approveEvolutionAction(action.id)}
                          style={{
                            flex: 1, padding: "10px", borderRadius: "8px", border: 0,
                            background: "#109741", color: "white", fontWeight: "bold", cursor: "pointer"
                          }}
                        >
                          İşlemi Onayla ve Çalıştır
                        </button>
                        <button
                          onClick={() => rejectEvolutionAction(action.id)}
                          style={{
                            flex: 1, padding: "10px", borderRadius: "8px", border: 0,
                            background: "#e05e5e", color: "white", fontWeight: "bold", cursor: "pointer"
                          }}
                        >
                          İşlemi Reddet / İptal Et
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}

              <div className="panel-card" style={{ marginBottom: "20px" }}>
                <p className="panel-label">Evrim Talimatı</p>
                <p style={{ fontSize: "14px", color: "#aeb7c8", marginBottom: "15px" }}>
                  Vex'e yeni bir özellik eklemesini, yeni bir sayfa açmasını veya mevcut tasarımı/fonksiyonları
                  değiştirmesini söyleyin. Vex kendi kodunu yazacak, test edecek ve sistemi otomatik güncelleyecektir.
                </p>
                
                <div style={{ display: "flex", gap: "10px" }}>
                  <input
                    type="text"
                    value={evolutionPrompt}
                    onChange={(e) => setEvolutionPrompt(e.target.value)}
                    placeholder="Örn: 'Dashboard'a stok uyarı grafiği ekle ve verileri mock eden yeni bir backend endpoint'i oluştur.'"
                    style={{
                      flex: 1,
                      padding: "12px 16px",
                      borderRadius: "10px",
                      border: "1px solid rgba(255, 255, 255, 0.1)",
                      background: "rgba(255, 255, 255, 0.05)",
                      color: "white"
                    }}
                    disabled={isEvolutionRunning}
                  />
                  <button
                    onClick={startEvolution}
                    disabled={isEvolutionRunning || !evolutionPrompt.trim()}
                    style={{
                      padding: "12px 24px",
                      borderRadius: "10px",
                      border: 0,
                      background: isEvolutionRunning ? "#e05e5e" : "#109741",
                      color: "white",
                      fontWeight: "bold",
                      cursor: isEvolutionRunning ? "not-allowed" : "pointer"
                    }}
                  >
                    {isEvolutionRunning ? "Geliştiriliyor..." : "Sistemi Geliştir"}
                  </button>
                </div>
              </div>

              <div className="panel-card" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <p className="panel-label">Evrim Logları (Gerçek Zamanlı Terminal)</p>
                <div
                  style={{
                    background: "#04060a",
                    border: "1px solid rgba(255, 255, 255, 0.05)",
                    borderRadius: "10px",
                    padding: "15px",
                    height: "400px",
                    overflowY: "auto",
                    fontFamily: "Courier, monospace",
                    fontSize: "13px",
                    color: "#00ff66",
                    display: "flex",
                    flexDirection: "column",
                    gap: "6px"
                  }}
                >
                  {evolutionLogs.length === 0 ? (
                    <span style={{ color: "#8d96aa" }}>Evrim logları bekleniyor. Henüz işlem başlatılmadı...</span>
                  ) : (
                    evolutionLogs.map((log, index) => {
                      let color = "#00ff66";
                      if (log.includes("[ERROR]")) color = "#ff4d4d";
                      if (log.includes("[SECURITY-BLOCK]")) color = "#ff4d4d";
                      if (log.includes("[INFO]")) color = "#3399ff";
                      if (log.includes("[AGENT-THOUGHT]")) color = "#ffcc00";
                      if (log.includes("[WAITING-APPROVAL]")) color = "#ffcc00";
                      if (log.includes("[SUCCESS]")) color = "#33cc33";
                      return <div key={index} style={{ color }}>{log}</div>;
                    })
                  )}
                </div>
              </div>
            </div>
          </>
        ) : null}

        {activeView === "computer" ? (
          <>
            <header className="topbar">
              <div>
                <p className="eyebrow">Bilgisayar Kontrol Modülü</p>
                <h2>Bilgisayar Kontrol</h2>
              </div>
              <div className="topbar-actions">
                <span className={`status-pill backend-${computerUseRunning ? "offline" : "online"}`}>
                  {computerUseRunning ? "Görev Çalışıyor..." : "Hazır"}
                </span>
                <span className="status-pill backend-online" style={{ background: "rgba(16, 151, 65, 0.2)", color: "#109741" }}>
                  pyautogui aktif
                </span>
              </div>
            </header>

            <div className="projects-page">
              {/* Sistem Bilgisi Kartı */}
              <div className="panel-card" style={{ marginBottom: "20px", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "15px" }}>
                <div>
                  <p className="panel-label" style={{ margin: 0 }}>Aktif Görev ID</p>
                  <strong style={{ fontSize: "14px", color: currentComputerTaskId ? "#ffcc00" : "#8d96aa" }}>
                    {currentComputerTaskId || "Yok"}
                  </strong>
                </div>
                <div>
                  <p className="panel-label" style={{ margin: 0 }}>Son Algılanan Niyet</p>
                  <strong style={{ fontSize: "14px", color: "#3399ff" }}>
                    {lastComputerIntent}
                  </strong>
                </div>
                <div>
                  <p className="panel-label" style={{ margin: 0 }}>Son Aksiyon</p>
                  <strong style={{ fontSize: "14px", color: "#16c766" }}>
                    {lastComputerAction}
                  </strong>
                </div>
              </div>

              {/* Önerilen Manuel Adım Onay Kartı */}
              {manualPendingAction ? (
                <div className="panel-card" style={{ marginBottom: "20px", border: "1px solid #ffcc00", background: "rgba(255, 204, 0, 0.05)" }}>
                  <p className="panel-label" style={{ color: "#ffcc00", fontWeight: "bold" }}>⚠️ MANUEL ADIM ONAYI BEKLENİYOR</p>
                  <p style={{ fontSize: "13px", color: "#aeb7c8", marginBottom: "15px" }}>
                    Vex bir sonraki adım için şu aksiyonu önerdi. Lütfen inceleyip onaylayın veya reddedin:
                  </p>
                  <div style={{ background: "rgba(0,0,0,0.3)", borderRadius: "8px", padding: "15px", marginBottom: "15px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "10px" }}>
                      <strong>Aksiyon: <span style={{ color: "#ffcc00" }}>{manualPendingAction.action}</span></strong>
                      {manualPendingAction.risk_level && (
                        <span className="status-pill" style={{ background: "rgba(224, 94, 94, 0.2)", color: "#ff4d4d" }}>Risk: {manualPendingAction.risk_level}</span>
                      )}
                    </div>
                    {manualPendingAction.thought && (
                      <p style={{ fontSize: "13px", color: "#f5f7fb", marginBottom: "10px" }}>
                        <strong>Vex'in Düşüncesi:</strong> {manualPendingAction.thought}
                      </p>
                    )}
                    {manualPendingAction.x !== undefined && (
                      <p style={{ fontSize: "13px", color: "#8d96aa", fontFamily: "Courier, monospace" }}>
                        <strong>Koordinatlar:</strong> X: {manualPendingAction.x}, Y: {manualPendingAction.y}
                      </p>
                    )}
                    {manualPendingAction.text && (
                      <p style={{ fontSize: "13px", color: "#8d96aa" }}>
                        <strong>Yazılacak Metin:</strong> "{manualPendingAction.text}"
                      </p>
                    )}
                    <div style={{ display: "flex", gap: "10px", marginTop: "15px" }}>
                      <button
                        onClick={async () => {
                          try {
                            const res = await fetch("http://127.0.0.1:8000/computer/step/approve", { method: "POST" });
                            if (!res.ok) {
                              throw new Error("Manuel adım onaylanamadı.");
                            }
                            setManualPendingAction(null);
                            pollComputerStatus();
                          } catch (e) {
                            alert("Onaylanamadı.");
                          }
                        }}
                        style={{
                          flex: 1, padding: "10px", borderRadius: "8px", border: 0,
                          background: "#109741", color: "white", fontWeight: "bold", cursor: "pointer"
                        }}
                      >
                        Bu Adımı Uygula
                      </button>
                      <button
                        onClick={async () => {
                          try {
                            await fetch("http://127.0.0.1:8000/computer/step/reject", { method: "POST" });
                            setManualPendingAction(null);
                            pollComputerStatus();
                          } catch (e) {
                            alert("Reddedilemedi.");
                          }
                        }}
                        style={{
                          flex: 1, padding: "10px", borderRadius: "8px", border: 0,
                          background: "#e05e5e", color: "white", fontWeight: "bold", cursor: "pointer"
                        }}
                      >
                        Reddet / Yeni Analiz İste
                      </button>
                    </div>
                  </div>
                </div>
              ) : null}

              <div className="panel-card" style={{ marginBottom: "20px" }}>
                <p className="panel-label">Ekran Görüntüsü</p>
                <div style={{ display: "flex", gap: "10px", marginBottom: "15px" }}>
                  <button
                    className="small-action-button"
                    onClick={async () => {
                      try {
                        const res = await fetch("http://127.0.0.1:8000/computer/screenshot");
                        const data = await res.json();
                        if (data.success) {
                          setComputerScreenshot(data.image_base64);
                          setComputerScreenshotTime(data.timestamp);
                        } else {
                          alert(data.message || "Screenshot alınamadı.");
                        }
                      } catch (e) {
                        alert("Screenshot alınamadı.");
                      }
                    }}
                  >
                    Ekranı Yenile
                  </button>
                  <button
                    className="small-action-button"
                    onClick={async () => {
                      try {
                        const res = await fetch("http://127.0.0.1:8000/computer/observe", { method: "POST" });
                        const data = await res.json();
                        if (data.success) {
                          setComputerAnalysis(data.analysis);
                          pollComputerStatus();
                        } else {
                          alert(data.message || "Ekran analizi yapılamadı.");
                        }
                      } catch (e) {
                        alert("Ekran analizi yapılamadı.");
                      }
                    }}
                  >
                    Ekranı Analiz Et
                  </button>
                </div>

                {computerScreenshot ? (
                  <div style={{ marginBottom: "15px" }}>
                    <img
                      src={`data:image/png;base64,${computerScreenshot}`}
                      alt="Ekran görüntüsü"
                      style={{ maxWidth: "100%", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.1)" }}
                    />
                    <p style={{ fontSize: "12px", color: "#8d96aa", marginTop: "5px" }}>
                      Son güncelleme: {computerScreenshotTime}
                    </p>
                  </div>
                ) : (
                  <div className="panel-card" style={{ marginBottom: "15px" }}>
                    <p>Henüz screenshot alınmadı. "Ekranı Yenile" butonuna basın.</p>
                  </div>
                )}

                {computerAnalysis && (
                  <div className="panel-card" style={{ marginBottom: "15px", background: "rgba(16,151,65,0.08)", borderLeft: "3px solid #16c766" }}>
                    <p className="panel-label">AI Ekran Analizi</p>
                    <p style={{ whiteSpace: "pre-wrap" }}>{computerAnalysis}</p>
                  </div>
                )}
              </div>

              <div className="panel-card" style={{ marginBottom: "20px" }}>
                <p className="panel-label">Görev Gönder</p>
                <div style={{ display: "flex", gap: "10px", marginBottom: "15px" }}>
                  <input
                    type="text"
                    value={computerTaskInput}
                    onChange={(e) => setComputerTaskInput(e.target.value)}
                    placeholder="Örn: 'Ekranıma bak ve Shopify siparişler sayfasını açmaya çalış'"
                    style={{
                      flex: 1,
                      padding: "12px 16px",
                      borderRadius: "10px",
                      border: "1px solid rgba(255, 255, 255, 0.1)",
                      background: "rgba(255, 255, 255, 0.05)",
                      color: "white"
                    }}
                    disabled={computerUseRunning}
                  />
                  <button
                    onClick={async () => {
                      if (!computerTaskInput.trim()) return;
                      try {
                        const res = await fetch("http://127.0.0.1:8000/computer/task", {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({
                            instruction: computerTaskInput,
                            mode: computerMode,
                            max_steps: 20
                          }),
                        });
                        const data = await res.json();
                        if (data.success) {
                          setComputerTaskInput("");
                          setComputerLastResult(data);
                          pollComputerStatus();
                        } else {
                          alert(data.message || "Görev başlatılamadı.");
                        }
                      } catch (e) {
                        alert("Görev başlatılamadı.");
                      }
                    }}
                    style={{
                      padding: "12px 24px",
                      borderRadius: "10px",
                      border: 0,
                      background: "#109741",
                      color: "white",
                      fontWeight: "bold",
                      cursor: computerUseRunning ? "not-allowed" : "pointer"
                    }}
                    disabled={computerUseRunning}
                  >
                    Görevi Başlat
                  </button>
                  <button
                    onClick={async () => {
                      try {
                        await fetch("http://127.0.0.1:8000/computer/stop", { method: "POST" });
                        pollComputerStatus();
                      } catch (e) {
                        alert("Durdurulamadı.");
                      }
                    }}
                    style={{
                      padding: "12px 24px",
                      borderRadius: "10px",
                      border: 0,
                      background: "#e05e5e",
                      color: "white",
                      fontWeight: "bold",
                      cursor: "pointer"
                    }}
                  >
                    Durdur
                  </button>
                </div>

                <div style={{ marginBottom: "15px" }}>
                  <label style={{ fontSize: "13px", color: "#aeb7c8", marginRight: "10px" }}>Çalışma Modu:</label>
                  <select
                    value={computerMode}
                    onChange={(e) => setComputerMode(e.target.value)}
                    style={{
                      padding: "8px 12px",
                      borderRadius: "6px",
                      border: "1px solid rgba(255,255,255,0.1)",
                      background: "rgba(255,255,255,0.05)",
                      color: "white"
                    }}
                  >
                    <option value="assisted_fast">assisted_fast (otomatik)</option>
                    <option value="observe_only">observe_only (sadece izle)</option>
                    <option value="manual_step">manual_step (adım adım onay)</option>
                  </select>
                </div>

                {computerLastResult && (
                  <div className="panel-card" style={{ background: "rgba(0,0,0,0.2)", marginBottom: "15px" }}>
                    <p className="panel-label">Son Sonuç</p>
                    <pre style={{ whiteSpace: "pre-wrap", fontSize: "13px" }}>
                      {JSON.stringify(computerLastResult, null, 2)}
                    </pre>
                  </div>
                )}
              </div>

              <div className="panel-card" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <p className="panel-label">Computer Use Logları</p>
                <div
                  style={{
                    background: "#04060a",
                    border: "1px solid rgba(255, 255, 255, 0.05)",
                    borderRadius: "10px",
                    padding: "15px",
                    height: "300px",
                    overflowY: "auto",
                    fontFamily: "Courier, monospace",
                    fontSize: "13px",
                    color: "#00ff66",
                    display: "flex",
                    flexDirection: "column",
                    gap: "6px"
                }}
                >
                  {computerLogs.length === 0 ? (
                    <span style={{ color: "#8d96aa" }}>Henüz log yok.</span>
                  ) : (
                    computerLogs.map((log, index) => {
                      let color = "#00ff66";
                      if (log.includes("ERROR") || log.includes("FAIL")) color = "#ff4d4d";
                      if (log.includes("Stopped")) color = "#ffcc00";
                      return <div key={index} style={{ color }}>{log}</div>;
                    })
                  )}
                </div>
              </div>
            </div>
          </>
        ) : null}

      </section>

      <aside className="work-panel">
        <h3>İş Paneli</h3>

        <div className="panel-card">
          <p className="panel-label">Backend durumu</p>
          <strong>{getBackendLabel()}</strong>
          <p className="panel-label">{backendMessage}</p>
        </div>

        <div className="panel-card">
          <p className="panel-label">Aktif proje</p>
          <strong>{activeProject?.name ?? "Seçilmedi"}</strong>
        </div>

        <div className="panel-card">
          <p className="panel-label">Aktif görev</p>
          <strong>{activeTask?.title ?? "Seçilmedi"}</strong>
        </div>

        <div className="panel-card">
          <p className="panel-label">Aktif bölüm</p>
          <strong>{getActiveViewLabel()}</strong>
        </div>

        <div className="panel-card">
          <p className="panel-label">Backend</p>
          <strong>http://127.0.0.1:8000</strong>
        </div>

        <div className="panel-card">
          <p className="panel-label">Model</p>
          <strong>Gemini API aktif</strong>
        </div>

        <div className="panel-card">
          <p className="panel-label">Ses algılama</p>
          <strong>{voiceStatus}</strong>
        </div>

        <div className="panel-card">
          <p className="panel-label">Sesli cevap</p>
          <strong>{voiceReplyEnabled ? "Açık" : "Kapalı"}</strong>
        </div>

        <div className="panel-card">
          <p className="panel-label">Otomatik gönder</p>
          <strong>{autoSendVoiceEnabled ? "Açık" : "Kapalı"}</strong>
        </div>
      </aside>
    </main>
  );
}

export default App;