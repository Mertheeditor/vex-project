# Vex Takım Mimarisi ve Çalışma Sözleşmesi

> Bu belge, Vex çok ajanlı geliştirme sisteminin temel organize edici prensiplerini tanımlar. Tüm ajanlar (Lead, uzmanlar, denetçiler) bu sözleşmeye uyar.

---

## 1. Oturum Yapısı

| Bileşen | Çalışma Yeri | Sorumluluk |
|---------|--------------|------------|
| **Vex Lead** | Ana checkout (`/Users/mert/Vex`) | Görev planlama, dağıtım, sentez, entegrasyon |
| **architect** | Ana checkout | Salt okunur mimari analiz, tasarım, planlama |
| **backend-builder** | İzole worktree | FastAPI/backend üretim kodu + testler |
| **frontend-builder** | İzole worktree | React/TypeScript/Tauri frontend üretim kodu + testler |
| **qa-engineer** | İzole worktree | Bağımsız doğrulama, test, lint, type-check |
| **security-auditor** | Ana checkout | Salt okunur güvenlik denetimi |
| **diff-auditor** | Ana checkout | Salt okunur diff denetimi (Lead isteğiyle) |

---

## 2. İki Çalışma Biçimi

### Agent Team Modu (Yan Yana Teammate)

- **Kullanım alanı**: Lead ana oturumda `fcc-claude --agent vex-lead` ile başlatılır.
- **Güvenilen alanlar**: Agent adı, talimat gövdesi, model, tools allowlist.
- **`permissionMode` / `isolation: worktree`**: Bu modda tek başına **güvenilmez**.
- **Yazma güvenliği**: Lead tarafından verilen açık worktree yolu, agent tools allowlist'i, ve PreToolUse hook'u ile uygulanır.

### Isolated Subagent Modu (Tek Başına Alt Ajan)

- **Kullanım alanı**: Builder veya QA `Task(agent=..., isolation="worktree")` ile tek başına çalıştırılırsa.
- **Aktif alan**: `isolation: worktree` frontmatter'daki bu alan **bu modda** işlev görür.

> **Kural**: Agent dosyaları **her iki kullanım biçimini de desteklemelidir**. Frontmatter'da `isolation: worktree` tanımlanır ama Agent Team modunda hook/lead tarafından uygulanır.

---

## 3. Lead'in Worktree Yönetimi

### Worktree Oluşturma (Lead Sorumluluğu)

Lead, bir builder veya QA'ya görev verirken **önceden** worktree oluşturur:

```bash
# Örnek
git worktree add .vex-worktrees/backend-builder feat/backend-<task-id>
git worktree add .vex-worktrees/frontend-builder feat/frontend-<task-id>
git worktree add .vex-worktrees/qa-engineer feat/qa-<task-id>
```

### Worktree Yapısı

```text
.vex-worktrees/
├── backend-builder/   # branch: feat/backend-<task-id>
├── frontend-builder/  # branch: feat/frontend-<task-id>
└── qa-engineer/       # branch: feat/qa-<task-id>
```

### Worktree Kuralları

| Kural | Açıklama |
|-------|----------|
| **Her worktree farklı branch** | Aynı dosya iki ajana asla verilmez |
| **Lead worktree yolu görev mesajında belirtir** | `WORKTREE_ROOT: .vex-worktrees/backend-builder` |
| **Commit SHA olmadan entegrasyon yapmaz** | Builder/QA handoff'ta branch + SHA zorunlu |
| **Push/deploy yasak** | Hiçbir ajan `git push`, `git merge`, deploy yapmaz |
| **QA ve Security onayı şart** | Merge/entegre sadece onaylarla |

---

## 4. Agent Sınırları (Yazma İzinleri)

| Agent | Yazabileceği Alanlar | Yazamayacağı Alanlar |
|-------|---------------------|---------------------|
| **backend-builder** | `vex-backend/**`, `docs/agent-system/**` (görevle ilgili) | `.claude/**`, `vex-app/**`, repo dışı |
| **frontend-builder** | `vex-app/**`, `docs/agent-system/**` (görevle ilgili) | `.claude/**`, `vex-backend/**`, repo dışı |
| **qa-engineer** | Test fixture/helper, `vex-backend/tests/**`, `vex-app/src/**/*.test.*`, `vex-app/src/**/*.spec.*`, doğrulama raporları | Üretim kodu (`.tsx`, `.py` ana dosyalar) |
| **architect** | Hiçbiri (salt okunur) | Tümü |
| **security-auditor** | Hiçbiri (salt okunur) | Tümü |
| **diff-auditor** | Hiçbiri (salt okunur) | Tümü |
| **vex-lead** | `docs/agent-system/**`, `.claude/**`, entegrasyon sırasında gerekli proje dosyaları | Doğrudan üretim kodu (istisnalar: entegrasyon çatışması, çok küçük düzeltme, kullanıcı talimatı) |

---

## 5. Görev Dağıtım Protokolü (Lead → Uzman)

Lead bir uzmana görev verirken **mutlaka** şunları içerir:

```markdown
## Task: [Net hedef]

**Assigned to**: [agent name]
**Scope**: [Dosya yolları, bileşenler, sınırlar]
**Acceptance Criteria**: [Doğrulanabilir koşullar]
**Dependencies**: [Önce bitmesi gereken görevler]
**Worktree**: [yes/no — builder/qa için evet, architect/security için hayır]
**Worktree Root**: [.vex-worktrees/... — builder/qa için]
**Branch**: [feat/... — builder/qa için]
```

---

## 6. Handoff Raporu (Uzman → Lead)

Bir uzman görevini bitirdiğinde Lead'e **handoff raporu** verir:

```markdown
## HANDOFF: [Görev Başlığı]
**From**: [agent-name]
**To**: vex-lead
**Status**: ready_for_review | blocked | in_progress
**Worktree Root**: [.vex-worktrees/...]
**Branch**: [feat/...]
**Commit SHA**: [abc123]
**Summary**: [2-3 cümle ne yapıldı]
**Verification**: [Çalıştırılan test/build komutları ve sonuçlar]
**Next Steps**: [Lead'in/sonraki ajanın yapması gerekenler]
**Acceptance Criteria Met**: [Evet/Hayır + detay]
```

---

## 7. Kalite Kapıları (Merge/Entegrasyon Öncesi)

| Kapı | Sorumlu | Kriter |
|------|---------|--------|
| **Kod Yazımı** | Builder | Üretim kodu + testler hazır |
| **Yerel Doğrulama** | Builder | `npm run build` / `python -m unittest` geçiyor |
| **Bağımsız QA** | QA Engineer | Test/lint/type-check/build raporu PASS |
| **Güvenlik Denetimi** | Security Auditor | VERDICT: PASS (kritik bulgu yoksa) |
| **Diff Denetimi** | Diff Auditor (isteğe bağlı) | Karar: UYGUN |
| **Lead Entegrasyonu** | Vex Lead | Çatışma çözümü, worktree commit merge, ana branch'e uygula |

---

## 8. Yasaklı İşlemler

| İşlem | Kimler Yasaklı | Neden |
|-------|----------------|-------|
| `git push` | Tüm ajanlar | Merkezi kontrol, review zorunlu |
| `git merge` / `rebase` | Tüm ajanlar | Lead entegre eder |
| `deploy` / dış servise yazma | Tüm ajanlar | Güvenlik, geri alınamazlık |
| Aynı dosyayı iki ajana verme | Lead | Çatışma riski |
| Worktree yolu belirtmeden görev verme | Lead | İzolasyon bozulur |
| Üretim kodu değiştirme (QA) | QA Engineer | Bağımsızlık bozulur |
| Kendi bulduğu güvenlik açığını kapatma | Security Auditor | Çelişki çıkar |

---

## 9. Çakışma Çözümü

| Çakışma Türü | Çözüm Yetkilisi |
|--------------|-----------------|
| Kapsam örtüşmesi | Lead anında parçalar |
| Teknik uyuşmazlık (mimari) | Architect karar verir |
| Teknik uyuşmazlık (süreç) | Lead karar verir |
| Güvenlik vs Özellik | **Güvenlik kazanır** — özellik yeniden tasarlanır |
| Kalite kapısı başarısız | QA bloke eder; builder düzeltip yeniden verir |

---

## 10. Onay ve Geçerlilik

Bu sözleşme, Vex projesinde çalışan tüm ajanlar (Lead, architect, backend-builder, frontend-builder, qa-engineer, security-auditor, diff-auditor) için **bağlayıcıdır**. Değişiklikler Lead tarafından `docs/agent-system/working-agreements.md` ile senkronize edilerek yapılır.

---
*Son güncelleme: 2026-07-12*
*Sürüm: 1.0 (Aşama 2A — Agent Definitions ve Worktree Contract)*