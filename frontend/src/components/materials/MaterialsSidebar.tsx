"use client";

import { useState, useEffect } from "react";
import { getMaterials, deleteMaterial, uploadMaterial, detectMaterialType } from "@/lib/api";
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

    // File validation. Size is checked inside uploadMaterial, against the
    // per-bucket limit rather than one blanket number — the old 60MB gate let
    // through files the buckets themselves reject.
    const type = detectMaterialType(file);
    if (!type) {
      alert("Desteklenmeyen dosya formatı.");
      return;
    }

    setUploading(true);
    setUploadProgress(`Yükleniyor: ${file.name}...`);

    try {
      // The progress line used to flip to "İşleniyor" only after the whole
      // call returned — so the slowest stage by far, transcription, ran
      // under a label that said "Yükleniyor" and looked frozen.
      await uploadMaterial(topicId, file, type, (phase) => {
        setUploadProgress(
          phase === "uploading"
            ? `Yükleniyor: ${file.name}...`
            : type === "audio"
              ? "Ses çözümleniyor (uzun kayıtlarda birkaç dakika sürebilir)..."
              : "İşleniyor..."
        );
      });
      setUploadProgress("Tamamlanıyor...");
      await loadMaterials();
    } catch (err: any) {
      // The backend reports processing failures (transcription, ingest) in
      // `detail`; without it the alert only ever said "Request failed with
      // status code 500".
      alert(`Yükleme hatası: ${err?.response?.data?.detail ?? err.message}`);
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
            PDF (50MB), Ses MP3/WAV/M4A (50MB), Görsel PNG/JPG (10MB)
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
