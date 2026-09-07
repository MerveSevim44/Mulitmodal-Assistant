"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { User } from "@supabase/supabase-js";
import {
  BookOpen,
  Check,
  FileText,
  FolderOpen,
  Image as ImageIcon,
  Info,
  Lock,
  LogOut,
  Mic,
  Target,
  Trash2,
} from "lucide-react";
import { supabase } from "@/lib/supabase";
import { deleteCourse, getOverview, type OverviewData } from "@/lib/api";
import styles from "./profile.module.css";

/**
 * Profil sayfası.
 *
 * Ekrandaki her sayı gerçek veriden gelir: istatistikler /api/v1/overview'in
 * ders / konu / materyal ağacından, kimlik bilgileri Supabase oturumundan.
 * Backend'de bir profiles tablosu yok, bu yüzden düzenlenebilir alanlar
 * Supabase Auth'un user_metadata'sına yazılır — ayrı bir tabloya (ve
 * migration'a) gerek kalmadan gerçekten veritabanında durur.
 *
 * Tekrar serisi / tamamlanan tekrar gibi alanlar burada yok: ortada bir
 * reviews tablosu olmadığı için uydurulmuş sayı göstermek yerine kütüphanenin
 * gerçek dağılımı gösteriliyor (ana sayfadaki yaklaşımın aynısı).
 */

interface ProfileMetadata {
  full_name?: string;
  school?: string;
  grade?: string;
  exam?: string;
  weekly_goal?: number;
  reminder_time?: string;
  notifications?: boolean;
  email_summary?: boolean;
}

const EXAM_OPTIONS = ["Belirtilmedi", "YKS", "LGS", "KPSS", "ALES", "Vize / Final", "Diğer"];
const GOAL_OPTIONS = [3, 5, 10, 15];

/** Materyal türlerinin rengi — globals.css'teki badge renkleriyle aynı. */
const TYPE_COLORS = { pdf: "#2563eb", audio: "#16a34a", image: "#9333ea" };

const DEFAULTS: Required<Pick<ProfileMetadata, "exam" | "weekly_goal" | "reminder_time">> = {
  exam: EXAM_OPTIONS[0],
  weekly_goal: 5,
  reminder_time: "20:00",
};

function formatDate(iso?: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/** Pazartesi 00:00 — haftalık hedefin başlangıcı. */
function startOfWeek(now: Date): Date {
  const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  monday.setDate(monday.getDate() - ((now.getDay() + 6) % 7));
  return monday;
}

function StatCard({
  color,
  soft,
  icon,
  value,
  label,
}: {
  color: string;
  soft: string;
  icon: React.ReactNode;
  value: React.ReactNode;
  label: string;
}) {
  return (
    <div
      className={styles.statCard}
      style={{ ["--c" as string]: color, ["--c-soft" as string]: soft }}
    >
      <div className={styles.statIcon}>{icon}</div>
      <div className={styles.statValue}>{value}</div>
      <div className={styles.statLabel}>{label}</div>
    </div>
  );
}

export default function ProfilePage() {
  const router = useRouter();

  const [user, setUser] = useState<User | null>(null);
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);

  // Düzenlenebilir alanlar (user_metadata'ya kaydedilir).
  const [form, setForm] = useState<ProfileMetadata>({});
  const [editingName, setEditingName] = useState(false);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<{ ok: boolean; text: string } | null>(null);

  // Hesap bölümündeki açılır paneller.
  const [panel, setPanel] = useState<"password" | "wipe" | null>(null);
  const [password, setPassword] = useState({ next: "", confirm: "" });
  const [wipeConfirm, setWipeConfirm] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      if (!data.user) return;
      setUser(data.user);
      const meta = (data.user.user_metadata ?? {}) as ProfileMetadata;
      setForm({ ...DEFAULTS, ...meta });
    });

    getOverview()
      .then(({ data }) => setOverview(data))
      .catch((err) => console.error("Profil özeti alınamadı:", err))
      .finally(() => setLoading(false));
  }, []);

  const refreshOverview = useCallback(() => {
    getOverview()
      .then(({ data }) => setOverview(data))
      .catch(() => setOverview(null));
  }, []);

  const stats = useMemo(() => {
    if (!overview) return null;

    const types = { pdf: 0, audio: 0, image: 0 };
    overview.topics.forEach((t) => {
      types.pdf += t.pdf_count;
      types.audio += t.audio_count;
      types.image += t.image_count;
    });

    const weekStart = startOfWeek(new Date()).getTime();
    const thisWeek = overview.topics.filter(
      (t) => new Date(t.created_at).getTime() >= weekStart
    ).length;

    // /overview konuları en yeniden eskiye sıralı döndürüyor.
    const lastActivity = overview.topics[0]?.created_at;

    return { types, thisWeek, lastActivity };
  }, [overview]);

  const displayName =
    (form.full_name || "").trim() || user?.email?.split("@")[0] || "Öğrenci";
  const initial = displayName.charAt(0).toLocaleUpperCase("tr-TR");

  /** Alanları Supabase Auth'un user_metadata'sına yazar. */
  const saveMetadata = async (patch: ProfileMetadata) => {
    setSaving(true);
    setStatus(null);
    const { data, error } = await supabase.auth.updateUser({ data: patch });
    setSaving(false);

    if (error) {
      setStatus({ ok: false, text: `Kaydedilemedi: ${error.message}` });
      return false;
    }
    if (data.user) setUser(data.user);
    setStatus({ ok: true, text: "Kaydedildi" });
    return true;
  };

  const saveAcademic = () =>
    saveMetadata({
      school: form.school?.trim() || "",
      grade: form.grade?.trim() || "",
      exam: form.exam ?? DEFAULTS.exam,
      weekly_goal: form.weekly_goal ?? DEFAULTS.weekly_goal,
    });

  /** Tercih satırları anında kaydedilir — ayrı bir kaydet butonu yok. */
  const savePreference = async (patch: ProfileMetadata) => {
    setForm((prev) => ({ ...prev, ...patch }));
    await saveMetadata(patch);
  };

  const saveName = async () => {
    const ok = await saveMetadata({ full_name: form.full_name?.trim() || "" });
    if (ok) setEditingName(false);
  };

  const changePassword = async () => {
    if (password.next.length < 6) {
      setStatus({ ok: false, text: "Şifre en az 6 karakter olmalı" });
      return;
    }
    if (password.next !== password.confirm) {
      setStatus({ ok: false, text: "Şifreler eşleşmiyor" });
      return;
    }

    setBusy(true);
    const { error } = await supabase.auth.updateUser({ password: password.next });
    setBusy(false);

    if (error) {
      setStatus({ ok: false, text: `Şifre değiştirilemedi: ${error.message}` });
      return;
    }
    setStatus({ ok: true, text: "Şifre güncellendi" });
    setPassword({ next: "", confirm: "" });
    setPanel(null);
  };

  /**
   * Bütün dersleri siler. Ders silme backend'de konulara, materyallere,
   * mesajlara ve vektör kayıtlarına kadar zincirleme gidiyor — yani bu işlem
   * kütüphaneyi gerçekten boşaltır.
   */
  const wipeData = async () => {
    if (!overview) return;
    setBusy(true);
    try {
      for (const course of overview.courses) {
        await deleteCourse(course.id);
      }
      setStatus({ ok: true, text: "Tüm ders verilerin silindi" });
      setPanel(null);
      setWipeConfirm("");
      refreshOverview();
    } catch (err) {
      console.error(err);
      setStatus({ ok: false, text: "Silme sırasında bir hata oldu" });
    } finally {
      setBusy(false);
    }
  };

  const logout = async () => {
    await supabase.auth.signOut();
    router.push("/login");
  };

  if (loading || !user) {
    return (
      <div className={styles.centered}>
        <div className="spinner spinner-lg" />
      </div>
    );
  }

  const totalMaterials = overview?.total_materials ?? 0;
  const goal = form.weekly_goal ?? DEFAULTS.weekly_goal;

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Profilim</h1>
      <p className={styles.subtitle}>
        Hesap bilgilerini ve çalışma tercihlerini yönet
      </p>

      {/* ── Başlık ──────────────────────────────────────────── */}
      <div className={styles.header}>
        <div className={styles.avatar}>{initial}</div>

        <div className={styles.headerBody}>
          {editingName ? (
            <input
              className={styles.nameInput}
              value={form.full_name ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
              placeholder="Adın"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") saveName();
                if (e.key === "Escape") setEditingName(false);
              }}
            />
          ) : (
            <div className={styles.name}>{displayName}</div>
          )}

          <div className={styles.email}>{user.email}</div>

          <div className={styles.badgeRow}>
            <span className={styles.badge}>
              ✦ {formatDate(user.created_at)} tarihinde katıldı
            </span>
            {stats?.lastActivity && (
              <span className={styles.badge}>
                son konu · {formatDate(stats.lastActivity)}
              </span>
            )}
          </div>
        </div>

        {editingName ? (
          <div className={styles.inlineActions}>
            <button
              className={styles.ghostButton}
              onClick={() => setEditingName(false)}
              disabled={saving}
            >
              Vazgeç
            </button>
            <button className={styles.primaryButton} onClick={saveName} disabled={saving}>
              {saving ? "Kaydediliyor…" : "Kaydet"}
            </button>
          </div>
        ) : (
          <button className={styles.primaryButton} onClick={() => setEditingName(true)}>
            Profili Düzenle
          </button>
        )}
      </div>

      {/* ── İstatistikler ───────────────────────────────────── */}
      <div className={styles.sectionLabel}>// ÇALIŞMA İSTATİSTİKLERİM</div>
      <div className={styles.statsGrid}>
        <StatCard
          color="var(--accent)"
          soft="var(--accent-soft)"
          icon={<BookOpen size={15} />}
          value={overview?.total_courses ?? 0}
          label="Toplam ders"
        />
        <StatCard
          color="#2563eb"
          soft="rgba(37, 99, 235, 0.12)"
          icon={<FolderOpen size={15} />}
          value={overview?.total_topics ?? 0}
          label="Toplam konu"
        />
        <StatCard
          color="#9333ea"
          soft="rgba(147, 51, 234, 0.12)"
          icon={<FileText size={15} />}
          value={totalMaterials}
          label="Yüklenen materyal"
        />
        <StatCard
          color="#16a34a"
          soft="rgba(22, 163, 74, 0.12)"
          icon={<Target size={15} />}
          value={`${stats?.thisWeek ?? 0}/${goal}`}
          label="Bu hafta eklenen konu"
        />
      </div>

      {/* ── Kütüphane dağılımı ──────────────────────────────── */}
      <div className={styles.sectionLabel}>// KÜTÜPHANE DAĞILIMI</div>
      <div className={styles.card}>
        {totalMaterials === 0 ? (
          <p className={styles.warning}>
            Henüz materyal yüklemedin. Bir konuya PDF, ses kaydı ya da görsel
            ekledikçe dağılım burada görünecek.
          </p>
        ) : (
          <>
            <div className={styles.bar}>
              {(["pdf", "audio", "image"] as const).map((type) => {
                const count = stats?.types[type] ?? 0;
                if (count === 0) return null;
                return (
                  <div
                    key={type}
                    className={styles.barSegment}
                    style={{
                      width: `${(count / totalMaterials) * 100}%`,
                      background: TYPE_COLORS[type],
                    }}
                  />
                );
              })}
            </div>

            <div className={styles.legend}>
              <span className={styles.legendItem}>
                <span
                  className={styles.legendDot}
                  style={{ background: TYPE_COLORS.pdf }}
                />
                <FileText size={13} /> PDF
                <span className={styles.legendValue}>{stats?.types.pdf ?? 0}</span>
              </span>
              <span className={styles.legendItem}>
                <span
                  className={styles.legendDot}
                  style={{ background: TYPE_COLORS.audio }}
                />
                <Mic size={13} /> Ses kaydı
                <span className={styles.legendValue}>{stats?.types.audio ?? 0}</span>
              </span>
              <span className={styles.legendItem}>
                <span
                  className={styles.legendDot}
                  style={{ background: TYPE_COLORS.image }}
                />
                <ImageIcon size={13} /> Görsel
                <span className={styles.legendValue}>{stats?.types.image ?? 0}</span>
              </span>
            </div>
          </>
        )}

        <p className={styles.note}>
          <Info size={12} />
          {overview?.empty_topics
            ? `${overview.empty_topics} konuda henüz materyal yok — tekrar için önce kaynak eklemen gerekiyor.`
            : "Sayılar derslerinin altındaki konulardan gerçek zamanlı toplanıyor."}
        </p>
      </div>

      {/* ── Akademik bilgiler ───────────────────────────────── */}
      <div className={styles.sectionLabel}>// AKADEMİK BİLGİLER</div>
      <div className={styles.card}>
        <div className={styles.formGrid}>
          <div className={styles.field}>
            <label htmlFor="school">Okul / Üniversite</label>
            <input
              id="school"
              value={form.school ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, school: e.target.value }))}
              placeholder="örn. Ankara Üniversitesi"
            />
          </div>

          <div className={styles.field}>
            <label htmlFor="grade">Sınıf / Bölüm</label>
            <input
              id="grade"
              value={form.grade ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, grade: e.target.value }))}
              placeholder="örn. 11. Sınıf, Sayısal"
            />
          </div>

          <div className={styles.field}>
            <label htmlFor="exam">Hazırlandığın Sınav</label>
            <select
              id="exam"
              value={form.exam ?? DEFAULTS.exam}
              onChange={(e) => setForm((f) => ({ ...f, exam: e.target.value }))}
            >
              {EXAM_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.field}>
            <label htmlFor="goal">Haftalık Konu Hedefi</label>
            <select
              id="goal"
              value={goal}
              onChange={(e) =>
                setForm((f) => ({ ...f, weekly_goal: Number(e.target.value) }))
              }
            >
              {GOAL_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option} konu
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className={styles.formFooter}>
          {status && (
            <span className={status.ok ? styles.savedNote : styles.errorNote}>
              {status.text}
            </span>
          )}
          <button className={styles.primaryButton} onClick={saveAcademic} disabled={saving}>
            {saving ? "Kaydediliyor…" : <><Check size={14} /> Bilgileri Kaydet</>}
          </button>
        </div>

        <p className={styles.note}>
          <Info size={12} />
          Haftalık hedef yukarıdaki &quot;bu hafta eklenen konu&quot; kartında
          takip edilir; bu hafta {stats?.thisWeek ?? 0} konu eklendi.
        </p>
      </div>

      {/* ── Tercihler ───────────────────────────────────────── */}
      <div className={styles.sectionLabel}>// ÇALIŞMA TERCİHLERİ</div>
      <div className={styles.card}>
        <div className={styles.toggleRow}>
          <div>
            <div className={styles.toggleLabel}>Günlük tekrar saati</div>
            <div className={styles.toggleDesc}>Çalışmayı planladığın saat</div>
          </div>
          <input
            type="time"
            className={styles.timeInput}
            value={form.reminder_time ?? DEFAULTS.reminder_time}
            onChange={(e) => setForm((f) => ({ ...f, reminder_time: e.target.value }))}
            onBlur={(e) => savePreference({ reminder_time: e.target.value })}
            aria-label="Günlük tekrar saati"
          />
        </div>

        <div className={styles.toggleRow}>
          <div>
            <div className={styles.toggleLabel}>Hatırlatma</div>
            <div className={styles.toggleDesc}>Tekrar zamanı geldiğinde uyar</div>
          </div>
          <button
            className={`${styles.switch} ${form.notifications ? styles.switchOn : ""}`}
            onClick={() => savePreference({ notifications: !form.notifications })}
            role="switch"
            aria-checked={!!form.notifications}
            aria-label="Hatırlatma"
          />
        </div>

        <div className={styles.toggleRow}>
          <div>
            <div className={styles.toggleLabel}>E-posta özeti</div>
            <div className={styles.toggleDesc}>Haftalık ilerleme raporu gönder</div>
          </div>
          <button
            className={`${styles.switch} ${form.email_summary ? styles.switchOn : ""}`}
            onClick={() => savePreference({ email_summary: !form.email_summary })}
            role="switch"
            aria-checked={!!form.email_summary}
            aria-label="E-posta özeti"
          />
        </div>

        <p className={styles.note}>
          <Info size={12} />
          Tercihler hesabına kaydedilir. Uygulamada henüz bir bildirim servisi
          yok, bu yüzden açık bırakılan hatırlatmalar şimdilik yalnızca tercih
          olarak saklanıyor.
        </p>
      </div>

      {/* ── Hesap ───────────────────────────────────────────── */}
      <div className={styles.sectionLabel}>// HESAP</div>
      <div className={styles.accountList}>
        <div className={styles.accountItem}>
          <div className={styles.accountItemLeft}>
            <div className={styles.accountItemIcon}>
              <Lock size={16} />
            </div>
            <div>
              <div className={styles.itemTitle}>Şifreyi Değiştir</div>
              <div className={styles.itemSub}>
                {user.email} adresine bağlı şifreyi güncelle
              </div>
            </div>
          </div>
          <button
            className={styles.ghostButton}
            onClick={() => setPanel(panel === "password" ? null : "password")}
          >
            {panel === "password" ? "Kapat" : "Değiştir"}
          </button>
        </div>

        {panel === "password" && (
          <div className={styles.expanded}>
            <div className={`${styles.expandedInner} ${styles.stack}`}>
              <div className={styles.field}>
                <label htmlFor="new-password">Yeni şifre</label>
                <input
                  id="new-password"
                  type="password"
                  value={password.next}
                  onChange={(e) =>
                    setPassword((p) => ({ ...p, next: e.target.value }))
                  }
                  placeholder="En az 6 karakter"
                />
              </div>
              <div className={styles.field}>
                <label htmlFor="confirm-password">Yeni şifre (tekrar)</label>
                <input
                  id="confirm-password"
                  type="password"
                  value={password.confirm}
                  onChange={(e) =>
                    setPassword((p) => ({ ...p, confirm: e.target.value }))
                  }
                  placeholder="Şifreyi tekrar gir"
                />
              </div>
              <div className={styles.inlineActions}>
                <button
                  className={styles.primaryButton}
                  onClick={changePassword}
                  disabled={busy}
                >
                  {busy ? "Güncelleniyor…" : "Şifreyi Güncelle"}
                </button>
              </div>
            </div>
          </div>
        )}

        <div className={styles.accountItem}>
          <div className={styles.accountItemLeft}>
            <div className={styles.accountItemIcon}>
              <LogOut size={16} />
            </div>
            <div>
              <div className={styles.itemTitle}>Çıkış Yap</div>
              <div className={styles.itemSub}>Bu cihazdaki oturumu kapat</div>
            </div>
          </div>
          <button className={styles.ghostButton} onClick={logout}>
            Çıkış
          </button>
        </div>

        <div className={styles.accountItem}>
          <div className={styles.accountItemLeft}>
            <div className={`${styles.accountItemIcon} ${styles.accountItemIconDanger}`}>
              <Trash2 size={16} />
            </div>
            <div>
              <div className={`${styles.itemTitle} ${styles.itemTitleDanger}`}>
                Tüm Ders Verilerimi Sil
              </div>
              <div className={styles.itemSub}>
                {overview?.total_courses ?? 0} ders, {overview?.total_topics ?? 0}{" "}
                konu ve {totalMaterials} materyal kalıcı olarak silinir
              </div>
            </div>
          </div>
          <button
            className={styles.dangerButton}
            onClick={() => setPanel(panel === "wipe" ? null : "wipe")}
            disabled={!overview?.total_courses}
          >
            {panel === "wipe" ? "Vazgeç" : "Sil"}
          </button>
        </div>

        {panel === "wipe" && (
          <div className={styles.expanded}>
            <div className={`${styles.expandedInner} ${styles.stack}`}>
              <p className={styles.warning}>
                Bu işlem geri alınamaz: bütün derslerin, konuların,
                materyallerin, sohbet geçmişin ve arama için oluşturulan vektör
                kayıtların silinir. Hesabın açık kalır, kütüphane sıfırlanır.
                Onaylamak için aşağıya <strong>SİL</strong> yaz.
              </p>
              <div className={styles.field}>
                <label htmlFor="wipe-confirm">Onay</label>
                <input
                  id="wipe-confirm"
                  value={wipeConfirm}
                  onChange={(e) => setWipeConfirm(e.target.value)}
                  placeholder="SİL"
                />
              </div>
              <div className={styles.inlineActions}>
                <button
                  className={styles.dangerButton}
                  onClick={wipeData}
                  disabled={busy || wipeConfirm.trim().toLocaleUpperCase("tr-TR") !== "SİL"}
                >
                  {busy ? "Siliniyor…" : "Kalıcı Olarak Sil"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <p className={styles.note} style={{ marginBottom: 8 }}>
        <Info size={12} />
        Hesabın tamamen kapatılması (auth kaydının silinmesi) için backend'de
        yönetici yetkili bir uç nokta gerekiyor — o eklenene kadar bu sayfa
        yalnızca ders verilerini silebiliyor.
      </p>
    </div>
  );
}
