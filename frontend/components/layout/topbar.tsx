"use client";

import { LogOut, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { NotificationBell } from "@/components/layout/notification-bell";
import { Button } from "@/components/ui/button";
import { Employee, fetchEmployees, fetchMyProfilePicture, fetchProfile } from "@/lib/api";

export function Topbar({ name, title = "Employee Directory" }: { name: string; title?: string }) {
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [results, setResults] = useState<Employee[]>([]);
  const [profilePictureUrl, setProfilePictureUrl] = useState("");
  const menuRef = useRef<HTMLDivElement | null>(null);
  const searchRef = useRef<HTMLDivElement | null>(null);
  const initials = name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");

  useEffect(() => {
    const onClickOutside = (event: MouseEvent) => {
      if (!menuRef.current) return;
      if (!menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setSearchOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("hrms_access_token");
    if (!token || query.trim().length < 2) {
      setResults([]);
      setSearchOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      setLoadingSearch(true);
      const response = await fetchEmployees(token, { q: query.trim(), limit: 6, offset: 0 });
      if (response.ok && "success" in response.body && response.body.success) {
        setResults(response.body.data.items);
        setSearchOpen(true);
      } else {
        setResults([]);
      }
      setLoadingSearch(false);
    }, 250);

    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const loadProfilePicture = async () => {
      const token = localStorage.getItem("hrms_access_token");
      if (!token) {
        setProfilePictureUrl("");
        return;
      }
      const profileResult = await fetchProfile(token);
      if (!profileResult.ok || !("success" in profileResult.body) || !profileResult.body.success) {
        setProfilePictureUrl("");
        return;
      }
      if (!profileResult.body.data.has_profile_photo) {
        setProfilePictureUrl("");
        return;
      }

      const pictureResult = await fetchMyProfilePicture(token);
      if (!pictureResult.ok) {
        setProfilePictureUrl("");
        return;
      }
      const url = URL.createObjectURL(pictureResult.body as Blob);
      setProfilePictureUrl((previous) => {
        if (previous) URL.revokeObjectURL(previous);
        return url;
      });
    };

    loadProfilePicture();
  }, []);

  useEffect(() => {
    return () => {
      if (profilePictureUrl) URL.revokeObjectURL(profilePictureUrl);
    };
  }, [profilePictureUrl]);

  const onLogout = () => {
    localStorage.removeItem("hrms_access_token");
    document.cookie = "hrms_auth=; path=/; max-age=0; samesite=lax";
    document.cookie = "hrms_role=; path=/; max-age=0; samesite=lax";
    router.push("/login");
  };

  return (
    <header className="border-b border-indigo-900/40 bg-gradient-to-r from-[#1b1f4f] via-[#3b3691] to-[#5b4cc4] px-4 py-3 shadow-sm md:px-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-indigo-200/80">Workspace</p>
            <h1 className="text-lg font-semibold text-white md:text-xl">{title}</h1>
          </div>
        </div>

        <div className="flex items-center gap-3 self-end md:self-auto">
          <div className="relative w-[18rem]" ref={searchRef}>
            <div className="flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-3 py-2">
              <Search className="h-4 w-4 text-indigo-100/80" />
              <input
                className="w-full bg-transparent text-sm text-white placeholder:text-indigo-100/70 outline-none"
                placeholder="Global search employees..."
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                suppressHydrationWarning
              />
            </div>
            {searchOpen ? (
              <div className="absolute right-0 z-50 mt-2 max-h-72 w-full overflow-auto rounded-xl border border-slate-700/80 bg-slate-950/95 p-2 shadow-2xl backdrop-blur">
                {loadingSearch ? <p className="px-2 py-1 text-xs text-slate-400">Searching...</p> : null}
                {!loadingSearch && results.length === 0 ? (
                  <p className="px-2 py-1 text-xs text-slate-400">No matching employees.</p>
                ) : null}
                {results.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className="w-full rounded-lg px-2 py-2 text-left hover:bg-white/5"
                    onClick={() => {
                      setSearchOpen(false);
                      setQuery(item.name);
                      router.push(`/employees?q=${encodeURIComponent(item.name)}`);
                    }}
                  >
                    <p className="text-sm font-medium text-white">{item.name}</p>
                    <p className="text-xs text-slate-400">{item.email}</p>
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          <NotificationBell />
          <div className="relative" ref={menuRef}>
            <button
              aria-label="Open profile menu"
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/20 bg-gradient-to-br from-amber-300 via-orange-300 to-rose-300 text-sm font-semibold text-slate-950 shadow-[0_8px_24px_-8px_rgba(251,146,60,0.55)] transition hover:scale-[1.02]"
              onClick={() => setMenuOpen((value) => !value)}
              type="button"
              suppressHydrationWarning
            >
              {profilePictureUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={profilePictureUrl} alt="Profile" className="h-10 w-10 rounded-full object-cover" />
              ) : (
                initials || "U"
              )}
            </button>

            {menuOpen ? (
              <div className="absolute right-0 z-50 mt-3 w-56 overflow-hidden rounded-2xl border border-slate-700/80 bg-slate-950/95 shadow-2xl backdrop-blur">
                <div className="border-b border-slate-800 px-4 py-3">
                  <p className="text-sm font-semibold text-white">{name}</p>
                  <p className="text-xs text-slate-400">Profile menu</p>
                </div>
                <div className="p-2">
                  <Button className="w-full justify-start gap-2" onClick={onLogout} variant="outline">
                    <LogOut className="h-4 w-4" />
                    Logout
                  </Button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  );
}
