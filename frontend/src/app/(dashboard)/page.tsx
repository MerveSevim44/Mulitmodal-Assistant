"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ChevronLeft,
  ChevronRight,
  FileText,
  Image as ImageIcon,
  Mic,
  Plus,
  Info,
  BookOpen,
} from "lucide-react";
import { getOverview, type OverviewData, type TopicOverview } from "@/lib/api";
import styles from "./home.module.css";

/**
 * Placeholder review times. There is no reviews/schedules table yet, so the
 * slots on the timeline are decorative — everything else on this page (courses,
 * topics, material types and counts) comes from /api/v1/overview.
 */
const MOCK_SLOTS = ["09:00", "11:30", "13:00", "15:30", "18:00", "20:00"];

const WEEKDAYS = ["P", "S", "Ç", "P", "C", "C", "P"];

function formatDate(date: Date): string {
  return date.toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    weekday: "long",
  });
}

function Tag({ children, index }: { children: React.ReactNode; index: number }) {
  // Courses alternate between the two tag colours from the design.
  const tone = index % 2 === 0 ? styles.tagLilac : styles.tagRose;
  return <span className={`${styles.tag} ${tone}`}>{children}</span>;
}

/**
 * Ring showing how many of the three source types a topic has (PDF, audio,
 * image). This is derived from real material counts rather than an invented
 * "memory strength" score, which the backend has no data for.
 */
function CoverageRing({ value }: { value: number }) {
  const r = 15;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className={styles.ring}>
      <svg width="36" height="36" viewBox="0 0 36 36">
        <circle cx="18" cy="18" r={r} fill="none" stroke="var(--border)" strokeWidth="4" />
        <circle
          cx="18"
          cy="18"
          r={r}
          fill="none"
          stroke="var(--accent)"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 18 18)"
        />
      </svg>
      <span className={styles.ringValue}>{value}</span>
    </div>
  );
}

function sourceIcons(topic: TopicOverview) {
  const icons: { Icon: typeof FileText; label: string }[] = [];
  if (topic.pdf_count > 0) icons.push({ Icon: FileText, label: `${topic.pdf_count} PDF` });
  if (topic.audio_count > 0) icons.push({ Icon: Mic, label: `${topic.audio_count} ses kaydı` });
  if (topic.image_count > 0) icons.push({ Icon: ImageIcon, label: `${topic.image_count} görsel` });
  return icons;
}

function describeTopic(topic: TopicOverview): string {
  const parts: string[] = [];
  if (topic.pdf_count) parts.push(`${topic.pdf_count} PDF`);
  if (topic.audio_count) parts.push(`${topic.audio_count} ses kaydı`);
  if (topic.image_count) parts.push(`${topic.image_count} görsel`);
  return parts.join(" · ");
}

export default function HomeDashboard() {
  const router = useRouter();
  const [data, setData] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);

  const today = useMemo(() => new Date(), []);
  const [selectedDay, setSelectedDay] = useState(today.getDate());

  useEffect(() => {
    getOverview()
      .then(({ data }) => setData(data))
      .catch((err) => console.error("Failed to load overview:", err))
      .finally(() => setLoading(false));
  }, []);

  const daysInMonth = useMemo(
    () => new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate(),
    [today]
  );

  const monthLabel = useMemo(
    () => today.toLocaleDateString("tr-TR", { month: "long", year: "numeric" }),
    [today]
  );

  // Course name -> stable index, so a course keeps the same tag colour.
  const courseIndex = useMemo(() => {
    const map = new Map<string, number>();
    data?.courses.forEach((c, i) => map.set(c.id, i));
    return map;
  }, [data]);

  const openTopic = (topic: TopicOverview) =>
    router.push(`/courses/${topic.course_id}/topics/${topic.id}`);

  if (loading) {
    return (
      <div className={styles.centered}>
        <div className="spinner spinner-lg" />
      </div>
    );
  }

  const topics = data?.topics ?? [];
  const queue = topics.slice(0, 6);
  const upcoming = topics.slice(0, 3);

  return (
    <div className={styles.board}>
      {/* ── Main: topic queue ─────────────────────────────────── */}
      <section className={styles.panel}>
        <header className={styles.panelHeader}>
          <h1 className={styles.panelTitle}>Bugünkü Tekrar Programı</h1>
          <p className={styles.panelSubtitle}>{formatDate(today)}</p>
          <p className={styles.mockNote}>
            <Info size={12} />
            Saatler örnek verilerdir — halka, konudaki kaynak çeşitliliğini gösterir.
          </p>
        </header>

        {queue.length === 0 ? (
          <div className={styles.emptyState}>
            <BookOpen size={32} className={styles.emptyIcon} />
            <p className={styles.emptyTitle}>Henüz konu yok</p>
            <p>Başlamak için bir ders açıp içine konu ekle.</p>
            <button
              className={styles.wideButton}
              style={{ marginTop: 20, maxWidth: 220, marginInline: "auto" }}
              onClick={() => router.push("/courses")}
            >
              <Plus size={15} /> Ders Oluştur
            </button>
          </div>
        ) : (
          <div className={styles.queue}>
            {queue.map((topic, i) => {
              const icons = sourceIcons(topic);
              const typesPresent = icons.length;
              const coverage = Math.round((typesPresent / 3) * 100);
              const isEmpty = typesPresent === 0;

              return (
                <div key={topic.id} className={styles.queueRow}>
                  <div className={styles.queueTime}>
                    <span className={styles.queueTimeLabel}>
                      {MOCK_SLOTS[i % MOCK_SLOTS.length]}
                    </span>
                    {i < queue.length - 1 && <div className={styles.queueLine} />}
                  </div>

                  <div className={styles.queueBody}>
                    {isEmpty ? (
                      <div className={styles.emptyCard}>
                        <span>{topic.name} — materyal eklenmedi</span>
                        <button
                          className={styles.linkButton}
                          onClick={() => openTopic(topic)}
                        >
                          <Plus size={14} /> Materyal Ekle
                        </button>
                      </div>
                    ) : (
                      <div className={styles.card}>
                        <div className={styles.cardMain}>
                          <CoverageRing value={coverage} />
                          <div className={styles.cardText}>
                            <Tag index={courseIndex.get(topic.course_id) ?? 0}>
                              {topic.course_name}
                            </Tag>
                            <p className={styles.cardTopic}>{topic.name}</p>
                            <p className={styles.cardDetail}>{describeTopic(topic)}</p>
                          </div>
                        </div>

                        <div className={styles.cardActions}>
                          <div className={styles.sourceIcons}>
                            {icons.map(({ Icon, label }) => (
                              <div key={label} className={styles.sourceIcon} title={label}>
                                <Icon size={13} />
                              </div>
                            ))}
                          </div>
                          <button
                            className={styles.darkButton}
                            onClick={() => openTopic(topic)}
                          >
                            Tekrar Et
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* ── Right rail: calendar + upcoming ───────────────────── */}
      <aside className={styles.rail}>
        <section className={styles.panel} style={{ padding: 20 }}>
          <div className={styles.railHeader}>
            <span className={styles.railTitle}>{monthLabel}</span>
            <div style={{ display: "flex", gap: 4 }}>
              <button className={styles.iconButton} aria-label="Önceki ay" disabled>
                <ChevronLeft size={13} />
              </button>
              <button className={styles.iconButton} aria-label="Sonraki ay" disabled>
                <ChevronRight size={13} />
              </button>
            </div>
          </div>

          <div className={styles.calendar}>
            {WEEKDAYS.map((d, i) => (
              <span key={i} className={styles.weekday}>
                {d}
              </span>
            ))}
            {Array.from({ length: daysInMonth }, (_, i) => i + 1).map((day) => {
              const isToday = day === today.getDate();
              const isSelected = day === selectedDay;
              return (
                <button
                  key={day}
                  onClick={() => setSelectedDay(day)}
                  className={`${styles.day} ${isToday ? styles.dayToday : ""} ${
                    isSelected ? styles.daySelected : ""
                  }`}
                >
                  {day}
                </button>
              );
            })}
          </div>
        </section>

        <section className={styles.panel} style={{ padding: 20 }}>
          <div className={styles.railHeader}>
            <span className={styles.railTitle}>Son Eklenen Konular</span>
            <button className={styles.linkButton} onClick={() => router.push("/courses")}>
              Tümü
            </button>
          </div>

          {upcoming.length === 0 ? (
            <p className={styles.panelSubtitle}>Henüz konu eklenmedi.</p>
          ) : (
            <div className={styles.upcomingList}>
              {upcoming.map((topic) => (
                <button
                  key={topic.id}
                  className={styles.upcomingCard}
                  onClick={() => openTopic(topic)}
                >
                  <Tag index={courseIndex.get(topic.course_id) ?? 0}>
                    {topic.course_name}
                  </Tag>
                  <p className={styles.upcomingTitle}>{topic.name}</p>
                  <p className={styles.upcomingWhen}>
                    {new Date(topic.created_at).toLocaleDateString("tr-TR", {
                      day: "numeric",
                      month: "long",
                    })}
                  </p>
                </button>
              ))}
            </div>
          )}

          <button
            className={styles.wideButton}
            style={{ marginTop: 16 }}
            onClick={() => router.push("/courses")}
          >
            <Plus size={15} /> Yeni Konu Ekle
          </button>
        </section>
      </aside>
    </div>
  );
}
