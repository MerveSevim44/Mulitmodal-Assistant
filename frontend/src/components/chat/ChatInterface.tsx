"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { getChatHistory, clearChatHistory } from "@/lib/api";
import { streamChat } from "@/lib/stream";
import styles from "./chat.module.css";
import MarkdownMessage from "./MarkdownMessage";
import MessageItem from "./MessageItem";
import type { Message } from "./types";

/** How close to the bottom still counts as "following along", in px. */
const STICK_THRESHOLD = 80;

export default function ChatInterface({ topicId }: { topicId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [input, setInput] = useState("");
  const [streamingText, setStreamingText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageAreaRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

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

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    const userMessage = input.trim();
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

  const handleClear = async () => {
    if (!confirm("Tüm sohbet geçmişi silinecek. Emin misiniz?")) return;
    try {
      await clearChatHistory(topicId);
      setMessages([]);
    } catch (err) {
      console.error("Failed to clear history:", err);
    }
  };

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
        ) : messages.length === 0 && !isStreaming ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>🤖</div>
            <p>Merhaba! Konuyla ilgili sormak istediğin bir şey var mı?</p>
            <p className={styles.emptyHint}>
              Sağ taraftan PDF veya ses yükledikten sonra sorularını sorabilirsin.
            </p>
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

      <form className={styles.inputArea} onSubmit={handleSend}>
        <input
          type="text"
          className="input"
          placeholder="Soru sor (Örn: Bu konunun özeti nedir?)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isStreaming}
          autoFocus
        />
        <button
          type="submit"
          className="btn btn-primary"
          disabled={!input.trim() || isStreaming}
        >
          {isStreaming ? "⏳" : "Gönder"}
        </button>
      </form>
    </div>
  );
}
