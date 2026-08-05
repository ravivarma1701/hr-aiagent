"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { RichText } from "@/components/ui/rich-text";
import { Announcement, createAnnouncement, fetchAnnouncements, fetchProfile } from "@/lib/api";
import { formatDateTimeDDMMYY } from "@/lib/date";

export default function AnnouncementsPage() {
  const [name, setName] = useState("User");
  const [role, setRole] = useState("EMPLOYEE");
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const token = useMemo(() => {
    if (typeof window === "undefined") {
      return null;
    }
    return localStorage.getItem("hrms_access_token");
  }, []);

  const clearAuthAndRedirect = () => {
    localStorage.removeItem("hrms_access_token");
    document.cookie = "hrms_auth=; path=/; max-age=0; samesite=lax";
    router.push("/login");
  };

  const loadData = async () => {
    if (!token) {
      clearAuthAndRedirect();
      return;
    }
    setLoading(true);
    setError("");

    try {
      const [profileResult, announcementResult] = await Promise.all([
        fetchProfile(token),
        fetchAnnouncements(token, { limit: 50, offset: 0 }),
      ]);

      if (profileResult.status === 401 || announcementResult.status === 401) {
        clearAuthAndRedirect();
        return;
      }

      if (profileResult.ok && "success" in profileResult.body && profileResult.body.success) {
        setName(profileResult.body.data.name);
        setRole(profileResult.body.data.role);
      }

      if (!announcementResult.ok || !("success" in announcementResult.body) || !announcementResult.body.success) {
        setError("Failed to load announcements");
        return;
      }

      setAnnouncements(announcementResult.body.data.items);
    } catch {
      setError("Failed to fetch announcements");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setError("");
    try {
      const result = await createAnnouncement(token, { title: title.trim(), body: body.trim() });
      if (!result.ok) {
        setError("Failed to create announcement");
        return;
      }
      setTitle("");
      setBody("");
      await loadData();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex w-full flex-col">
        <Topbar name={name} title="Announcements" />
        <div className="space-y-4 p-6">
          {error ? <p className="text-sm text-red-600">{error}</p> : null}

          {(role === "ADMIN" || role === "MANAGER") && (
            <Card>
              <CardHeader>
                <CardTitle>Create Announcement</CardTitle>
              </CardHeader>
              <CardContent>
                <form className="space-y-3" onSubmit={onSubmit}>
                  <Input
                    placeholder="Title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    required
                    minLength={3}
                    maxLength={180}
                  />
                  <textarea
                    className="min-h-28 w-full rounded-md border border-border px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    placeholder="Announcement details (supports markdown: # heading, - list, **bold**, *italic*)"
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    required
                    minLength={5}
                    maxLength={5000}
                  />
                  <Button disabled={submitting || loading} type="submit">
                    {submitting ? "Posting..." : "Post Announcement"}
                  </Button>
                </form>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Feed</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? <p className="text-sm text-muted-foreground">Loading announcements...</p> : null}
              {!loading && announcements.length === 0 ? (
                <p className="text-sm text-muted-foreground">No announcements yet.</p>
              ) : null}
              <div className="space-y-3">
                {announcements.map((item) => (
                  <article className="rounded-md border border-border bg-white p-4" key={item.id}>
                    <h3 className="text-base font-semibold text-slate-900">{item.title}</h3>
                    <div className="mt-2">
                      <RichText content={item.body} />
                    </div>
                    <p className="mt-3 text-xs text-muted-foreground">
                      By {item.author_name} on {formatDateTimeDDMMYY(item.created_at)}
                    </p>
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
