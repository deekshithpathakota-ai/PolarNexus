"use client";

import { Suspense } from "react";
import { Container } from "@/components/layout/AppShell";
import { DemoBadge, PageHeader } from "@/components/common/ui";
import { ExploreView } from "@/components/search/ExploreView";

export default function DatasetsPage() {
  return (
    <Container>
      <Suspense>
        <ExploreView
          kind="dataset"
          header={
            <PageHeader
              eyebrow="Data portal"
              title="Datasets"
              description="Structured polar datasets with variables, units, coverage and licences. Preview records, filter values and visualise them in the browser."
            >
              <div className="mt-3"><DemoBadge label="Synthetic demonstration values" /></div>
            </PageHeader>
          }
        />
      </Suspense>
    </Container>
  );
}
