"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Poll, PollResultItem, createPoll, fetchPollResults, fetchPolls, fetchProfile, votePoll } from "@/lib/api";

export default function PollsPage() {
  const [name, setName] = useState("User");
  const [role, setRole] = useState("EMPLOYEE");
  const [polls, setPolls] = useState<Poll[]>([]);
  const [question, setQuestion] = useState("");
  const [optionsText, setOptionsText] = useState("");
  const [resultsByPoll, setResultsByPoll] = useState<Record<number, PollResultItem[]>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
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

  const loadData = async () => {
    if (!token) return clearAuthAndRedirect();
    setLoading(true);
    setError("");
    try {
      const [profileResult, pollsResult] = await Promise.all([fetchProfile(token), fetchPolls(token, { limit: 50, offset: 0 })]);
      if (profileResult.status === 401 || pollsResult.status === 401) return clearAuthAndRedirect();

      if (profileResult.ok && "success" in profileResult.body && profileResult.body.success) {
        setName(profileResult.body.data.name);
        setRole(profileResult.body.data.role);
      }
      if (!pollsResult.ok || !("success" in pollsResult.body) || !pollsResult.body.success) {
        setError("Failed to load polls");
        return;
      }
      setPolls(pollsResult.body.data.items);
    } catch {
      setError("Failed to fetch polls");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const onCreate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setError("");
    try {
      const options = optionsText
        .split(",")
        .map((value) =>
          value
            .replace(/^\s*Option A\s*/i, "")
            .replace(/\s*Option B\s*$/i, "")
            .trim()
        )
        .filter(Boolean);
      const result = await createPoll(token, { question: question.trim(), options });
      if (!result.ok) {
        setError("Failed to create poll");
        return;
      }
      setQuestion("");
      setOptionsText("");
      await loadData();
    } finally {
      setSubmitting(false);
    }
  };

  const onVote = async (pollId: number, optionIndex: number) => {
    if (!token) return;
    const result = await votePoll(token, pollId, optionIndex);
    if (!result.ok) {
      setError("Failed to submit vote");
      return;
    }
    await loadData();
    await loadResults(pollId);
  };

  const loadResults = async (pollId: number) => {
    if (!token) return;
    const result = await fetchPollResults(token, pollId);
    if (!result.ok || !("success" in result.body) || !result.body.success) return;
    setResultsByPoll((prev) => ({ ...prev, [pollId]: result.body.data.items }));
  };

  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex w-full flex-col">
        <Topbar name={name} title="Polls" />
        <div className="space-y-4 p-6">
          {error ? <p className="text-sm text-red-600">{error}</p> : null}

          {(role === "ADMIN" || role === "MANAGER") && (
            <Card>
              <CardHeader>
                <CardTitle>Create Poll</CardTitle>
              </CardHeader>
              <CardContent>
                <form className="grid gap-3 md:grid-cols-3" onSubmit={onCreate}>
                  <Input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Question" required />
                  <Input
                    value={optionsText}
                    onChange={(e) => setOptionsText(e.target.value)}
                    placeholder="Option A, Option B"
                    required
                  />
                  <Button type="submit" disabled={submitting || loading}>
                    {submitting ? "Creating..." : "Create"}
                  </Button>
                </form>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Polls Feed</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? <p className="text-sm text-muted-foreground">Loading polls...</p> : null}
              {!loading && polls.length === 0 ? <p className="text-sm text-muted-foreground">No polls available.</p> : null}
              <div className="space-y-3">
                {polls.map((poll) => (
                  <article className="rounded border border-border p-4" key={poll.id}>
                    <p className="text-sm font-semibold text-slate-900">{poll.question}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {poll.options.map((option, idx) => (
                        <Button
                          key={`${poll.id}-${idx}`}
                          size="sm"
                          variant={poll.my_vote === idx ? "default" : "outline"}
                          onClick={() => onVote(poll.id, idx)}
                        >
                          {option}
                        </Button>
                      ))}
                    </div>
                    <div className="mt-3 flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => loadResults(poll.id)}>
                        View Results
                      </Button>
                    </div>
                    {(resultsByPoll[poll.id] || []).length > 0 && (
                      <div className="mt-3 space-y-1">
                        {resultsByPoll[poll.id].map((row) => (
                          <p className="text-xs text-muted-foreground" key={`${poll.id}-${row.option_index}`}>
                            {row.option}: {row.votes} votes ({row.percentage}%)
                          </p>
                        ))}
                      </div>
                    )}
                  </article>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
