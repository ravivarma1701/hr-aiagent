import { cn } from "@/lib/utils";

function Badge({ className, children }: { className?: string; children: React.ReactNode }) {
  return <span className={cn("inline-flex rounded-full px-2 py-1 text-xs font-medium", className)}>{children}</span>;
}

export { Badge };
