"use client";

import { BookOpenText } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/common/ui";
import { useAuth } from "@/lib/auth";

/** Starts the Research Story builder from any record (topic, paper, dataset, expedition, station, media…). */
export function StoryButton({ type, slug, variant = "secondary" }: { type: string; slug: string; variant?: "secondary" | "subtle" | "ghost" }) {
  const { can } = useAuth();
  const router = useRouter();
  const target = `/stories/new?type=${type}&slug=${encodeURIComponent(slug)}`;
  return (
    <Button
      variant={variant}
      onClick={() => router.push(can("generate_content") ? target : `/login?next=${encodeURIComponent(target)}`)}
      icon={<BookOpenText className="h-4 w-4 text-cyan-deep" aria-hidden />}
      title="Connect this record with its papers, datasets, expeditions, places, media and people in an evidence-grounded story"
    >
      Build Research Story
    </Button>
  );
}
