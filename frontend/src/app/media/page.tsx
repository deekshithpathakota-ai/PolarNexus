"use client";

import { Suspense } from "react";
import { Container } from "@/components/layout/AppShell";
import { DemoBadge, PageHeader } from "@/components/common/ui";
import { ExploreView } from "@/components/search/ExploreView";

export default function MediaPage() {
  return (
    <Container>
      <Suspense>
        <ExploreView
          kind="media"
          header={
            <PageHeader
              eyebrow="Media library"
              title="Photographs, Videos & Infographics"
              description="Visual stories from the poles, each linked to the stations, expeditions and research it depicts."
            >
              <div className="mt-3"><DemoBadge label="Original prototype artwork stands in for institutional media" /></div>
            </PageHeader>
          }
        />
      </Suspense>
    </Container>
  );
}
