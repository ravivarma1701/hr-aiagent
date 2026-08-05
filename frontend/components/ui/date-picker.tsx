"use client";

import { ChevronLeft, ChevronRight, CalendarDays } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { formatDateDDMMYY } from "@/lib/date";

type DatePickerProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
};

const WEEK_DAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

function formatIsoDate(year: number, month: number, day: number): string {
  const mm = String(month + 1).padStart(2, "0");
  const dd = String(day).padStart(2, "0");
  return `${year}-${mm}-${dd}`;
}

function parseIso(value: string): Date | null {
  if (!value) return null;
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(year, month - 1, day);
}

export function DatePicker({ value, onChange, placeholder = "Select date" }: DatePickerProps) {
  const selectedDate = parseIso(value);
  const [open, setOpen] = useState(false);
  const [viewDate, setViewDate] = useState<Date>(selectedDate ?? new Date());
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onClickOutside = (event: MouseEvent) => {
      if (!wrapperRef.current) return;
      if (!wrapperRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  useEffect(() => {
    if (selectedDate) {
      setViewDate(selectedDate);
    }
  }, [value]); // eslint-disable-line react-hooks/exhaustive-deps

  const calendarDays = useMemo(() => {
    const year = viewDate.getFullYear();
    const month = viewDate.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const lastDate = new Date(year, month + 1, 0).getDate();
    const cells: Array<{ day: number; iso: string } | null> = [];

    for (let i = 0; i < firstDay; i += 1) {
      cells.push(null);
    }
    for (let day = 1; day <= lastDate; day += 1) {
      cells.push({ day, iso: formatIsoDate(year, month, day) });
    }
    while (cells.length % 7 !== 0) {
      cells.push(null);
    }
    return cells;
  }, [viewDate]);

  const yearOptions = useMemo(() => {
    const current = new Date().getFullYear();
    const years: number[] = [];
    for (let year = current - 80; year <= current + 5; year += 1) {
      years.push(year);
    }
    return years;
  }, []);

  const displayValue = selectedDate ? formatDateDDMMYY(value) : placeholder;

  return (
    <div className="relative" ref={wrapperRef}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between rounded-md border border-border bg-background px-3 py-2 text-left text-sm shadow-sm transition hover:border-indigo-300/60"
      >
        <span className={selectedDate ? "text-slate-900" : "text-muted-foreground"}>{displayValue}</span>
        <CalendarDays className="h-4 w-4 text-slate-500" />
      </button>

      {open ? (
        <div className="absolute z-50 mt-2 w-72 rounded-xl border border-slate-700/70 bg-slate-950 p-3 shadow-2xl">
          <div className="mb-3 flex items-center justify-between">
            <button
              type="button"
              onClick={() => setViewDate((prev) => new Date(prev.getFullYear(), prev.getMonth() - 1, 1))}
              className="rounded-lg border border-slate-700 p-1.5 text-slate-300 transition hover:bg-slate-800"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <div className="flex items-center gap-2">
              <select
                value={viewDate.getMonth()}
                onChange={(event) => {
                  const month = Number(event.target.value);
                  setViewDate((prev) => new Date(prev.getFullYear(), month, 1));
                }}
                className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-white outline-none"
              >
                {Array.from({ length: 12 }).map((_, month) => (
                  <option key={month} value={month}>
                    {new Date(2000, month, 1).toLocaleString("en-US", { month: "long" })}
                  </option>
                ))}
              </select>
              <select
                value={viewDate.getFullYear()}
                onChange={(event) => {
                  const year = Number(event.target.value);
                  setViewDate((prev) => new Date(year, prev.getMonth(), 1));
                }}
                className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-white outline-none"
              >
                {yearOptions.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={() => setViewDate((prev) => new Date(prev.getFullYear(), prev.getMonth() + 1, 1))}
              className="rounded-lg border border-slate-700 p-1.5 text-slate-300 transition hover:bg-slate-800"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          <div className="grid grid-cols-7 gap-1">
            {WEEK_DAYS.map((day) => (
              <div key={day} className="pb-1 text-center text-[11px] font-medium text-slate-400">
                {day}
              </div>
            ))}
            {calendarDays.map((cell, index) => {
              if (!cell) {
                return <div key={`empty-${index}`} className="h-9" />;
              }
              const isSelected = value === cell.iso;
              return (
                <button
                  key={cell.iso}
                  type="button"
                  onClick={() => {
                    onChange(cell.iso);
                    setOpen(false);
                  }}
                  className={`h-9 rounded-md text-sm transition ${
                    isSelected
                      ? "bg-indigo-500 font-semibold text-white"
                      : "text-slate-200 hover:bg-slate-800"
                  }`}
                >
                  {cell.day}
                </button>
              );
            })}
          </div>

          <div className="mt-3 flex justify-between">
            <button
              type="button"
              onClick={() => {
                onChange("");
                setOpen(false);
              }}
              className="text-xs text-slate-400 hover:text-slate-200"
            >
              Clear
            </button>
            <button
              type="button"
              onClick={() => {
                const now = new Date();
                onChange(formatIsoDate(now.getFullYear(), now.getMonth(), now.getDate()));
                setOpen(false);
              }}
              className="text-xs text-indigo-300 hover:text-indigo-200"
            >
              Today
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
