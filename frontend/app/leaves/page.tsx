"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DatePicker } from "@/components/ui/date-picker";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  LeaveBalance,
  LeaveRequest,
  approveLeaveRequest,
  fetchMyLeaveBalances,
  fetchMyLeaveRequests,
  fetchPendingLeaveRequests,
  fetchProfile,
  rejectLeaveRequest,
  submitLeaveRequest,
} from "@/lib/api";
import { formatDateDDMMYY } from "@/lib/date";

const statusClassMap: Record<string, string> = {
  PENDING: "bg-amber-100 text-amber-700",
  APPROVED: "bg-emerald-100 text-emerald-700",
  REJECTED: "bg-rose-100 text-rose-700",
};

export default function LeavesPage() {
  const [name, setName] = useState("User");
  const [role, setRole] = useState("EMPLOYEE");
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [myRequests, setMyRequests] = useState<LeaveRequest[]>([]);
  const [pendingRequests, setPendingRequests] = useState<LeaveRequest[]>([]);
  const [leaveType, setLeaveType] = useState<"CASUAL" | "SICK" | "EARNED">("CASUAL");
  const [leaveDuration, setLeaveDuration] = useState<"FULL_DAY" | "FIRST_HALF" | "SECOND_HALF">("FULL_DAY");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
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

  const extractErrorMessage = (body: unknown, fallback: string) => {
    if (!body || typeof body !== "object") return fallback;
    const record = body as Record<string, unknown>;
    const detail = record.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object") {
      const detailRecord = detail as Record<string, unknown>;
      if (
        detailRecord.error &&
        typeof detailRecord.error === "object" &&
        typeof (detailRecord.error as Record<string, unknown>).message === "string"
      ) {
        return (detailRecord.error as Record<string, unknown>).message as string;
      }
      if (typeof detailRecord.message === "string") return detailRecord.message;
    }
    return fallback;
  };

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
      const profileResult = await fetchProfile(token);
      if (profileResult.status === 401) {
        clearAuthAndRedirect();
        return;
      }
      if (!profileResult.ok || !("success" in profileResult.body) || !profileResult.body.success) {
        setError("Failed to load profile");
        return;
      }

      const nextRole = profileResult.body.data.role;
      setRole(nextRole);
      setName(profileResult.body.data.name);

      const [balancesResult, myReqResult] = await Promise.all([
        fetchMyLeaveBalances(token),
        fetchMyLeaveRequests(token, { limit: 50, offset: 0 }),
      ]);

      if (balancesResult.status === 401 || myReqResult.status === 401) {
        clearAuthAndRedirect();
        return;
      }

      if (balancesResult.ok && "success" in balancesResult.body && balancesResult.body.success) {
        setBalances(balancesResult.body.data);
      }

      if (myReqResult.ok && "success" in myReqResult.body && myReqResult.body.success) {
        setMyRequests(myReqResult.body.data.items);
      }

      if (nextRole === "ADMIN" || nextRole === "MANAGER") {
        const pendingResult = await fetchPendingLeaveRequests(token, { limit: 50, offset: 0 });
        if (pendingResult.ok && "success" in pendingResult.body && pendingResult.body.success) {
          setPendingRequests(pendingResult.body.data.items);
        }
      } else {
        setPendingRequests([]);
      }
    } catch {
      setError("Failed to fetch leave data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (leaveDuration !== "FULL_DAY") {
      setEndDate(startDate);
    }
  }, [leaveDuration, startDate]);

  const onSubmitLeave = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token) return;
    const effectiveEndDate = leaveDuration === "FULL_DAY" ? endDate : startDate;
    if (!startDate || !effectiveEndDate) {
      setError("Start date and end date are required.");
      return;
    }
    setSubmitting(true);
    setError("");

    try {
      const result = await submitLeaveRequest(token, {
        leave_type: leaveType,
        start_date: startDate,
        end_date: effectiveEndDate,
        is_half_day: leaveDuration !== "FULL_DAY",
        half_day_period: leaveDuration === "FULL_DAY" ? undefined : leaveDuration,
        reason,
      });
      if (!result.ok) {
        setError(extractErrorMessage(result.body, "Failed to submit leave request"));
        return;
      }

      setStartDate("");
      setEndDate("");
      setLeaveDuration("FULL_DAY");
      setReason("");
      await loadData();
    } finally {
      setSubmitting(false);
    }
  };

  const onApprove = async (requestId: number) => {
    if (!token) return;
    const result = await approveLeaveRequest(token, requestId);
    if (!result.ok) {
      setError(extractErrorMessage(result.body, "Failed to approve leave request"));
      return;
    }
    await loadData();
  };

  const onReject = async (requestId: number) => {
    if (!token) return;
    const result = await rejectLeaveRequest(token, requestId);
    if (!result.ok) {
      setError(extractErrorMessage(result.body, "Failed to reject leave request"));
      return;
    }
    await loadData();
  };

  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex w-full flex-col">
        <Topbar name={name} title="Leaves" />
        <div className="space-y-4 p-6">
          {error ? <p className="text-sm text-red-600">{error}</p> : null}

          <Card>
            <CardHeader>
              <CardTitle>My Leave Balances</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-3">
                {balances.map((balance) => (
                  <div className="rounded-md border border-border bg-white p-4" key={balance.id}>
                    <p className="text-sm text-muted-foreground">{balance.leave_type}</p>
                    <p className="text-xl font-semibold">{balance.remaining}</p>
                    <p className="text-xs text-muted-foreground">
                      Used {balance.used} / Total {balance.total}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Submit Leave Request</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="grid gap-3 md:grid-cols-6" onSubmit={onSubmitLeave}>
                <select
                  className="h-10 rounded-md border border-border px-3 text-sm"
                  value={leaveType}
                  onChange={(e) => setLeaveType(e.target.value as "CASUAL" | "SICK" | "EARNED")}
                >
                  <option value="CASUAL">CASUAL</option>
                  <option value="SICK">SICK</option>
                  <option value="EARNED">EARNED</option>
                </select>
                <select
                  className="h-10 rounded-md border border-border px-3 text-sm"
                  value={leaveDuration}
                  onChange={(e) => setLeaveDuration(e.target.value as "FULL_DAY" | "FIRST_HALF" | "SECOND_HALF")}
                >
                  <option value="FULL_DAY">FULL DAY</option>
                  <option value="FIRST_HALF">FIRST HALF</option>
                  <option value="SECOND_HALF">SECOND HALF</option>
                </select>
                <DatePicker value={startDate} onChange={setStartDate} placeholder="Start date" />
                {leaveDuration === "FULL_DAY" ? (
                  <DatePicker value={endDate} onChange={setEndDate} placeholder="End date" />
                ) : (
                  <Input value={startDate ? formatDateDDMMYY(startDate) : ""} placeholder="Same as start date" disabled />
                )}
                <Input placeholder="Reason" value={reason} onChange={(e) => setReason(e.target.value)} required />
                <Button disabled={submitting || loading} type="submit">
                  {submitting ? "Submitting..." : "Submit"}
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>My Leave Requests</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? <p className="text-sm text-muted-foreground">Loading leave requests...</p> : null}
              {!loading ? (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>ID</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>From</TableHead>
                        <TableHead>To</TableHead>
                        <TableHead>Reason</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {myRequests.map((req) => (
                        <TableRow key={req.id}>
                          <TableCell>{req.id}</TableCell>
                          <TableCell>
                            {req.leave_type}
                            {req.is_half_day ? ` (${req.half_day_period === "FIRST_HALF" ? "FIRST HALF" : "SECOND HALF"})` : ""}
                          </TableCell>
                          <TableCell>{formatDateDDMMYY(req.start_date)}</TableCell>
                          <TableCell>{formatDateDDMMYY(req.end_date)}</TableCell>
                          <TableCell>{req.reason}</TableCell>
                          <TableCell>
                            <Badge className={statusClassMap[req.status] || "bg-slate-200 text-slate-700"}>{req.status}</Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : null}
            </CardContent>
          </Card>

          {(role === "ADMIN" || role === "MANAGER") && (
            <Card>
              <CardHeader>
                <CardTitle>Pending Approvals</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>ID</TableHead>
                        <TableHead>Employee ID</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>From</TableHead>
                        <TableHead>To</TableHead>
                        <TableHead>Reason</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {pendingRequests.map((req) => (
                        <TableRow key={req.id}>
                          <TableCell>{req.id}</TableCell>
                          <TableCell>{req.employee_id}</TableCell>
                          <TableCell>
                            {req.leave_type}
                            {req.is_half_day ? ` (${req.half_day_period === "FIRST_HALF" ? "FIRST HALF" : "SECOND HALF"})` : ""}
                          </TableCell>
                          <TableCell>{formatDateDDMMYY(req.start_date)}</TableCell>
                          <TableCell>{formatDateDDMMYY(req.end_date)}</TableCell>
                          <TableCell>{req.reason}</TableCell>
                          <TableCell>
                            <div className="flex gap-2">
                              <Button size="sm" onClick={() => onApprove(req.id)}>
                                Approve
                              </Button>
                              <Button size="sm" variant="outline" onClick={() => onReject(req.id)}>
                                Reject
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </section>
    </main>
  );
}
