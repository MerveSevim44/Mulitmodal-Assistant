"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  FileText,
  FolderOpen,
  Image as ImageIcon,
  Mic,
  Search,
  Trash2,
} from "lucide-react";
import {
  deleteMaterial,
  getAllMaterials,
  type LibraryMaterial,
  type MaterialLibrary,
} from "@/lib/api";
import styles from "./materials.module.css";

/**
 * Materyaller sayfası.
 *
 * Konu sayfasındaki kenar çubuğu tek bir konunun dosyalarını gösterir; burası
 * ise kullanıcının yüklediği bütün materyallerin düz listesi — ders/konu farkı
 * gözetmeden, /api/v1/materials'ın tek çağrısıyla.
 *
 * Yükleme burada yok: bir dosya her zaman bir konuya bağlı, o yüzden "Yükle"
 * yolu konu sayfasında kalıyor; buradaki her satır kendi konusuna götürür.
 */

const TYPE_META = {
  pdf: { label: "PDF", icon: FileText, color: "#2563eb", soft: "#E4EDFD" },
  audio: { label: "Ses", icon: Mic, color: "#16a34a", soft: "#E2F3E8" },
  image: { label: "Görsel", icon: ImageIcon, color: "#9333ea", soft: "#F1E5FB" },
} as const;

type TypeFilter = "all" | keyof typeof TYPE_META;

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default function MaterialsPage() {
  const router = useRouter();

  const [library, setLibrary] = useState<MaterialLibrary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [courseFilter, setCourseFilter] = useState("all");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = async () => {
    try {
      const { data } = await getAllMaterials();
      setLibrary(data);
      setError("");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Materyaller yüklenemedi.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const materials = library?.materials ?? [];

  // Ders filtresi listesi — materyali olan dersler, adına göre sıralı.
  const courses = useMemo(() => {
    const byId = new Map<string, { id: string; name: string; count: number }>();
    for (const m of materials) {
      const entry = byId.get(m.course_id);
      if (entry) entry.count += 1;
      else byId.set(m.course_id, { id: m.course_id, name: m.course_name, count: 1 });
    }
    return [...byId.values()].sort((a, b) => a.name.localeCompare(b.name, "tr"));
  }, [materials]);

  const visible = useMemo(() => {
    const q = query.trim().toLocaleLowerCase("tr");
    return materials.filter((m) => {
      if (typeFilter !== "all" && m.type !== typeFilter) return false;
      if (courseFilter !== "all" && m.course_id !== courseFilter) return false;
      if (!q) return true;
      return (
        m.file_name.toLocaleLowerCase("tr").includes(q) ||
        m.topic_name.toLocaleLowerCase("tr").includes(q) ||
        m.course_name.toLocaleLowerCase("tr").includes(q)
      );
    });
  }, [materials, query, typeFilter, courseFilter]);

  const handleDelete = async (m: LibraryMaterial) => {
    if (!confirm(`"${m.file_name}" silinecek. Emin misiniz?`)) return;
    setDeletingId(m.id);
    try {
      await deleteMaterial(m.id);
      await load();
    } catch (err: any) {
      alert(`Silinemedi: ${err?.response?.data?.detail ?? err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) {
    return (
      <div className={styles.centered}>
        <div className="spinner spinner-lg" />
      </div>
    );
  }

  const filters: { key: TypeFilter; label: string; count: number }[] = [
    { key: "all", label: "Tümü", count: library?.total ?? 0 },
    { key: "pdf", label: "PDF", count: library?.pdf_count ?? 0 },
    { key: "audio", label: "Ses", count: library?.audio_count ?? 0 },
    { key: "image", label: "Görsel", count: library?.image_count ?? 0 },
  ];

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Materyaller</h1>
      <p className={styles.subtitle}>
        {materials.length === 0
          ? "Yüklediğin bütün dosyalar burada toplanır"
          : `${materials.length} dosya · ${courses.length} ders`}
      </p>

      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.toolbar}>
        <div className={styles.searchBox}>
          <Search size={15} strokeWidth={2} />
          <input
            className={styles.searchInput}
            placeholder="Dosya, konu veya ders ara"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>

        <div className={styles.chips}>
          {filters.map((f) => (
            <button
              key={f.key}
              className={`${styles.chip} ${
                typeFilter === f.key ? styles.chipActive : ""
              }`}
              onClick={() => setTypeFilter(f.key)}
            >
              {f.label}
              <span className={styles.chipCount}>{f.count}</span>
            </button>
          ))}
        </div>

        {courses.length > 1 && (
          <select
            className={styles.select}
            value={courseFilter}
            onChange={(e) => setCourseFilter(e.target.value)}
          >
            <option value="all">Tüm dersler</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.count})
              </option>
            ))}
          </select>
        )}
      </div>

      {visible.length === 0 ? (
        <div className={styles.empty}>
          <span className={styles.emptyIcon}>
            <FolderOpen size={22} strokeWidth={1.8} />
          </span>
          <p className={styles.emptyTitle}>
            {materials.length === 0
              ? "Henüz materyal yüklenmedi"
              : "Bu filtreye uyan materyal yok"}
          </p>
          <p className={styles.emptyHint}>
            {materials.length === 0
              ? "Materyaller konu sayfasından yüklenir — bir konu aç ve dosyanı ekle."
              : "Aramayı ya da filtreleri değiştirmeyi dene."}
          </p>
          {materials.length === 0 && (
            <button
              className={styles.emptyButton}
              onClick={() => router.push("/courses")}
            >
              Derslerime git
            </button>
          )}
        </div>
      ) : (
        <div className={styles.list}>
          {visible.map((m) => {
            const meta = TYPE_META[m.type];
            const Icon = meta.icon;
            const href = `/courses/${m.course_id}/topics/${m.topic_id}`;
            return (
              <div
                key={m.id}
                className={styles.row}
                role="button"
                tabIndex={0}
                onClick={() => router.push(href)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    router.push(href);
                  }
                }}
                style={
                  {
                    ["--c" as string]: meta.color,
                    ["--c-soft" as string]: meta.soft,
                  } as React.CSSProperties
                }
              >
                <span className={styles.rowIcon}>
                  <Icon size={18} strokeWidth={2} />
                </span>

                <div className={styles.rowBody}>
                  <div className={styles.rowName} title={m.file_name}>
                    {m.file_name}
                  </div>
                  <div className={styles.rowMeta}>
                    <span className={styles.rowBadge}>{meta.label}</span>
                    <span className={styles.rowPath}>
                      {m.course_name} › {m.topic_name}
                    </span>
                  </div>
                </div>

                <div className={styles.rowSide}>
                  <span className={styles.rowChunks}>{m.chunk_count} parça</span>
                  <span className={styles.rowDate}>{formatDate(m.created_at)}</span>
                </div>

                <button
                  className={styles.delButton}
                  title="Materyali sil"
                  aria-label={`${m.file_name} materyalini sil`}
                  disabled={deletingId === m.id}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(m);
                  }}
                >
                  {deletingId === m.id ? (
                    <span className="spinner" />
                  ) : (
                    <Trash2 size={14} strokeWidth={2} />
                  )}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
