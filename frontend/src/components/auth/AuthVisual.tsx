import styles from "@/app/(auth)/login/auth.module.css";

/**
 * Giriş/kayıt ekranlarının sol yarısı: ders masası fotoğrafı üzerine
 * "stay focused." sloganı. Fotoğraf `public/auth-visual.jpg` dosyasından
 * gelir; dosya yoksa CSS'teki degrade zemin devreye girer.
 */
export default function AuthVisual() {
  return (
    <div className={styles.visual}>
      <div className={styles.visualInner}>
        <p className={styles.visualText}>
          <span>stay</span>
          <span>focused.</span>
        </p>
        <p className={styles.visualTagline}>Akademik Bellek Asistanı</p>
      </div>
    </div>
  );
}
