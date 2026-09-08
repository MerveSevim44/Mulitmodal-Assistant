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
  { icon: Brain, label: "Tekrar", href: "/review" },
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
  // What the prompt card reports: how many topics the SM-2 schedule says are
  // due right now, plus the ones still empty — a topic with no material is
  // nothing to review yet, so it is called out separately rather than counted.
  const [counts, setCounts] = useState<{ due: number; empty: number } | null>(
    null
  );

  // Null until the session check has answered. The API calls below wait for
  // it: firing them alongside the check meant a signed-out load sent a
  // token-less /overview before the redirect landed.
  const [authed, setAuthed] = useState(false);

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
      setAuthed(true);
    };
    checkAuth();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session) {
        setAuthed(false);
        router.replace("/login");
      }
    });

    return () => subscription.unsubscribe();
  }, [router]);

  useEffect(() => {
    if (!authed) return;
    getOverview()
      .then(({ data }) =>
        setCounts({ due: data.due_topics, empty: data.empty_topics })
      )
      .catch(() => setCounts(null));
  }, [authed]);

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
                : counts.due === 0
                ? "Tekrar edilecek konu yok"
                : `${counts.due} konu tekrar bekliyor`}
            </p>
            <p className={styles.promptHint}>
              {counts === null
                ? "Bir saniye"
                : counts.due > 0
                ? "Unutmadan bugün tekrar et"
                : counts.empty > 0
                ? `${counts.empty} konuda henüz materyal yok`
                : "Bir sonraki tekrar zamanı gelince burada görünecek"}
            </p>
            <button
              className={styles.promptButton}
              onClick={() => router.push(counts?.due ? "/review" : "/courses")}
              disabled={counts === null}
            >
              {counts?.due ? "Tekrara Başla" : "Ders Oluştur"}
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
