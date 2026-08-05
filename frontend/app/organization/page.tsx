"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { OrgNode, fetchOrgTree, fetchProfile } from "@/lib/api";

function TreeNode({ node, depth = 0 }: { node: OrgNode; depth?: number }) {
  return (
    <div className="space-y-2">
      <div className="rounded border border-border p-2" style={{ marginLeft: depth * 16 }}>
        <p className="text-sm font-medium text-slate-900">{node.name}</p>
        <p className="text-xs text-muted-foreground">{node.role}</p>
      </div>
      {node.children.map((child) => (
        <TreeNode key={child.id} node={child} depth={depth + 1} />
      ))}
    </div>
  );
}

export default function OrganizationPage() {
  const [name, setName] = useState("User");
  const [tree, setTree] = useState<OrgNode[]>([]);
  const [loading, setLoading] = useState(true);
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
      const [profileResult, orgResult] = await Promise.all([fetchProfile(token), fetchOrgTree(token)]);
      if (profileResult.status === 401 || orgResult.status === 401) return clearAuthAndRedirect();
      if (profileResult.ok && "success" in profileResult.body && profileResult.body.success) {
        setName(profileResult.body.data.name);
      }
      if (!orgResult.ok || !("success" in orgResult.body) || !orgResult.body.success) {
        setError("Failed to load organization tree");
        return;
      }
      setTree(orgResult.body.data.items);
    } catch {
      setError("Failed to fetch organization tree");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex w-full flex-col">
        <Topbar name={name} title="Organization" />
        <div className="space-y-4 p-6">
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          <Card>
            <CardHeader>
              <CardTitle>Org Tree</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? <p className="text-sm text-muted-foreground">Loading organization tree...</p> : null}
              {!loading && tree.length === 0 ? <p className="text-sm text-muted-foreground">No hierarchy data available.</p> : null}
              <div className="space-y-2">
                {tree.map((node) => (
                  <TreeNode key={node.id} node={node} />
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
