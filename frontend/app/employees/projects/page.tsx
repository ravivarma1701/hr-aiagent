"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Employee,
  EmployeeProjectItem,
  ProjectCatalogItem,
  assignEmployeeProject,
  createProjectCatalogItem,
  fetchEmployeeProjects,
  fetchEmployees,
  fetchProfile,
  fetchProjectsCatalog,
  removeEmployeeProject,
  updateProjectCatalogStatus,
} from "@/lib/api";

export default function EmployeeProjectsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [name, setName] = useState("User");
  const [viewerRole, setViewerRole] = useState("EMPLOYEE");
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState("");
  const [catalog, setCatalog] = useState<ProjectCatalogItem[]>([]);
  const [assigned, setAssigned] = useState<EmployeeProjectItem[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [roleOnProject, setRoleOnProject] = useState("");
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDescription, setNewProjectDescription] = useState("");
  const [newProjectStatus, setNewProjectStatus] = useState<"ONGOING" | "COMPLETED" | "ON_HOLD" | "PLANNED">("ONGOING");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [creatingProject, setCreatingProject] = useState(false);
  const [updatingStatusProjectId, setUpdatingStatusProjectId] = useState<number | null>(null);
  const [removingProjectId, setRemovingProjectId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "ONGOING" | "COMPLETED" | "ON_HOLD" | "PLANNED">("ALL");

  const token = useMemo(() => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("hrms_access_token");
  }, []);

  const clearAuthAndRedirect = () => {
    localStorage.removeItem("hrms_access_token");
    document.cookie = "hrms_auth=; path=/; max-age=0; samesite=lax";
    router.push("/login");
  };

  const formatProjectStatus = (status: "ONGOING" | "COMPLETED" | "ON_HOLD" | "PLANNED") =>
    status.replace("_", " ");

  const loadAssigned = async (accessToken: string, employeeId: number) => {
    const assignedResult = await fetchEmployeeProjects(accessToken, employeeId);
    if (!assignedResult.ok || !("success" in assignedResult.body) || !assignedResult.body.success) {
      setError("Failed to load assigned projects.");
      return;
    }
    setAssigned(assignedResult.body.data || []);
  };

  useEffect(() => {
    const load = async () => {
      if (!token) return clearAuthAndRedirect();
      setLoading(true);
      setError("");

      const profileResult = await fetchProfile(token);
      if (profileResult.status === 401) return clearAuthAndRedirect();
      if (!profileResult.ok || !("success" in profileResult.body) || !profileResult.body.success) {
        setError("Failed to load profile.");
        setLoading(false);
        return;
      }
      setName(profileResult.body.data.name);
      setViewerRole(profileResult.body.data.role);
      if (profileResult.body.data.role !== "ADMIN" && profileResult.body.data.role !== "MANAGER") {
        router.push("/employees");
        return;
      }

      const [employeesResult, catalogResult] = await Promise.all([
        fetchEmployees(token, { limit: 100, offset: 0 }),
        fetchProjectsCatalog(token),
      ]);
      if (employeesResult.status === 401 || catalogResult.status === 401) return clearAuthAndRedirect();
      if (!employeesResult.ok || !("success" in employeesResult.body) || !employeesResult.body.success) {
        setError("Failed to load employees.");
        setLoading(false);
        return;
      }
      if (!catalogResult.ok || !("success" in catalogResult.body) || !catalogResult.body.success) {
        setError("Failed to load projects catalog.");
        setLoading(false);
        return;
      }

      const employeeItems = employeesResult.body.data.items || [];
      setEmployees(employeeItems);
      setCatalog(catalogResult.body.data || []);

      const queryEmployeeId = searchParams.get("employee_id");
      let employeeId = employeeItems[0]?.id || 0;
      if (queryEmployeeId && employeeItems.some((emp) => String(emp.id) === queryEmployeeId)) {
        employeeId = Number(queryEmployeeId);
      }
      if (employeeId > 0) {
        setSelectedEmployeeId(String(employeeId));
        await loadAssigned(token, employeeId);
      }
      setLoading(false);
    };

    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const availableProjects = catalog.filter(
    (project) => !assigned.some((item) => item.project_id === project.id)
  );
  const filteredAssigned = assigned.filter((item) =>
    statusFilter === "ALL" ? true : item.project_status === statusFilter
  );

  useEffect(() => {
    if (!selectedProjectId && availableProjects.length > 0) {
      setSelectedProjectId(String(availableProjects[0].id));
    }
  }, [availableProjects, selectedProjectId]);

  const handleAssign = async () => {
    if (!token || !selectedEmployeeId || !selectedProjectId) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const result = await assignEmployeeProject(token, Number(selectedEmployeeId), {
        project_id: Number(selectedProjectId),
        role_on_project: roleOnProject.trim() || undefined,
      });
      if (result.status === 401) return clearAuthAndRedirect();
      if (!result.ok || !("success" in result.body) || !result.body.success) {
        setError("Failed to assign project.");
        return;
      }
      await loadAssigned(token, Number(selectedEmployeeId));
      setRoleOnProject("");
      setMessage("Project assigned.");
    } finally {
      setSaving(false);
    }
  };

  const handleCreateProject = async () => {
    if (!token) return;
    if (!newProjectName.trim()) {
      setError("Project name is required.");
      return;
    }
    setCreatingProject(true);
    setError("");
    setMessage("");
    try {
      const result = await createProjectCatalogItem(token, {
        name: newProjectName.trim(),
        description: newProjectDescription.trim() || undefined,
        status: newProjectStatus,
      });
      if (result.status === 401) return clearAuthAndRedirect();
      if (!result.ok || !("success" in result.body) || !result.body.success) {
        setError("Failed to create project.");
        return;
      }
      const catalogResult = await fetchProjectsCatalog(token);
      if (catalogResult.ok && "success" in catalogResult.body && catalogResult.body.success) {
        setCatalog(catalogResult.body.data || []);
      }
      if ("success" in result.body && result.body.success) {
        setSelectedProjectId(String(result.body.data.id));
      }
      setNewProjectName("");
      setNewProjectDescription("");
      setNewProjectStatus("ONGOING");
      setMessage("Project created.");
    } finally {
      setCreatingProject(false);
    }
  };

  const handleUpdateProjectStatus = async (
    projectId: number,
    statusValue: "ONGOING" | "COMPLETED" | "ON_HOLD" | "PLANNED"
  ) => {
    if (!token || !selectedEmployeeId) return;
    setUpdatingStatusProjectId(projectId);
    setError("");
    setMessage("");
    try {
      const result = await updateProjectCatalogStatus(token, projectId, statusValue);
      if (result.status === 401) return clearAuthAndRedirect();
      if (!result.ok || !("success" in result.body) || !result.body.success) {
        setError("Failed to update project status.");
        return;
      }

      const [catalogResult, assignedResult] = await Promise.all([
        fetchProjectsCatalog(token),
        fetchEmployeeProjects(token, Number(selectedEmployeeId)),
      ]);
      if (catalogResult.ok && "success" in catalogResult.body && catalogResult.body.success) {
        setCatalog(catalogResult.body.data || []);
      }
      if (assignedResult.ok && "success" in assignedResult.body && assignedResult.body.success) {
        setAssigned(assignedResult.body.data || []);
      }
      setMessage("Project status updated.");
    } finally {
      setUpdatingStatusProjectId(null);
    }
  };

  const handleRemove = async (projectId: number) => {
    if (!token || !selectedEmployeeId) return;
    setRemovingProjectId(projectId);
    setError("");
    setMessage("");
    try {
      const result = await removeEmployeeProject(token, Number(selectedEmployeeId), projectId);
      if (result.status === 401) return clearAuthAndRedirect();
      if (!result.ok || !("success" in result.body) || !result.body.success) {
        setError("Failed to remove project assignment.");
        return;
      }
      await loadAssigned(token, Number(selectedEmployeeId));
      setMessage("Project removed.");
    } finally {
      setRemovingProjectId(null);
    }
  };

  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex w-full flex-col">
        <Topbar name={name} title="Project Management" />
        <div className="space-y-4 p-6">
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          {message ? <p className="text-sm text-emerald-600">{message}</p> : null}

          <Card className="border border-indigo-200/70 bg-gradient-to-br from-indigo-50 via-white to-blue-50 shadow-sm">
            <CardHeader>
              <CardTitle>Manage Employee Projects</CardTitle>
              <CardDescription>
                Assign and remove project memberships in a dedicated workspace.
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
                      value={selectedEmployeeId}
                      onChange={async (e) => {
                        const id = e.target.value;
                        setSelectedEmployeeId(id);
                        if (token && id) {
                          await loadAssigned(token, Number(id));
                        }
                      }}
                    >
                      {employees.map((emp) => (
                        <option key={emp.id} value={emp.id}>
                          {emp.id} - {emp.name} ({emp.email})
                        </option>
                      ))}
                    </select>
                  </label>

                  <div className="rounded-md border border-border p-3">
                    <p className="mb-2 text-xs font-medium text-slate-700">Create Project</p>
                    <div className="grid gap-3 md:grid-cols-4">
                      <Input
                        placeholder="Project name"
                        value={newProjectName}
                        onChange={(e) => setNewProjectName(e.target.value)}
                      />
                      <Input
                        placeholder="Description (optional)"
                        value={newProjectDescription}
                        onChange={(e) => setNewProjectDescription(e.target.value)}
                      />
                      <select
                        className="h-10 rounded-md border border-border bg-white px-3 py-2 text-sm"
                        value={newProjectStatus}
                        onChange={(e) => setNewProjectStatus(e.target.value as "ONGOING" | "COMPLETED" | "ON_HOLD" | "PLANNED")}
                      >
                        <option value="ONGOING">ONGOING</option>
                        <option value="PLANNED">PLANNED</option>
                        <option value="ON_HOLD">ON_HOLD</option>
                        <option value="COMPLETED">COMPLETED</option>
                      </select>
                      <Button
                        type="button"
                        onClick={handleCreateProject}
                        disabled={creatingProject || !newProjectName.trim()}
                      >
                        {creatingProject ? "Creating..." : "Create Project"}
                      </Button>
                    </div>
                  </div>

                  <div className="rounded-md border border-border p-3">
                    <p className="mb-2 text-xs font-medium text-slate-700">Assign New Project</p>
                    <div className="grid gap-3 md:grid-cols-3">
                      <select
                        className="h-10 rounded-md border border-border bg-white px-3 py-2 text-sm"
                        value={selectedProjectId}
                        onChange={(e) => setSelectedProjectId(e.target.value)}
                      >
                        {availableProjects.length === 0 ? <option value="">No available projects</option> : null}
                        {availableProjects.map((project) => (
                          <option key={project.id} value={project.id}>
                            {project.name}
                          </option>
                        ))}
                      </select>
                      <Input
                        placeholder="Role on project (optional)"
                        value={roleOnProject}
                        onChange={(e) => setRoleOnProject(e.target.value)}
                      />
                      <Button
                        type="button"
                        onClick={handleAssign}
                        disabled={saving || !selectedEmployeeId || !selectedProjectId || availableProjects.length === 0}
                      >
                        {saving ? "Assigning..." : "Assign Project"}
                      </Button>
                    </div>
                  </div>

                  <div className="rounded-md border border-border p-3">
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <p className="text-xs font-medium text-slate-700">Assigned Projects</p>
                      <select
                        className="h-8 rounded-md border border-border bg-white px-2 text-xs"
                        value={statusFilter}
                        onChange={(e) =>
                          setStatusFilter(
                            e.target.value as "ALL" | "ONGOING" | "COMPLETED" | "ON_HOLD" | "PLANNED"
                          )
                        }
                      >
                        <option value="ALL">All statuses</option>
                        <option value="ONGOING">Ongoing</option>
                        <option value="COMPLETED">Completed</option>
                        <option value="ON_HOLD">On hold</option>
                        <option value="PLANNED">Planned</option>
                      </select>
                    </div>
                    {filteredAssigned.length === 0 ? (
                      <p className="text-sm text-muted-foreground">
                        {assigned.length === 0 ? "No projects assigned yet." : "No projects match this status."}
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {filteredAssigned.map((item) => (
                          <article key={item.project_id} className="flex items-center justify-between rounded-md border border-border px-3 py-2">
                            <div>
                              <p className="text-sm font-medium text-slate-900">{item.project_name}</p>
                              <div className="mt-1 flex items-center gap-2">
                                <p className="text-xs text-muted-foreground">
                                  {item.role_on_project || "No project role specified"}
                                </p>
                                <span className="rounded-full border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700">
                                  {formatProjectStatus(item.project_status)}
                                </span>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <select
                                className="h-9 rounded-md border border-border bg-white px-2 py-1 text-xs"
                                value={item.project_status}
                                onChange={(e) =>
                                  handleUpdateProjectStatus(
                                    item.project_id,
                                    e.target.value as "ONGOING" | "COMPLETED" | "ON_HOLD" | "PLANNED"
                                  )
                                }
                                disabled={updatingStatusProjectId === item.project_id}
                              >
                                <option value="ONGOING">ONGOING</option>
                                <option value="PLANNED">PLANNED</option>
                                <option value="ON_HOLD">ON_HOLD</option>
                                <option value="COMPLETED">COMPLETED</option>
                              </select>
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                disabled={removingProjectId === item.project_id}
                                onClick={() => handleRemove(item.project_id)}
                              >
                                {removingProjectId === item.project_id ? "Removing..." : "Remove"}
                              </Button>
                            </div>
                          </article>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex justify-end">
                    <Button type="button" variant="outline" onClick={() => router.push("/employees")}>
                      Back to Employees
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
