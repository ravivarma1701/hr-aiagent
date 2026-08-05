import { PolicySource } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

export function SourceList({ sources }: { sources: PolicySource[] }) {
  if (!sources.length) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {sources.map((source, index) => (
        <Badge key={`${source.title}-${index}`} className="border border-indigo-200 bg-indigo-50 text-indigo-700">
          {source.title}
          <span className="ml-1 text-indigo-400">· {source.category}</span>
        </Badge>
      ))}
    </div>
  );
}
