"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { downloadHRPolicyDocument, fetchHRPolicies, fetchProfile, HRPolicy, uploadHRPolicyDocument } from "@/lib/api";
import { formatDateDDMMYY } from "@/lib/date";

export default function HRPoliciesPage() {
  const [name, setName] = useState("User");
  const [role, setRole] = useState("EMPLOYEE");
  const [items, setItems] = useState<HRPolicy[]>([]);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("GENERAL");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [downloadingPolicyId, setDownloadingPolicyId] = useState<number | null>(null);
  const [viewingPolicyId, setViewingPolicyId] = useState<number | null>(null);
  const [searchText, setSearchText] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const router = useRouter();
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

  const loadData = async () => {
    if (!token) {
      clearAuthAndRedirect();
      return;
    }
    setLoading(true);
    setError("");
    try {
      const [profileResult, policiesResult] = await Promise.all([fetchProfile(token), fetchHRPolicies(token, { limit: 100, offset: 0 })]);
      if (profileResult.status === 401 || policiesResult.status === 401) {
        clearAuthAndRedirect();
        return;
      }
      if (profileResult.ok && "success" in profileResult.body && profileResult.body.success) {
        setName(profileResult.body.data.name);
        setRole(profileResult.body.data.role);
      }
      if (!policiesResult.ok || !("success" in policiesResult.body) || !policiesResult.body.success) {
        setError("Failed to load HR policies");
        return;
      }
      setItems(policiesResult.body.data.items || []);
    } catch {
      setError("Failed to load HR policies");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const onUpload = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token || !file) return;
    setUploading(true);
    setError("");
    setMessage("");
    try {
      const result = await uploadHRPolicyDocument(token, {
        title: title.trim(),
        category: category.trim(),
        file,
      });
      if (!result.ok || !("success" in result.body) || !result.body.success) {
        setError("Upload failed. Use .txt, .md, or .pdf files (max 2 MB).");
        return;
      }
      setTitle("");
      setCategory("GENERAL");
      setFile(null);
      setMessage("Policy file saved to storage and metadata saved in DB.");
      await loadData();
    } finally {
      setUploading(false);
    }
  };

  const canUpload = role === "ADMIN" || role === "MANAGER";

  const sortedItems = useMemo(() => {
    return [...items].sort((a, b) => {
      const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
      const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
      return bTime - aTime;
    });
  }, [items]);

  const filteredItems = useMemo(() => {
    const needle = searchText.trim().toLowerCase();
    if (!needle) return sortedItems;
    return sortedItems.filter((item) => {
      const inTitle = item.title.toLowerCase().includes(needle);
      const inCategory = item.category.toLowerCase().includes(needle);
      const inFileName = (item.original_filename || "").toLowerCase().includes(needle);
      return inTitle || inCategory || inFileName;
    });
  }, [searchText, sortedItems]);

  const suggestionValues = useMemo(() => {
    const seen = new Set<string>();
    const values: string[] = [];
    for (const item of sortedItems) {
      const label = item.title || item.original_filename || "";
      if (!label) continue;
      if (seen.has(label)) continue;
      if (searchText && !label.toLowerCase().includes(searchText.toLowerCase())) continue;
      seen.add(label);
      values.push(label);
      if (values.length >= 8) break;
    }
    return values;
  }, [searchText, sortedItems]);

  const onDownload = async (policy: HRPolicy) => {
    if (!token) return;
    setDownloadingPolicyId(policy.id);
    setError("");
    setMessage("");
    try {
      const result = await downloadHRPolicyDocument(token, policy.id);
      if (!result.ok) {
        setError("Failed to download policy file.");
        return;
      }
      const blob = result.body as Blob;
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = policy.original_filename || `${policy.title}.bin`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(objectUrl);
      setMessage("Policy file download started.");
    } finally {
      setDownloadingPolicyId(null);
    }
  };

  const onView = async (policy: HRPolicy) => {
    if (!token) return;
    setViewingPolicyId(policy.id);
    setError("");
    setMessage("");
    try {
      const result = await downloadHRPolicyDocument(token, policy.id);
      if (!result.ok) {
        setError("Failed to open policy file.");
        return;
      }
      const blob = result.body as Blob;
      const objectUrl = URL.createObjectURL(blob);
      window.open(objectUrl, "_blank", "noopener,noreferrer");
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 30000);
    } finally {
      setViewingPolicyId(null);
    }
  };

  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex w-full flex-col">
        <Topbar name={name} title="HR Policies" />
        <div className="space-y-4 p-6">
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          {message ? <p className="text-sm text-emerald-600">{message}</p> : null}

          {canUpload ? (
            <Card>
              <CardHeader>
                <CardTitle>Upload Policy Document</CardTitle>
              </CardHeader>
              <CardContent>
                <form className="space-y-3" onSubmit={onUpload}>
                  <Input
                    placeholder="Policy title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    minLength={3}
                    maxLength={220}
                    required
                  />
                  <Input
                    placeholder="Category (e.g. LEAVE, SECURITY, BENEFITS)"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    minLength={2}
                    maxLength={60}
                    required
                  />
                  <input
                    ref={fileInputRef}
                    className="hidden"
                    type="file"
                    accept=".txt,.md,.pdf,text/plain,text/markdown,application/pdf"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  />
                  <div className="flex items-center gap-3 rounded-md border border-border px-3 py-2">
                    <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()}>
                      Choose File
                    </Button>
                    <span className="truncate text-sm text-muted-foreground">{file?.name || "No file chosen"}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">Allowed: .txt, .md, .pdf (max 2 MB).</p>
                  <Button type="submit" disabled={uploading || loading || !file}>
                    {uploading ? "Uploading..." : "Upload Policy"}
                  </Button>
                </form>
              </CardContent>
            </Card>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle>Policy Library</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-4">
                <div className="relative">
                  <Input
                    placeholder="Search policy (e.g. leave)"
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                    onFocus={() => setSearchOpen(true)}
                    onBlur={() => window.setTimeout(() => setSearchOpen(false), 120)}
                  />
                  {searchOpen && suggestionValues.length > 0 ? (
                    <div className="absolute z-20 mt-1 w-full rounded-md border border-slate-200 bg-white shadow-lg">
                      {suggestionValues.map((value) => (
                        <button
                          key={value}
                          type="button"
                          className="block w-full px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                          onMouseDown={(e) => {
                            e.preventDefault();
                            setSearchText(value);
                            setSearchOpen(false);
                          }}
                        >
                          {value}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
              {loading ? <p className="text-sm text-muted-foreground">Loading policies...</p> : null}
              {!loading && filteredItems.length === 0 ? <p className="text-sm text-muted-foreground">No policies found.</p> : null}
              <div className="space-y-3">
                {filteredItems.map((item) => (
                  <article key={item.id} className="rounded-md border border-border bg-white p-4">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="text-base font-semibold text-slate-900">{item.original_filename || item.title}</h3>
                      <span className="text-xs text-slate-600">
                        Uploaded: {formatDateDDMMYY(item.created_at || undefined)}
                      </span>
                    </div>
                    <div className="mt-3 flex items-center gap-2 text-xs font-normal">
                      <button
                        type="button"
                        onClick={() => onView(item)}
                        disabled={viewingPolicyId === item.id}
                        title={viewingPolicyId === item.id ? "Opening..." : "View policy"}
                        aria-label={viewingPolicyId === item.id ? "Opening policy" : "View policy"}
                        className="text-slate-500 transition-colors hover:text-indigo-600 disabled:cursor-not-allowed disabled:text-slate-300"
                      >
                        {viewingPolicyId === item.id ? "Opening..." : "View"}
                      </button>
                      <span className="text-slate-300">|</span>
                      <button
                        type="button"
                        onClick={() => onDownload(item)}
                        disabled={downloadingPolicyId === item.id}
                        title={downloadingPolicyId === item.id ? "Downloading..." : "Download policy"}
                        aria-label={downloadingPolicyId === item.id ? "Downloading policy" : "Download policy"}
                        className="text-slate-500 transition-colors hover:text-indigo-600 disabled:cursor-not-allowed disabled:text-slate-300"
                      >
                        {downloadingPolicyId === item.id ? "Downloading..." : "Download"}
                      </button>
                    </div>
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
