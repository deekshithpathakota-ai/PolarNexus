"use client";

import { Suspense } from "react";
import { Container } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/common/ui";
import { ExploreView } from "@/components/search/ExploreView";

export default function ExplorePage() {
  return (
    <Container>
      <Suspense>
        <ExploreView
          header={
            <PageHeader
              eyebrow="Discover"
              title="Explore Polar Knowledge"
              description="Search documents, datasets, media, expeditions, stations and researchers in one place — by keyword, by meaning, or both."
            />
          }
        />
      </Suspense>
    </Container>
  );
}
