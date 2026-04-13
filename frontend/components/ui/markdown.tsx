"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const plugins = [remarkGfm];

export function Markdown({
  children,
  className,
}: {
  children: string;
  className?: string;
}) {
  if (className) {
    return (
      <div className={className}>
        <ReactMarkdown remarkPlugins={plugins}>{children}</ReactMarkdown>
      </div>
    );
  }
  return (
    <ReactMarkdown remarkPlugins={plugins}>{children}</ReactMarkdown>
  );
}
