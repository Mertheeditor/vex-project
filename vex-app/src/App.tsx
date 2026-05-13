import { useState } from "react";
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

type ActiveView = "chat" | "memory" | "projects";

function App() {
  const [activeView, setActiveView] = useState<ActiveView>("chat");
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);

  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState("Lokal mikrofon hazır");
  const [voiceReplyEnabled, setVoiceReplyEnabled] = useState(true);
  const [autoSendVoiceEnabled, setAutoSendVoiceEnabled] = useState(true);

  const [memoryData, setMemoryData] = useState<MemoryData | null>(null);
  const [isMemoryLoading, setIsMemoryLoading] = useState(false);

  const [projects, setProjects] = useState<ProjectData[]>([]);
  const [isProjectsLoading, setIsProjectsLoading] = useState(false);
  const [showProjectForm, setShowProjectForm] = useState(false);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [projectType, setProjectType] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [projectGoals, setProjectGoals] = useState("");
  const [projectNotes, setProjectNotes] = useState("");

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      sender: "Vex",
      text: "Hazırım Mert. Artık mikrofonu başlatıp durdurarak konuşmanı dinleyebiliyorum.",
    },
  ]);

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

  async function loadMemory() {
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
    } catch (error) {
      console.error(error);
      alert("Proje oluşturulamadı. Backend çalışıyor mu kontrol edelim.");
    } finally {
      setIsCreatingProject(false);
    }
  }

  async function deleteProject(projectId: string, projectName: string) {
    try {
      const response = await fetch(`http://127.0.0.1:8000/projects/${projectId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error("Proje silinemedi.");
      }

      await loadProjects();
    } catch (error) {
      console.error(error);
      alert("Proje silinemedi. Backend çalışıyor mu kontrol edelim.");
    }
  }

  async function startVoiceRecording() {
    if (isRecording || isSending || isTranscribing) {
      return;
    }

    stopSpeaking();
    setIsRecording(true);
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
        setIsRecording(false);
        setVoiceStatus(data?.message ?? "Kayıt başlatılamadı.");
        alert(data?.message ?? "Kayıt başlatılamadı.");
      }
    } catch (error) {
      console.error(error);
      setIsRecording(false);
      setVoiceStatus("Kayıt başlatılamadı.");
      alert("Kayıt başlatılamadı. Backend açık mı kontrol edelim.");
    }
  }

  async function stopVoiceRecordingAndTranscribe() {
    if (!isRecording || isTranscribing) {
      return;
    }

    setIsRecording(false);
    setIsTranscribing(true);
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
      setIsTranscribing(false);
    }
  }

  function toggleVoiceRecording() {
    if (isRecording) {
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

  async function sendMessage(messageOverride?: string) {
    const cleanInput = (messageOverride ?? input).trim();

    if (!cleanInput || isSending || (isRecording && !messageOverride)) {
      return;
    }

    stopSpeaking();

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
    setIsSending(true);

    try {
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
      setIsSending(false);
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

          <button className="nav-item">Shopify</button>
          <button className="nav-item">Tasarım</button>
          <button className="nav-item">Dosyalar</button>

          <button
            className={`nav-item ${activeView === "memory" ? "active" : ""}`}
            onClick={openMemoryView}
          >
            Hafıza
          </button>

          <button className="nav-item">Onay Merkezi</button>
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

                <span className="status-pill">
                  {isRecording
                    ? "Kayıt alınıyor..."
                    : isTranscribing
                      ? "Yazıya çevriliyor..."
                      : "Başlat / durdur ses aktif"}
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
                onClick={toggleVoiceRecording}
                disabled={isSending || isTranscribing}
                title={isRecording ? "Kaydı durdur ve yazıya çevir" : "Kaydı başlat"}
              >
                {isRecording ? "Durdur" : isTranscribing ? "Çevriliyor..." : "Mikrofon"}
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
                disabled={isSending || isRecording || isTranscribing}
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
                            onClick={() => deleteProject(project.id, project.name)}
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
      </section>

      <aside className="work-panel">
        <h3>İş Paneli</h3>

        <div className="panel-card">
          <p className="panel-label">Aktif bölüm</p>
          <strong>
            {activeView === "chat"
              ? "Genel sohbet"
              : activeView === "memory"
                ? "Hafıza merkezi"
                : "Proje merkezi"}
          </strong>
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