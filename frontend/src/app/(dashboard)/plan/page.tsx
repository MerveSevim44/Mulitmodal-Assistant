"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { Plus, RotateCcw, X } from "lucide-react";
import { getOverview } from "@/lib/api";
import styles from "./plan.module.css";

/**
 * Study plan corkboard. There is no plans table in the backend yet, so notes
 * live in localStorage — the board is per-browser until an API exists.
 */
const STORAGE_KEY = "akademik-bellek:plan-notes:v1";

const SURFACE = { width: 1400, height: 1100 };
const NOTE_WIDTH = 250;
const NOTE_HEIGHT = 170;

/** Pin/label colours; a subject keeps its palette entry by index. */
const PALETTE = [
  { soft: "#EEF0FF", text: "#4338CA", pin: "#6366F1" },
  { soft: "#FDF0F6", text: "#BE185D", pin: "#EC4899" },
  { soft: "#EEFBF4", text: "#047857", pin: "#10B981" },
  { soft: "#FEF8EA", text: "#B45309", pin: "#F59E0B" },
  { soft: "#EEF7FE", text: "#0369A1", pin: "#0EA5E9" },
];

/** Used until the real courses arrive from /overview. */
const FALLBACK_SUBJECTS = ["Matematik", "Fizik", "Kimya", "Biyoloji", "Tarih"];

interface PlanNote {
  id: string;
  date: string; // yyyy-mm-dd
  time: string; // HH:mm
  subject: string;
  title: string;
  note: string;
  x: number;
  y: number;
  rotation: number;
  z: number;
}

type NoteDraft = Omit<PlanNote, "id" | "x" | "y" | "rotation" | "z">;

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function toISODate(date: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function formatWhen(note: PlanNote) {
  const date = new Date(`${note.date}T00:00:00`);
  if (Number.isNaN(date.getTime())) return note.time;
  const label = date.toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    weekday: "long",
  });
  return `${label} · ${note.time}`;
}

/** Fresh notes land on a zig-zag so a new board looks pinned, not stacked. */
function defaultPosition(index: number) {
  return {
    x: index % 2 === 0 ? 90 : 430,
    y: Math.min(60 + index * 210, SURFACE.height - NOTE_HEIGHT - 20),
  };
}

function loadNotes(): PlanNote[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as PlanNote[]) : [];
  } catch {
    return [];
  }
}

/* ---------------- pin ---------------- */

function Pin({ color }: { color: string }) {
  return (
    <div className={styles.pin} aria-hidden>
      <div
        className={styles.pinHead}
        style={{
          background: `radial-gradient(circle at 35% 30%, #ffffff 0%, ${color} 42%, ${color} 100%)`,
        }}
      />
      <div className={styles.pinNeedle} style={{ background: color }} />
    </div>
  );
}

/* ---------------- page ---------------- */

export default function PlanPage() {
  const [notes, setNotes] = useState<PlanNote[]>([]);
  const [hydrated, setHydrated] = useState(false);
  const [subjects, setSubjects] = useState<string[]>(FALLBACK_SUBJECTS);
  const [adding, setAdding] = useState(false);
  const [draggingId, setDraggingId] = useState<string | null>(null);

  const surfaceRef = useRef<HTMLDivElement>(null);
  // Where inside the card the pointer grabbed it, so it does not jump.
  const grabOffset = useRef({ x: 0, y: 0 });

  useEffect(() => {
    setNotes(loadNotes());
    setHydrated(true);
  }, []);

  // Persist only after the first load, or the initial empty state would
  // overwrite what is already stored.
  useEffect(() => {
    if (!hydrated) return;
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(notes));
    } catch {
      /* storage blocked or full — the board still works for this session */
    }
  }, [notes, hydrated]);

  // Real course names make better subject options than the placeholder list.
  useEffect(() => {
    getOverview()
      .then(({ data }) => {
        const names = data.courses.map((c) => c.name).filter(Boolean);
        if (names.length) setSubjects(names);
      })
      .catch(() => {
        /* keep the fallback subjects */
      });
  }, []);

  const subjectMeta = useCallback(
    (subject: string) => {
      const index = subjects.indexOf(subject);
      return PALETTE[(index < 0 ? 0 : index) % PALETTE.length];
    },
    [subjects]
  );

  const addNote = (entry: NoteDraft) => {
    setNotes((prev) => {
      const { x, y } = defaultPosition(prev.length);
      return [
        ...prev,
        {
          ...entry,
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          x,
          y,
          rotation: prev.length % 2 === 0 ? -1.5 : 1.5,
          z: prev.reduce((max, n) => Math.max(max, n.z), 0) + 1,
        },
      ];
    });
    setAdding(false);
  };

  const deleteNote = (id: string) =>
    setNotes((prev) => prev.filter((n) => n.id !== id));

  /* ── drag & drop ─────────────────────────────────────────── */

  const handlePointerDown = (
    event: ReactPointerEvent<HTMLDivElement>,
    note: PlanNote
  ) => {
    // Let the delete button (and anything else interactive) win the event.
    if ((event.target as HTMLElement).closest("button")) return;
    if (event.button !== 0) return;

    const surface = surfaceRef.current;
    if (!surface) return;

    const rect = surface.getBoundingClientRect();
    grabOffset.current = {
      x: event.clientX - rect.left - note.x,
      y: event.clientY - rect.top - note.y,
    };

    event.currentTarget.setPointerCapture(event.pointerId);
    setDraggingId(note.id);
    // Bring it to the front, and leave it there after the drop.
    setNotes((prev) => {
      const top = prev.reduce((max, n) => Math.max(max, n.z), 0);
      return prev.map((n) => (n.id === note.id ? { ...n, z: top + 1 } : n));
    });
  };

  const handlePointerMove = (
    event: ReactPointerEvent<HTMLDivElement>,
    id: string
  ) => {
    if (draggingId !== id) return;
    const surface = surfaceRef.current;
    if (!surface) return;

    const rect = surface.getBoundingClientRect();
    const x = clamp(
      event.clientX - rect.left - grabOffset.current.x,
      0,
      SURFACE.width - NOTE_WIDTH
    );
    const y = clamp(
      event.clientY - rect.top - grabOffset.current.y,
      0,
      SURFACE.height - NOTE_HEIGHT
    );

    setNotes((prev) => prev.map((n) => (n.id === id ? { ...n, x, y } : n)));
  };

  const endDrag = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    setDraggingId(null);
  };

  /** Re-pins every note back onto the zig-zag, ordered by date and time. */
  const tidyBoard = () => {
    setNotes((prev) =>
      [...prev]
        .sort((a, b) => a.date.localeCompare(b.date) || a.time.localeCompare(b.time))
        .map((note, i) => ({
          ...note,
          ...defaultPosition(i),
          rotation: i % 2 === 0 ? -1.5 : 1.5,
        }))
    );
  };

  // The number on a card is its place in the schedule, not its place on the board.
  const orderById = useMemo(() => {
    const map = new Map<string, number>();
    [...notes]
      .sort((a, b) => a.date.localeCompare(b.date) || a.time.localeCompare(b.time))
      .forEach((n, i) => map.set(n.id, i + 1));
    return map;
  }, [notes]);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Ders Planı</h1>
          <p className={styles.subtitle}>
            Panoya iğnele: hangi gün, hangi saatte, hangi dersi çalışacaksın.
            Notları sürükleyip istediğin yere bırakabilirsin.
          </p>
        </div>
        <div className={styles.headerActions}>
          <button
            className={styles.ghostButton}
            onClick={tidyBoard}
            disabled={notes.length === 0}
            title="Notları tarihe göre yeniden diz"
          >
            <RotateCcw size={14} />
            Panoyu Topla
          </button>
          <button className={styles.addButton} onClick={() => setAdding(true)}>
            <Plus size={15} />
            Yeni Not İğnele
          </button>
        </div>
      </header>

      <div className={styles.board}>
        <div
          className={styles.surface}
          ref={surfaceRef}
          style={{ width: SURFACE.width, height: SURFACE.height }}
        >
          {hydrated && notes.length === 0 && !adding && (
            <p className={styles.boardHint}>
              Pano boş — sağ üstten ilk notunu iğnele.
            </p>
          )}

          {notes.map((note) => {
            const meta = subjectMeta(note.subject);
            const isDragging = draggingId === note.id;

            return (
              <div
                key={note.id}
                className={`${styles.note} ${isDragging ? styles.noteDragging : ""}`}
                style={{
                  left: note.x,
                  top: note.y,
                  zIndex: note.z,
                  transform: `rotate(${isDragging ? 0 : note.rotation}deg)`,
                  background: `linear-gradient(180deg, var(--bg-tertiary) 0%, var(--bg-tertiary) 55%, ${meta.soft} 100%)`,
                }}
                onPointerDown={(e) => handlePointerDown(e, note)}
                onPointerMove={(e) => handlePointerMove(e, note.id)}
                onPointerUp={endDrag}
                onPointerCancel={endDrag}
              >
                <Pin color={meta.pin} />

                <button
                  className={styles.deleteButton}
                  onClick={() => deleteNote(note.id)}
                  aria-label={`${note.title} notunu sil`}
                >
                  <X size={14} />
                </button>

                <span className={styles.noteIndex} style={{ color: meta.text }}>
                  {String(orderById.get(note.id) ?? 0).padStart(2, "0")}
                </span>

                <span
                  className={styles.noteSubject}
                  style={{ backgroundColor: meta.soft, color: meta.text }}
                >
                  {note.subject}
                </span>

                <p className={styles.noteTitle}>{note.title}</p>
                {note.note && <p className={styles.noteText}>{note.note}</p>}

                <p className={styles.noteWhen} style={{ color: meta.text }}>
                  {formatWhen(note)}
                </p>
              </div>
            );
          })}

          {adding && (
            <AddNoteForm
              subjects={subjects}
              position={defaultPosition(notes.length)}
              onAdd={addNote}
              onCancel={() => setAdding(false)}
            />
          )}
        </div>
      </div>
    </div>
  );
}

/* ---------------- add form ---------------- */

function AddNoteForm({
  subjects,
  position,
  onAdd,
  onCancel,
}: {
  subjects: string[];
  position: { x: number; y: number };
  onAdd: (entry: NoteDraft) => void;
  onCancel: () => void;
}) {
  const [date, setDate] = useState(() => toISODate(new Date()));
  const [time, setTime] = useState("09:00");
  const [subject, setSubject] = useState(subjects[0]);
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");

  // The subject list changes once the courses request resolves.
  useEffect(() => {
    if (!subjects.includes(subject)) setSubject(subjects[0]);
  }, [subjects, subject]);

  const submit = () => {
    if (!title.trim()) return;
    onAdd({ date, time, subject, title: title.trim(), note: note.trim() });
  };

  return (
    <div
      className={styles.form}
      style={{ left: position.x, top: Math.min(position.y, SURFACE.height - 320) }}
    >
      <Pin color="#9CA3AF" />
      <p className={styles.formTitle}>Yeni not ekle</p>

      <div className={styles.formGrid}>
        <div className={styles.formRow}>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className={styles.field}
            aria-label="Tarih"
          />
          <input
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
            className={styles.field}
            style={{ width: 96 }}
            aria-label="Saat"
          />
        </div>

        <select
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className={styles.field}
          aria-label="Ders"
        >
          {subjects.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Ne çalışacaksın?"
          className={styles.field}
          aria-label="Başlık"
        />

        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Not (opsiyonel)"
          rows={2}
          className={`${styles.field} ${styles.textarea}`}
          aria-label="Not"
        />

        <div className={styles.formActions}>
          <button className={styles.cancelButton} onClick={onCancel}>
            Vazgeç
          </button>
          <button
            className={styles.submitButton}
            onClick={submit}
            disabled={!title.trim()}
          >
            Panoya Ekle
          </button>
        </div>
      </div>
    </div>
  );
}
