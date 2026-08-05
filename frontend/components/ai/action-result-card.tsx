import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PendingAction } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  completed: "bg-emerald-50 text-emerald-700 border border-emerald-200",
  pending_confirmation: "bg-amber-50 text-amber-700 border border-amber-200",
  forbidden: "bg-red-50 text-red-700 border border-red-200",
  failed: "bg-red-50 text-red-700 border border-red-200",
  no_action: "bg-slate-100 text-slate-600 border border-slate-200",
  unavailable: "bg-slate-100 text-slate-600 border border-slate-200",
  error: "bg-red-50 text-red-700 border border-red-200",
};

export function ActionResultCard({
  action,
  status,
  result,
  pendingAction,
  onConfirm,
  onCancel,
  confirming,
}: {
  action: string | null;
  status: string;
  result: unknown;
  pendingAction: PendingAction | null;
  onConfirm?: () => void;
  onCancel?: () => void;
  confirming?: boolean;
}) {
  return (
    <div className="mt-2 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {action ? <Badge className="border border-border bg-white text-slate-600">{action}</Badge> : null}
        <Badge className={STATUS_STYLES[status] ?? "border border-border bg-white text-slate-600"}>
          {status.replace(/_/g, " ")}
        </Badge>
      </div>

      {status === "pending_confirmation" && pendingAction ? (
        <div className="flex gap-2">
          <Button size="sm" onClick={onConfirm} disabled={confirming}>
            {confirming ? "Confirming..." : "Confirm"}
          </Button>
          <Button size="sm" variant="outline" onClick={onCancel} disabled={confirming}>
            Cancel
          </Button>
        </div>
      ) : null}

      {result ? (
        <pre className="overflow-x-auto rounded-md bg-slate-900 p-3 text-xs text-slate-100">
          <code>{JSON.stringify(result, null, 2)}</code>
        </pre>
      ) : null}
    </div>
  );
}
