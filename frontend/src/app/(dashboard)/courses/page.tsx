"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCourses, createCourse, deleteCourse } from "@/lib/api";
import styles from "./courses.module.css";

interface Course {
  id: string;
  name: string;
  topic_count: number;
  created_at: string;
}

export default function CoursesPage() {
  const router = useRouter();
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  const loadCourses = async () => {
    try {
      const { data } = await getCourses();
      setCourses(data.courses || []);
    } catch (err) {
      console.error("Failed to load courses:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCourses();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);

    try {
      await createCourse(newName.trim());
      setNewName("");
      setShowCreate(false);
      await loadCourses();
    } catch (err) {
      console.error("Failed to create course:", err);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`"${name}" dersi ve tüm içeriği silinecek. Emin misiniz?`)) return;
    try {
      await deleteCourse(id);
      await loadCourses();
    } catch (err) {
      console.error("Failed to delete course:", err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: "60vh" }}>
        <div className="spinner spinner-lg" />
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div className={styles.header}>
        <div>
          <h1>🎓 Akademik Bellek Asistanı</h1>
          <p className={styles.subtitle}>
            Derslerini seç veya yeni ders oluştur
          </p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setShowCreate(!showCreate)}
        >
          ➕ Yeni Ders
        </button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className={styles.createForm}>
          <input
            type="text"
            className="input"
            placeholder="Ders adı (örn: Veri Yapıları)"
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

      <div className="label mt-lg">// Derslerim</div>

      {courses.length === 0 ? (
        <div className={styles.empty}>
          <p>📚 Henüz ders yok</p>
          <p className={styles.emptyHint}>
            Yukarıdaki &quot;Yeni Ders&quot; butonuna tıklayarak başla
          </p>
        </div>
      ) : (
        <div className={styles.grid}>
          {courses.map((course, i) => (
            <div
              key={course.id}
              className={`card card-interactive ${styles.courseCard}`}
              style={{ animationDelay: `${i * 50}ms` }}
              onClick={() => router.push(`/courses/${course.id}`)}
            >
              <div className={styles.cardContent}>
                <span className={styles.cardIcon}>📚</span>
                <div className="card-title">{course.name}</div>
                <div className="card-meta">
                  {course.topic_count || 0} konu
                </div>
              </div>
              <button
                className="btn btn-icon btn-ghost"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(course.id, course.name);
                }}
                title="Dersi sil"
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
