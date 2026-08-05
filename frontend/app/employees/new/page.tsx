"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DatePicker } from "@/components/ui/date-picker";
import { Input } from "@/components/ui/input";
import {
  DepartmentOption,
  EmployeeCreatePayload,
  EmployeeUpdatePayload,
  createEmployee,
  fetchDepartments,
  fetchEmployeeById,
  fetchProfile,
  updateEmployee,
} from "@/lib/api";

export default function NewEmployeePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const rawEmployeeId = searchParams.get("employee_id");
  const parsedEmployeeId = rawEmployeeId ? Number(rawEmployeeId) : null;
  const editingEmployeeId = parsedEmployeeId && Number.isFinite(parsedEmployeeId) ? parsedEmployeeId : null;
  const isEditMode = editingEmployeeId !== null;
  const [token, setToken] = useState<string | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [name, setName] = useState("User");
  const [departments, setDepartments] = useState<DepartmentOption[]>([]);
  const [createStep, setCreateStep] = useState<1 | 2>(1);
  const [initializingForm, setInitializingForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [createForm, setCreateForm] = useState({
    name: "",
    email: "",
    password: "",
    joiningDate: "",
    dateOfBirth: "",
    jobTitle: "",
    countryCode: "+91",
    phone: "",
    occupancy: "",
    role: "EMPLOYEE",
    departmentId: "",
    currentSalaryUsd: "",
    bankName: "",
    bankAccountNumber: "",
    bankAccountName: "",
    bankBranch: "",
    bankIfsc: "",
    panNumber: "",
    panName: "",
    panDob: "",
    pfUan: "",
    esiNo: "",
  });
  const stepCompletion = createStep === 1 ? 50 : 100;
  const countryCodes = [
    { label: "IN (+91)", value: "+91" },
    { label: "US (+1)", value: "+1" },
    { label: "UK (+44)", value: "+44" },
    { label: "AE (+971)", value: "+971" },
    { label: "SG (+65)", value: "+65" },
    { label: "AU (+61)", value: "+61" },
    { label: "DE (+49)", value: "+49" },
  ];

  const clearAuthAndRedirect = () => {
    localStorage.removeItem("hrms_access_token");
    document.cookie = "hrms_auth=; path=/; max-age=0; samesite=lax";
    router.push("/login");
  };

  useEffect(() => {
    if (typeof window === "undefined") return;
    setToken(localStorage.getItem("hrms_access_token"));
    setAuthReady(true);
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
    return fallback;
  };

  useEffect(() => {
    const load = async () => {
      if (!authReady) return;
      if (!token) {
        router.push("/login");
        return;
      }
      const profileResult = await fetchProfile(token);
      if (profileResult.status === 401) return clearAuthAndRedirect();
      if (!profileResult.ok || !("success" in profileResult.body) || !profileResult.body.success) {
        setError("Failed to load profile");
        return;
      }
      setName(profileResult.body.data.name);
      if (profileResult.body.data.role !== "ADMIN") {
        router.push("/employees");
        return;
      }
      const departmentsResult = await fetchDepartments(token);
      if (departmentsResult.ok && "success" in departmentsResult.body && departmentsResult.body.success) {
        setDepartments(departmentsResult.body.data || []);
      }

      if (isEditMode && editingEmployeeId) {
        setInitializingForm(true);
        const employeeResult = await fetchEmployeeById(token, editingEmployeeId);
        if (employeeResult.status === 401) {
          setInitializingForm(false);
          return clearAuthAndRedirect();
        }
        if (!employeeResult.ok || !("success" in employeeResult.body) || !employeeResult.body.success) {
          setError("Failed to load employee details");
          setInitializingForm(false);
          return;
        }

        const employee = employeeResult.body.data;
        const parsedCountryCode =
          employee.phone && employee.phone.startsWith("+")
            ? (employee.phone.match(/^\+\d{1,3}/)?.[0] ?? "+91")
            : "+91";
        const localPhone =
          employee.phone && employee.phone.startsWith(parsedCountryCode)
            ? employee.phone.slice(parsedCountryCode.length)
            : employee.phone || "";

        setCreateForm((current) => ({
          ...current,
          name: employee.name || "",
          email: employee.email || "",
          password: "",
          joiningDate: employee.joining_date || "",
          dateOfBirth: employee.date_of_birth || "",
          jobTitle: employee.job_title || "",
          countryCode: parsedCountryCode,
          phone: localPhone,
          occupancy: employee.occupancy || "",
          role: employee.role || "EMPLOYEE",
          departmentId: employee.department_id != null ? String(employee.department_id) : "",
          currentSalaryUsd: employee.current_salary_usd != null ? String(employee.current_salary_usd) : "",
          bankName: employee.bank_name || "",
          bankAccountNumber: employee.bank_account_number || "",
          bankAccountName: employee.bank_account_name || "",
          bankBranch: employee.bank_branch || "",
          bankIfsc: employee.bank_ifsc || "",
          panNumber: employee.pan_number || "",
          panName: employee.pan_name || "",
          panDob: employee.pan_dob || "",
          pfUan: employee.pf_uan || "",
          esiNo: employee.esi_no || "",
        }));
        setInitializingForm(false);
      }
    };
    load();
  }, [authReady, token, router, isEditMode, editingEmployeeId]);

  const validateStepOne = () => {
    if (
      !createForm.name.trim() ||
      !createForm.email.trim() ||
      (!isEditMode && !createForm.password) ||
      !createForm.joiningDate ||
      !createForm.dateOfBirth ||
      !createForm.jobTitle.trim() ||
      !createForm.phone.trim() ||
      !createForm.occupancy.trim()
    ) {
      setError("Name, email, joining date, date of birth, job title, phone, and employment type are required.");
      return false;
    }
    if (!isEditMode && createForm.password.length < 8) {
      setError("Temporary password must be at least 8 characters.");
      return false;
    }
    const localPhoneDigits = createForm.phone.replace(/[^\d]/g, "");
    if (localPhoneDigits.length < 6) {
      setError("Phone number must be at least 6 digits.");
      return false;
    }
    return true;
  };

  const validateStepTwo = () => {
    if (
      !createForm.currentSalaryUsd.trim() ||
      !createForm.bankName.trim() ||
      !createForm.bankAccountNumber.trim() ||
      !createForm.bankAccountName.trim() ||
      !createForm.bankBranch.trim() ||
      !createForm.bankIfsc.trim() ||
      !createForm.panNumber.trim() ||
      !createForm.panName.trim() ||
      !createForm.panDob ||
      !createForm.pfUan.trim() ||
      !createForm.esiNo.trim()
    ) {
      setError("All finance and statutory fields are required.");
      return false;
    }
    const salary = Number(createForm.currentSalaryUsd);
    if (!Number.isFinite(salary) || salary < 0) {
      setError("Salary must be a valid positive number.");
      return false;
    }
    if (createForm.panNumber.trim().length < 8) {
      setError("PAN number must be at least 8 characters.");
      return false;
    }
    if (createForm.pfUan.trim().length < 6 || createForm.esiNo.trim().length < 6) {
      setError("PF UAN and ESI Number must be at least 6 characters.");
      return false;
    }
    return true;
  };

  const handleCreateEmployee = async () => {
    if (!token) return;
    setError("");
    setSuccess("");
    if (!validateStepOne()) {
      setCreateStep(1);
      return;
    }
    if (!validateStepTwo()) {
      setCreateStep(2);
      return;
    }

    setSubmitting(true);
    try {
      const commonPayload: EmployeeUpdatePayload = {
        name: createForm.name.trim(),
        email: createForm.email.trim(),
        joining_date: createForm.joiningDate,
        date_of_birth: createForm.dateOfBirth,
        job_title: createForm.jobTitle.trim(),
        phone: `${createForm.countryCode}${createForm.phone.replace(/[^\d]/g, "")}`,
        occupancy: createForm.occupancy.trim(),
        role: createForm.role as "ADMIN" | "MANAGER" | "EMPLOYEE",
        current_salary_usd: Number(createForm.currentSalaryUsd),
        bank_name: createForm.bankName.trim(),
        bank_account_number: createForm.bankAccountNumber.trim(),
        bank_account_name: createForm.bankAccountName.trim(),
        bank_branch: createForm.bankBranch.trim(),
        bank_ifsc: createForm.bankIfsc.trim().toUpperCase(),
        pan_number: createForm.panNumber.trim().toUpperCase(),
        pan_name: createForm.panName.trim(),
        pan_dob: createForm.panDob,
        pf_uan: createForm.pfUan.trim(),
        esi_no: createForm.esiNo.trim(),
      };
      if (createForm.departmentId) commonPayload.department_id = Number(createForm.departmentId);

      let result:
        | Awaited<ReturnType<typeof createEmployee>>
        | Awaited<ReturnType<typeof updateEmployee>>;
      if (isEditMode && editingEmployeeId) {
        if (createForm.password.trim()) {
          commonPayload.password = createForm.password.trim();
        }
        result = await updateEmployee(token, editingEmployeeId, commonPayload);
      } else {
        const payload: EmployeeCreatePayload = {
          ...(commonPayload as EmployeeCreatePayload),
          password: createForm.password,
        };
        result = await createEmployee(token, payload);
      }
      if (result.status === 401) return clearAuthAndRedirect();
      if (!result.ok || !("success" in result.body) || !result.body.success) {
        setError(extractErrorMessage(result.body, isEditMode ? "Failed to update employee" : "Failed to create employee"));
        return;
      }

      setSuccess(isEditMode ? "Employee updated successfully." : "Employee created successfully.");
      router.push("/employees");
    } catch {
      setError(isEditMode ? "Failed to update employee" : "Failed to create employee");
    } finally {
      setSubmitting(false);
    }
  };

  const updateCreateField = (field: keyof typeof createForm, value: string) => {
    setCreateForm((current) => ({ ...current, [field]: value }));
  };

  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex w-full flex-col">
        <Topbar name={name} title={isEditMode ? "Edit Employee" : "Add Employee"} />
        <div className="space-y-4 p-6">
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          {success ? <p className="text-sm text-emerald-600">{success}</p> : null}
          {initializingForm ? <p className="text-sm text-muted-foreground">Loading employee data...</p> : null}

          <Card className="border border-indigo-200/70 bg-gradient-to-br from-indigo-50 via-white to-blue-50 shadow-sm">
            <CardHeader>
              <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
                <div>
                  <CardTitle>{isEditMode ? "Edit Employee Profile" : "New Employee Onboarding"}</CardTitle>
                  <CardDescription>
                    Step {createStep} of 2. Capture profile details first, then finance and statutory setup.
                  </CardDescription>
                </div>
                <div className="text-sm font-medium text-indigo-700">{stepCompletion}% Complete</div>
              </div>
              <div className="h-2 rounded-full bg-indigo-100">
                <div className="h-2 rounded-full bg-indigo-600 transition-all duration-300" style={{ width: `${stepCompletion}%` }} />
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-2 md:grid-cols-2">
                <Button type="button" variant={createStep === 1 ? "default" : "outline"} className="justify-start" onClick={() => setCreateStep(1)}>
                  Basic Info
                </Button>
                <Button type="button" variant={createStep === 2 ? "default" : "outline"} className="justify-start" onClick={() => setCreateStep(2)}>
                  Finance & Statutory
                </Button>
              </div>

              {createStep === 1 ? (
                  <div className="rounded-xl border border-indigo-200 bg-white p-4 shadow-sm">
                  <p className="mb-4 text-sm font-semibold text-slate-900">Profile Basics</p>
                  <div className="grid gap-4 md:grid-cols-2">
                    <label className="space-y-1">
                      <span className="text-xs text-slate-500">Full Name</span>
                      <Input placeholder="e.g. John Miller" value={createForm.name} onChange={(e) => updateCreateField("name", e.target.value)} />
                    </label>
                    <label className="space-y-1">
                      <span className="text-xs text-slate-500">Work Email</span>
                      <Input placeholder="e.g. john@company.com" type="email" value={createForm.email} onChange={(e) => updateCreateField("email", e.target.value)} />
                    </label>
                    <label className="space-y-1">
                      <span className="text-xs text-slate-500">Temporary Password</span>
                      <Input
                        placeholder={isEditMode ? "Leave blank to keep current password" : "Minimum 8 characters"}
                        type="password"
                        value={createForm.password}
                        onChange={(e) => updateCreateField("password", e.target.value)}
                      />
                    </label>
                    <label className="space-y-1">
                      <span className="text-xs text-slate-500">Date of Joining</span>
                      <DatePicker value={createForm.joiningDate} onChange={(value) => updateCreateField("joiningDate", value)} placeholder="Select joining date" />
                    </label>
                    <label className="space-y-1">
                      <span className="text-xs text-slate-500">Date of Birth</span>
                      <DatePicker value={createForm.dateOfBirth} onChange={(value) => updateCreateField("dateOfBirth", value)} placeholder="Select date of birth" />
                    </label>
                    <label className="space-y-1">
                      <span className="text-xs text-slate-500">Job Title</span>
                      <Input placeholder="e.g. Software Engineer" value={createForm.jobTitle} onChange={(e) => updateCreateField("jobTitle", e.target.value)} />
                    </label>
                    <label className="space-y-1">
                      <span className="text-xs text-slate-500">Phone Number</span>
                      <div className="flex gap-2">
                        <select
                          className="h-10 min-w-28 rounded-md border border-border bg-white px-2 py-2 text-sm"
                          value={createForm.countryCode}
                          onChange={(e) => updateCreateField("countryCode", e.target.value)}
                        >
                          {countryCodes.map((code) => (
                            <option key={code.value} value={code.value}>
                              {code.label}
                            </option>
                          ))}
                        </select>
                        <Input
                          placeholder="Local number"
                          value={createForm.phone}
                          onChange={(e) => updateCreateField("phone", e.target.value)}
                        />
                      </div>
                    </label>
                    <label className="space-y-1">
                      <span className="text-xs text-slate-500">Employment Type</span>
                      <select className="h-10 w-full rounded-md border border-border bg-white px-3 py-2 text-sm" value={createForm.occupancy} onChange={(e) => updateCreateField("occupancy", e.target.value)}>
                        <option value="">Select employment type</option>
                        <option value="Full-Time">Full-Time</option>
                        <option value="Part-Time">Part-Time</option>
                        <option value="Contract">Contract</option>
                        <option value="Intern">Intern</option>
                      </select>
                    </label>
                    <label className="space-y-1">
                      <span className="text-xs text-slate-500">Role</span>
                      <select className="h-10 w-full rounded-md border border-border bg-white px-3 py-2 text-sm" value={createForm.role} onChange={(e) => updateCreateField("role", e.target.value)}>
                        <option value="EMPLOYEE">EMPLOYEE</option>
                        <option value="MANAGER">MANAGER</option>
                        <option value="ADMIN">ADMIN</option>
                      </select>
                    </label>
                    <label className="space-y-1">
                      <span className="text-xs text-slate-500">Department</span>
                      <select className="h-10 w-full rounded-md border border-border bg-white px-3 py-2 text-sm" value={createForm.departmentId} onChange={(e) => updateCreateField("departmentId", e.target.value)}>
                        <option value="">No department</option>
                        {departments.map((dept) => (
                          <option key={dept.id} value={dept.id}>{dept.name}</option>
                        ))}
                      </select>
                    </label>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="rounded-xl border border-indigo-200 bg-white p-4 shadow-sm">
                    <p className="mb-4 text-sm font-semibold text-slate-900">Compensation & Banking</p>
                    <div className="grid gap-4 md:grid-cols-2">
                      <label className="space-y-1">
                        <span className="text-xs text-slate-500">Current Salary (USD)</span>
                        <Input placeholder="e.g. 65000" type="number" min="0" value={createForm.currentSalaryUsd} onChange={(e) => updateCreateField("currentSalaryUsd", e.target.value)} />
                      </label>
                      <label className="space-y-1">
                        <span className="text-xs text-slate-500">Bank Name</span>
                        <Input placeholder="e.g. HDFC Bank" value={createForm.bankName} onChange={(e) => updateCreateField("bankName", e.target.value)} />
                      </label>
                      <label className="space-y-1">
                        <span className="text-xs text-slate-500">Bank Account Number</span>
                        <Input placeholder="e.g. 123456789012" value={createForm.bankAccountNumber} onChange={(e) => updateCreateField("bankAccountNumber", e.target.value)} />
                      </label>
                      <label className="space-y-1">
                        <span className="text-xs text-slate-500">Bank Account Name</span>
                        <Input placeholder="As per bank records" value={createForm.bankAccountName} onChange={(e) => updateCreateField("bankAccountName", e.target.value)} />
                      </label>
                      <label className="space-y-1">
                        <span className="text-xs text-slate-500">Bank Branch</span>
                        <Input placeholder="e.g. City Center" value={createForm.bankBranch} onChange={(e) => updateCreateField("bankBranch", e.target.value)} />
                      </label>
                      <label className="space-y-1">
                        <span className="text-xs text-slate-500">IFSC</span>
                        <Input placeholder="e.g. HDFC0001234" value={createForm.bankIfsc} onChange={(e) => updateCreateField("bankIfsc", e.target.value)} />
                      </label>
                    </div>
                  </div>
                  <div className="rounded-xl border border-amber-200 bg-amber-50/40 p-4 shadow-sm">
                    <p className="mb-4 text-sm font-semibold text-slate-900">Statutory Details</p>
                    <div className="grid gap-4 md:grid-cols-2">
                      <label className="space-y-1">
                        <span className="text-xs text-slate-500">PAN Number</span>
                        <Input placeholder="e.g. ABCDE1234F" value={createForm.panNumber} onChange={(e) => updateCreateField("panNumber", e.target.value)} />
                      </label>
                      <label className="space-y-1">
                        <span className="text-xs text-slate-500">PAN Name</span>
                        <Input placeholder="As per PAN card" value={createForm.panName} onChange={(e) => updateCreateField("panName", e.target.value)} />
                      </label>
                      <label className="space-y-1">
                        <span className="text-xs text-slate-500">PAN Date of Birth</span>
                        <DatePicker value={createForm.panDob} onChange={(value) => updateCreateField("panDob", value)} placeholder="Select PAN DOB" />
                      </label>
                      <label className="space-y-1">
                        <span className="text-xs text-slate-500">PF UAN</span>
                        <Input placeholder="Provident Fund UAN" value={createForm.pfUan} onChange={(e) => updateCreateField("pfUan", e.target.value)} />
                      </label>
                      <label className="space-y-1 md:col-span-2">
                        <span className="text-xs text-slate-500">ESI Number</span>
                        <Input placeholder="Employee State Insurance Number" value={createForm.esiNo} onChange={(e) => updateCreateField("esiNo", e.target.value)} />
                      </label>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex flex-col gap-3 rounded-lg border border-border bg-white p-3 md:flex-row md:items-center md:justify-between">
                <p className="text-xs text-muted-foreground">
                  {createStep === 1
                    ? "Complete basic profile fields to continue."
                    : isEditMode
                      ? "Review all financial and statutory fields before saving changes."
                      : "Review all financial and statutory fields before creating the employee."}
                </p>
                <Button type="button" variant="outline" onClick={() => router.push("/employees")}>
                  Cancel
                </Button>
                <div className="flex gap-2">
                  {createStep === 2 ? (
                    <Button type="button" variant="outline" onClick={() => setCreateStep(1)}>
                      Back
                    </Button>
                  ) : null}
                  {createStep === 1 ? (
                    <Button
                      type="button"
                      onClick={() => {
                        setError("");
                        if (validateStepOne()) setCreateStep(2);
                      }}
                    >
                      Continue
                    </Button>
                  ) : (
                    <Button type="button" onClick={handleCreateEmployee} disabled={submitting}>
                      {submitting ? (isEditMode ? "Saving..." : "Creating...") : (isEditMode ? "Save Changes" : "Create Employee")}
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
