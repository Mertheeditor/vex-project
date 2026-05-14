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

type ActiveView = "chat" | "memory" | "projects" | "tasks" | "approvals";
type BackendStatus = "checking" | "online" | "offline";

function App() {
  const [activeView, setActiveView] = useState<ActiveView>("chat");
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);

  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const [backendMessage, setBackendMessage] = useState("Backend kontrol ediliyor...");

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
  const [showProjectForm, setShowProjectForm] = useState(false);
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

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      sender: "Vex",
      text: "Hazırım Mert. Artık mikrofonu başlatıp durdurarak konuşmanı dinleyebiliyorum, backend durumunu takip ediyorum ve sohbetten proje oluşturabiliyorum.",
    },
  ]);

  useEffect(() => {
    checkBackendHealth({ force: true });

    const intervalId = window.setInterval(() => {
      checkBackendHealth();
    }, 7000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, []);

  function setBusyState(value: boolean) {
    isBusyRef.current = value;
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
    const shouldSkip =
      !options?.force &&
      (isBusyRef.current ||
        isRecordingRef.current ||
        isTranscribingRef.current ||
        isSendingRef.current);

    if (shouldSkip) {
      return;
    }

    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => {
      controller.abort();
    }, 2500);

    try {
      const response = await fetch("http://127.0.0.1:8000/", {
        method: "GET",
        signal: controller.signal,
      });

      window.clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error("Backend cevap verdi ama sağlıklı değil.");
      }

      const data = await response.json();

      setBackendStatus("online");
      setBackendMessage(data?.message ?? "Vex backend bağlı.");
    } catch (error) {
      window.clearTimeout(timeoutId);

      const stillBusy =
        isBusyRef.current ||
        isRecordingRef.current ||
        isTranscribingRef.current ||
        isSendingRef.current;

      if (stillBusy) {
        return;
      }

      console.error(error);
      setBackendStatus("offline");
      setBackendMessage("Backend kapalı veya ulaşılamıyor.");
    }
  }

  function getBackendLabel() {
    if (backendStatus === "online") return "Backend: Bağlı";
    if (backendStatus === "offline") return "Backend: Kapalı";
    return "Backend: Kontrol ediliyor";
  }

  function getActiveViewLabel() {
    if (activeView === "chat") return "Genel sohbet";
    if (activeView === "memory") return "Hafıza merkezi";
    if (activeView === "projects") return "Proje merkezi";
    if (activeView === "tasks") return "Görev merkezi";
    if (activeView === "approvals") return "Onay Merkezi";
    return "Vex";
  }

  function slugify(text: string) {
    return text
      .toLocaleLowerCase("tr-TR")
      .replaceAll("ı", "i")
      .replaceAll("ğ", "g")
      .replaceAll("ü", "u")
      .replaceAll("ş", "s")
      .replaceAll("ö", "o")
      .replaceAll("ç", "c")
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
      }),
    });

    if (!response.ok) {
      throw new Error("Sohbetten görev oluşturma endpoint'i cevap vermedi.");
    }

    return response.json();
  }

  async function createApprovalFromChat(text: string): Promise<ApprovalFromChatResult> {
    const response = await fetch("http://127.0.0.1:8000/approvals/from-chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: text,
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

  function toggleVoiceRecording() {
    if (isRecordingRef.current) {
      stopVoiceRecordingAndTranscribe();
    } else {
      startVoiceRecording();
    }
  }

  function openMemoryView() {
    setActiveView("memory");
    loadMemory();
  }

  function openProjectsView() {
    setActiveView("projects");
    loadProjects();
  }

  function openTasksView() {
    setActiveView("tasks");
    loadTasks();
  }

  function openApprovalsView() {
    setActiveView("approvals");
    loadApprovals();
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

    stopSpeaking();
    setBusyState(true);

    const userMessage: Message = {
      id: Date.now(),
      sender: "Sen",
      text: cleanInput,
    };

    const historyForBackend = messages.map((message) => ({
      sender: message.sender,
      text: message.text,
    }));

    setMessages((currentMessages) => [...currentMessages, userMessage]);
    setInput("");
    updateSending(true);

    try {
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
        text: "Backend bağlantısında sorun oldu. Python backend'in çalıştığından emin olalım.",
      };

      setMessages((currentMessages) => [...currentMessages, errorReply]);
      console.error(error);
    } finally {
      updateSending(false);
      setBusyState(false);
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
        </nav>
      </aside>

      <section className="chat-area">
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

                <span className={`status-pill backend-${backendStatus}`}>
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

      </section>

      <aside className="work-panel">
        <h3>İş Paneli</h3>

        <div className="panel-card">
          <p className="panel-label">Backend durumu</p>
          <strong>{getBackendLabel()}</strong>
          <p className="panel-label">{backendMessage}</p>
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