export interface CampaignOptions {
  audiences: { key: string; label: string }[];
  channels: { key: string; label: string; live: boolean; note: string }[];
  topics: { slug: string; name: string }[];
  content: { id: number; title: string; status: string; format: string; audience: string; is_demo: boolean }[];
}

export const CAMPAIGN_TONE = { draft: "slate", scheduled: "cyan", published: "teal", archived: "amber" } as const;
