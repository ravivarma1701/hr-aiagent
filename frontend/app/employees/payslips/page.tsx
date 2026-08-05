"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Employee, fetchEmployees, fetchProfile, uploadEmployeeDocument, uploadEmployeePayslip } from "@/lib/api";

export default function EmployeePayslipsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [name, setName] = useState("User");
  const [viewerRole, setViewerRole] = useState<string>("EMPLOYEE");
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [employeeId, setEmployeeId] = useState("");
  const [documentType, setDocumentType] = useState<"PAYSLIP" | "APPOINTMENT" | "TAX" | "OTHER">("PAYSLIP");
  const [title, setTitle] = useState("");
  const [period, setPeriod] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

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
      setLoading(true);
      setError("");
      const profileResult = await fetchProfile(token);
      if (profileResult.status === 401) return clearAuthAndRedirect();
      if (!profileResult.ok || !("success" in profileResult.body) || !profileResult.body.success) {
        setError("Failed to load profile");
        setLoading(false);
        return;
      }

      const role = profileResult.body.data.role;
      setName(profileResult.body.data.name);
      setViewerRole(role);
      if (role !== "ADMIN" && role !== "MANAGER") {
        router.push("/employees");
        return;
      }

      const employeesResult = await fetchEmployees(token, { limit: 100, offset: 0 });
      if (employeesResult.status === 401) return clearAuthAndRedirect();
      if (!employeesResult.ok || !("success" in employeesResult.body) || !employeesResult.body.success) {
        setError("Failed to load employees");
        setLoading(false);
        return;
      }
      let items = employeesResult.body.data.items || [];

      const queryEmployeeId = searchParams.get("employee_id");
      if (queryEmployeeId && !items.some((emp) => String(emp.id) === queryEmployeeId)) {
        const exactResult = await fetchEmployees(token, { q: queryEmployeeId, limit: 20, offset: 0 });
        if (exactResult.ok && "success" in exactResult.body && exactResult.body.success) {
          const exactItems = exactResult.body.data.items || [];
          if (exactItems.length > 0) {
            const existing = new Set(items.map((emp) => emp.id));
            items = [...exactItems.filter((emp) => !existing.has(emp.id)), ...items];
          }
        }
      }

      setEmployees(items);

      if (queryEmployeeId && items.some((emp) => String(emp.id) === queryEmployeeId)) {
        setEmployeeId(queryEmployeeId);
      } else if (items.length > 0) {
        setEmployeeId(String(items[0].id));
      }
      setLoading(false);
    };
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    const selected = employees.find((emp) => String(emp.id) === employeeId);
    if (!selected) return;
    if (!title.trim()) {
      if (documentType === "PAYSLIP") {
        setTitle(`${selected.name} Payslip`);
      } else if (documentType === "APPOINTMENT") {
        setTitle(`${selected.name} Appointment Letter`);
      } else if (documentType === "TAX") {
        setTitle(`${selected.name} Tax Statement`);
      } else {
        setTitle(`${selected.name} Document`);
      }
    }
  }, [documentType, employeeId, employees, title]);

  useEffect(() => {
    if (period) return;
    const now = new Date();
    const previousMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    setPeriod(`${previousMonth.getFullYear()}-${String(previousMonth.getMonth() + 1).padStart(2, "0")}`);
  }, [period]);

  const handleUpload = async () => {
    if (!token || !employeeId || !file) return;
    if (!title.trim()) {
      setError("Document title is required.");
      return;
    }
    setSubmitting(true);
    setError("");
    setSuccess("");
    try {
      const result =
        documentType === "PAYSLIP"
          ? await uploadEmployeePayslip(token, Number(employeeId), {
              title: title.trim(),
              period: period || undefined,
              file,
            })
          : await uploadEmployeeDocument(token, Number(employeeId), {
              title: title.trim(),
              document_type: documentType,
              file,
            });
      if (result.status === 401) return clearAuthAndRedirect();
      if (!result.ok || !("success" in result.body) || !result.body.success) {
        setError("Failed to upload document");
        return;
      }
      setFile(null);
      setSuccess(`${documentType === "PAYSLIP" ? "Payslip" : "Document"} uploaded successfully.`);
    } catch {
      setError("Failed to upload document");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex w-full flex-col">
        <Topbar name={name} title="Employee Documents Upload" />
        <div className="space-y-4 p-6">
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          {success ? <p className="text-sm text-emerald-600">{success}</p> : null}

          <Card className="border border-indigo-200/70 bg-gradient-to-br from-indigo-50 via-white to-blue-50 shadow-sm">
            <CardHeader>
              <CardTitle>Upload Employee Document</CardTitle>
              <CardDescription>
                {viewerRole === "ADMIN" ? "Admin" : "Manager"} access. Upload payslip, appointment letter, tax statement, or other employee documents.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {loading ? (
                <p className="text-sm text-muted-foreground">Loading...</p>
              ) : (
                <>
                  <label className="space-y-1">
                    <span className="text-xs text-slate-500">Employee</span>
                    <select
                      className="h-10 w-full rounded-md border border-border bg-white px-3 py-2 text-sm"
                      value={employeeId}
                      onChange={(e) => setEmployeeId(e.target.value)}
                    >
                      {employees.map((emp) => (
                        <option key={emp.id} value={emp.id}>
                          {emp.id} - {emp.name} ({emp.email})
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="space-y-1">
                    <span className="text-xs text-slate-500">Document Type</span>
                    <select
                      className="h-10 w-full rounded-md border border-border bg-white px-3 py-2 text-sm"
                      value={documentType}
                      onChange={(e) => setDocumentType(e.target.value as "PAYSLIP" | "APPOINTMENT" | "TAX" | "OTHER")}
                    >
                      <option value="PAYSLIP">PAYSLIP</option>
                      <option value="APPOINTMENT">APPOINTMENT</option>
                      <option value="TAX">TAX</option>
                      <option value="OTHER">OTHER</option>
                    </select>
                  </label>
                  <div className="grid gap-4 md:grid-cols-2">
                    <label className="space-y-1">
                      <span className="text-xs text-slate-500">Document Title</span>
                      <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Employee Document" />
                    </label>
                    {documentType === "PAYSLIP" ? (
                      <label className="space-y-1">
                        <span className="text-xs text-slate-500">Period</span>
                        <Input type="month" value={period} onChange={(e) => setPeriod(e.target.value)} />
                      </label>
                    ) : (
                      <div />
                    )}
                  </div>
                  <label className="space-y-1">
                    <span className="text-xs text-slate-500">Document File</span>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.txt,.md,.doc,.docx,application/pdf,text/plain,text/markdown,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                      className="hidden"
                      onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                    />
                    <div className="flex items-center gap-3">
                      <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()}>
                        Choose File
                      </Button>
                      <span className="text-sm text-muted-foreground">{file?.name || "No file chosen"}</span>
                    </div>
                  </label>
                  <div className="flex justify-end gap-2">
                    <Button type="button" variant="outline" onClick={() => router.push("/employees")}>
                      Back to Employees
                    </Button>
                    <Button type="button" onClick={handleUpload} disabled={submitting || !file || !employeeId}>
                      {submitting ? "Uploading..." : "Upload Document"}
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
