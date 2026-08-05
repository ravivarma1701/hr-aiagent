"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  EmployeeDocument,
  FinanceProfile,
  PayrollRecord,
  StatutoryDetails,
  downloadMyDocument,
  fetchMyDocuments,
  fetchMyFinanceProfile,
  fetchMyPayroll,
  fetchMyStatutory,
  fetchProfile,
} from "@/lib/api";
import { formatDateDDMMYY, formatMonthToDDMMYY } from "@/lib/date";

export default function FinancePage() {
  const [name, setName] = useState("User");
  const [employeeId, setEmployeeId] = useState<number | null>(null);
  const [payroll, setPayroll] = useState<PayrollRecord[]>([]);
  const [payslipDocs, setPayslipDocs] = useState<EmployeeDocument[]>([]);
  const [financeProfile, setFinanceProfile] = useState<FinanceProfile | null>(null);
  const [statutory, setStatutory] = useState<StatutoryDetails | null>(null);
  const [selectedMonth, setSelectedMonth] = useState("");
  const [downloadingPayslip, setDownloadingPayslip] = useState(false);
  const [viewingPayslip, setViewingPayslip] = useState(false);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const router = useRouter();

  const token = useMemo(() => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("hrms_access_token");
  }, []);

  const monthOptions = useMemo(() => {
    const now = new Date();
    const currentMonthKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    return [...new Set(payroll.map((row) => row.month.slice(0, 7)))]
      .filter(Boolean)
      .filter((month) => month < currentMonthKey)
      .sort()
      .reverse();
  }, [payroll]);

  const payslipMonth = (doc: EmployeeDocument) => {
    const match = doc.title.match(/\[(\d{4}-\d{2})\]/);
    if (match?.[1]) return match[1];
    return (doc.issued_on || "").slice(0, 7);
  };

  const clearAuthAndRedirect = () => {
    localStorage.removeItem("hrms_access_token");
    document.cookie = "hrms_auth=; path=/; max-age=0; samesite=lax";
    router.push("/login");
  };

  const loadData = async () => {
    if (!token) return clearAuthAndRedirect();
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const [profileResult, payrollResult, financeProfileResult, statutoryResult, docsResult] = await Promise.all([
        fetchProfile(token),
        fetchMyPayroll(token),
        fetchMyFinanceProfile(token),
        fetchMyStatutory(token),
        fetchMyDocuments(token),
      ]);
      if (
        profileResult.status === 401 ||
        payrollResult.status === 401 ||
        financeProfileResult.status === 401 ||
        statutoryResult.status === 401 ||
        docsResult.status === 401
      ) {
        return clearAuthAndRedirect();
      }

      if (profileResult.ok && "success" in profileResult.body && profileResult.body.success) {
        setName(profileResult.body.data.name);
        setEmployeeId(profileResult.body.data.id);
      }
      if (payrollResult.ok && "success" in payrollResult.body && payrollResult.body.success) {
        setPayroll(payrollResult.body.data);
      }
      if (financeProfileResult.ok && "success" in financeProfileResult.body && financeProfileResult.body.success) {
        setFinanceProfile(financeProfileResult.body.data);
      }
      if (statutoryResult.ok && "success" in statutoryResult.body && statutoryResult.body.success) {
        setStatutory(statutoryResult.body.data);
      }
      if (docsResult.ok && "success" in docsResult.body && docsResult.body.success) {
        const docs = (docsResult.body.data || []).filter(
          (doc) => doc.type === "PAYSLIP" && !String(doc.id).startsWith("system-")
        );
        setPayslipDocs(docs);
      }
    } catch {
      setError("Failed to load finance data");
    } finally {
      setLoading(false);
    }
  };

  const getPayslipTargetIds = () => {
    const matchingUploaded = payslipDocs.find(
      (doc) => doc.type === "PAYSLIP" && payslipMonth(doc) === selectedMonth
    );
    const fallbackSystemDocumentId = employeeId ? `system-payslip-${employeeId}-${selectedMonth}` : null;
    return {
      matchingUploaded,
      uploadedId: matchingUploaded?.id ? String(matchingUploaded.id) : null,
      fallbackSystemDocumentId,
    };
  };

  const fetchPayslipBlob = async () => {
    const { uploadedId, fallbackSystemDocumentId } = getPayslipTargetIds();
    if (!uploadedId && !fallbackSystemDocumentId) {
      return { ok: false as const, blob: null, selectedDocumentId: null as string | null };
    }

    if (fallbackSystemDocumentId) {
      const fallbackResult = await downloadMyDocument(token as string, String(fallbackSystemDocumentId));
      if (fallbackResult.ok) {
        return {
          ok: true as const,
          blob: fallbackResult.body as Blob,
          selectedDocumentId: String(fallbackSystemDocumentId),
        };
      }
    }

    if (uploadedId) {
      const uploadedResult = await downloadMyDocument(token as string, uploadedId);
      if (uploadedResult.ok) {
        return { ok: true as const, blob: uploadedResult.body as Blob, selectedDocumentId: uploadedId };
      }
    }

    return { ok: false as const, blob: null, selectedDocumentId: null as string | null };
  };

  const handleDownloadPayslip = async () => {
    if (!token || !selectedMonth) return;
    setDownloadingPayslip(true);
    setError("");
    setMessage("");
    try {
      const { matchingUploaded, fallbackSystemDocumentId } = getPayslipTargetIds();
      const result = await fetchPayslipBlob();
      if (!result.ok || !result.blob) {
        setError("Unable to download payslip for selected month.");
        return;
      }
      const blob = result.blob;
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const fileMonth = selectedMonth.replace("-", "_");
      const usedSystemPayslip = !!fallbackSystemDocumentId && result.selectedDocumentId === String(fallbackSystemDocumentId);
      link.download =
        usedSystemPayslip ? `payslip_${employeeId ?? "me"}_${fileMonth}.pdf` : (matchingUploaded?.original_filename || `payslip_${employeeId ?? "me"}_${fileMonth}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setMessage(`Payslip downloaded for ${formatMonthToDDMMYY(selectedMonth)}.`);
    } catch {
      setError("Unable to download payslip for selected month.");
    } finally {
      setDownloadingPayslip(false);
    }
  };

  const handleViewPayslip = async () => {
    if (!token || !selectedMonth) return;
    setViewingPayslip(true);
    setError("");
    setMessage("");
    try {
      const result = await fetchPayslipBlob();
      if (!result.ok || !result.blob) {
        setError("Unable to open payslip for selected month.");
        return;
      }
      const blobUrl = URL.createObjectURL(result.blob);
      window.open(blobUrl, "_blank", "noopener,noreferrer");
      window.setTimeout(() => URL.revokeObjectURL(blobUrl), 30000);
      setMessage(`Payslip opened for ${formatMonthToDDMMYY(selectedMonth)}.`);
    } catch {
      setError("Unable to open payslip for selected month.");
    } finally {
      setViewingPayslip(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (monthOptions.length === 0) return;
    setSelectedMonth((current) => {
      if (!current) return monthOptions[0];
      if (!monthOptions.includes(current)) return monthOptions[0];
      return current;
    });
  }, [monthOptions]);

  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex w-full flex-col">
        <Topbar name={name} title="Finance" />
        <div className="space-y-4 p-6">
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          {message ? <p className="text-sm text-emerald-600">{message}</p> : null}

          <Card className="border border-indigo-200/60 bg-gradient-to-br from-indigo-50 via-white to-blue-50 shadow-sm">
            <CardHeader>
              <CardTitle>Current Salary (USD)</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? <p className="text-sm text-muted-foreground">Loading salary...</p> : null}
              {!loading && (
                <div className="rounded-xl border border-indigo-200 bg-white/90 p-5">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Current Salary</p>
                  <p className="mt-1 text-3xl font-bold text-slate-900">
                    {financeProfile?.current_salary_usd != null ? `$${financeProfile.current_salary_usd.toLocaleString()}` : "-"}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border border-slate-200/80 shadow-sm">
            <CardHeader>
              <CardTitle>Bank Info</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? <p className="text-sm text-muted-foreground">Loading bank info...</p> : null}
              {!loading && (
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-lg border border-slate-200 bg-gradient-to-r from-white to-slate-50 p-3 text-sm"><span className="font-medium text-slate-700">Bank Name:</span> {financeProfile?.bank_name || "-"}</div>
                  <div className="rounded-lg border border-slate-200 bg-gradient-to-r from-white to-slate-50 p-3 text-sm"><span className="font-medium text-slate-700">Account Number:</span> {financeProfile?.bank_account_number || "-"}</div>
                  <div className="rounded-lg border border-slate-200 bg-gradient-to-r from-white to-slate-50 p-3 text-sm"><span className="font-medium text-slate-700">Account Name:</span> {financeProfile?.bank_account_name || "-"}</div>
                  <div className="rounded-lg border border-slate-200 bg-gradient-to-r from-white to-slate-50 p-3 text-sm"><span className="font-medium text-slate-700">Branch:</span> {financeProfile?.bank_branch || "-"}</div>
                  <div className="rounded-lg border border-slate-200 bg-gradient-to-r from-white to-slate-50 p-3 text-sm"><span className="font-medium text-slate-700">IFSC:</span> {financeProfile?.bank_ifsc || "-"}</div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border border-slate-200/80 shadow-sm">
            <CardHeader>
              <CardTitle>PAN Card Details</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? <p className="text-sm text-muted-foreground">Loading PAN details...</p> : null}
              {!loading && (
                <div className="grid gap-3 md:grid-cols-3">
                  <div className="rounded-lg border border-amber-200 bg-gradient-to-r from-amber-50 to-white p-3 text-sm"><span className="font-medium text-slate-700">Permanent Account Number:</span> {statutory?.pan || financeProfile?.pan_number || "-"}</div>
                  <div className="rounded-lg border border-amber-200 bg-gradient-to-r from-amber-50 to-white p-3 text-sm"><span className="font-medium text-slate-700">Name:</span> {financeProfile?.pan_name || "-"}</div>
                  <div className="rounded-lg border border-amber-200 bg-gradient-to-r from-amber-50 to-white p-3 text-sm"><span className="font-medium text-slate-700">DOB:</span> {formatDateDDMMYY(financeProfile?.pan_dob)}</div>
                </div>
              )}
              {!loading && (
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div className="rounded-lg border border-amber-200 bg-gradient-to-r from-amber-50 to-white p-3 text-sm"><span className="font-medium text-slate-700">PF UAN:</span> {statutory?.pf_uan || "-"}</div>
                  <div className="rounded-lg border border-amber-200 bg-gradient-to-r from-amber-50 to-white p-3 text-sm"><span className="font-medium text-slate-700">ESI Number:</span> {statutory?.esi_no || "-"}</div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border border-slate-200/80 shadow-sm">
            <CardHeader>
              <CardTitle>Payroll Summary</CardTitle>
            </CardHeader>
            <CardContent>
              {!loading && payroll.length > 0 ? (
                <div className="mb-4 flex flex-col gap-2 rounded-lg border border-border p-3 md:flex-row md:items-center">
                  <select
                    className="h-10 min-w-64 rounded-md border border-border bg-white px-3 text-sm"
                    value={selectedMonth}
                    onChange={(e) => setSelectedMonth(e.target.value)}
                  >
                    {monthOptions.map((month) => (
                      <option key={month} value={month}>
                        {formatMonthToDDMMYY(month)}
                      </option>
                    ))}
                  </select>
                  <div className="flex h-10 items-center gap-2 text-sm font-normal">
                    <button
                      type="button"
                      onClick={handleViewPayslip}
                      disabled={!selectedMonth || viewingPayslip || downloadingPayslip}
                      className="text-indigo-600 underline-offset-4 hover:text-indigo-700 hover:underline disabled:cursor-not-allowed disabled:text-indigo-300 disabled:no-underline"
                    >
                      {viewingPayslip ? "Opening..." : "View Payslip"}
                    </button>
                    <span className="text-slate-400">|</span>
                    <button
                      type="button"
                      onClick={handleDownloadPayslip}
                      disabled={!selectedMonth || downloadingPayslip || viewingPayslip}
                      className="text-indigo-600 underline-offset-4 hover:text-indigo-700 hover:underline disabled:cursor-not-allowed disabled:text-indigo-300 disabled:no-underline"
                    >
                      {downloadingPayslip ? "Downloading..." : "Download Payslip"}
                    </button>
                  </div>
                </div>
              ) : null}
              {loading ? <p className="text-sm text-muted-foreground">Loading payroll records...</p> : null}
              {!loading && payroll.length === 0 ? <p className="text-sm text-muted-foreground">No payroll records available.</p> : null}
              {!loading && monthOptions.length > 0 ? (
                <p className="text-sm text-muted-foreground">
                  Select a month and click <span className="font-medium text-slate-700">View Payslip</span> or <span className="font-medium text-slate-700">Download Payslip</span>.
                </p>
              ) : null}
              {!loading && monthOptions.length > 0 ? (
                <p className="text-xs text-muted-foreground">PDF password: DOB in DD-MM-YY format.</p>
              ) : null}
              {!loading && monthOptions.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No payroll months available yet.
                </p>
              ) : null}
              {!loading && monthOptions.length > 0 && payslipDocs.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Payroll months are listed. Payslip download will work after admin/manager uploads the file for that month.
                </p>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
