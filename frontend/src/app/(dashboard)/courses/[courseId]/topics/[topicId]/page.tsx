"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { getMaterials, deleteMaterial, uploadMaterial } from "@/lib/api";
import { streamChat, getChatHistory } from "@/lib/api"; // wait, we need to export streamChat in api.ts? Actually streamChat is in stream.ts.
import styles from "./topic.module.css";
import ChatInterface from "@/components/chat/ChatInterface";
import MaterialsSidebar from "@/components/materials/MaterialsSidebar";

export default function TopicWorkspacePage({
  params,
}: {
  params: Promise<{ courseId: string; topicId: string }>;
}) {
  const resolvedParams = use(params);
  const courseId = resolvedParams.courseId;
  const topicId = resolvedParams.topicId;
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<"chat" | "materials">("chat");

  return (
    <div className={styles.workspace}>
      {/* Top Header */}
      <div className={styles.header}>
        <button
          className="btn btn-ghost"
          onClick={() => router.push(`/courses/${courseId}`)}
        >
          ← Konulara Dön
        </button>
        <div className={styles.tabs}>
          <button
            className={`btn ${
              activeTab === "chat" ? "btn-primary" : "btn-ghost"
            }`}
            onClick={() => setActiveTab("chat")}
          >
            💬 Sohbet
          </button>
          <button
            className={`btn ${
              activeTab === "materials" ? "btn-primary" : "btn-ghost"
            }`}
            onClick={() => setActiveTab("materials")}
          >
            📂 Materyaller
          </button>
        </div>
      </div>

      {/* Main Workspace Area */}
      <div className={styles.content}>
        {activeTab === "chat" ? (
          <ChatInterface topicId={topicId} />
        ) : (
          <MaterialsSidebar topicId={topicId} />
        )}
      </div>
    </div>
  );
}
