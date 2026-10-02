"use client";

import { Upload } from "lucide-react";
import { Suspense } from "react";
import { Container } from "@/components/layout/AppShell";
import { LinkButton, PageHeader } from "@/components/common/ui";
import { ExploreView } from "@/components/search/ExploreView";
import { useAuth } from "@/lib/auth";

export default function DocumentsPage() {
  const { can } = useAuth();
  return (
    <Container>
      <Suspense>
        <ExploreView
          kind="document"
          header={
            <PageHeader
              eyebrow="Repository"
              title="Documents"
              description="Research papers, technical reports, expedition reports, educational resources and outreach records — each indexed passage by passage for search and AI."
              actions={can("upload") ? <LinkButton href="/workspace" icon={<Upload className="h-4 w-4" />}>Upload document</LinkButton> : undefined}
            />
          }
        />
      </Suspense>
    </Container>
  );
}
