"use client";

import { Bell, CheckCheck, Dot, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { fetchAnnouncements, fetchMyDocuments, fetchMyLeaveRequests, fetchPolls, fetchProfile, fetchTickets } from "@/lib/api";
import { formatDateTimeDDMMYY } from "@/lib/date";
import { cn } from "@/lib/utils";

type NotificationItem = {
  id: string;
  title: string;
  description: string;
  created_at: string;
  read: boolean;
  href: string;
};

const STORAGE_KEY = "hrms_notification_state";

type PersistedNotificationState = {
  read_ids: string[];
  dismissed_ids: string[];
};

function loadPersistedState(): PersistedNotificationState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { read_ids: [], dismissed_ids: [] };
    }
    const parsed = JSON.parse(raw) as PersistedNotificationState;
    return {
      read_ids: Array.isArray(parsed.read_ids) ? parsed.read_ids : [],
      dismissed_ids: Array.isArray(parsed.dismissed_ids) ? parsed.dismissed_ids : [],
    };
  } catch {
    return { read_ids: [], dismissed_ids: [] };
  }
}

function persistState(state: PersistedNotificationState) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function NotificationBell() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const panelRef = useRef<HTMLDivElement | null>(null);

  const loadNotifications = useCallback(async () => {
    if (typeof window === "undefined") return;

    const token = localStorage.getItem("hrms_access_token");
    if (!token) return;

    setLoading(true);
    try {
      const [profileResult, announcementsResult, pollsResult, ticketsResult, leaveRequestsResult, documentsResult] = await Promise.all([
        fetchProfile(token),
        fetchAnnouncements(token, { limit: 20, offset: 0 }),
        fetchPolls(token, { limit: 20, offset: 0 }),
        fetchTickets(token, { limit: 100, offset: 0 }),
        fetchMyLeaveRequests(token, { limit: 50, offset: 0 }),
        fetchMyDocuments(token),
      ]);

      const nextItems: NotificationItem[] = [];
      const currentUserId =
        profileResult.ok && "success" in profileResult.body && profileResult.body.success
          ? profileResult.body.data.id
          : null;

      if (announcementsResult.ok && "success" in announcementsResult.body && announcementsResult.body.success) {
        for (const announcement of announcementsResult.body.data.items) {
          nextItems.push({
            id: `announcement:${announcement.id}`,
            title: `Announcement: ${announcement.title}`,
            description: announcement.body,
            created_at: announcement.created_at,
            read: false,
            href: "/announcements",
          });
        }
      }

      if (pollsResult.ok && "success" in pollsResult.body && pollsResult.body.success) {
        for (const poll of pollsResult.body.data.items) {
          nextItems.push({
            id: `poll:${poll.id}`,
            title: `New Poll: ${poll.question}`,
            description: `Options: ${poll.options.join(", ")}`,
            created_at: poll.created_at,
            read: false,
            href: "/polls",
          });
        }
      }

      if (currentUserId !== null && ticketsResult.ok && "success" in ticketsResult.body && ticketsResult.body.success) {
        for (const ticket of ticketsResult.body.data.items) {
          if (ticket.assignee_id === currentUserId && ticket.employee_id !== currentUserId) {
            nextItems.push({
              id: `ticket-assigned:${ticket.id}:${currentUserId}`,
              title: `Ticket Assigned: #${ticket.id} ${ticket.title}`,
              description: `You were assigned this ${ticket.category} ticket (${ticket.priority}).`,
              created_at: ticket.created_at,
              read: false,
              href: "/tickets",
            });
          }

          if (ticket.employee_id === currentUserId && ticket.status !== "OPEN") {
            nextItems.push({
              id: `ticket-status:${ticket.id}:${ticket.status}`,
              title: `Ticket Update: #${ticket.id}`,
              description: `Your ticket is now ${ticket.status}.`,
              created_at: ticket.created_at,
              read: false,
              href: "/tickets",
            });
          }
        }
      }

      if (
        leaveRequestsResult.ok &&
        "success" in leaveRequestsResult.body &&
        leaveRequestsResult.body.success
      ) {
        for (const leave of leaveRequestsResult.body.data.items) {
          if (leave.status === "APPROVED" || leave.status === "REJECTED") {
            nextItems.push({
              id: `leave-status:${leave.id}:${leave.status}`,
              title: `Leave ${leave.status}: #${leave.id}`,
              description: `${leave.leave_type} leave from ${leave.start_date} to ${leave.end_date}.`,
              created_at: `${leave.end_date}T00:00:00`,
              read: false,
              href: "/leaves",
            });
          }
        }
      }

      if (documentsResult.ok && "success" in documentsResult.body && documentsResult.body.success) {
        for (const doc of documentsResult.body.data) {
          if (String(doc.id).startsWith("system-")) continue;
          if (currentUserId !== null && doc.uploaded_by === currentUserId) continue;
          const createdAt = doc.created_at || (doc.issued_on ? `${doc.issued_on}T00:00:00` : new Date().toISOString());
          nextItems.push({
            id: `document-upload:${doc.id}`,
            title: `New Document: ${doc.title}`,
            description: `${doc.type} uploaded to your documents.`,
            created_at: createdAt,
            read: false,
            href: "/me/documents",
          });
        }
      }

      const persisted = loadPersistedState();
      const readSet = new Set(persisted.read_ids);
      const dismissedSet = new Set(persisted.dismissed_ids);

      const merged = nextItems
        .filter((item) => !dismissedSet.has(item.id))
        .map((item) => ({ ...item, read: readSet.has(item.id) }))
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

      setItems(merged);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  useEffect(() => {
    if (!open) return;
    loadNotifications();
  }, [open, loadNotifications]);

  useEffect(() => {
    const onClickOutside = (event: MouseEvent) => {
      if (!panelRef.current) return;
      if (!panelRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const unreadCount = useMemo(() => items.filter((item) => !item.read).length, [items]);

  const persistItems = (nextItems: NotificationItem[]) => {
    setItems(nextItems);
    const persisted = loadPersistedState();
    const nextRead = nextItems.filter((item) => item.read).map((item) => item.id);
    persistState({ read_ids: nextRead, dismissed_ids: persisted.dismissed_ids });
  };

  const markAllRead = () => {
    persistItems(items.map((item) => ({ ...item, read: true })));
  };

  const dismissNotification = (id: string) => {
    const nextItems = items.filter((item) => item.id !== id);
    setItems(nextItems);
    const persisted = loadPersistedState();
    const dismissed = new Set(persisted.dismissed_ids);
    dismissed.add(id);
    const readIds = nextItems.filter((item) => item.read).map((item) => item.id);
    persistState({ read_ids: readIds, dismissed_ids: Array.from(dismissed) });
  };

  const openNotification = (item: NotificationItem) => {
    const next = items.map((row) => (row.id === item.id ? { ...row, read: true } : row));
    persistItems(next);
    setOpen(false);
    router.push(item.href);
  };

  return (
    <div className="relative" ref={panelRef}>
      <button
        aria-label="Notifications"
        className="relative inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/15 bg-white/5 text-white transition hover:bg-white/10"
        onClick={() => setOpen((value) => !value)}
        type="button"
        suppressHydrationWarning
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 ? (
          <span className="absolute -right-1 -top-1 inline-flex min-w-5 items-center justify-center rounded-full bg-rose-500 px-1.5 text-[10px] font-semibold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        ) : null}
      </button>

      {open ? (
        <div className="absolute right-0 z-50 mt-3 w-[360px] overflow-hidden rounded-2xl border border-slate-700/80 bg-slate-950/95 shadow-2xl backdrop-blur">
          <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
            <div>
              <p className="text-sm font-semibold text-white">Notifications</p>
              <p className="text-xs text-slate-400">{unreadCount} unread</p>
            </div>
            <Button onClick={markAllRead} size="sm" variant="outline">
              <CheckCheck className="mr-1 h-3.5 w-3.5" /> Mark all read
            </Button>
          </div>

          <div className="max-h-96 overflow-y-auto p-2">
            {loading ? (
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-300">Loading notifications...</div>
            ) : null}
            {!loading && items.length === 0 ? (
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-300">No notifications</div>
            ) : (
              <div className="space-y-2">
                {items.map((item) => (
                  <div
                    className={cn(
                      "rounded-xl border px-3 py-3 transition",
                      item.read
                        ? "border-slate-800 bg-slate-900/50"
                        : "border-indigo-500/30 bg-indigo-500/10"
                    )}
                    key={item.id}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <button className="min-w-0 flex-1 text-left" onClick={() => openNotification(item)} type="button">
                        <div className="flex items-center gap-2">
                          {!item.read ? <Dot className="h-4 w-4 text-indigo-300" /> : null}
                          <p className="truncate text-sm font-medium text-white">{item.title}</p>
                        </div>
                        <p className="mt-1 text-xs text-slate-300">{item.description}</p>
                        <p className="mt-2 text-[11px] text-slate-500">{formatDateTimeDDMMYY(item.created_at)}</p>
                      </button>
                      <button
                        aria-label="Dismiss notification"
                        className="rounded-md p-1 text-slate-400 hover:bg-white/5 hover:text-white"
                        onClick={() => dismissNotification(item.id)}
                        type="button"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
