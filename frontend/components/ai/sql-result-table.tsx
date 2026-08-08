const MAX_ROWS_BEFORE_SCROLL = 20;

export function SqlResultTable({ rows, sql }: { rows: Record<string, unknown>[]; sql?: string | null }) {
  if (!rows.length) return null;

  const columns = Object.keys(rows[0]);
  const scrollable = rows.length > MAX_ROWS_BEFORE_SCROLL;

  return (
    <div className="mt-2 space-y-2">
      {sql ? (
        <pre className="overflow-x-auto rounded-md bg-slate-900 p-3 text-xs text-slate-100">
          <code>{sql}</code>
        </pre>
      ) : null}
      <div
        className={`overflow-x-auto rounded-md border border-border ${scrollable ? "max-h-96 overflow-y-auto" : ""}`}
      >
        <table className="w-full min-w-max text-left text-xs">
          <thead className="bg-muted text-muted-foreground">
            <tr>
              {columns.map((column) => (
                <th
                  key={column}
                  className={`whitespace-nowrap px-3 py-2 font-medium ${scrollable ? "sticky top-0 bg-muted" : ""}`}
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={rowIndex} className="border-t border-border">
                {columns.map((column) => (
                  <td key={column} className="whitespace-nowrap px-3 py-2">
                    {String(row[column] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {scrollable ? (
        <p className="text-[11px] text-muted-foreground">
          Showing all {rows.length} rows — scroll within the table to see more.
        </p>
      ) : null}
    </div>
  );
}
