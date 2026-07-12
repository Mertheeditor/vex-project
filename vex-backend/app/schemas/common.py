from __future__ import annotations

from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    sender: str = ""
    text: str = ""

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)

class MessageRequest(BaseModel):
    message: str = ""

class UrlAnalyzeRequest(BaseModel):
    url: str = ""
    prompt: str = "Siteyi SEO, tasarım, içerik ve güven algısı açısından analiz et."

class SiteProductFinderRequest(BaseModel):
    url: str = ""
    query: str = ""
    language: str = "Turkish"
    max_pages: int = 40

class ShopifyContentFromChatRequest(BaseModel):
    message: str
    project_id: str = ""
    task_id: str = ""
    language: str = "English"

class ScreenAnalyzeRequest(BaseModel):
    prompt: str = "Ekranda ne olduğunu analiz et."

class ComputerPlanRequest(BaseModel):
    instruction: str = ""

class ReminderFromChatRequest(BaseModel):
    message: str
    project_id: str = ""
    task_id: str = ""

class ReminderDueRequest(BaseModel):
    mark_as_notified: bool = True

class ProjectRequest(BaseModel):
    id: str
    name: str
    type: str = "Genel proje"
    status: str = "aktif"
    description: str = ""
    main_goals: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

class TaskRequest(BaseModel):
    id: str = ""
    title: str
    project_id: str = ""
    status: str = "açık"
    priority: str = "normal"
    description: str = ""
    notes: list[str] = Field(default_factory=list)

class ApprovalRequest(BaseModel):
    id: str = ""
    title: str
    project_id: str = ""
    action_type: str = "genel"
    risk_level: str = "normal"
    status: str = "bekliyor"
    description: str = ""
    payload: dict = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)

class ActiveProjectRequest(BaseModel):
    project_id: str

class ActiveTaskRequest(BaseModel):
    task_id: str

class OutputRequest(BaseModel):
    id: str = ""
    title: str = ""
    project_id: str = ""
    task_id: str = ""
    output_type: str = "genel"
    content: str = ""
    status: str = "taslak"
    notes: list[str] = Field(default_factory=list)

class RecordSpeechRequest(BaseModel):
    duration_seconds: float = 5

class ListenSpeechRequest(BaseModel):
    max_seconds: float = 20
    silence_seconds: float = 1.2
    peak_threshold: float = 0.025
    average_threshold: float = 0.003

class WakeListenSpeechRequest(BaseModel):
    wake_seconds: float = 4
    active_silence_seconds: float = 10
    max_active_seconds: float = 90
    peak_threshold: float = 0.075
    average_threshold: float = 0.012

class DetectWakeWordRequest(BaseModel):
    wake_seconds: float = 4
    peak_threshold: float = 0.075
    average_threshold: float = 0.012

class ActiveListenSpeechRequest(BaseModel):
    active_silence_seconds: float = 10
    max_active_seconds: float = 90
    peak_threshold: float = 0.075
    average_threshold: float = 0.012

class SpeakTextRequest(BaseModel):
    text: str = ""
