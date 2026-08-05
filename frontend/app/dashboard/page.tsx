"use client";

import { CalendarDays, Gift, PlaneTakeoff } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { fetchBirthdays, fetchHolidays, fetchProfile, type Birthday, type Holiday } from "@/lib/api";
import { formatDateDDMMYY } from "@/lib/date";

export default function DashboardPage() {
  const [name, setName] = useState("User");
  const [error, setError] = useState("");
  const [holidays, setHolidays] = useState<Holiday[]>([]);
  const [holidayIndex, setHolidayIndex] = useState(0);
  const [birthdays, setBirthdays] = useState<Birthday[]>([]);
  const router = useRouter();
  const todayIso = useMemo(() => new Date().toISOString().slice(0, 10), []);

  const { birthdaysToday, upcomingBirthdays } = useMemo(() => {
    const todays = birthdays.filter((person) => person.date === todayIso);
    const upcoming = birthdays
      .filter((person) => {
        if (person.date === todayIso) {
          return false;
        }
        return person.date > todayIso;
      })
      .sort((a, b) => {
        if (a.date !== b.date) {
          return a.date.localeCompare(b.date);
        }
        return a.name.localeCompare(b.name);
      })
      .slice(0, 5);

    return { birthdaysToday: todays, upcomingBirthdays: upcoming };
  }, [birthdays, todayIso]);

  const token = useMemo(() => {
    if (typeof window === "undefined") {
      return null;
    }
    return localStorage.getItem("hrms_access_token");
  }, []);

  useEffect(() => {
    const loadProfile = async () => {
      if (!token) {
        localStorage.removeItem("hrms_access_token");
        document.cookie = "hrms_auth=; path=/; max-age=0; samesite=lax";
        router.push("/login");
        return;
      }

      try {
        const profile = await fetchProfile(token);
        if (profile.status === 401) {
          localStorage.removeItem("hrms_access_token");
          document.cookie = "hrms_auth=; path=/; max-age=0; samesite=lax";
          router.push("/login");
          return;
        }
        if (profile.ok && "success" in profile.body && profile.body.success) {
          setName(profile.body.data.name);
        } else {
          setError("Unable to load dashboard profile");
        }

        const holidaysResponse = await fetchHolidays(token, { limit: 200 });
        if (holidaysResponse.status === 401) {
          localStorage.removeItem("hrms_access_token");
          document.cookie = "hrms_auth=; path=/; max-age=0; samesite=lax";
          router.push("/login");
          return;
        }
        if (holidaysResponse.ok && "success" in holidaysResponse.body && holidaysResponse.body.success) {
          const holidayItems = holidaysResponse.body.data;
          setHolidays(holidayItems);
          if (holidayItems.length > 0) {
            const today = new Date().toISOString().slice(0, 10);
            const upcomingIndex = holidayItems.findIndex((item) => item.date >= today);
            setHolidayIndex(upcomingIndex >= 0 ? upcomingIndex : holidayItems.length - 1);
          } else {
            setHolidayIndex(0);
          }
        }

        const birthdaysResponse = await fetchBirthdays(token, { limit: 500 });
        if (birthdaysResponse.status === 401) {
          localStorage.removeItem("hrms_access_token");
          document.cookie = "hrms_auth=; path=/; max-age=0; samesite=lax";
          router.push("/login");
          return;
        }
        if (birthdaysResponse.ok && "success" in birthdaysResponse.body && birthdaysResponse.body.success) {
          setBirthdays(birthdaysResponse.body.data);
        }
      } catch {
        setError("Unable to load dashboard profile");
      }
    };

    loadProfile();
  }, [router, token]);

  return (
    <main className="flex min-h-screen bg-[#0b1020]">
      <Sidebar />
      <section className="flex w-full min-w-0 flex-col bg-[#060a16]">
        <Topbar name={name} title="Dashboard" />
        <div className="p-4 md:p-6">
          <div className="grid items-start gap-5 xl:grid-cols-[1.05fr_1fr_1fr]">
            <Card className="border border-slate-800/90 bg-gradient-to-br from-[#171a3f] via-[#342f72] to-[#6f5bd3] text-white shadow-[0_30px_80px_-45px_rgba(99,102,241,0.7)]">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-white/15 bg-white/10">
                    <CalendarDays className="h-5 w-5" />
                  </div>
                  <span className="rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs text-indigo-100">Holidays</span>
                </div>
                <h2 className="mt-4 text-xl font-semibold">Upcoming Holidays</h2>
                <p className="mt-1 text-sm text-indigo-100/85">Plan leave requests around upcoming holidays.</p>
                <div className="mt-4 space-y-2">
                  {holidays.length > 0 ? (
                    <div
                      className="flex w-full items-center justify-between rounded-xl border border-white/10 bg-black/10 px-3 py-2 text-left"
                      key={holidays[holidayIndex].name}
                    >
                      <button
                        type="button"
                        onClick={() => setHolidayIndex((prev) => Math.max(prev - 1, 0))}
                        disabled={holidayIndex === 0}
                        className="mr-3 rounded-md border border-white/15 px-2 py-1 text-sm text-indigo-100 disabled:cursor-not-allowed disabled:opacity-40"
                        aria-label="Previous holiday"
                      >
                        {"<"}
                      </button>
                      <div>
                        <p className="text-sm font-medium text-white">{holidays[holidayIndex].name}</p>
                        <p className="text-xs text-indigo-100/80">{formatDateDDMMYY(holidays[holidayIndex].date)}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setHolidayIndex((prev) => Math.min(prev + 1, holidays.length - 1))}
                        disabled={holidayIndex === holidays.length - 1}
                        className="ml-3 rounded-md border border-white/15 px-2 py-1 text-sm text-indigo-100 disabled:cursor-not-allowed disabled:opacity-40"
                        aria-label="Next holiday"
                      >
                        {">"}
                      </button>
                    </div>
                  ) : (
                    <div className="rounded-xl border border-white/10 bg-black/10 px-3 py-3 text-sm text-indigo-100/80">
                      No holidays available right now.
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="border border-slate-800/90 bg-[#0d1428] text-white shadow-lg shadow-black/20">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-emerald-300/15 bg-emerald-400/10 text-emerald-200">
                    <PlaneTakeoff className="h-5 w-5" />
                  </div>
                  <span className="rounded-full border border-emerald-300/15 bg-emerald-400/10 px-3 py-1 text-xs text-emerald-200">Leave</span>
                </div>
                <h2 className="mt-4 text-xl font-semibold">Request Leave</h2>
                <p className="mt-1 text-sm text-slate-300">Open the leaves module to submit a request and track approvals.</p>
                <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                  <p className="text-sm text-slate-300">Use this to apply for casual, sick, or earned leave.</p>
                  <Button className="mt-4 w-full" onClick={() => router.push("/leaves")}>Open Leave Module</Button>
                </div>
              </CardContent>
            </Card>

            <Card className="border border-slate-800/90 bg-[#0d1428] text-white shadow-lg shadow-black/20">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-amber-300/15 bg-amber-400/10 text-amber-200">
                    <Gift className="h-5 w-5" />
                  </div>
                  <span className="rounded-full border border-amber-300/15 bg-amber-400/10 px-3 py-1 text-xs text-amber-200">Birthdays</span>
                </div>
                <h2 className="mt-4 text-xl font-semibold">Employee Birthdays</h2>
                <p className="mt-1 text-sm text-slate-300">Upcoming celebrations across teams.</p>
                <div className="mt-4 space-y-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-amber-200/90">Birthdays Today</p>
                  {birthdaysToday.map((person) => (
                    <div className="rounded-xl border border-slate-800 bg-slate-950/50 px-3 py-3" key={`${person.name}-${person.date}`}>
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-white">{person.name}</p>
                          <p className="truncate text-xs text-slate-400">{person.team}</p>
                        </div>
                        <p className="shrink-0 text-xs text-amber-200">{formatDateDDMMYY(person.date)}</p>
                      </div>
                    </div>
                  ))}
                  {birthdaysToday.length === 0 ? (
                    <div className="rounded-xl border border-slate-800 bg-slate-950/50 px-3 py-3 text-sm text-slate-400">
                      No birthdays today.
                    </div>
                  ) : null}

                  <p className="pt-2 text-xs font-semibold uppercase tracking-wide text-amber-200/90">Upcoming Birthdays</p>
                  {upcomingBirthdays.map((person) => (
                    <div className="rounded-xl border border-slate-800 bg-slate-950/50 px-3 py-3" key={`${person.name}-${person.date}`}>
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-white">{person.name}</p>
                          <p className="truncate text-xs text-slate-400">{person.team}</p>
                        </div>
                        <p className="shrink-0 text-xs text-amber-200">{formatDateDDMMYY(person.date)}</p>
                      </div>
                    </div>
                  ))}
                  {upcomingBirthdays.length === 0 ? (
                    <div className="rounded-xl border border-slate-800 bg-slate-950/50 px-3 py-3 text-sm text-slate-400">
                      No upcoming birthdays.
                    </div>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          </div>
          {error ? <p className="mt-4 text-sm text-rose-300">{error}</p> : null}
        </div>
      </section>
    </main>
  );
}
