"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Trash2, Folder } from "lucide-react";
import { getCourses, createCourse, deleteCourse } from "@/lib/api";
import styles from "./courses.module.css";

interface Course {
  id: string;
  name: string;
  topic_count: number;
  created_at: string;
}

/**
 * Her ders bir dosya klasörü; renk sıradan türetiliyor, böylece aynı ders
 * her yüklemede aynı yerde aynı renkte duruyor.
 */
const FOLDERS = [
  { c1: "#E7E1FC", c2: "#B7A6F0", ink: "#6C4CF5" },
  { c1: "#DCEBFB", c2: "#8FBEEB", ink: "#2A6FA8" },
  { c1: "#FBEBDF", c2: "#F0B283", ink: "#B14E31" },
  { c1: "#E1F2E7", c2: "#95CDAB", ink: "#2F7D4F" },
  { c1: "#FBE0EC", c2: "#EFA2C4", ink: "#C2447A" },
  { c1: "#FCF3DD", c2: "#EBCD8A", ink: "#96702A" },
];

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
          const folder = FOLDERS[i % FOLDERS.length];
          return (
            <div
              key={course.id}
              className={styles.folder}
              style={
                {
                  "--folder-c1": folder.c1,
                  "--folder-c2": folder.c2,
                  "--folder-ink": folder.ink,
                  animationDelay: `${i * 50}ms`,
                } as React.CSSProperties
              }
            >
              <div className={styles.folderTab} />
              <div
                className={styles.folderBody}
                role="button"
                tabIndex={0}
                onClick={() => router.push(`/courses/${course.id}`)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    router.push(`/courses/${course.id}`);
                  }
                }}
              >
                <div className={styles.folderTitle}>{course.name}</div>
                <div>
                  <div className={styles.folderDivider} />
                  <div className={styles.folderFooter}>
                    <span className={styles.miniIcon}>
                      <Folder size={14} strokeWidth={2} />
                    </span>
                    <span className={styles.topicCount}>
                      {course.topic_count || 0} konu
                    </span>
                  </div>
                </div>
              </div>
              <button
                className={styles.delBtn}
                aria-label={`${course.name} dersini sil`}
                title="Dersi sil"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(course.id, course.name);
                }}
              >
                <Trash2 size={13} />
              </button>
            </div>
          );
        })}

        <button
          type="button"
          className={styles.newCard}
          onClick={() => setShowCreate(true)}
        >
          <span className={styles.newCardBody}>
            <span className={styles.newPlus}>
              <Plus size={15} strokeWidth={2.2} />
            </span>
            <span className={styles.newLabel}>Yeni Ders</span>
          </span>
        </button>
      </div>
    </div>
  );
}
