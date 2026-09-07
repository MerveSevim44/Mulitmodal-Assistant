"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  Home,
  BookOpen,
  CalendarDays,
  FolderOpen,
  MessageCircle,
  User,
  Brain,
  LogOut,
} from "lucide-react";
import { supabase } from "@/lib/supabase";
import { getOverview } from "@/lib/api";
import styles from "./dashboard.module.css";

/**
 * Sidebar navigation. Chat lives inside a topic rather than as a standalone
 * page, so that entry is rendered disabled instead of as a link that would
 * 404. Materials do have a standalone page: a flat library of everything
 * uploaded, across all courses.
 */
const NAV_ITEMS = [
  { icon: Home, label: "Ana Sayfa", href: "/" },
  { icon: BookOpen, label: "Derslerim", href: "/courses" },
  { icon: CalendarDays, label: "Ders Planı", href: "/plan" },
  { icon: FolderOpen, label: "Materyaller", href: "/materials" },
  { icon: MessageCircle, label: "Sohbet", href: null },
  { icon: User, label: "Profilim", href: "/profile" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [userEmail, setUserEmail] = useState("");
  // Topics that actually have material behind them, plus the ones still empty
  // — the card promises a review, so it should not count empty topics.
  const [counts, setCounts] = useState<{ ready: number; empty: number } | null>(
    null
  );

  useEffect(() => {
    const checkAuth = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        router.replace("/login");
        return;
      }
      setUserEmail(session.user.email || "");
    };
    checkAuth();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session) router.replace("/login");
    });

    return () => subscription.unsubscribe();
  }, [router]);

  useEffect(() => {
    getOverview()
      .then(({ data }) =>
        setCounts({
          ready: data.total_topics - data.empty_topics,
          empty: data.empty_topics,
        })
      )
      .catch(() => setCounts(null));
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push("/login");
  };

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <div className={styles.layout}>
      <aside className={styles.sidebar}>
        <div>
          <div className={styles.sidebarHeader}>
            <span className={styles.logo}>AB</span>
            <span className={styles.logoText}>Akademik Bellek</span>
          </div>

          <nav className={styles.nav}>
            {NAV_ITEMS.map(({ icon: Icon, label, href }) => (
              <button
                key={label}
                className={`${styles.navItem} ${
                  href && isActive(href) ? styles.navItemActive : ""
                }`}
                onClick={href ? () => router.push(href) : undefined}
                disabled={!href}
                title={href ? undefined : "Bu bölüm konu sayfasının içinde"}
              >
                <Icon size={17} strokeWidth={2} />
                {label}
              </button>
            ))}
          </nav>
        </div>

        <div>
          <div className={styles.promptCard}>
            <div className={styles.promptIcon}>
              <Brain size={22} strokeWidth={2} />
            </div>
            <p className={styles.promptTitle}>
              {counts === null
                ? "Konuların yükleniyor"
                : counts.ready === 0
                ? "Tekrar edilecek konu yok"
                : `${counts.ready} konu tekrar bekliyor`}
            </p>
            <p className={styles.promptHint}>
              {counts === null
                ? "Bir saniye"
                : counts.ready > 0
                ? "Unutmadan bugün tekrar et"
                : counts.empty > 0
                ? `${counts.empty} konuda henüz materyal yok`
                : "Başlamak için bir ders ekle"}
            </p>
            <button
              className={styles.promptButton}
              onClick={() => router.push(counts?.ready ? "/" : "/courses")}
              disabled={counts === null}
            >
              {counts?.ready ? "Tekrara Başla" : "Ders Oluştur"}
            </button>
          </div>

          <div className={styles.sidebarFooter}>
            <button
              className={styles.userInfo}
              onClick={() => router.push("/profile")}
              title="Profilim"
            >
              <div className={styles.avatar}>
                {userEmail.charAt(0).toUpperCase()}
              </div>
              <span className={styles.email}>{userEmail}</span>
            </button>
            <button className={styles.navItem} onClick={handleLogout}>
              <LogOut size={17} strokeWidth={2} />
              Çıkış Yap
            </button>
          </div>
        </div>
      </aside>

      <main className={styles.main}>{children}</main>
    </div>
  );
}
