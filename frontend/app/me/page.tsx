"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Camera } from "lucide-react";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DatePicker } from "@/components/ui/date-picker";
import { Input } from "@/components/ui/input";
import {
  JobHistoryItem,
  fetchMyJobHistory,
  fetchMyProfilePicture,
  fetchProfile,
  updateMyProfile,
  uploadMyProfilePicture,
} from "@/lib/api";
import { formatDateDDMMYY } from "@/lib/date";

export default function MePage() {
  const [employeeId, setEmployeeId] = useState<number | null>(null);
  const [name, setName] = useState("User");
  const [role, setRole] = useState("");
  const [email, setEmail] = useState("");
  const [editName, setEditName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [bloodType, setBloodType] = useState("");
  const [occupancy, setOccupancy] = useState("");
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [jobHistory, setJobHistory] = useState<JobHistoryItem[]>([]);
  const [profilePictureUrl, setProfilePictureUrl] = useState("");
  const [uploadingPicture, setUploadingPicture] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const router = useRouter();
  const pictureInputRef = useRef<HTMLInputElement | null>(null);

  const token = useMemo(() => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("hrms_access_token");
  }, []);
  const currentJobTitle = useMemo(() => {
    const active = jobHistory.find((item) => item.is_current);
    return active?.designation || jobHistory[0]?.designation || "No job title set";
  }, [jobHistory]);

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
      const [profileResult, historyResult] = await Promise.all([fetchProfile(token), fetchMyJobHistory(token)]);
      if (profileResult.status === 401 || historyResult.status === 401) return clearAuthAndRedirect();
      if (!profileResult.ok || !("success" in profileResult.body) || !profileResult.body.success) {
        setError("Failed to load profile");
        return;
      }
      setName(profileResult.body.data.name);
      setEmployeeId(profileResult.body.data.id);
      setEditName(profileResult.body.data.name);
      setEmail(profileResult.body.data.email);
      setRole(profileResult.body.data.role);
      setPhone(profileResult.body.data.phone || "");
      setAddress(profileResult.body.data.address || "");
      setBloodType(profileResult.body.data.blood_type || "");
      setOccupancy(profileResult.body.data.occupancy || "");
      setDateOfBirth(profileResult.body.data.date_of_birth || "");
      if (profileResult.body.data.has_profile_photo) {
        const photoResult = await fetchMyProfilePicture(token);
        if (photoResult.ok) {
          const url = URL.createObjectURL(photoResult.body as Blob);
          setProfilePictureUrl((previous) => {
            if (previous) URL.revokeObjectURL(previous);
            return url;
          });
        } else {
          setProfilePictureUrl("");
        }
      } else {
        setProfilePictureUrl("");
      }
      if (historyResult.ok && "success" in historyResult.body && historyResult.body.success) {
        setJobHistory(historyResult.body.data);
      }
    } catch {
      setError("Failed to fetch profile");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    return () => {
      if (profilePictureUrl) URL.revokeObjectURL(profilePictureUrl);
    };
  }, [profilePictureUrl]);

  const onSave = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token) return;
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const optionalTrim = (value: string) => {
        const trimmed = value.trim();
        return trimmed.length > 0 ? trimmed : undefined;
      };
      const result = await updateMyProfile(token, {
        name: editName.trim(),
        phone: optionalTrim(phone),
        address: optionalTrim(address),
        blood_type: optionalTrim(bloodType),
        occupancy: optionalTrim(occupancy),
        date_of_birth: dateOfBirth || undefined,
      });
      if (!result.ok || !("success" in result.body) || !result.body.success) {
        const fallbackMessage = "Failed to update profile";
        let message = fallbackMessage;
        if ("detail" in result.body) {
          const detail = result.body.detail;
          if (typeof detail === "string") {
            message = detail;
          } else if (Array.isArray(detail) && detail.length > 0) {
            const first = detail[0];
            if (first && typeof first === "object" && "msg" in first && typeof first.msg === "string") {
              message = first.msg;
            }
          } else if (detail && typeof detail === "object" && "error" in detail) {
            const maybeError = (detail as { error?: { message?: unknown } }).error;
            if (maybeError && typeof maybeError.message === "string") {
              message = maybeError.message;
            }
          }
        }
        setError(message);
        return;
      }
      setName(result.body.data.name);
      setEditName(result.body.data.name);
      setPhone(result.body.data.phone || "");
      setAddress(result.body.data.address || "");
      setBloodType(result.body.data.blood_type || "");
      setOccupancy(result.body.data.occupancy || "");
      setDateOfBirth(result.body.data.date_of_birth || "");
      setSuccess("Profile updated");
    } finally {
      setSaving(false);
    }
  };

  const onUploadPicture = async (file: File) => {
    if (!token) return;
    setUploadingPicture(true);
    setError("");
    setSuccess("");
    try {
      const result = await uploadMyProfilePicture(token, file);
      if (!result.ok || !("success" in result.body) || !result.body.success) {
        setError("Failed to upload profile picture");
        return;
      }
      await loadData();
      setSuccess("Profile picture updated");
    } finally {
      setUploadingPicture(false);
    }
  };

  const onSelectPicture: React.ChangeEventHandler<HTMLInputElement> = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    await onUploadPicture(file);
    event.target.value = "";
  };

  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex w-full flex-col">
        <Topbar name={name} title="My Profile" />
        <div className="space-y-4 p-6">
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          {success ? <p className="text-sm text-emerald-600">{success}</p> : null}

          <Card>
            <CardHeader>
              <CardTitle>Profile Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {loading ? <p className="text-sm text-muted-foreground">Loading profile...</p> : null}
              {!loading && (
                <form className="space-y-3" onSubmit={onSave}>
                  <div className="rounded-md border border-border p-3">
                    <div className="mb-3 flex flex-wrap items-center gap-4 rounded-xl border border-indigo-200/60 bg-gradient-to-r from-indigo-50 via-white to-blue-50 p-4">
                      <div className="relative">
                        <button
                        type="button"
                        onClick={() => pictureInputRef.current?.click()}
                        disabled={uploadingPicture}
                        className="group relative h-24 w-24 overflow-hidden rounded-full bg-indigo-100 text-2xl font-semibold text-indigo-700 disabled:cursor-not-allowed"
                        aria-label="Add profile image"
                      >
                        {profilePictureUrl ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={profilePictureUrl} alt="Profile" className="h-24 w-24 object-cover object-center" />
                        ) : (
                          name
                            .split(" ")
                            .filter(Boolean)
                            .slice(0, 2)
                            .map((part) => part[0]?.toUpperCase())
                            .join("") || "U"
                        )}
                          <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-slate-900/65 text-white opacity-0 transition-opacity duration-200 group-hover:opacity-100 group-focus-visible:opacity-100">
                            <Camera className="h-5 w-5" />
                          </div>
                        </button>
                      </div>
                      <input
                        ref={pictureInputRef}
                        type="file"
                        accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"
                        onChange={onSelectPicture}
                        className="hidden"
                      />
                      <div className="space-y-1">
                        <p className="text-lg font-semibold leading-tight text-slate-900">{editName || name}</p>
                        <p className="text-sm text-slate-500">{currentJobTitle}</p>
                      </div>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Employee ID</p>
                    <Input value={employeeId != null ? String(employeeId) : "-"} disabled />
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Email</p>
                    <Input value={email} disabled />
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Role</p>
                    <Input value={role} disabled />
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Phone</p>
                    <Input value={phone} onChange={(e) => setPhone(e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Address</p>
                    <Input value={address} onChange={(e) => setAddress(e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Blood Type</p>
                    <Input value={bloodType} onChange={(e) => setBloodType(e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Employment Type</p>
                    <Input value={occupancy} onChange={(e) => setOccupancy(e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Date of Birth</p>
                    <DatePicker value={dateOfBirth} onChange={setDateOfBirth} placeholder="Choose your date of birth" />
                  </div>
                  <Button type="submit" disabled={saving}>
                    {saving ? "Saving..." : "Save Changes"}
                  </Button>
                </form>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Job History Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              {jobHistory.length === 0 ? <p className="text-sm text-muted-foreground">No job history records yet.</p> : null}
              <div className="space-y-3">
                {jobHistory.map((item) => (
                  <div className="rounded-md border border-border p-3" key={item.id}>
                    <p className="text-sm font-semibold text-slate-900">{item.designation}</p>
                    <p className="text-xs text-muted-foreground">
                      {item.business_unit} / {item.department}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatDateDDMMYY(item.start_date)} to {item.end_date ? formatDateDDMMYY(item.end_date) : "Present"} {item.is_current ? "(Current)" : ""}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
