"use client";

import { useState, useEffect, useRef } from "react";
import { getChatHistory, clearChatHistory } from "@/lib/api";
import { streamChat } from "@/lib/stream";
import styles from "./chat.module.css";
import MarkdownMessage from "./MarkdownMessage";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  metadata?: any;
  created_at: string;
}

export default function ChatInterface({ topicId }: { topicId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [input, setInput] = useState("");
  const [streamingToken, setStreamingToken] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const loadHistory = async () => {
    try {
      const { data } = await getChatHistory(topicId);
      setMessages(data.messages || []);
    } catch (err) {
      console.error("Failed to load chat history:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [topicId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingToken]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    const userMessage = input.trim();
    setInput("");

    // Optimistically add user message
    const tempUserMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: userMessage,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setIsStreaming(true);
    setStreamingToken("");

    abortControllerRef.current = streamChat({
      topicId,
      message: userMessage,
      onToken: (token) => {
        setStreamingToken((prev) => prev + token);
      },
      onDone: () => {
        setIsStreaming(false);
        loadHistory(); // Reload to get the saved message with DB ID and metadata
        setStreamingToken("");
      },
      onError: (error) => {
        console.error("Stream error:", error);
        setIsStreaming(false);
        loadHistory();
        setStreamingToken("");
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

      <div className={styles.messageArea}>
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
              <div
                key={msg.id}
                className={`${styles.messageWrapper} ${
                  msg.role === "user" ? styles.userWrapper : styles.assistantWrapper
                }`}
              >
                <div className={`${styles.messageBubble} ${styles[msg.role]}`}>
                  <MarkdownMessage content={msg.content} />
                  
                  {msg.role === "assistant" && msg.metadata?.sources && (
                    <div className={styles.sources}>
                      {msg.metadata.sources.pdf && <span className="badge badge-pdf">📄 PDF</span>}
                      {msg.metadata.sources.audio && <span className="badge badge-audio">🎤 Ses</span>}
                      {msg.metadata.sources.image && <span className="badge badge-image">🖼️ Görsel</span>}
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {isStreaming && (
              <div className={`${styles.messageWrapper} ${styles.assistantWrapper}`}>
                <div className={`${styles.messageBubble} ${styles.assistant}`}>
                  <MarkdownMessage content={streamingToken} />
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
