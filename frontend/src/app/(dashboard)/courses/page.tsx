"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Trash2 } from "lucide-react";
import { getCourses, createCourse, deleteCourse } from "@/lib/api";
import styles from "./courses.module.css";

interface Course {
  id: string;
  name: string;
  topic_count: number;
  created_at: string;
}

/**
 * Her ders bir kağıt sayfası gibi görünüyor; renk ve eğim sıradan türetiliyor,
 * böylece aynı ders her yüklemede aynı yerde aynı renkte duruyor.
 */
const PAPERS = [
  { bg: "#EDEAFB", fold: "#D5CDF5", title: "#4B3FAE", meta: "#8A7FD6" },
  { bg: "#E3F0FC", fold: "#C4DFF5", title: "#2A6FA8", meta: "#5C97C4" },
  { bg: "#FCEAE3", fold: "#F5CFBC", title: "#B14E31", meta: "#D68868" },
  { bg: "#E7F4EA", fold: "#C6E5CF", title: "#2F7D4F", meta: "#6BA783" },
  { bg: "#FBDCE9", fold: "#F3C2D8", title: "#C2447A", meta: "#D782A6" },
  { bg: "#FCF3DD", fold: "#F0DFAF", title: "#96702A", meta: "#C0A05C" },
];

const ROTATIONS = ["-2.2deg", "1.6deg", "-1deg", "2deg"];

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
            {courses.length === 0
              ? "Başlamak için ilk dersini oluştur"
              : "Derslerini seç veya yeni ders oluştur"}
          </p>
        </div>
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

      <div className={styles.grid}>
        {courses.map((course, i) => {
          const paper = PAPERS[i % PAPERS.length];
          return (
            <div
              key={course.id}
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
              onClick={() => router.push(`/courses/${course.id}`)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  router.push(`/courses/${course.id}`);
                }
              }}
            >
              <button
                className={styles.delBtn}
                aria-label={`${course.name} dersini sil`}
                title="Dersi sil"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(course.id, course.name);
                }}
              >
                <Trash2 size={12} />
              </button>
              <div className={styles.paperTitle}>{course.name}</div>
              <div className={styles.paperMeta}>{course.topic_count || 0} konu</div>
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
          <span className={styles.newLabel}>yeni ders</span>
        </button>
      </div>
    </div>
  );
}
