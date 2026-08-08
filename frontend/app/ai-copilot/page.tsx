"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Bot } from "lucide-react";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { ChatMessage, ChatPanel } from "@/components/ai/chat-panel";
import {
  ensureChatSession,
  fetchChatSessionMessages,
  fetchProfile,
  sendRouterChat,
  streamChat,
} from "@/lib/api";

type Mode = "AUTO" | "POLICY_QA" | "SQL_QUERY" | "HR_ACTION";

const MODES: { key: Mode; label: string; description: string }[] = [
  { key: "AUTO", label: "Auto", description: "Let the router decide" },
  { key: "POLICY_QA", label: "Ask HR Policy", description: "Grounded answers with sources" },
  { key: "SQL_QUERY", label: "Ask About People & Projects", description: "Safe, read-only data lookups" },
  { key: "HR_ACTION", label: "Automate HR Task", description: "Apply leave, raise tickets, and more" },
];

function newId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function AiCopilotPage() {
  const [name, setName] = useState("User");
  const [role, setRole] = useState("EMPLOYEE");
  const [mode, setMode] = useState<Mode>("AUTO");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState<string | null>(null);
  const [confirmingMessageId, setConfirmingMessageId] = useState<string | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const router = useRouter();

  const token = useMemo(() => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("hrms_access_token");
  }, []);

  const clearAuthAndRedirect = () => {
    localStorage.removeItem("hrms_access_token");
    document.cookie = "hrms_auth=; path=/; max-age=0; samesite=lax";
    router.push("/login");
  };

  useEffect(() => {
    const load = async () => {
      if (!token) return clearAuthAndRedirect();
      try {
        const profileResult = await fetchProfile(token);
        if (profileResult.status === 401) return clearAuthAndRedirect();
        if (profileResult.ok && "success" in profileResult.body && profileResult.body.success) {
          setName(profileResult.body.data.name);
          setRole(profileResult.body.data.role);
        }

        // Get-or-create this user's one continuous session, then hydrate
        // the transcript so far (plain text only -- source chips/SQL
        // tables/action cards aren't persisted, only used live).
        const sessionResult = await ensureChatSession(token);
        if (sessionResult.status === 401) return clearAuthAndRedirect();
        if (sessionResult.ok && "success" in sessionResult.body && sessionResult.body.success) {
          const id = sessionResult.body.data.id;
          setSessionId(id);

          const messagesResult = await fetchChatSessionMessages(token, id);
          if (messagesResult.ok && "success" in messagesResult.body && messagesResult.body.success) {
            setMessages(
              messagesResult.body.data.map((m) => ({
                id: String(m.id),
                role: m.role,
                content: m.content,
                route: m.route ?? undefined,
              }))
            );
          }
        }
      } finally {
        setProfileLoading(false);
      }
    };
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const appendMessage = (message: ChatMessage) => setMessages((prev) => [...prev, message]);
  const updateMessage = (id: string, patch: Partial<ChatMessage>) =>
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)));

  const runPolicy = async (text: string) => {
    if (!token) return;
    await streamChat(
      token,
      { message: text, forcedIntent: "POLICY_QA", sessionId },
      {
        onProgress: setLoadingStage,
        onUnauthorized: clearAuthAndRedirect,
        onError: () =>
          appendMessage({ id: newId(), role: "assistant", route: "POLICY_QA", content: "Sorry, I couldn't answer that right now.", isError: true }),
        onFinal: (data) =>
          appendMessage({ id: newId(), role: "assistant", route: "POLICY_QA", content: data.answer, sources: data.sources }),
      }
    );
  };

  const runSql = async (text: string) => {
    if (!token) return;
    await streamChat(
      token,
      { message: text, forcedIntent: "SQL_QUERY", sessionId },
      {
        onProgress: setLoadingStage,
        onUnauthorized: clearAuthAndRedirect,
        onError: () =>
          appendMessage({ id: newId(), role: "assistant", route: "SQL_QUERY", content: "Sorry, I couldn't answer that right now.", isError: true }),
        onFinal: (data) =>
          appendMessage({ id: newId(), role: "assistant", route: "SQL_QUERY", content: data.answer, sql: data.sql, rows: data.rows }),
      }
    );
  };

  const runAction = async (
    text: string,
    confirm?: boolean,
    pendingAction?: ChatMessage["pendingAction"],
    priorMessageId?: string
  ) => {
    if (!token) return;
    await streamChat(
      token,
      { message: text, forcedIntent: "HR_ACTION", sessionId, confirm, pendingAction: pendingAction ?? null },
      {
        onProgress: setLoadingStage,
        onUnauthorized: clearAuthAndRedirect,
        onError: () => {
          const content = "Sorry, that action couldn't be completed right now.";
          if (priorMessageId) updateMessage(priorMessageId, { content, isError: true, status: "error" });
          else appendMessage({ id: newId(), role: "assistant", route: "HR_ACTION", content, isError: true });
        },
        onFinal: (data) => {
          const patch: Partial<ChatMessage> = {
            content: data.answer,
            action: data.action,
            status: data.status,
            result: data.result,
            pendingAction: data.pending_action,
          };
          if (priorMessageId) updateMessage(priorMessageId, patch);
          else appendMessage({ id: newId(), role: "assistant", route: "HR_ACTION", ...patch } as ChatMessage);
        },
      }
    );
  };

  const handleSend = async (text: string) => {
    appendMessage({ id: newId(), role: "user", content: text });
    setLoading(true);
    setLoadingStage(null);
    try {
      let route: Mode = mode;
      if (mode === "AUTO" && token) {
        // Session-backed history (not client-resent) means the router can
        // still understand a reply like "its a casual leave" as answering
        // the assistant's previous clarifying question, not an isolated
        // new message.
        const routed = await sendRouterChat(token, text, sessionId);
        if (routed.status === 401) return clearAuthAndRedirect();
        if (routed.ok && "success" in routed.body && routed.body.success) {
          route = routed.body.data.intent as Mode;
        }
      }

      if (route === "POLICY_QA") await runPolicy(text);
      else if (route === "SQL_QUERY") await runSql(text);
      else if (route === "HR_ACTION") await runAction(text);
      else
        appendMessage({
          id: newId(),
          role: "assistant",
          content: "I'm not sure whether that's a policy question, a data lookup, or a task. Could you rephrase, or pick a mode above?",
        });
    } finally {
      setLoading(false);
      setLoadingStage(null);
    }
  };

  const handleConfirm = async (messageId: string) => {
    const message = messages.find((m) => m.id === messageId);
    if (!message?.pendingAction) return;
    setConfirmingMessageId(messageId);
    try {
      await runAction("", true, message.pendingAction, messageId);
    } finally {
      setConfirmingMessageId(null);
      setLoadingStage(null);
    }
  };

  const handleCancel = (messageId: string) => {
    updateMessage(messageId, { status: "cancelled", pendingAction: null, content: "Okay, I won't go ahead with that." });
  };

  return (
    <main className="flex h-screen overflow-hidden">
      <Sidebar />
      <section className="flex w-full flex-col overflow-hidden">
        <Topbar name={name} title="AI Copilot" />
        <div className="flex min-h-0 flex-1 flex-col gap-4 p-6">
          <Card>
            <CardHeader className="flex flex-row items-center gap-2 space-y-0">
              <Bot className="h-5 w-5 text-primary" />
              <div>
                <CardTitle>NovaWorks PeopleOps Copilot</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Signed in as {name} ({role}). Answers and actions are scoped to what your role can see and do.
                </p>
              </div>
            </CardHeader>
          </Card>

          <div className="flex flex-wrap gap-2">
            {MODES.map((m) => (
              <button
                key={m.key}
                onClick={() => setMode(m.key)}
                className={cn(
                  "rounded-full border px-3 py-1.5 text-xs font-medium transition",
                  mode === m.key
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-white text-slate-600 hover:bg-muted"
                )}
                title={m.description}
              >
                {m.label}
              </button>
            ))}
          </div>

          <Card className="flex min-h-[520px] flex-1 flex-col overflow-hidden">
            {profileLoading ? (
              <div className="p-6 text-sm text-muted-foreground">Loading...</div>
            ) : (
              <ChatPanel
                messages={messages}
                onSend={handleSend}
                loading={loading}
                loadingStage={loadingStage}
                confirmingMessageId={confirmingMessageId}
                onConfirmAction={handleConfirm}
                onCancelAction={handleCancel}
                placeholder={
                  mode === "POLICY_QA"
                    ? "e.g. What is the sick leave policy?"
                    : mode === "SQL_QUERY"
                    ? "e.g. Which employees know Python?"
                    : mode === "HR_ACTION"
                    ? "e.g. Apply casual leave for tomorrow"
                    : "Ask a question or describe a task..."
                }
              />
            )}
          </Card>
        </div>
      </section>
    </main>
  );
}
