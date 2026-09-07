"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { Plus, Trash2 } from "lucide-react";
import { getTopics, createTopic, deleteTopic } from "@/lib/api";
import styles from "./course.module.css";

interface Topic {
  id: string;
  name: string;
  material_counts: {
    pdf: number;
    audio: number;
    image: number;
  };
}

/** Konu kağıtları: renk ve eğim sıradan türetiliyor, konum sabit kalıyor. */
const PAPERS = [
  { bg: "#EDEAFB", fold: "#D5CDF5", title: "#4B3FAE", meta: "#8A7FD6" },
  { bg: "#E3F0FC", fold: "#C4DFF5", title: "#2A6FA8", meta: "#5C97C4" },
  { bg: "#FCEAE3", fold: "#F5CFBC", title: "#B14E31", meta: "#D68868" },
  { bg: "#E7F4EA", fold: "#C6E5CF", title: "#2F7D4F", meta: "#6BA783" },
  { bg: "#FBDCE9", fold: "#F3C2D8", title: "#C2447A", meta: "#D782A6" },
  { bg: "#FCF3DD", fold: "#F0DFAF", title: "#96702A", meta: "#C0A05C" },
];

const ROTATIONS = ["-2.2deg", "1.6deg", "-1deg", "2deg"];

export default function CourseDetailPage({
  params,
}: {
  params: Promise<{ courseId: string }>;
}) {
  const resolvedParams = use(params);
  const courseId = resolvedParams.courseId;
  const router = useRouter();
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  const loadTopics = async () => {
    try {
      const { data } = await getTopics(courseId);
      setTopics(data.topics || []);
    } catch (err) {
      console.error("Failed to load topics:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTopics();
  }, [courseId]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);

    try {
      await createTopic(courseId, newName.trim());
      setNewName("");
      setShowCreate(false);
      await loadTopics();
    } catch (err) {
      console.error("Failed to create topic:", err);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`"${name}" konusu ve tüm materyalleri silinecek. Emin misiniz?`))
      return;
    try {
      await deleteTopic(id);
      await loadTopics();
    } catch (err) {
      console.error("Failed to delete topic:", err);
    }
  };

  if (loading) {
    return (
      <div
        className="flex items-center justify-center"
        style={{ minHeight: "60vh" }}
      >
        <div className="spinner spinner-lg" />
      </div>
    );
  }

  return (
    <div className="fade-in">
      <button
        className="btn btn-ghost mb-md"
        onClick={() => router.push("/courses")}
      >
        ← Derslere Dön
      </button>

      <div className={styles.header}>
        <div>
          <h1>📖 Ders Konuları</h1>
          <p className={styles.subtitle}>Konu seç veya yeni konu oluştur</p>
        </div>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className={styles.createForm}>
          <input
            type="text"
            className="input"
            placeholder="Konu adı (örn: Bağlı Listeler)"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            autoFocus
          />
          <button
            type="submit"
            className="btn btn-primary"
            disabled={creating || !newName.trim()}
          >
            {creating ? <span className="spinner" /> : "Oluştur"}
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => setShowCreate(false)}
          >
            İptal
          </button>
        </form>
      )}

      <div className="label mt-lg">// Konular</div>

      <div className={styles.grid}>
        {topics.map((topic, i) => {
          const paper = PAPERS[i % PAPERS.length];
          const counts = topic.material_counts;
          const hasMaterial =
            !!counts?.pdf || !!counts?.audio || !!counts?.image;
          return (
            <div
              key={topic.id}
              className={styles.paper}
              role="button"
              tabIndex={0}
              style={
                {
                  "--paper-bg": paper.bg,
                  "--paper-fold": paper.fold,
                  "--paper-title": paper.title,
                  "--paper-meta": paper.meta,
                  "--rot": ROTATIONS[i % ROTATIONS.length],
                  animationDelay: `${i * 50}ms`,
                } as React.CSSProperties
              }
              onClick={() =>
                router.push(`/courses/${courseId}/topics/${topic.id}`)
              }
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  router.push(`/courses/${courseId}/topics/${topic.id}`);
                }
              }}
            >
              <button
                className={styles.delBtn}
                aria-label={`${topic.name} konusunu sil`}
                title="Konuyu sil"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(topic.id, topic.name);
                }}
              >
                <Trash2 size={12} />
              </button>
              <div className={styles.paperTitle}>{topic.name}</div>
              <div className={styles.badges}>
                {counts?.pdf > 0 && (
                  <span className={styles.paperBadge}>📄 {counts.pdf}</span>
                )}
                {counts?.audio > 0 && (
                  <span className={styles.paperBadge}>🎤 {counts.audio}</span>
                )}
                {counts?.image > 0 && (
                  <span className={styles.paperBadge}>🖼️ {counts.image}</span>
                )}
                {!hasMaterial && (
                  <span className={styles.emptyBadge}>materyal yok</span>
                )}
              </div>
            </div>
          );
        })}

        <button
          type="button"
          className={styles.newCard}
          onClick={() => setShowCreate(true)}
        >
          <span className={styles.newPlus}>
            <Plus size={15} strokeWidth={2.2} />
          </span>
          <span className={styles.newLabel}>yeni konu</span>
        </button>
      </div>
    </div>
  );
}
