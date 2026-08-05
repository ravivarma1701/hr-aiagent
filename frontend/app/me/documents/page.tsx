"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { deleteMyDocument, downloadMyDocument, EmployeeDocument, fetchMyDocuments, fetchProfile, uploadMyDocument } from "@/lib/api";
import { formatDateDDMMYY } from "@/lib/date";

export default function MyDocumentsPage() {
  const [name, setName] = useState("User");
  const [items, setItems] = useState<EmployeeDocument[]>([]);
  const [title, setTitle] = useState("");
  const [docType, setDocType] = useState<"APPOINTMENT" | "PAYSLIP" | "TAX" | "OTHER">("OTHER");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [searchText, setSearchText] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [viewingId, setViewingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const token = useMemo(() => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("hrms_access_token");
  }, []);

  useEffect(() => {
    const load = async () => {
      if (!token) {
        router.push("/login");
        return;
      }
      setLoading(true);
      setError("");
      try {
        const [profileResult, docsResult] = await Promise.all([fetchProfile(token), fetchMyDocuments(token)]);
        if (profileResult.status === 401 || docsResult.status === 401) {
          localStorage.removeItem("hrms_access_token");
          document.cookie = "hrms_auth=; path=/; max-age=0; samesite=lax";
          router.push("/login");
          return;
        }
        if (profileResult.ok && "success" in profileResult.body && profileResult.body.success) {
          setName(profileResult.body.data.name);
        }
        if (!docsResult.ok || !("success" in docsResult.body) || !docsResult.body.success) {
          setError("Unable to load documents.");
          return;
        }
        setItems(docsResult.body.data);
      } catch {
        setError("Unable to load documents.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [router, token]);

  const reloadDocuments = async () => {
    if (!token) return;
    const docsResult = await fetchMyDocuments(token);
    if (docsResult.ok && "success" in docsResult.body && docsResult.body.success) {
      setItems(docsResult.body.data);
    }
  };

  const sortedItems = useMemo(() => {
    return [...items].sort((a, b) => {
      const aDate = a.issued_on || "";
      const bDate = b.issued_on || "";
      return bDate.localeCompare(aDate);
    });
  }, [items]);

  const filteredItems = useMemo(() => {
    const needle = searchText.trim().toLowerCase();
    if (!needle) return sortedItems;
    return sortedItems.filter((doc) => {
      const inTitle = doc.title.toLowerCase().includes(needle);
      const inType = doc.type.toLowerCase().includes(needle);
      return inTitle || inType;
    });
  }, [searchText, sortedItems]);

  const suggestionValues = useMemo(() => {
    const seen = new Set<string>();
    const values: string[] = [];
    for (const doc of sortedItems) {
      const label = doc.title;
      if (!label || seen.has(label)) continue;
      if (searchText && !label.toLowerCase().includes(searchText.toLowerCase())) continue;
      seen.add(label);
      values.push(label);
      if (values.length >= 8) break;
    }
    return values;
  }, [searchText, sortedItems]);

  const onUpload = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token || !selectedFile) return;

    setSubmitting(true);
    setError("");
    setMessage("");
    const result = await uploadMyDocument(token, { title: title.trim(), document_type: docType, file: selectedFile });
    if (!result.ok || !("success" in result.body) || !result.body.success) {
      setError("Unable to upload document.");
      setSubmitting(false);
      return;
    }

    setTitle("");
    setDocType("OTHER");
    setSelectedFile(null);
    await reloadDocuments();
    setMessage("Document uploaded.");
    setSubmitting(false);
  };

  const onDownload = async (doc: EmployeeDocument) => {
    if (!token) return;
    setDownloadingId(doc.id);
    setError("");
    setMessage("");
    const result = await downloadMyDocument(token, doc.id);
    if (!result.ok) {
      setError("Unable to download document.");
      setDownloadingId(null);
      return;
    }
    const blob = result.body as Blob;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = doc.original_filename || `${doc.title}.bin`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setMessage("Document downloaded.");
    setDownloadingId(null);
  };

  const onView = async (doc: EmployeeDocument) => {
    if (!token) return;
    setViewingId(doc.id);
    setError("");
    setMessage("");
    const result = await downloadMyDocument(token, doc.id);
    if (!result.ok) {
      setError("Unable to open document.");
      setViewingId(null);
      return;
    }
    const blob = result.body as Blob;
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank", "noopener,noreferrer");
    window.setTimeout(() => URL.revokeObjectURL(url), 30000);
    setMessage("Document opened.");
    setViewingId(null);
  };

  const onDelete = async (doc: EmployeeDocument) => {
    if (!token) return;
    if (doc.id.startsWith("system-")) return;
    const confirmed = window.confirm(`Delete "${doc.title}"?`);
    if (!confirmed) return;

    setDeletingId(doc.id);
    setError("");
    setMessage("");
    const result = await deleteMyDocument(token, doc.id);
    if (!result.ok) {
      setError("Unable to delete document.");
      setDeletingId(null);
      return;
    }
    setItems((prev) => prev.filter((item) => item.id !== doc.id));
    setMessage("Document deleted.");
    setDeletingId(null);
  };

  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex w-full flex-col">
        <Topbar name={name} title="My Documents" />
        <div className="p-6">
          <Card>
            <CardHeader>
              <CardTitle>Upload Document</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="grid gap-3 md:grid-cols-5" onSubmit={onUpload}>
                <Input
                  placeholder="Document title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                />
                <select
                  className="h-10 rounded-md border border-border px-3 text-sm"
                  value={docType}
                  onChange={(e) => setDocType(e.target.value as "APPOINTMENT" | "PAYSLIP" | "TAX" | "OTHER")}
                >
                  <option value="APPOINTMENT">APPOINTMENT</option>
                  <option value="PAYSLIP">PAYSLIP</option>
                  <option value="TAX">TAX</option>
                  <option value="OTHER">OTHER</option>
                </select>
                <div className="flex items-center gap-2 rounded-md border border-border px-3 py-2">
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  />
                  <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()}>
                    Choose File
                  </Button>
                  <span className="truncate text-sm text-muted-foreground">{selectedFile?.name || "No file chosen"}</span>
                </div>
                <div className="md:col-span-2">
                  <Button type="submit" disabled={submitting || loading || !selectedFile}>
                    {submitting ? "Uploading..." : "Upload"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Documents Dashboard</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-3">
                <div className="relative">
                  <Input
                    placeholder="Search document (e.g. leave)"
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
              {loading ? <p className="text-sm text-muted-foreground">Loading documents...</p> : null}
              {error ? <p className="text-sm text-red-600">{error}</p> : null}
              {message ? <p className="text-sm text-emerald-600">{message}</p> : null}
              {!loading && !error && filteredItems.length === 0 ? (
                <p className="text-sm text-muted-foreground">No documents available.</p>
              ) : null}
              <div className="space-y-2">
                {filteredItems.map((doc) => (
                  <article key={doc.id} className="flex items-center justify-between gap-3 rounded-md border border-border px-3 py-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{doc.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {doc.type} | Issued on {formatDateDDMMYY(doc.issued_on)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 text-xs font-normal">
                      <button
                        type="button"
                        onClick={() => onView(doc)}
                        disabled={viewingId === doc.id}
                        title={viewingId === doc.id ? "Opening..." : "View document"}
                        aria-label={viewingId === doc.id ? "Opening document" : "View document"}
                        className="text-slate-500 transition-colors hover:text-indigo-600 disabled:cursor-not-allowed disabled:text-slate-300"
                      >
                        {viewingId === doc.id ? "Opening..." : "View"}
                      </button>
                      <span className="text-slate-300">|</span>
                      <button
                        type="button"
                        onClick={() => onDownload(doc)}
                        disabled={downloadingId === doc.id}
                        title={downloadingId === doc.id ? "Downloading..." : "Download document"}
                        aria-label={downloadingId === doc.id ? "Downloading document" : "Download document"}
                        className="text-slate-500 transition-colors hover:text-indigo-600 disabled:cursor-not-allowed disabled:text-slate-300"
                      >
                        {downloadingId === doc.id ? "Downloading..." : "Download"}
                      </button>
                      {!doc.id.startsWith("system-") && doc.type === "OTHER" ? (
                        <>
                          <span className="text-slate-300">|</span>
                          <button
                            type="button"
                            onClick={() => onDelete(doc)}
                            disabled={deletingId === doc.id}
                            title={deletingId === doc.id ? "Deleting..." : "Delete document"}
                            aria-label={deletingId === doc.id ? "Deleting document" : "Delete document"}
                            className="text-slate-500 transition-colors hover:text-rose-600 disabled:cursor-not-allowed disabled:text-slate-300"
                          >
                            {deletingId === doc.id ? "Deleting..." : "Delete"}
                          </button>
                        </>
                      ) : null}
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
