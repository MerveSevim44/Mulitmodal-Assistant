"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
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
          <p className={styles.subtitle}>
            Konu seç veya yeni konu oluştur
          </p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setShowCreate(!showCreate)}
        >
          ➕ Yeni Konu
        </button>
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

      {topics.length === 0 ? (
        <div className={styles.empty}>
          <p>📋 Henüz konu yok</p>
          <p className={styles.emptyHint}>
            &quot;Yeni Konu&quot; butonuna tıklayarak ilk konunu oluştur
          </p>
        </div>
      ) : (
        <div className={styles.grid}>
          {topics.map((topic, i) => (
            <div
              key={topic.id}
              className={`card card-interactive ${styles.topicCard}`}
              style={{ animationDelay: `${i * 50}ms` }}
              onClick={() =>
                router.push(`/courses/${courseId}/topics/${topic.id}`)
              }
            >
              <div className={styles.cardContent}>
                <div className="card-title">{topic.name}</div>
                <div className={styles.badges}>
                  {topic.material_counts?.pdf > 0 && (
                    <span className="badge badge-pdf">
                      📄 {topic.material_counts.pdf} PDF
                    </span>
                  )}
                  {topic.material_counts?.audio > 0 && (
                    <span className="badge badge-audio">
                      🎤 {topic.material_counts.audio} Ses
                    </span>
                  )}
                  {topic.material_counts?.image > 0 && (
                    <span className="badge badge-image">
                      🖼️ {topic.material_counts.image} Görsel
                    </span>
                  )}
                  {!topic.material_counts?.pdf &&
                    !topic.material_counts?.audio &&
                    !topic.material_counts?.image && (
                      <span className={styles.emptyBadge}>Materyal yok</span>
                    )}
                </div>
              </div>
              <button
                className="btn btn-icon btn-ghost"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(topic.id, topic.name);
                }}
                title="Konuyu sil"
              >
                🗑
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
