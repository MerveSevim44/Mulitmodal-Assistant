"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { getChatHistory, clearChatHistory, uploadMaterial, detectMaterialType } from "@/lib/api";
import { streamChat } from "@/lib/stream";
import styles from "./chat.module.css";
import MarkdownMessage from "./MarkdownMessage";
import MessageItem from "./MessageItem";
import type { Message } from "./types";

/** How close to the bottom still counts as "following along", in px. */
const STICK_THRESHOLD = 80;

/** Boş sohbette gösterilen hazır başlangıç soruları. */
const SUGGESTIONS = [
  { icon: "summary", text: "Bu konunun kısa bir özetini çıkar" },
  { icon: "exam", text: "Beni bu konudan sınava hazırla" },
  { icon: "help", text: "Anlamadığım kısımları basitçe anlat" },
] as const;

function SuggestionIcon({ name }: { name: (typeof SUGGESTIONS)[number]["icon"] }) {
  if (name === "summary") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <path d="M4 6h16M4 12h16M4 18h10" />
      </svg>
    );
  }
  if (name === "exam") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 5H5a2 2 0 00-2 2v12a2 2 0 002 2h12a2 2 0 002-2v-4M17 3l4 4-11 11H6v-4z" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <circle cx="12" cy="12" r="9" />
      <path d="M9.5 9a2.5 2.5 0 015 .5c0 1.5-2.5 2-2.5 3.5M12 17h.01" />
    </svg>
  );
}

/** Asistan işareti — emoji yerine arayüzün geri kalanıyla aynı vektör dilinde. */
function AssistantMark() {
  return (
    <div className={styles.assistantMark} aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round">
        <path
          d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3z"
          fill="currentColor"
          fillOpacity="0.16"
        />
        <path
          d="M18.4 15.2l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7.7-2z"
          fill="currentColor"
          fillOpacity="0.16"
        />
      </svg>
    </div>
  );
}

export default function ChatInterface({ topicId }: { topicId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [input, setInput] = useState("");
  const [streamingText, setStreamingText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadNote, setUploadNote] = useState("Yükleniyor…");
  // Set on success and cleared on a timer, so the icons visibly do something
  // — the chat has no material list to reflect a finished upload.
  const [uploadDone, setUploadDone] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageAreaRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const imagePickerRef = useRef<HTMLInputElement>(null);
  const filePickerRef = useRef<HTMLInputElement>(null);
  const audioPickerRef = useRef<HTMLInputElement>(null);

  // Whether the reader is pinned to the bottom. A ref, not state: it changes on
  // every scroll and must never itself cause a render.
  const stickToBottomRef = useRef(true);
  const scrollRafRef = useRef<number | null>(null);

  // Tokens arrive far faster than the screen refreshes, so they are buffered
  // here and flushed once per frame instead of re-rendering per token.
  const pendingTokensRef = useRef("");
  const flushRafRef = useRef<number | null>(null);

  const loadHistory = useCallback(async () => {
    try {
      const { data } = await getChatHistory(topicId);
      setMessages(data.messages || []);
    } catch (err) {
      console.error("Failed to load chat history:", err);
    } finally {
      setLoading(false);
    }
  }, [topicId]);

  useEffect(() => {
    loadHistory();
    return () => {
      abortControllerRef.current?.abort();
      if (scrollRafRef.current !== null) cancelAnimationFrame(scrollRafRef.current);
      if (flushRafRef.current !== null) cancelAnimationFrame(flushRafRef.current);
    };
  }, [loadHistory]);

  // ── Scroll tracking ───────────────────────────────────────────
  // One layout read per frame at most, and no state updates, so scrolling
  // itself stays off the React render path entirely.

  const handleScroll = useCallback(() => {
    if (scrollRafRef.current !== null) return;
    scrollRafRef.current = requestAnimationFrame(() => {
      scrollRafRef.current = null;
      const el = messageAreaRef.current;
      if (!el) return;
      const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
      stickToBottomRef.current = distanceFromBottom < STICK_THRESHOLD;
    });
  }, []);

  // A new message was appended — animate down, but only if the reader was
  // already at the bottom. Keyed on the count so re-renders that merely
  // re-fetch the same messages do not re-trigger a scroll.
  const messageCount = messages.length;
  useEffect(() => {
    if (!stickToBottomRef.current) return;
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messageCount]);

  // While streaming, keep the tail in view with a direct, non-animated jump.
  // `scrollIntoView({ behavior: "smooth" })` here would restart its animation
  // on every flush and fight the user's own scrolling.
  useEffect(() => {
    if (!isStreaming || !stickToBottomRef.current) return;
    const el = messageAreaRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [streamingText, isStreaming]);

  const flushTokens = useCallback(() => {
    flushRafRef.current = null;
    const pending = pendingTokensRef.current;
    if (!pending) return;
    pendingTokensRef.current = "";
    setStreamingText((prev) => prev + pending);
  }, []);

  const send = (text: string) => {
    const userMessage = text.trim();
    if (!userMessage || isStreaming) return;
    setInput("");

    // Optimistically add user message
    const tempUserMsg: Message = {
      id: `pending-${Date.now()}`,
      role: "user",
      content: userMessage,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    // Sending is an explicit intent to follow the answer.
    stickToBottomRef.current = true;
    setIsStreaming(true);
    setStreamingText("");

    const finish = () => {
      if (flushRafRef.current !== null) {
        cancelAnimationFrame(flushRafRef.current);
        flushRafRef.current = null;
      }
      pendingTokensRef.current = "";
      setIsStreaming(false);
      loadHistory(); // Reload to get the saved message with DB ID and metadata
      setStreamingText("");
    };

    abortControllerRef.current = streamChat({
      topicId,
      message: userMessage,
      onToken: (token) => {
        pendingTokensRef.current += token;
        if (flushRafRef.current === null) {
          flushRafRef.current = requestAnimationFrame(flushTokens);
        }
      },
      onDone: finish,
      onError: (error) => {
        console.error("Stream error:", error);
        finish();
      },
    });
  };

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    send(input);
  };

  const handleClear = async () => {
    if (!confirm("Tüm sohbet geçmişi silinecek. Emin misiniz?")) return;
    try {
      await clearChatHistory(topicId);
      setMessages([]);
    } catch (err) {
      console.error("Failed to clear history:", err);
    }
  };

  // Yazma çubuğundaki ekleme düğmeleri materyal yükler: dosya konunun
  // materyalleri arasına girer ve sonraki sorularda kaynak olarak kullanılır.
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    // Classified by extension, not by `file.type` — the browser leaves the
    // type empty for .m4a/.wav often enough, and calls .mp4 a video, either of
    // which used to send an audio recording to the PDF bucket.
    const type = detectMaterialType(file);
    if (!type) {
      alert("Desteklenmeyen dosya formatı. PDF, ses (mp3/wav/m4a/mp4) veya görsel (png/jpg) yükleyin.");
      return;
    }

    setUploading(true);
    setUploadDone(null);
    setUploadNote("Yükleniyor…");
    try {
      await uploadMaterial(topicId, file, type, (phase) => {
        setUploadNote(
          phase === "uploading"
            ? "Yükleniyor…"
            : type === "audio"
              ? "Ses çözümleniyor, birkaç dakika sürebilir…"
              : "İşleniyor…"
        );
      });
      setUploadDone(`${file.name} eklendi — artık bu materyale soru sorabilirsin.`);
      setTimeout(() => setUploadDone(null), 6000);
    } catch (err) {
      console.error("Upload failed:", err);
      const detail =
        (err as { response?: { data?: { detail?: string } }; message?: string })?.response?.data
          ?.detail ?? (err as Error)?.message;
      alert(`Dosya yüklenemedi: ${detail ?? "Lütfen tekrar deneyin."}`);
    } finally {
      setUploading(false);
    }
  };

  const isEmpty = messages.length === 0 && !isStreaming;

  const composer = (
    <div className={styles.composerWrap}>
      <div className={styles.composerGlow} aria-hidden="true" />
      <form className={styles.composer} onSubmit={handleSend}>
        <input
          type="text"
          className={styles.composerInput}
          placeholder="Bir şey sor..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isStreaming}
          autoFocus
        />
        <div className={styles.composerControls}>
          <div className={styles.composerIcons}>
            <button
              type="button"
              className={styles.iconBtn}
              title="Görsel yükle (PNG/JPG)"
              onClick={() => imagePickerRef.current?.click()}
              disabled={uploading}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <rect x="3" y="4" width="18" height="16" rx="2.5" />
                <circle cx="9" cy="10" r="1.5" />
                <path d="M21 16l-5.5-5-4 4L9 13l-6 6" />
              </svg>
            </button>
            <button
              type="button"
              className={styles.iconBtn}
              title="PDF yükle"
              onClick={() => filePickerRef.current?.click()}
              disabled={uploading}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                <path d="M21 12.5V7a2 2 0 00-2-2H8L4 9v8a2 2 0 002 2h6M17 15v6M14 18h6" />
              </svg>
            </button>
            <button
              type="button"
              className={styles.iconBtn}
              title="Ses dosyası yükle (MP3/WAV/M4A)"
              onClick={() => audioPickerRef.current?.click()}
              disabled={uploading}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <rect x="9" y="3" width="6" height="11" rx="3" />
                <path d="M5 11a7 7 0 0014 0M12 18v3" />
              </svg>
            </button>
            {uploading && <span className={styles.uploadNote}>{uploadNote}</span>}
            {!uploading && uploadDone && (
              <span className={styles.uploadNote}>{uploadDone}</span>
            )}
          </div>
          <button
            type="submit"
            className={styles.sendBtn}
            disabled={!input.trim() || isStreaming}
            title="Gönder"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 19V5M5 12l7-7 7 7" />
            </svg>
          </button>
        </div>
      </form>

      {/* One picker per type, each restricted to what its bucket accepts, so
          the file dialog cannot offer a format the upload would reject. */}
      <input
        ref={imagePickerRef}
        type="file"
        accept=".png,.jpg,.jpeg,image/png,image/jpeg"
        hidden
        onChange={handleUpload}
      />
      <input
        ref={audioPickerRef}
        type="file"
        accept=".mp3,.wav,.m4a,.mp4,audio/*"
        hidden
        onChange={handleUpload}
      />
      <input
        ref={filePickerRef}
        type="file"
        accept=".pdf,application/pdf"
        hidden
        onChange={handleUpload}
      />
    </div>
  );

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.title}>
          <span className="mono" style={{ color: "var(--text-label)" }}>
            // Asistan ile Sohbet
          </span>
        </div>
        {messages.length > 0 && (
          <button className="btn btn-ghost btn-icon" onClick={handleClear} title="Geçmişi temizle">
            🗑
          </button>
        )}
      </div>

      <div className={styles.messageArea} ref={messageAreaRef} onScroll={handleScroll}>
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="spinner" />
          </div>
        ) : isEmpty ? (
          <div className={styles.emptyState}>
            <AssistantMark />
            <h1 className={styles.emptyTitle}>Bu konu hakkında ne öğrenmek istersin?</h1>
            <p className={styles.emptySub}>
              Detaylı sorular sor, asistan konunun içeriğine göre cevap versin
            </p>

            {composer}

            <div className={styles.suggestions}>
              {SUGGESTIONS.map((s) => (
                <button key={s.text} type="button" className={styles.chip} onClick={() => send(s.text)}>
                  <SuggestionIcon name={s.icon} />
                  {s.text}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className={styles.messageList}>
            {messages.map((msg) => (
              <MessageItem key={msg.id} message={msg} />
            ))}

            {isStreaming && (
              <div className={`${styles.messageWrapper} ${styles.assistantWrapper}`}>
                <div className={`${styles.messageBubble} ${styles.assistant} ${styles.streaming}`}>
                  <MarkdownMessage content={streamingText} />
                  <span className="cursor-blink" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {!isEmpty && !loading && <div className={styles.inputArea}>{composer}</div>}
    </div>
  );
}
