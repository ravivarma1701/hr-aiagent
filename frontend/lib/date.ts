export function formatDateDDMMYY(value?: string | null): string {
  if (!value) return "-";
  const datePart = value.split("T")[0];
  const parts = datePart.split("-");
  if (parts.length !== 3) return value;
  const [year, month, day] = parts;
  if (!year || !month || !day) return value;
  return `${day.padStart(2, "0")}-${month.padStart(2, "0")}-${year.slice(-2)}`;
}

export function formatDateTimeDDMMYY(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return formatDateDDMMYY(value);
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = String(date.getFullYear()).slice(-2);
  const hour = String(date.getHours()).padStart(2, "0");
  const minute = String(date.getMinutes()).padStart(2, "0");
  return `${day}-${month}-${year} ${hour}:${minute}`;
}

export function formatMonthToDDMMYY(monthKey?: string | null): string {
  if (!monthKey) return "-";
  const parts = monthKey.split("-");
  if (parts.length !== 2) return monthKey;
  const [year, month] = parts;
  return `${month.padStart(2, "0")}-${year.slice(-2)}`;
}
