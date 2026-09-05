"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  Home,
  BookOpen,
  CalendarDays,
  FolderOpen,
  MessageCircle,
  Settings,
  Brain,
  LogOut,
} from "lucide-react";
import { supabase } from "@/lib/supabase";
import { getOverview } from "@/lib/api";
import styles from "./dashboard.module.css";

/**
 * Sidebar navigation. Materials and chat live inside a topic rather than as
 * standalone pages, and there is no settings screen yet, so those entries are
 * rendered disabled instead of as links that would 404.
 */
const NAV_ITEMS = [
  { icon: Home, label: "Ana Sayfa", href: "/" },
  { icon: BookOpen, label: "Derslerim", href: "/courses" },
  { icon: CalendarDays, label: "Ders Planı", href: "/plan" },
  { icon: FolderOpen, label: "Materyaller", href: null },
  { icon: MessageCircle, label: "Sohbet", href: null },
  { icon: Settings, label: "Ayarlar", href: null },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [userEmail, setUserEmail] = useState("");
  const [topicCount, setTopicCount] = useState<number | null>(null);

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
      .then(({ data }) => setTopicCount(data.total_topics))
      .catch(() => setTopicCount(null));
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
              {topicCount === null
                ? "Konuların yükleniyor"
                : topicCount === 0
                ? "Henüz konu yok"
                : `${topicCount} konu tekrar bekliyor`}
            </p>
            <p className={styles.promptHint}>
              {topicCount ? "Unutmadan bugün tekrar et" : "Başlamak için bir ders ekle"}
            </p>
            <button
              className={styles.promptButton}
              onClick={() => router.push(topicCount ? "/" : "/courses")}
              disabled={topicCount === null}
            >
              {topicCount ? "Tekrara Başla" : "Ders Oluştur"}
            </button>
          </div>

          <div className={styles.sidebarFooter}>
            <div className={styles.userInfo}>
              <div className={styles.avatar}>
                {userEmail.charAt(0).toUpperCase()}
              </div>
              <span className={styles.email}>{userEmail}</span>
            </div>
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
