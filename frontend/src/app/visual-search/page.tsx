"use client";

import { PageHeader } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { VisualSearch } from "@/components/search/VisualSearch";

export default function VisualSearchPage() {
  return (
    <Container>
      <PageHeader eyebrow="Intelligence" title="Visual Media Search" description="Find photographs and moments in videos by describing what they show." />
      <VisualSearch />
    </Container>
  );
}
