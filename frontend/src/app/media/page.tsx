"use client";

import { Suspense } from "react";
import { Container } from "@/components/layout/AppShell";
import { DemoBadge, PageHeader } from "@/components/common/ui";
import { ExploreView } from "@/components/search/ExploreView";
import { VisualSearch } from "@/components/search/VisualSearch";

export default function MediaPage() {
  return (
    <Container>
      <Suspense>
        <ExploreView
          kind="media"
          header={
            <>
            <PageHeader
              eyebrow="Media library"
              title="Photographs, Videos & Infographics"
              description="Visual stories from the poles, each linked to the stations, expeditions and research it depicts."
            >
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <DemoBadge label="Illustrated items are prototype artwork" />
                <span className="text-[12.5px] text-steel">Photographs marked “Public source” are real, openly licensed images with attribution.</span>
              </div>
            </PageHeader>
            <div className="mb-6"><VisualSearch compact /></div>
            </>
          }
        />
      </Suspense>
    </Container>
  );
}
