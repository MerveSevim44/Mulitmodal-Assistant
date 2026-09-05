"use client";

import { memo } from "react";
import styles from "./chat.module.css";
import MarkdownMessage from "./MarkdownMessage";
import type { Message } from "./types";

/**
 * One chat bubble.
 *
 * Memoized on the message object: history is reloaded wholesale after every
 * turn, so without this each reload re-parsed the markdown and KaTeX of every
 * message that had not actually changed.
 */
function MessageItem({ message }: { message: Message }) {
  const images = message.metadata?.images?.filter((img) => img.url) ?? [];
  const sources = message.metadata?.sources;
  const isAssistant = message.role === "assistant";

  return (
    <div
      className={`${styles.messageWrapper} ${
        message.role === "user" ? styles.userWrapper : styles.assistantWrapper
      }`}
    >
      <div className={`${styles.messageBubble} ${styles[message.role]}`}>
        <MarkdownMessage content={message.content} />

        {isAssistant && images.length > 0 && (
          <div className={styles.sourceImages}>
            {images.map((img) => (
              <a
                key={img.storage_path}
                href={img.url!}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.sourceImage}
                title={`${img.file_name} — büyütmek için tıkla`}
              >
                {/* Plain <img>: these are private, per-request signed URLs, so
                    next/image optimization would cache a link that expires
                    within the hour. */}
                <img src={img.url!} alt={img.file_name} loading="lazy" decoding="async" />
                <span className={styles.sourceImageCaption}>🖼️ {img.file_name}</span>
              </a>
            ))}
          </div>
        )}

        {isAssistant && sources && (
          <div className={styles.sources}>
            {sources.pdf && <span className="badge badge-pdf">📄 PDF</span>}
            {sources.audio && <span className="badge badge-audio">🎤 Ses</span>}
            {sources.image && <span className="badge badge-image">🖼️ Görsel</span>}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * `loadHistory` refetches the whole conversation after every turn, so each
 * message arrives as a brand new object and reference equality would never
 * hold. Stored messages are immutable, so comparing the fields this component
 * actually renders is both correct and enough to skip the re-parse.
 */
function propsAreEqual(
  prev: { message: Message },
  next: { message: Message }
): boolean {
  const a = prev.message;
  const b = next.message;

  if (a.id !== b.id || a.content !== b.content || a.role !== b.role) return false;

  const aSources = a.metadata?.sources;
  const bSources = b.metadata?.sources;
  if (
    aSources?.pdf !== bSources?.pdf ||
    aSources?.audio !== bSources?.audio ||
    aSources?.image !== bSources?.image
  ) {
    return false;
  }

  // Signed URLs are re-minted on each history read, so they are compared too:
  // a changed URL must reach the <img>, or it would keep an expiring link.
  const aImages = a.metadata?.images ?? [];
  const bImages = b.metadata?.images ?? [];
  if (aImages.length !== bImages.length) return false;
  return aImages.every(
    (img, i) =>
      img.url === bImages[i].url && img.storage_path === bImages[i].storage_path
  );
}

export default memo(MessageItem, propsAreEqual);
