"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Brain,
  CheckCircle2,
  ExternalLink,
  FileText,
  Image as ImageIcon,
  Info,
  Mic,
  RotateCcw,
} from "lucide-react";
import axios from "axios";
import {
  formatDayCount,
  getReviewQueue,
  getTopicReview,
  submitReview,
  REVIEW_GRADES,
  REVIEW_GRADE_LABELS,
  type ReviewGrade,
  type ReviewTopic,
} from "@/lib/api";
import styles from "./review.module.css";

/**
 * The review screen — one topic at a time, graded with the four SM-2 buttons.
 *
 * Every interval shown here comes from the server (`preview_days` on
 * /reviews/topics/{id}); the scheduling maths deliberately has no second
 * implementation in the browser, so a change to the algorithm cannot leave
 * the button labels lying about what they will do.
 *
 * `?topic=<id>` starts the session on a specific topic — that is what the
 * "Tekrar Et" buttons on the home dashboard link to.
 */

/** How each grade reads, and which colour it takes. */
const GRADE_HINTS: Record<ReviewGrade, string> = {
  hard: "Hatırlayamadım",
  medium: "Zorlanarak hatırladım",
  easy: "Rahat hatırladım",
  very_easy: "Anında hatırladım",
};

const GRADE_CLASS: Record<ReviewGrade, string> = {
  hard: styles.gradeHard,
  medium: styles.gradeMedium,
  easy: styles.gradeEasy,
  very_easy: styles.gradeVeryEasy,
};

function sourceIcons(topic: ReviewTopic) {
  const icons: { Icon: typeof FileText; label: string }[] = [];
  if (topic.pdf_count > 0) icons.push({ Icon: FileText, label: `${topic.pdf_count} PDF` });
  if (topic.audio_count > 0) icons.push({ Icon: Mic, label: `${topic.audio_count} ses kaydı` });
  if (topic.image_count > 0)
    icons.push({ Icon: ImageIcon, label: `${topic.image_count} görsel` });
  return icons;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function ReviewSession() {
  const router = useRouter();
  const params = useSearchParams();
  const focusTopicId = params.get("topic");

  const [queue, setQueue] = useState<ReviewTopic[]>([]);
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Per-button interval preview for the topic on screen, fetched from the
  // server. Null while it is in flight — the buttons stay usable, just
  // without their "· 6 gün" suffix.
  const [preview, setPreview] = useState<Record<ReviewGrade, number> | null>(null);
  const [submitting, setSubmitting] = useState<ReviewGrade | null>(null);
  // What the last grade scheduled, shown as a confirmation line.
  const [lastResult, setLastResult] = useState<{ name: string; days: number } | null>(
    null
  );
  const [reviewedCount, setReviewedCount] = useState(0);

  const current: ReviewTopic | undefined = queue[index];

  useEffect(() => {
    // The whole queue, not just what is due: a user who opens a specific
    // topic from the dashboard may well be reviewing it ahead of schedule.
    getReviewQueue(false)
      .then(({ data }) => {
        const topics = data.topics;
        setQueue(topics);
        if (focusTopicId) {
          const at = topics.findIndex((t) => t.id === focusTopicId);
          if (at >= 0) setIndex(at);
        }
      })
      .catch((err) => {
        if (!axios.isCancel(err)) {
          console.error("Failed to load review queue:", err);
          setError("Tekrar listesi yüklenemedi.");
        }
      })
      .finally(() => setLoading(false));
  }, [focusTopicId]);

  useEffect(() => {
    if (!current) return;
    let cancelled = false;
    setPreview(null);
    getTopicReview(current.id)
      .then(({ data }) => {
        if (!cancelled) setPreview(data.preview_days);
      })
      .catch(() => {
        // A missing preview only costs the interval hint on the buttons.
        if (!cancelled) setPreview(null);
      });
    return () => {
      cancelled = true;
    };
  }, [current]);

  const advance = useCallback(() => {
    setIndex((i) => i + 1);
  }, []);

  const grade = async (value: ReviewGrade) => {
    if (!current || submitting) return;
    setSubmitting(value);
    setError(null);
    try {
      const { data } = await submitReview(current.id, value);
      setLastResult({ name: current.name, days: data.schedule.interval_days });
      setReviewedCount((n) => n + 1);
      advance();
    } catch (err) {
      console.error("Failed to submit review:", err);
      setError("Tekrar kaydedilemedi. Tekrar dene.");
    } finally {
      setSubmitting(null);
    }
  };

  // Only the topics still ahead in this session, for the "sırada" strip.
  const upNext = useMemo(() => queue.slice(index + 1, index + 4), [queue, index]);

  if (loading) {
    return (
      <div className={styles.centered}>
        <div className="spinner spinner-lg" />
      </div>
    );
  }

  if (queue.length === 0) {
    return (
      <div className={styles.centered}>
        <div className={styles.empty}>
          <Brain size={36} className={styles.emptyIcon} />
          <h1 className={styles.emptyTitle}>Tekrar edilecek konu yok</h1>
          <p className={styles.emptyText}>
            Bir ders açıp konu ekle; her yeni konu tekrar listesine hemen düşer.
          </p>
          <button className={styles.primaryButton} onClick={() => router.push("/courses")}>
            Derslerime Git
          </button>
        </div>
      </div>
    );
  }

  if (!current) {
    return (
      <div className={styles.centered}>
        <div className={styles.empty}>
          <CheckCircle2 size={36} className={styles.emptyIconDone} />
          <h1 className={styles.emptyTitle}>Oturum tamamlandı</h1>
          <p className={styles.emptyText}>
            {reviewedCount > 0
              ? `Bu oturumda ${reviewedCount} konu tekrar edildi.`
              : "Listedeki bütün konulara baktın."}
            {lastResult &&
              ` Son olarak "${lastResult.name}" ${formatDayCount(
                lastResult.days
              )} tekrar edilecek.`}
          </p>
          <div className={styles.emptyActions}>
            <button
              className={styles.secondaryButton}
              onClick={() => {
                setIndex(0);
                setReviewedCount(0);
              }}
            >
              <RotateCcw size={15} /> Baştan Başla
            </button>
            <button className={styles.primaryButton} onClick={() => router.push("/")}>
              Ana Sayfa
            </button>
          </div>
        </div>
      </div>
    );
  }

  const icons = sourceIcons(current);
  const progress = ((index + (submitting ? 1 : 0)) / queue.length) * 100;

  return (
    <div className={styles.wrap}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Tekrar Oturumu</h1>
          <p className={styles.subtitle}>
            {index + 1} / {queue.length} konu · aralıklı tekrar (SM-2)
          </p>
        </div>
        <button className={styles.linkButton} onClick={() => router.push("/")}>
          Oturumu bitir
        </button>
      </header>

      <div className={styles.progressTrack}>
        <div className={styles.progressBar} style={{ width: `${progress}%` }} />
      </div>

      {lastResult && (
        <p className={styles.toast}>
          <CheckCircle2 size={14} /> “{lastResult.name}” kaydedildi —{" "}
          {formatDayCount(lastResult.days)} tekrar edilecek.
        </p>
      )}

      {error && <p className={styles.error}>{error}</p>}

      <section className={styles.card}>
        <span className={styles.tag}>{current.course_name}</span>
        <h2 className={styles.topicName}>{current.name}</h2>

        <div className={styles.sources}>
          {icons.length === 0 ? (
            <span className={styles.sourceEmpty}>Bu konuda henüz materyal yok</span>
          ) : (
            icons.map(({ Icon, label }) => (
              <span key={label} className={styles.source}>
                <Icon size={13} /> {label}
              </span>
            ))
          )}
          <button
            className={styles.linkButton}
            onClick={() =>
              router.push(`/courses/${current.course_id}/topics/${current.id}`)
            }
          >
            Konuyu aç <ExternalLink size={13} />
          </button>
        </div>

        <dl className={styles.stats}>
          <div className={styles.stat}>
            <dt>Son tekrar</dt>
            <dd>{formatDate(current.last_reviewed_at)}</dd>
          </div>
          <div className={styles.stat}>
            <dt>Planlanan tarih</dt>
            <dd>
              {formatDate(current.next_review_at)}
              {current.next_review_at && (
                <span className={current.due ? styles.due : styles.notDue}>
                  {" "}
                  ({formatDayCount(current.days_until_due)})
                </span>
              )}
            </dd>
          </div>
          <div className={styles.stat}>
            <dt>Kolaylık faktörü</dt>
            <dd>{current.ease_factor.toFixed(2)}</dd>
          </div>
          <div className={styles.stat}>
            <dt>Ardışık doğru</dt>
            <dd>
              {current.repetitions}
              {current.lapses > 0 && (
                <span className={styles.lapses}> · {current.lapses} kez zorlandın</span>
              )}
            </dd>
          </div>
        </dl>

        <p className={styles.prompt}>
          Konuyu aklından geçir, sonra ne kadar zorlandığını işaretle.
        </p>

        <div className={styles.grades}>
          {REVIEW_GRADES.map((value) => (
            <button
              key={value}
              className={`${styles.grade} ${GRADE_CLASS[value]}`}
              onClick={() => grade(value)}
              disabled={submitting !== null}
            >
              <span className={styles.gradeLabel}>{REVIEW_GRADE_LABELS[value]}</span>
              <span className={styles.gradeHint}>{GRADE_HINTS[value]}</span>
              <span className={styles.gradeInterval}>
                {preview ? formatDayCount(preview[value]) : "…"}
              </span>
            </button>
          ))}
        </div>

        <p className={styles.note}>
          <Info size={12} />
          Süreler SM-2 algoritmasıyla hesaplanır: kolay bulduğun konular
          seyrekleşir, zorlandıkların yarın tekrar karşına çıkar.
        </p>

        <button className={styles.skip} onClick={advance} disabled={submitting !== null}>
          Şimdilik atla
        </button>
      </section>

      {upNext.length > 0 && (
        <section className={styles.upNext}>
          <span className={styles.upNextTitle}>Sırada</span>
          <div className={styles.upNextList}>
            {upNext.map((topic) => (
              <div key={topic.id} className={styles.upNextItem}>
                <span className={styles.upNextCourse}>{topic.course_name}</span>
                <span className={styles.upNextName}>{topic.name}</span>
                <span className={styles.upNextWhen}>
                  {formatDayCount(topic.days_until_due)}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

/**
 * `useSearchParams` forces the subtree into client-side rendering, so Next
 * requires a Suspense boundary around it — without one the production build
 * fails on this route.
 */
export default function ReviewPage() {
  return (
    <Suspense
      fallback={
        <div className={styles.centered}>
          <div className="spinner spinner-lg" />
        </div>
      }
    >
      <ReviewSession />
    </Suspense>
  );
}
