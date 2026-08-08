"use client";

import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PendingAction, PolicySource } from "@/lib/api";
import { ActionResultCard } from "@/components/ai/action-result-card";
import { SourceList } from "@/components/ai/source-list";
import { SqlResultTable } from "@/components/ai/sql-result-table";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  route?: "POLICY_QA" | "SQL_QUERY" | "HR_ACTION" | "UNKNOWN";
  content: string;
  sources?: PolicySource[];
  sql?: string | null;
  rows?: Record<string, unknown>[];
  action?: string | null;
  status?: string;
  result?: unknown;
  pendingAction?: PendingAction | null;
  isError?: boolean;
};

const ROUTE_LABELS: Record<string, string> = {
  POLICY_QA: "Policy",
  SQL_QUERY: "Data",
  HR_ACTION: "Action",
  UNKNOWN: "",
};

export function ChatPanel({
  messages,
  onSend,
  loading,
  loadingStage,
  placeholder,
  onConfirmAction,
  onCancelAction,
  confirmingMessageId,
}: {
  messages: ChatMessage[];
  onSend: (text: string) => void;
  loading: boolean;
  loadingStage?: string | null;
  placeholder?: string;
  onConfirmAction?: (messageId: string) => void;
  onCancelAction?: (messageId: string) => void;
  confirmingMessageId?: string | null;
}) {
  const [draft, setDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the latest message whenever the list changes -- a new
  // message, an existing one being patched with a result (e.g. rows/status
  // arriving after a pending action resolves), the "Thinking..." bubble
  // appearing/disappearing, or a stage-progress update while streaming all
  // update messages/loading/loadingStage, so this covers every case a user
  // would expect the view to jump to the bottom for.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading, loadingStage]);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || loading) return;
    onSend(trimmed);
    setDraft("");
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Ask about HR policies, employee/project data, or say what you&apos;d like to do (apply for leave, raise a
            ticket, etc).
          </p>
        ) : null}

        {messages.map((message) => (
          <div key={message.id} className={message.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div
              className={
                message.role === "user"
                  ? "max-w-[80%] rounded-2xl rounded-br-sm bg-primary px-4 py-2 text-sm text-primary-foreground"
                  : `max-w-[85%] rounded-2xl rounded-bl-sm border px-4 py-3 text-sm ${
                      message.isError ? "border-red-200 bg-red-50 text-red-700" : "border-border bg-card"
                    }`
              }
            >
              {message.role === "assistant" && message.route && ROUTE_LABELS[message.route] ? (
                <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                  {ROUTE_LABELS[message.route]}
                </div>
              ) : null}
              <p className="whitespace-pre-wrap">{message.content}</p>

              {message.sources ? <SourceList sources={message.sources} /> : null}
              {message.rows ? <SqlResultTable rows={message.rows} sql={message.sql} /> : null}
              {message.route === "HR_ACTION" && message.status ? (
                <ActionResultCard
                  action={message.action ?? null}
                  status={message.status}
                  result={message.result}
                  pendingAction={message.pendingAction ?? null}
                  confirming={confirmingMessageId === message.id}
                  onConfirm={() => onConfirmAction?.(message.id)}
                  onCancel={() => onCancelAction?.(message.id)}
                />
              ) : null}
            </div>
          </div>
        ))}

        {loading ? (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-sm border border-border bg-card px-4 py-2 text-sm text-muted-foreground">
              {loadingStage ?? "Thinking..."}
            </div>
          </div>
        ) : null}

        <div ref={bottomRef} />
      </div>

      <form onSubmit={submit} className="flex gap-2 border-t border-border p-3">
        <Input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={placeholder ?? "Ask a question or describe a task..."}
          disabled={loading}
        />
        <Button type="submit" disabled={loading || !draft.trim()}>
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  );
}
