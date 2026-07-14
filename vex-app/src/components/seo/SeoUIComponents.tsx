import React from "react";
import { IssueSeverity, PageType } from "../../types/seo";

// SEO Issue Badge Component
interface IssueBadgeProps {
  severity?: IssueSeverity;
  category?: IssueSeverity | string;
  label?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function IssueBadge({
  severity = "P2",
  category,
  label,
  size = "md",
  className = "",
}: IssueBadgeProps) {
  const displayLabel = label || severity;
  const severityClass = `issue-badge-${severity.toLowerCase()}`;
  const sizeClass = `issue-badge-${size}`;

  return (
    <span className={`issue-badge ${severityClass} ${sizeClass} ${className}`} title={category}>
      {displayLabel}
    </span>
  );
}

// Score Display Component
interface ScoreDisplayProps {
  score: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
}

const getScoreColor = (score: number) => {
  if (score >= 80) return "score-excellent";
  if (score >= 60) return "score-good";
  if (score >= 40) return "score-fair";
  return "score-poor";
};

const getScoreLabel = (score: number) => {
  if (score >= 80) return "Mükemmel";
  if (score >= 60) return "İyi";
  if (score >= 40) return "Orta";
  return "Zayıf";
};

export function ScoreDisplay({ score, size = "md", showLabel = true, className = "" }: ScoreDisplayProps) {
  const scoreClass = getScoreColor(score);

  return (
    <div className={`score-display ${size} ${scoreClass} ${className}`}>
      <span className="score-value">{score}</span>
      {showLabel && <span className="score-label">{getScoreLabel(score)}</span>}
      <span className="score-max">/100</span>
    </div>
  );
}

// Progress Ring for scores
interface ScoreRingProps {
  score: number;
  size?: number;
  strokeWidth?: number;
  className?: string;
}

export function ScoreRing({ score, size = 60, strokeWidth = 4, className = "" }: ScoreRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - score / 100);
  const scoreClass = getScoreColor(score);

  return (
    <div className={`score-ring ${scoreClass} ${className}`} style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          className="score-ring-bg"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
        />
        <circle
          className="score-ring-progress"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transform: "rotate(-90deg)", transformOrigin: "center" }}
        />
      </svg>
      <div className="score-ring-text">
        <span className="score-ring-value">{score}</span>
      </div>
    </div>
  );
}

// Page Type Badge
interface PageTypeBadgeProps {
  pageType: PageType | string;
  size?: "sm" | "md";
  className?: string;
}

const pageTypeLabels: Record<string, string> = {
  homepage: "Ana Sayfa",
  collection: "Koleksiyon",
  product: "Ürün",
  blog_article: "Blog Yazısı",
  content_page: "İçerik Sayfası",
  cart: "Sepet",
  account: "Hesap",
  policy: "Politika",
  search: "Arama",
  unknown: "Bilinmiyor",
  category: "Kategori",
  tag: "Etiket",
  author: "Yazar",
  archive: "Arşiv",
  landing: "Landing Page",
  thank_you: "Teşekkür",
  "404": "404 Sayfası",
  "500": "500 Hatası",
};

export function PageTypeBadge({ pageType, size = "md", className = "" }: PageTypeBadgeProps) {
  const label = pageTypeLabels[pageType] || pageType;
  return (
    <span className={`page-type-badge page-type-${size} ${className}`}>
      {label}
    </span>
  );
}

// Issue Severity Indicator
interface SeverityIndicatorProps {
  severity: IssueSeverity;
  showLabel?: boolean;
  className?: string;
}

const severityLabels: Record<IssueSeverity, string> = {
  P0: "Kritik",
  P1: "Yüksek",
  P2: "Orta",
  P3: "Düşük",
};

const severityColors: Record<IssueSeverity, string> = {
  P0: "#ef4444",
  P1: "#f97316",
  P2: "#eab308",
  P3: "#22c55e",
};

export function SeverityIndicator({
  severity,
  showLabel = true,
  className = "",
}: SeverityIndicatorProps) {
  return (
    <span
      className={`severity-indicator ${className}`}
      style={{ borderLeftColor: severityColors[severity] }}
      title={severityLabels[severity]}
    >
      {showLabel && <span className="severity-label">{severityLabels[severity]}</span>}
      <span className="severity-code">{severity}</span>
    </span>
  );
}

// Category Badge
interface CategoryBadgeProps {
  category: string;
  className?: string;
}

const categoryLabels: Record<string, string> = {
  technical: "Teknik",
  content: "İçerik",
  on_page: "On-Page",
  technical_seo: "Teknik SEO",
  performance: "Performans",
  mobile: "Mobil",
  structured_data: " Yapılandırılmış Veri",
  international: "Uluslararası",
  ecommerce: "E-Ticaret",
  security: "Güvenlik",
  accessibility: "Erişilebilirlik",
  links: "Bağlantılar",
  images: "Görseller",
};

export function CategoryBadge({ category, className = "" }: CategoryBadgeProps) {
  const label = categoryLabels[category] || category;
  return (
    <span className={`category-badge category-${category} ${className}`}>
      {label}
    </span>
  );
}

// Compact Metric Display
interface MetricItemProps {
  label: string;
  value: string | number;
  trend?: "up" | "down" | "neutral";
  tooltip?: string;
  className?: string;
}

export function MetricItem({ label, value, trend, tooltip, className = "" }: MetricItemProps) {
  return (
    <div className={`metric-item ${className}`} title={tooltip}>
      <span className="metric-label">{label}</span>
      <span className="metric-value">
        {value}
        {trend && (
          <span className={`metric-trend trend-${trend}`}>
            {trend === "up" ? "↑" : trend === "down" ? "↓" : "→"}
          </span>
        )}
      </span>
    </div>
  );
}

// Issue List Item
interface IssueItemProps {
  issue: {
    severity: IssueSeverity;
    category: string;
    code: string;
    message: string;
    url?: string;
    recommendation?: string;
    current_value?: string;
    expected_value?: string;
  };
  onClick?: () => void;
  className?: string;
}

export function IssueItem({ issue, onClick, className = "" }: IssueItemProps) {
  return (
    <div
      className={`issue-item severity-${issue.severity.toLowerCase()} ${className}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e: React.KeyboardEvent) => e.key === "Enter" && onClick() : undefined}
    >
      <div className="issue-header">
        <IssueBadge severity={issue.severity} size="sm" />
        <CategoryBadge category={issue.category} />
        <span className="issue-code">{issue.code}</span>
      </div>
      <div className="issue-message">{issue.message}</div>
      {issue.url && <div className="issue-url">{issue.url}</div>}
      {issue.current_value && (
        <div className="issue-values">
          <span className="issue-current">Mevcut: {issue.current_value}</span>
          {issue.expected_value && (
            <span className="issue-expected">Beklenen: {issue.expected_value}</span>
          )}
        </div>
      )}
      {issue.recommendation && (
        <div className="issue-recommendation">{issue.recommendation}</div>
      )}
    </div>
  );
}

// SEO Summary Card
interface SeoSummaryCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: "up" | "down" | "neutral";
  icon?: React.ReactNode;
  className?: string;
}

export function SeoSummaryCard({ title, value, subtitle, trend, icon, className = "" }: SeoSummaryCardProps) {
  return (
    <div className={`seo-summary-card ${className}`}>
      <div className="summary-header">
        <span className="summary-title">{title}</span>
        {icon && <span className="summary-icon">{icon}</span>}
      </div>
      <div className="summary-value">
        {value}
        {trend && <span className={`summary-trend trend-${trend}`}>{trend === "up" ? "▲" : trend === "down" ? "▼" : "◆"}</span>}
      </div>
      {subtitle && <div className="summary-subtitle">{subtitle}</div>}
    </div>
  );
}

// Export all components
export * from "./SeoProjectSelector";
export * from "./ProviderStatusField";