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
import axios from "axios";
import { getOverview, type OverviewData, type TopicOverview } from "@/lib/api";
import styles from "./home.module.css";

/**
 * The home dashboard is built entirely from /api/v1/overview — courses,
 * topics, material type counts and the topics' created_at timestamps. There is
 * no reviews/schedules table yet, so nothing here invents a review time: the
 * timeline labels are the times the topics were actually added.
 */

// Monday-first, matching Date#getDay() shifted by one.
const WEEKDAYS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];

/** Local YYYY-MM-DD key — used to group topics by the day they were added. */
function dayKey(date: Date): string {
  const m = `${date.getMonth() + 1}`.padStart(2, "0");
  const d = `${date.getDate()}`.padStart(2, "0");
  return `${date.getFullYear()}-${m}-${d}`;
}

/** 0 = Monday … 6 = Sunday. */
function mondayIndex(date: Date): number {
  return (date.getDay() + 6) % 7;
}

function formatLongDate(date: Date): string {
  return date.toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    weekday: "long",
  });
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("tr-TR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function Tag({ children, index }: { children: React.ReactNode; index: number }) {
  // Courses alternate between the two tag colours from the design.
  const tone = index % 2 === 0 ? styles.tagLilac : styles.tagRose;
  return <span className={`${styles.tag} ${tone}`}>{children}</span>;
}

/**
 * Ring showing how many of the three source types a topic has (PDF, audio,
 * image). Labelled as a fraction rather than a percentage so it does not read
 * as a "memory strength" score, which the backend has no data for.
 */
function CoverageRing({ present, total }: { present: number; total: number }) {
  const r = 15;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (present / total) * circumference;

  return (
    <div
      className={styles.ring}
      title={`${total} kaynak türünden ${present} tanesi eklendi`}
    >
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
      <span className={styles.ringValue}>
        {present}/{total}
      </span>
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
  return sourceIcons(topic)
    .map((icon) => icon.label)
    .join(" · ");
}

export default function HomeDashboard() {
  const router = useRouter();
  const [data, setData] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);

  const today = useMemo(() => new Date(), []);
  // Month the calendar is showing, and the day the user picked (null = the
  // default "most recent topics" view).
  const [viewMonth, setViewMonth] = useState(
    () => new Date(today.getFullYear(), today.getMonth(), 1)
  );
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  useEffect(() => {
    getOverview()
      .then(({ data }) => setData(data))
      // A cancelled request means there is no session and the client is
      // already redirecting to /login — not a failure worth reporting.
      .catch((err) => {
        if (!axios.isCancel(err)) console.error("Failed to load overview:", err);
      })
      .finally(() => setLoading(false));
  }, []);

  const topics = useMemo(() => data?.topics ?? [], [data]);

  // Day key -> topics added that day, for the calendar dots and the day filter.
  const topicsByDay = useMemo(() => {
    const map = new Map<string, TopicOverview[]>();
    topics.forEach((topic) => {
      const key = dayKey(new Date(topic.created_at));
      const bucket = map.get(key);
      if (bucket) bucket.push(topic);
      else map.set(key, [topic]);
    });
    return map;
  }, [topics]);

  // Course id -> stable index, so a course keeps the same tag colour.
  const courseIndex = useMemo(() => {
    const map = new Map<string, number>();
    data?.courses.forEach((course, i) => map.set(course.id, i));
    return map;
  }, [data]);

  const daysInMonth = new Date(
    viewMonth.getFullYear(),
    viewMonth.getMonth() + 1,
    0
  ).getDate();
  const leadingBlanks = mondayIndex(viewMonth);
  const monthLabel = viewMonth.toLocaleDateString("tr-TR", {
    month: "long",
    year: "numeric",
  });

  const shiftMonth = (delta: number) =>
    setViewMonth((m) => new Date(m.getFullYear(), m.getMonth() + delta, 1));

  const openTopic = (topic: TopicOverview) =>
    router.push(`/courses/${topic.course_id}/topics/${topic.id}`);

  if (loading) {
    return (
      <div className={styles.centered}>
        <div className="spinner spinner-lg" />
      </div>
    );
  }

  // Default view: the six most recent topics. Pick a day on the calendar and
  // the list narrows to what was actually added that day.
  const selectedDate = selectedKey ? new Date(`${selectedKey}T00:00:00`) : null;
  const queue = selectedKey ? topicsByDay.get(selectedKey) ?? [] : topics.slice(0, 6);
  const recent = topics.slice(0, 3);

  return (
    <div className={styles.board}>
      {/* ── Main: topic queue ─────────────────────────────────── */}
      <section className={styles.panel}>
        <header className={styles.panelHeader}>
          <h1 className={styles.panelTitle}>
            {selectedDate ? formatLongDate(selectedDate) : "Tekrar Listesi"}
          </h1>
          <p className={styles.panelSubtitle}>
            {selectedDate
              ? "Bu gün eklenen konular"
              : `${formatLongDate(today)} · en son eklenen konular`}
          </p>

          {data && (
            <p className={styles.stats}>
              {data.total_courses} ders · {data.total_topics} konu ·{" "}
              {data.total_materials} materyal
              {data.empty_topics > 0 && ` · ${data.empty_topics} konu boş`}
            </p>
          )}

          <p className={styles.mockNote}>
            <Info size={12} />
            Saatler konunun eklendiği zamanı, halka ise konudaki kaynak
            çeşitliliğini gösterir.
          </p>

          {selectedKey && (
            <button className={styles.linkButton} onClick={() => setSelectedKey(null)}>
              Tüm konulara dön
            </button>
          )}
        </header>

        {queue.length === 0 ? (
          <div className={styles.emptyState}>
            <BookOpen size={32} className={styles.emptyIcon} />
            <p className={styles.emptyTitle}>
              {selectedKey ? "Bu güne ait konu yok" : "Henüz konu yok"}
            </p>
            <p>
              {selectedKey
                ? "Takvimden başka bir gün seç ya da yeni bir konu ekle."
                : "Başlamak için bir ders açıp içine konu ekle."}
            </p>
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
              const isEmpty = typesPresent === 0;

              return (
                <div key={topic.id} className={styles.queueRow}>
                  <div className={styles.queueTime}>
                    <span className={styles.queueTimeLabel}>
                      {formatTime(topic.created_at)}
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
                          <CoverageRing present={typesPresent} total={3} />
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

      {/* ── Right rail: calendar + recent ─────────────────────── */}
      <aside className={styles.rail}>
        <section className={styles.panel} style={{ padding: 20 }}>
          <div className={styles.railHeader}>
            <span className={styles.railTitle}>{monthLabel}</span>
            <div style={{ display: "flex", gap: 4 }}>
              <button
                className={styles.iconButton}
                aria-label="Önceki ay"
                onClick={() => shiftMonth(-1)}
              >
                <ChevronLeft size={13} />
              </button>
              <button
                className={styles.iconButton}
                aria-label="Sonraki ay"
                onClick={() => shiftMonth(1)}
              >
                <ChevronRight size={13} />
              </button>
            </div>
          </div>

          <div className={styles.calendar}>
            {WEEKDAYS.map((d) => (
              <span key={d} className={styles.weekday}>
                {d}
              </span>
            ))}
            {/* Blank cells so the 1st lands under its real weekday. */}
            {Array.from({ length: leadingBlanks }, (_, i) => (
              <span key={`blank-${i}`} />
            ))}
            {Array.from({ length: daysInMonth }, (_, i) => i + 1).map((day) => {
              const date = new Date(viewMonth.getFullYear(), viewMonth.getMonth(), day);
              const key = dayKey(date);
              const added = topicsByDay.get(key)?.length ?? 0;
              const isToday = key === dayKey(today);
              const isSelected = key === selectedKey;

              return (
                <button
                  key={key}
                  onClick={() => setSelectedKey(isSelected ? null : key)}
                  title={added > 0 ? `${added} konu eklendi` : undefined}
                  className={`${styles.day} ${isToday ? styles.dayToday : ""} ${
                    isSelected ? styles.daySelected : ""
                  }`}
                >
                  {day}
                  {added > 0 && <span className={styles.dayDot} />}
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

          {recent.length === 0 ? (
            <p className={styles.panelSubtitle}>Henüz konu eklenmedi.</p>
          ) : (
            <div className={styles.upcomingList}>
              {recent.map((topic) => (
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
