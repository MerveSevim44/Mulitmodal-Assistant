export interface SourceImage {
  file_name: string;
  storage_path: string;
  /** Short-lived signed URL, minted by the backend on each history read. */
  url?: string | null;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  metadata?: {
    sources?: { pdf?: boolean; audio?: boolean; image?: boolean };
    images?: SourceImage[];
    [key: string]: unknown;
  };
  created_at: string;
}
