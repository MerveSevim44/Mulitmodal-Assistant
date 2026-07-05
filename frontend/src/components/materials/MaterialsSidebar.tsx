"use client";

import { useState, useEffect } from "react";
import { getMaterials, deleteMaterial, uploadMaterial } from "@/lib/api";
import styles from "./materials.module.css";

interface Material {
  id: string;
  type: "pdf" | "audio" | "image";
  file_name: string;
  created_at: string;
  chunk_count: number;
}

export default function MaterialsSidebar({ topicId }: { topicId: string }) {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState("");

  const loadMaterials = async () => {
    try {
      const { data } = await getMaterials(topicId);
      setMaterials(data.materials || []);
    } catch (err) {
      console.error("Failed to load materials:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMaterials();
  }, [topicId]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Reset input
    e.target.value = "";

    // File validation
    const ext = file.name.split(".").pop()?.toLowerCase() || "";
    let type: "pdf" | "audio" | "image" | null = null;

    if (ext === "pdf") type = "pdf";
    else if (["mp3", "mp4", "wav", "m4a"].includes(ext)) type = "audio";
    else if (["png", "jpg", "jpeg"].includes(ext)) type = "image";

    if (!type) {
      alert("Desteklenmeyen dosya formatı.");
      return;
    }

    if (file.size > 60 * 1024 * 1024) {
      alert("Dosya boyutu 60MB'dan küçük olmalıdır.");
      return;
    }

    setUploading(true);
    setUploadProgress(`Yükleniyor: ${file.name}...`);

    try {
      await uploadMaterial(topicId, file, type);
      setUploadProgress("İşleniyor...");
      await loadMaterials();
    } catch (err: any) {
      alert(`Yükleme hatası: ${err.message}`);
    } finally {
      setUploading(false);
      setUploadProgress("");
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`"${name}" silinecek. Emin misiniz?`)) return;
    try {
      await deleteMaterial(id);
      await loadMaterials();
    } catch (err) {
      console.error("Failed to delete material:", err);
    }
  };

  const getIcon = (type: string) => {
    switch (type) {
      case "pdf": return "📄";
      case "audio": return "🎤";
      case "image": return "🖼️";
      default: return "📁";
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className="mono" style={{ fontSize: "14px", color: "var(--text-label)" }}>
          // Konu Materyalleri
        </h3>
      </div>

      <div className={styles.uploadArea}>
        <label className={styles.uploadBox}>
          <input
            type="file"
            onChange={handleFileUpload}
            disabled={uploading}
            style={{ display: "none" }}
            accept=".pdf,.mp3,.mp4,.wav,.m4a,.png,.jpg,.jpeg"
          />
          <div className={styles.uploadIcon}>📥</div>
          <div className={styles.uploadText}>
            {uploading ? (
              <span className="pulse">{uploadProgress}</span>
            ) : (
              <>Dosya Seç veya Sürükle Bırak</>
            )}
          </div>
          <div className={styles.uploadSubtext}>
            PDF, Ses (MP3/WAV), Görsel (PNG/JPG) - Max 60MB
          </div>
        </label>
      </div>

      <div className={styles.list}>
        {loading ? (
          <div className="flex justify-center mt-lg"><div className="spinner" /></div>
        ) : materials.length === 0 ? (
          <div className={styles.empty}>Henüz materyal yüklenmedi.</div>
        ) : (
          materials.map((m) => (
            <div key={m.id} className={styles.materialItem}>
              <div className={styles.materialIcon}>{getIcon(m.type)}</div>
              <div className={styles.materialInfo}>
                <div className={styles.materialName} title={m.file_name}>
                  {m.file_name}
                </div>
                <div className={styles.materialMeta}>
                  {new Date(m.created_at).toLocaleDateString("tr-TR")} • {m.chunk_count} parça
                </div>
              </div>
              <button
                className="btn btn-icon btn-ghost"
                onClick={() => handleDelete(m.id, m.file_name)}
                title="Sil"
              >
                🗑
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
