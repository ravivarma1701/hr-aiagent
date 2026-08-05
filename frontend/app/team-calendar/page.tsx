"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Holiday, TeamCalendarDay, TeamCalendarItem, fetchHolidays, fetchProfile, fetchTeamCalendar } from "@/lib/api";
import { formatMonthToDDMMYY } from "@/lib/date";

const markerClassMap: Record<string, string> = {
  LEAVE: "bg-amber-200 text-amber-900 border border-amber-300",
  WFH: "bg-blue-200 text-blue-900 border border-blue-300",
};

export default function TeamCalendarPage() {
  const now = new Date();
  const [name, setName] = useState("User");
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [days, setDays] = useState<TeamCalendarDay[]>([]);
  const [items, setItems] = useState<TeamCalendarItem[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [holidaysByDate, setHolidaysByDate] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const router = useRouter();

  const token = useMemo(() => {
    if (typeof window === "undefined") {
      return null;
    }
    return localStorage.getItem("hrms_access_token");
  }, []);

  const clearAuthAndRedirect = () => {
    localStorage.removeItem("hrms_access_token");
    document.cookie = "hrms_auth=; path=/; max-age=0; samesite=lax";
    router.push("/login");
  };

  const loadData = async (nextYear = year, nextMonth = month) => {
    if (!token) {
      clearAuthAndRedirect();
      return;
    }
    setLoading(true);
    setError("");
    try {
      const [profileResult, calendarResult, holidaysResult] = await Promise.all([
        fetchProfile(token),
        fetchTeamCalendar(token, { year: nextYear, month: nextMonth }),
        fetchHolidays(token, { limit: 500 }),
      ]);
      if (profileResult.status === 401 || calendarResult.status === 401 || holidaysResult.status === 401) {
        clearAuthAndRedirect();
        return;
      }

      if (profileResult.ok && "success" in profileResult.body && profileResult.body.success) {
        setName(profileResult.body.data.name);
      }

      if (!calendarResult.ok || !("success" in calendarResult.body) || !calendarResult.body.success) {
        setError("Failed to load team calendar");
        return;
      }

      setYear(calendarResult.body.data.year);
      setMonth(calendarResult.body.data.month);
      setDays(calendarResult.body.data.days);
      setItems(calendarResult.body.data.items);
      if (holidaysResult.ok && "success" in holidaysResult.body && holidaysResult.body.success) {
        const byDate: Record<string, string> = {};
        (holidaysResult.body.data as Holiday[]).forEach((holiday) => {
          const date = new Date(`${holiday.date}T00:00:00`);
          if (date.getFullYear() === nextYear && date.getMonth() + 1 === nextMonth) {
            byDate[holiday.date] = holiday.name;
          }
        });
        setHolidaysByDate(byDate);
      } else {
        setHolidaysByDate({});
      }
    } catch {
      setError("Failed to fetch calendar data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const goPreviousMonth = () => {
    const prevMonth = month === 1 ? 12 : month - 1;
    const prevYear = month === 1 ? year - 1 : year;
    loadData(prevYear, prevMonth);
  };

  const goNextMonth = () => {
    const nextMonth = month === 12 ? 1 : month + 1;
    const nextYear = month === 12 ? year + 1 : year;
    loadData(nextYear, nextMonth);
  };

  const filteredItems = items.filter((item) => {
    const term = searchTerm.trim().toLowerCase();
    if (!term) return true;
    const numericOnly = /^[0-9]+$/.test(term);
    if (numericOnly) {
      return String(item.employee_id) === term;
    }
    return item.employee_name.toLowerCase().includes(term);
  });

  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex w-full flex-col">
        <Topbar name={name} title="Team Calendar" />
        <div className="space-y-4 p-6">
          {error ? <p className="text-sm text-red-600">{error}</p> : null}

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <CardTitle>
                {formatMonthToDDMMYY(`${year}-${String(month).padStart(2, "0")}`)}
              </CardTitle>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={goPreviousMonth}>
                  Previous
                </Button>
                <Button size="sm" onClick={goNextMonth}>
                  Next
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? <p className="text-sm text-muted-foreground">Loading team calendar...</p> : null}
              {!loading && (
                <div className="space-y-3 overflow-x-auto">
                  <div className="max-w-sm">
                    <Input
                      placeholder="Search employee by name or ID"
                      value={searchTerm}
                      onChange={(event) => setSearchTerm(event.target.value)}
                    />
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="rounded px-2 py-1 font-medium text-slate-700">Legend:</span>
                    <span className={`rounded px-2 py-1 font-medium ${markerClassMap.LEAVE}`}>L = Leave</span>
                    <span className={`rounded px-2 py-1 font-medium ${markerClassMap.WFH}`}>W = WFH</span>
                    <span className="rounded border border-rose-300 bg-rose-100 px-2 py-1 font-medium text-rose-800">H = Holiday</span>
                  </div>
                  <table className="min-w-full border-collapse text-sm">
                    <thead>
                      <tr>
                        <th className="sticky left-0 bg-white px-3 py-2 text-left font-medium">Employee</th>
                        {days.map((day) => (
                          <th className="border-b px-2 py-2 text-center font-medium" key={day.date}>
                            <div>{day.day}</div>
                            <div className="text-xs text-muted-foreground">{day.weekday}</div>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {filteredItems.map((item) => (
                        <tr key={item.employee_id}>
                          <td className="sticky left-0 border-b bg-white px-3 py-2">
                            <div className="font-medium text-slate-900">{item.employee_name}</div>
                            <div className="text-xs text-muted-foreground">
                              ID: {item.employee_id} | {item.employee_role}
                            </div>
                          </td>
                          {days.map((day) => {
                            const marker = item.markers[day.date];
                            const isHoliday = Boolean(holidaysByDate[day.date]);
                            return (
                              <td className="border-b px-1 py-2 text-center" key={`${item.employee_id}-${day.date}`}>
                                {isHoliday ? (
                                  <span
                                    className="inline-block rounded border border-rose-300 bg-rose-100 px-2 py-1 text-xs font-medium text-rose-800"
                                    title={holidaysByDate[day.date]}
                                  >
                                    H
                                  </span>
                                ) : marker ? (
                                  <span className={`inline-block rounded px-2 py-1 text-xs font-medium ${markerClassMap[marker]}`}>
                                    {marker === "LEAVE" ? "L" : "W"}
                                  </span>
                                ) : (
                                  <span className="text-xs text-slate-300">-</span>
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                      {filteredItems.length === 0 ? (
                        <tr>
                          <td className="border-b px-3 py-3 text-sm text-slate-500" colSpan={days.length + 1}>
                            No employees found for this search.
                          </td>
                        </tr>
                      ) : null}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
