"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Pencil } from "lucide-react";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  deactivateEmployee,
  DepartmentOption,
  Employee,
  EmployeeDetails,
  fetchDepartments,
  fetchEmployeeById,
  fetchEmployeeProfilePicture,
  fetchEmployees,
  fetchProfile,
  reactivateEmployee,
} from "@/lib/api";
import { formatDateDDMMYY } from "@/lib/date";

const roleClassMap: Record<string, string> = {
  ADMIN: "bg-red-100 text-red-700",
  MANAGER: "bg-amber-100 text-amber-700",
  EMPLOYEE: "bg-blue-100 text-blue-700",
};

export default function EmployeesPage() {
  const pageSize = 20;
  const [viewerRole, setViewerRole] = useState<string>("EMPLOYEE");
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [departments, setDepartments] = useState<DepartmentOption[]>([]);
  const [selectedEmployee, setSelectedEmployee] = useState<EmployeeDetails | null>(null);
  const [selectedEmployeePhotoUrl, setSelectedEmployeePhotoUrl] = useState("");
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [name, setName] = useState("User");
  const [location, setLocation] = useState("");
  const [activeLocation, setActiveLocation] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [activeDepartmentId, setActiveDepartmentId] = useState("");
  const [search, setSearch] = useState("");
  const [activeSearch, setActiveSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [deactivatingEmployee, setDeactivatingEmployee] = useState(false);
  const [reactivatingEmployee, setReactivatingEmployee] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();

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
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      if (first && typeof first === "object" && "msg" in first && typeof (first as { msg?: unknown }).msg === "string") {
        return (first as { msg: string }).msg;
      }
    }
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

    if (
      record.error &&
      typeof record.error === "object" &&
      typeof (record.error as Record<string, unknown>).message === "string"
    ) {
      return (record.error as Record<string, unknown>).message as string;
    }

    return fallback;
  };

  const clearAuthAndRedirect = () => {
    localStorage.removeItem("hrms_access_token");
    document.cookie = "hrms_auth=; path=/; max-age=0; samesite=lax";
    router.push("/login");
  };

  const loadData = async (params?: { loc?: string; deptId?: string; searchTerm?: string; nextOffset?: number }) => {
    if (!token) {
      clearAuthAndRedirect();
      return;
    }

    setLoading(true);
    setError("");
    setSuccess("");

    try {
      const loc = params?.loc ?? activeLocation;
      const deptId = params?.deptId ?? activeDepartmentId;
      const searchTerm = params?.searchTerm ?? activeSearch;
      const nextOffset = params?.nextOffset ?? offset;
      const profileResult = await fetchProfile(token);

      if (profileResult.status === 401) {
        clearAuthAndRedirect();
        return;
      }

      if (!profileResult.ok || !("success" in profileResult.body) || !profileResult.body.success) {
        setError("Failed to load profile");
        return;
      }

      const role = profileResult.body.data.role;
      setName(profileResult.body.data.name);
      setViewerRole(role);
      const employeeResult = await fetchEmployees(token, {
        location: loc || undefined,
        department_id: deptId ? Number(deptId) : undefined,
        q: searchTerm || undefined,
        limit: pageSize,
        offset: nextOffset,
      });
      if (employeeResult.status === 401) {
        clearAuthAndRedirect();
        return;
      }
      if (!employeeResult.ok || !("success" in employeeResult.body) || !employeeResult.body.success) {
        setError("Failed to load employees");
        return;
      }
      setEmployees(employeeResult.body.data.items || []);
      setTotal(employeeResult.body.data.meta.total || 0);
      setOffset(employeeResult.body.data.meta.offset || 0);
      setActiveLocation(loc);
      setActiveDepartmentId(deptId);
      setActiveSearch(searchTerm);
    } catch {
      setError("Failed to fetch data from API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const query = searchParams.get("q") || "";
    setSearch(query);
    setActiveSearch(query);
    loadData({ searchTerm: query, nextOffset: 0 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, searchParams]);

  useEffect(() => {
    const loadDepartments = async () => {
      if (!token) return;
      const result = await fetchDepartments(token);
      if (result.ok && "success" in result.body && result.body.success) {
        setDepartments(result.body.data || []);
      }
    };
    loadDepartments();
  }, [token]);

  const currentPage = Math.floor(offset / pageSize) + 1;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const isAdmin = viewerRole === "ADMIN";
  const canEditJobTitle = viewerRole === "ADMIN" || viewerRole === "MANAGER";

  const handleDeactivateEmployee = async (employeeId: number) => {
    if (!token) return;
    setDeactivatingEmployee(true);
    setError("");
    setSuccess("");
    try {
      const result = await deactivateEmployee(token, employeeId);
      if (result.status === 401) {
        clearAuthAndRedirect();
        return;
      }
      if (!result.ok || !("success" in result.body) || !result.body.success) {
        setError(extractErrorMessage(result.body, "Failed to deactivate employee"));
        return;
      }
      setSelectedEmployee((current) =>
        current && current.id === employeeId ? { ...current, status: "INACTIVE" } : current
      );
      setSuccess("Employee deactivated.");
      await loadData();
    } catch {
      setError("Failed to deactivate employee");
    } finally {
      setDeactivatingEmployee(false);
    }
  };

  const handleReactivateEmployee = async (employeeId: number) => {
    if (!token) return;
    setReactivatingEmployee(true);
    setError("");
    setSuccess("");
    try {
      const result = await reactivateEmployee(token, employeeId);
      if (result.status === 401) {
        clearAuthAndRedirect();
        return;
      }
      if (!result.ok || !("success" in result.body) || !result.body.success) {
        setError(extractErrorMessage(result.body, "Failed to reactivate employee"));
        return;
      }
      setSelectedEmployee((current) =>
        current && current.id === employeeId ? { ...current, status: "ACTIVE" } : current
      );
      setSuccess("Employee reactivated.");
      await loadData();
    } catch {
      setError("Failed to reactivate employee");
    } finally {
      setReactivatingEmployee(false);
    }
  };

  const loadEmployeeDetails = async (employeeId: number) => {
    if (!token) return;
    setDetailsLoading(true);
    setError("");
    try {
      const result = await fetchEmployeeById(token, employeeId);
      if (result.status === 401) {
        clearAuthAndRedirect();
        return;
      }
      if (!result.ok || !("success" in result.body) || !result.body.success) {
        setError("Failed to load employee details");
        return;
      }
      setSelectedEmployee(result.body.data);
      if (result.body.data.has_profile_photo) {
        const photoResult = await fetchEmployeeProfilePicture(token, employeeId);
        if (photoResult.ok) {
          const url = URL.createObjectURL(photoResult.body as Blob);
          setSelectedEmployeePhotoUrl((previous) => {
            if (previous) URL.revokeObjectURL(previous);
            return url;
          });
        } else {
          setSelectedEmployeePhotoUrl((previous) => {
            if (previous) URL.revokeObjectURL(previous);
            return "";
          });
        }
      } else {
        setSelectedEmployeePhotoUrl((previous) => {
          if (previous) URL.revokeObjectURL(previous);
          return "";
        });
      }
    } catch {
      setError("Failed to load employee details");
    } finally {
      setDetailsLoading(false);
    }
  };

  useEffect(() => {
    return () => {
      if (selectedEmployeePhotoUrl) URL.revokeObjectURL(selectedEmployeePhotoUrl);
    };
  }, [selectedEmployeePhotoUrl]);

  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex w-full flex-col">
        <Topbar name={name} />
        <div className="space-y-4 p-6">
          {success ? <p className="text-sm text-emerald-600">{success}</p> : null}
          <Card>
            <CardContent className="pt-6">
              {isAdmin ? (
                <div className="mb-4 flex items-center justify-between rounded-md border border-border p-3">
                  <div>
                    <p className="text-sm font-medium text-slate-900">Add New Employee</p>
                    <p className="text-xs text-muted-foreground">Open the dedicated onboarding screen for basic + finance setup.</p>
                  </div>
                  <Button type="button" onClick={() => router.push("/employees/new")}>
                    Add New Employee
                  </Button>
                </div>
              ) : null}
              <div className="flex flex-col gap-3 md:flex-row">
                <Input
                  placeholder="Search by ID, name, or email"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                <Input
                  placeholder="Filter by office location (e.g. Bengaluru)"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                />
                <select
                  className="h-10 rounded-md border border-border bg-white px-3 py-2 text-sm"
                  value={departmentId}
                  onChange={(e) => setDepartmentId(e.target.value)}
                >
                  <option value="">All departments</option>
                  {departments.map((dept) => (
                    <option key={dept.id} value={dept.id}>
                      {dept.name}
                    </option>
                  ))}
                </select>
                <Button onClick={() => loadData({ loc: location.trim(), deptId: departmentId, searchTerm: search.trim(), nextOffset: 0 })}>Apply</Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setLocation("");
                    setDepartmentId("");
                    setSearch("");
                    setActiveLocation("");
                    setActiveDepartmentId("");
                    setActiveSearch("");
                    loadData({ loc: "", deptId: "", searchTerm: "", nextOffset: 0 });
                  }}
                >
                  Reset
                </Button>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
            <Card>
              <CardContent className="pt-6">
                {loading ? <p className="text-sm text-muted-foreground">Loading employees...</p> : null}
                {error ? <p className="text-sm text-red-600">{error}</p> : null}

                {!loading && !error ? (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>ID</TableHead>
                          <TableHead>Name</TableHead>
                          <TableHead>Email</TableHead>
                          <TableHead>Role</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Joining Date</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {employees.map((employee) => (
                          <TableRow
                            key={employee.id}
                            className="cursor-pointer"
                            onClick={() => loadEmployeeDetails(employee.id)}
                          >
                            <TableCell>{employee.id}</TableCell>
                            <TableCell>{employee.name}</TableCell>
                            <TableCell>{employee.email}</TableCell>
                            <TableCell>
                              <Badge className={roleClassMap[employee.role] || "bg-slate-100 text-slate-700"}>{employee.role}</Badge>
                            </TableCell>
                            <TableCell>{employee.status}</TableCell>
                            <TableCell>{formatDateDDMMYY(employee.joining_date)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ) : null}

                {!loading && !error ? (
                  <div className="mt-4 flex items-center justify-between">
                    <p className="text-sm text-muted-foreground">
                      Page {currentPage} of {totalPages} ({total} total employees)
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={offset <= 0}
                        onClick={() => loadData({ nextOffset: Math.max(0, offset - pageSize) })}
                      >
                        Previous
                      </Button>
                      <Button
                        size="sm"
                        disabled={offset + pageSize >= total}
                        onClick={() => loadData({ nextOffset: offset + pageSize })}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <h3 className="text-base font-semibold text-slate-900">Employee Details</h3>
                {detailsLoading ? <p className="mt-3 text-sm text-muted-foreground">Loading details...</p> : null}
                {!detailsLoading && !selectedEmployee ? (
                  <p className="mt-3 text-sm text-muted-foreground">Click an employee row to view details.</p>
                ) : null}
                {!detailsLoading && selectedEmployee ? (
                  <div className="mt-4 space-y-3 text-sm">
                    <div className="flex items-center gap-4">
                      <div className="flex h-24 w-24 items-center justify-center overflow-hidden rounded-full bg-indigo-100 text-2xl font-semibold text-indigo-700">
                        {selectedEmployeePhotoUrl ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={selectedEmployeePhotoUrl} alt={selectedEmployee.name} className="h-full w-full object-cover object-center" />
                        ) : (
                          selectedEmployee.name
                            .split(" ")
                            .filter(Boolean)
                            .slice(0, 2)
                            .map((part) => part[0]?.toUpperCase())
                            .join("") || "U"
                        )}
                      </div>
                      <div>
                        <p className="font-semibold text-slate-900">{selectedEmployee.name}</p>
                        <p className="text-xs text-slate-500">{selectedEmployee.job_title || "No job title set"}</p>
                      </div>
                      {isAdmin ? (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="ml-auto"
                          onClick={() => router.push(`/employees/new?employee_id=${selectedEmployee.id}`)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                      ) : null}
                    </div>
                    <p><span className="font-medium">Email:</span> {selectedEmployee.email}</p>
                    <p><span className="font-medium">Phone:</span> {selectedEmployee.phone || "-"}</p>
                    <p><span className="font-medium">Status:</span> {selectedEmployee.status}</p>
                    <p><span className="font-medium">Office Location:</span> {selectedEmployee.location || "-"}</p>
                    <p><span className="font-medium">Department:</span> {selectedEmployee.department || "-"}</p>
                    <p><span className="font-medium">Job Title:</span> {selectedEmployee.job_title || "-"}</p>
                    <div className="grid gap-2 rounded-md border border-border bg-slate-50/60 p-3 md:grid-cols-2">
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Address</p>
                        <p className="mt-1 text-sm text-slate-900">{selectedEmployee.address || "Not provided"}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Blood Group</p>
                        <p className="mt-1 text-sm text-slate-900">{selectedEmployee.blood_type || "Not provided"}</p>
                      </div>
                    </div>
                    {canEditJobTitle ? (
                      <div className="space-y-2 rounded-md border border-border p-3">
                        <p className="text-xs font-medium text-slate-700">Projects</p>
                        <Button
                          variant="outline"
                          onClick={() =>
                            router.push(
                              selectedEmployee
                                ? `/employees/projects?employee_id=${selectedEmployee.id}`
                                : "/employees/projects"
                            )
                          }
                        >
                          Manage Projects
                        </Button>
                      </div>
                    ) : null}
                    {canEditJobTitle ? (
                      <div className="space-y-2 rounded-md border border-border p-3">
                        <p className="text-xs font-medium text-slate-700">Employee Documents</p>
                        <Button
                          variant="outline"
                          onClick={() =>
                            router.push(
                              selectedEmployee
                                ? `/employees/payslips?employee_id=${selectedEmployee.id}`
                                : "/employees/payslips"
                            )
                          }
                        >
                          Manage Documents
                        </Button>
                      </div>
                    ) : null}
                    {isAdmin ? (
                      selectedEmployee.status === "INACTIVE" ? (
                        <Button
                          variant="outline"
                          className="border-emerald-300 text-emerald-700 hover:bg-emerald-50"
                          disabled={reactivatingEmployee}
                          onClick={() => handleReactivateEmployee(selectedEmployee.id)}
                        >
                          {reactivatingEmployee ? "Reactivating..." : "Reactivate Employee"}
                        </Button>
                      ) : (
                        <Button
                          variant="outline"
                          className="border-red-300 text-red-700 hover:bg-red-50"
                          disabled={deactivatingEmployee}
                          onClick={() => handleDeactivateEmployee(selectedEmployee.id)}
                        >
                          {deactivatingEmployee ? "Deactivating..." : "Deactivate Employee"}
                        </Button>
                      )
                    ) : null}
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </div>
        </div>
      </section>
    </main>
  );
}
