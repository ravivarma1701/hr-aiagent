"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AttendanceLog, clockIn, clockOut, fetchAttendanceLogs, fetchProfile, fetchTodayAttendance } from "@/lib/api";
import { formatDateDDMMYY } from "@/lib/date";

const statusClassMap: Record<string, string> = {
  ON_TIME: "bg-emerald-100 text-emerald-700",
  LATE: "bg-amber-100 text-amber-700",
  HALF_DAY: "bg-rose-100 text-rose-700",
  ABSENT: "bg-slate-200 text-slate-700",
};

const modeClassMap: Record<string, string> = {
  PRESENT: "bg-indigo-100 text-indigo-700",
  WFH: "bg-blue-100 text-blue-700",
  ABSENT: "bg-slate-200 text-slate-700",
};

export default function AttendancePage() {
  const pageSize = 10;
  const [name, setName] = useState("User");
  const [today, setToday] = useState<AttendanceLog | null>(null);
  const [logs, setLogs] = useState<AttendanceLog[]>([]);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
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

  const loadData = async (nextOffset = 0) => {
    if (!token) {
      clearAuthAndRedirect();
      return;
    }

    setLoading(true);
    setError("");

    try {
      const [logsResult, todayResult, profileResult] = await Promise.all([
        fetchAttendanceLogs(token, { limit: pageSize, offset: nextOffset }),
        fetchTodayAttendance(token),
        fetchProfile(token),
      ]);

      if (logsResult.status === 401 || todayResult.status === 401 || profileResult.status === 401) {
        clearAuthAndRedirect();
        return;
      }

      if (!logsResult.ok || !("success" in logsResult.body) || !logsResult.body.success) {
        setError("Failed to load attendance logs");
        return;
      }

      if (todayResult.ok && "success" in todayResult.body && todayResult.body.success) {
        setToday(todayResult.body.data);
      }

      if (profileResult.ok && "success" in profileResult.body && profileResult.body.success) {
        setName(profileResult.body.data.name);
      }

      setLogs(logsResult.body.data.items);
      setOffset(logsResult.body.data.meta.offset);
      setTotal(logsResult.body.data.meta.total);
    } catch {
      setError("Failed to fetch attendance data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const handleClockIn = async (mode: "PRESENT" | "WFH") => {
    if (!token) return;
    setActionLoading(true);
    setError("");
    const result = await clockIn(token, mode);
    if (!result.ok) {
      setError("Unable to clock in. You may already be clocked in today.");
      setActionLoading(false);
      return;
    }
    await loadData(0);
    setActionLoading(false);
  };

  const handleClockOut = async () => {
    if (!token) return;
    setActionLoading(true);
    setError("");
    const result = await clockOut(token);
    if (!result.ok) {
      setError("Unable to clock out. Clock in first or check if already clocked out.");
      setActionLoading(false);
      return;
    }
    await loadData(0);
    setActionLoading(false);
  };

  const currentPage = Math.floor(offset / pageSize) + 1;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex w-full flex-col">
        <Topbar name={name} title="Attendance" />
        <div className="space-y-4 p-6">
          <Card>
            <CardHeader>
              <CardTitle>Today's Attendance</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <Button disabled={actionLoading || !!today?.clock_in} onClick={() => handleClockIn("PRESENT")}>
                  Clock In (Present)
                </Button>
                <Button disabled={actionLoading || !!today?.clock_in} variant="outline" onClick={() => handleClockIn("WFH")}>
                  Clock In (WFH)
                </Button>
                <Button disabled={actionLoading || !today?.clock_in || !!today?.clock_out} onClick={handleClockOut}>
                  Clock Out
                </Button>
              </div>

              <div className="text-sm text-slate-600">
                {today ? (
                  <div className="flex items-center gap-3">
                    <span>Date: {formatDateDDMMYY(today.date)}</span>
                    <span>Clock In: {today.clock_in || "-"}</span>
                    <span>Clock Out: {today.clock_out || "-"}</span>
                    <Badge className={statusClassMap[today.status] || "bg-slate-200 text-slate-700"}>{today.status}</Badge>
                    {today.work_mode ? (
                      <Badge className={modeClassMap[today.work_mode] || "bg-slate-200 text-slate-700"}>{today.work_mode}</Badge>
                    ) : null}
                  </div>
                ) : (
                  <span>No attendance record for today yet.</span>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Attendance History</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? <p className="text-sm text-muted-foreground">Loading attendance logs...</p> : null}
              {error ? <p className="text-sm text-red-600">{error}</p> : null}

              {!loading && !error ? (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Clock In</TableHead>
                        <TableHead>Clock Out</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Mode</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {logs.map((log) => (
                        <TableRow key={log.id}>
                          <TableCell>{formatDateDDMMYY(log.date)}</TableCell>
                          <TableCell>{log.clock_in || "-"}</TableCell>
                          <TableCell>{log.clock_out || "-"}</TableCell>
                          <TableCell>
                            <Badge className={statusClassMap[log.status] || "bg-slate-200 text-slate-700"}>{log.status}</Badge>
                          </TableCell>
                          <TableCell>
                            {log.work_mode ? (
                              <Badge className={modeClassMap[log.work_mode] || "bg-slate-200 text-slate-700"}>{log.work_mode}</Badge>
                            ) : (
                              "-"
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : null}

              {!loading && !error ? (
                <div className="mt-4 flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    Page {currentPage} of {totalPages} ({total} total records)
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={offset <= 0}
                      onClick={() => loadData(Math.max(0, offset - pageSize))}
                    >
                      Previous
                    </Button>
                    <Button size="sm" disabled={offset + pageSize >= total} onClick={() => loadData(offset + pageSize)}>
                      Next
                    </Button>
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
