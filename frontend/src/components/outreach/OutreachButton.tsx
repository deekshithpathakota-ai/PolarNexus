"use client";

import { Megaphone } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/common/ui";
import { useAuth } from "@/lib/auth";

/** Flagship action: research record → evidence-grounded, human-reviewed outreach draft in the Content Studio. */
export function OutreachButton({ type, slug, ids, size = "md", variant = "dark", label = "Turn Research Into Outreach" }: {
  type: "document" | "dataset" | "expedition" | "station" | "researcher" | "activity" | "topic" | "chunks";
  slug?: string;
  ids?: number[];
  size?: "sm" | "md" | "lg";
  variant?: "dark" | "primary" | "secondary";
  label?: string;
}) {
  const { can } = useAuth();
  const router = useRouter();
  const target = type === "chunks" ? `/studio?type=chunks&ids=${(ids || []).join(",")}` : `/studio?type=${type}&slug=${slug}`;
  return (
    <Button
      size={size}
      variant={variant}
      icon={<Megaphone className="h-4 w-4" />}
      onClick={() => router.push(can("generate_content") ? target : `/login?next=${encodeURIComponent(target)}`)}
      title="Retrieve evidence, generate a cited draft, run the evidence check and send it for human review"
    >
      {label}
    </Button>
  );
}
