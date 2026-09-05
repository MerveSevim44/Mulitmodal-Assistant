"use client";

import { memo, useMemo } from "react";
import ReactMarkdown, { type Options } from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { normalizeMath } from "@/lib/math";

// Hoisted so the arrays keep the same identity across renders — a fresh array
// literal on every render defeats react-markdown's internal processor cache.
const REMARK_PLUGINS: Options["remarkPlugins"] = [remarkGfm, remarkMath];
const REHYPE_PLUGINS: Options["rehypePlugins"] = [
  [rehypeKatex, { throwOnError: false, strict: false }],
];

/**
 * Renders one message as markdown with LaTeX.
 *
 * Parsing a typical answer costs ~12ms (markdown + KaTeX), so this is memoized
 * on `content`: without it, a single streamed token re-parsed every message in
 * the conversation.
 */
function MarkdownMessage({ content }: { content: string }) {
  const normalized = useMemo(() => normalizeMath(content), [content]);

  return (
    <ReactMarkdown
      remarkPlugins={REMARK_PLUGINS}
      rehypePlugins={REHYPE_PLUGINS}
    >
      {normalized}
    </ReactMarkdown>
  );
}

export default memo(MarkdownMessage);
