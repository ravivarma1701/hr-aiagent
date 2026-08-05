"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Ticket,
  assignTicket,
  completeOnboardingTask,
  createOnboardingTask,
  createTicket,
  fetchProfile,
  fetchTickets,
  updateTicketStatus,
} from "@/lib/api";

export default function TicketsPage() {
  const [name, setName] = useState("User");
  const [currentUserId, setCurrentUserId] = useState<number | null>(null);
  const [role, setRole] = useState("EMPLOYEE");
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<"IT" | "HR" | "ONBOARDING">("IT");
  const [priority, setPriority] = useState<"LOW" | "MEDIUM" | "HIGH">("MEDIUM");
  const [assigneeByTicket, setAssigneeByTicket] = useState<Record<number, string>>({});
  const [taskNameByTicket, setTaskNameByTicket] = useState<Record<number, string>>({});
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
      const [profileResult, ticketsResult] = await Promise.all([
        fetchProfile(token),
        fetchTickets(token, { limit: 100, offset: 0 }),
      ]);
      if (profileResult.status === 401 || ticketsResult.status === 401) return clearAuthAndRedirect();

      if (profileResult.ok && "success" in profileResult.body && profileResult.body.success) {
        setName(profileResult.body.data.name);
        setCurrentUserId(profileResult.body.data.id);
        setRole(profileResult.body.data.role);
      }
      if (!ticketsResult.ok || !("success" in ticketsResult.body) || !ticketsResult.body.success) {
        setError("Failed to load tickets");
        return;
      }
      setTickets(ticketsResult.body.data.items);
    } catch {
      setError("Failed to fetch tickets");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const onCreateTicket = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setError("");
    try {
      const result = await createTicket(token, { title, description, category, priority });
      if (!result.ok) {
        setError("Failed to create ticket");
        return;
      }
      setTitle("");
      setDescription("");
      setCategory("IT");
      setPriority("MEDIUM");
      await loadData();
    } finally {
      setSubmitting(false);
    }
  };

  const onAssign = async (ticketId: number) => {
    if (!token) return;
    const value = Number(assigneeByTicket[ticketId]);
    if (!value) return;
    const result = await assignTicket(token, ticketId, value);
    if (!result.ok) {
      setError("Failed to assign ticket");
      return;
    }
    await loadData();
  };

  const onStatus = async (ticketId: number, nextStatus: "OPEN" | "IN_PROGRESS" | "RESOLVED") => {
    if (!token) return;
    const result = await updateTicketStatus(token, ticketId, nextStatus);
    if (!result.ok) {
      setError("Failed to update status");
      return;
    }
    await loadData();
  };

  const onAddTask = async (ticketId: number) => {
    if (!token) return;
    const taskName = (taskNameByTicket[ticketId] || "").trim();
    if (!taskName) return;
    const result = await createOnboardingTask(token, ticketId, { task_name: taskName });
    if (!result.ok) {
      setError("Failed to add onboarding task");
      return;
    }
    setTaskNameByTicket((prev) => ({ ...prev, [ticketId]: "" }));
    await loadData();
  };

  const onCompleteTask = async (ticketId: number, taskId: number) => {
    if (!token) return;
    const result = await completeOnboardingTask(token, ticketId, taskId);
    if (!result.ok) {
      setError("Failed to complete onboarding task");
      return;
    }
    await loadData();
  };

  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex w-full flex-col">
        <Topbar name={name} title="Tickets" />
        <div className="space-y-4 p-6">
          {error ? <p className="text-sm text-red-600">{error}</p> : null}

          <Card>
            <CardHeader>
              <CardTitle>Raise Ticket</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="grid gap-3 md:grid-cols-5" onSubmit={onCreateTicket}>
                <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title" required />
                <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description" required />
                <select
                  className="h-10 rounded-md border border-border px-3 text-sm"
                  value={category}
                  onChange={(e) => setCategory(e.target.value as "IT" | "HR" | "ONBOARDING")}
                >
                  <option value="IT">IT</option>
                  <option value="HR">HR</option>
                  <option value="ONBOARDING">ONBOARDING</option>
                </select>
                <select
                  className="h-10 rounded-md border border-border px-3 text-sm"
                  value={priority}
                  onChange={(e) => setPriority(e.target.value as "LOW" | "MEDIUM" | "HIGH")}
                >
                  <option value="LOW">LOW</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="HIGH">HIGH</option>
                </select>
                <Button type="submit" disabled={submitting || loading}>
                  {submitting ? "Submitting..." : "Submit"}
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Ticket Dashboard</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? <p className="text-sm text-muted-foreground">Loading tickets...</p> : null}
              {!loading && tickets.length === 0 ? <p className="text-sm text-muted-foreground">No tickets yet.</p> : null}
              <div className="space-y-3">
                {tickets.map((ticket) => (
                  <article className="rounded-md border border-border bg-white p-4" key={ticket.id}>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-base font-semibold text-slate-900">
                        #{ticket.id} {ticket.title}
                      </h3>
                      <span className="rounded bg-slate-100 px-2 py-1 text-xs">{ticket.category}</span>
                      <span className="rounded bg-slate-100 px-2 py-1 text-xs">{ticket.priority}</span>
                      <span className="rounded bg-blue-100 px-2 py-1 text-xs text-blue-700">{ticket.status}</span>
                    </div>
                    <p className="mt-2 text-sm text-slate-700">{ticket.description}</p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      Employee #{ticket.employee_id} | Assignee: {ticket.assignee_id ?? "-"}
                    </p>
                    {(() => {
                      const isAdminOrManager = role === "ADMIN" || role === "MANAGER";
                      const isAssignedEmployee = role === "EMPLOYEE" && currentUserId !== null && ticket.assignee_id === currentUserId;
                      const canControlStatus = isAdminOrManager || isAssignedEmployee;
                      return (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {canControlStatus && (
                            <>
                              <Button size="sm" variant="outline" onClick={() => onStatus(ticket.id, "IN_PROGRESS")}>
                                Start
                              </Button>
                              <Button size="sm" variant="outline" onClick={() => onStatus(ticket.id, "RESOLVED")}>
                                Resolve
                              </Button>
                            </>
                          )}
                          {isAdminOrManager && (
                            <>
                              <Input
                                className="h-8 w-32"
                                placeholder="Assignee ID"
                                value={assigneeByTicket[ticket.id] || ""}
                                onChange={(e) => setAssigneeByTicket((prev) => ({ ...prev, [ticket.id]: e.target.value }))}
                              />
                              <Button size="sm" onClick={() => onAssign(ticket.id)}>
                                Assign
                              </Button>
                            </>
                          )}
                        </div>
                      );
                    })()}

                    {ticket.category === "ONBOARDING" && (
                      <div className="mt-3 space-y-2 rounded-md border border-dashed border-border p-3">
                        <p className="text-sm font-medium">Onboarding Checklist</p>
                        {(ticket.onboarding_tasks || []).map((task) => (
                          <div key={task.id} className="flex items-center justify-between text-sm">
                            <span>
                              {task.task_name} {task.is_completed ? "(Done)" : ""}
                            </span>
                            {!task.is_completed && (
                              <Button size="sm" variant="outline" onClick={() => onCompleteTask(ticket.id, task.id)}>
                                Mark Done
                              </Button>
                            )}
                          </div>
                        ))}

                        {(role === "ADMIN" || role === "MANAGER") && (
                          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                            <Input
                              value={taskNameByTicket[ticket.id] || ""}
                              onChange={(e) => setTaskNameByTicket((prev) => ({ ...prev, [ticket.id]: e.target.value }))}
                              placeholder="Add onboarding task"
                            />
                            <Button className="whitespace-nowrap px-4 sm:min-w-28" onClick={() => onAddTask(ticket.id)}>
                              Add Task
                            </Button>
                          </div>
                        )}
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
