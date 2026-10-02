"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export const SERIES = ["#0f7fa1", "#128a87", "#c98a1b", "#7b6cd9", "#c4553f", "#5b7489", "#4fd1a5"];
const axis = { fontSize: 11, fill: "#5b7489" };
const tip = { contentStyle: { borderRadius: 10, border: "1px solid #d5e6ee", fontSize: 12 } };

export interface Analytics {
  label: string;
  totals: Record<string, number>;
  timeline: { date: string; views: number; searches: number; ai_questions: number; generated: number; published: number }[];
  popular: { title: string; url: string; type: string; views: number }[];
  top_searches: { query: string; count: number }[];
  search_modes: Record<string, number>;
  ai: { by_mode: Record<string, number>; by_evidence: Record<string, number>; feedback: Record<string, number> };
  content_workflow: Record<string, number>;
  content_formats: Record<string, number>;
  review_turnaround_hours: number | null;
  resource_types: Record<string, number>;
  document_types: Record<string, number>;
  topics: { name: string; count: number }[];
  growth: { month: string; total: number; added: number }[];
}

const toArr = (o: Record<string, number>) => Object.entries(o).map(([name, value]) => ({ name: name.replace(/_/g, " "), value }));

export function UsageChart({ data }: { data: Analytics["timeline"] }) {
  const weekly: typeof data = [];
  for (let i = 0; i < data.length; i += 7) {
    const chunk = data.slice(i, i + 7);
    weekly.push(chunk.reduce((a, c) => ({ date: chunk[0].date, views: a.views + c.views, searches: a.searches + c.searches, ai_questions: a.ai_questions + c.ai_questions, generated: a.generated + c.generated, published: a.published + c.published }), { date: "", views: 0, searches: 0, ai_questions: 0, generated: 0, published: 0 }));
  }
  return (
    <div className="h-[280px]">
      <ResponsiveContainer>
        <AreaChart data={weekly} margin={{ top: 10, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid stroke="#e3eef3" vertical={false} />
          <XAxis dataKey="date" tick={axis} tickFormatter={(d) => d.slice(5)} />
          <YAxis tick={axis} />
          <Tooltip {...tip} labelFormatter={(d) => `Week of ${d}`} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Area type="monotone" dataKey="views" name="Resource views" stroke={SERIES[0]} fill={SERIES[0]} fillOpacity={0.15} strokeWidth={2} />
          <Area type="monotone" dataKey="searches" name="Searches" stroke={SERIES[1]} fill={SERIES[1]} fillOpacity={0.12} strokeWidth={2} />
          <Area type="monotone" dataKey="ai_questions" name="AI questions" stroke={SERIES[3]} fill={SERIES[3]} fillOpacity={0.1} strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function GrowthChart({ data }: { data: Analytics["growth"] }) {
  return (
    <div className="h-[240px]">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 10, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid stroke="#e3eef3" vertical={false} />
          <XAxis dataKey="month" tick={axis} />
          <YAxis tick={axis} />
          <Tooltip {...tip} />
          <Line type="monotone" dataKey="total" name="Total resources" stroke={SERIES[0]} strokeWidth={2.2} dot={{ r: 2.5 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function Donut({ data, height = 240 }: { data: Record<string, number>; height?: number }) {
  const arr = toArr(data);
  return (
    <div style={{ height }}>
      <ResponsiveContainer>
        <PieChart>
          <Pie data={arr} dataKey="value" nameKey="name" innerRadius="55%" outerRadius="85%" paddingAngle={2} stroke="none">
            {arr.map((_, i) => <Cell key={i} fill={SERIES[i % SERIES.length]} />)}
          </Pie>
          <Tooltip {...tip} />
          <Legend wrapperStyle={{ fontSize: 12, textTransform: "capitalize" }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HBar({ data, height = 260, color = SERIES[0] }: { data: { name: string; value: number }[]; height?: number; color?: string }) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
          <CartesianGrid stroke="#e3eef3" horizontal={false} />
          <XAxis type="number" tick={axis} />
          <YAxis type="category" dataKey="name" tick={{ ...axis, fontSize: 11 }} width={150} />
          <Tooltip {...tip} />
          <Bar dataKey="value" fill={color} radius={[0, 6, 6, 0]} barSize={14} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function VBar({ data, height = 240 }: { data: Record<string, number>; height?: number }) {
  const arr = toArr(data);
  return (
    <div style={{ height }}>
      <ResponsiveContainer>
        <BarChart data={arr} margin={{ top: 10, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid stroke="#e3eef3" vertical={false} />
          <XAxis dataKey="name" tick={{ ...axis, fontSize: 10.5 }} interval={0} />
          <YAxis tick={axis} allowDecimals={false} />
          <Tooltip {...tip} />
          <Bar dataKey="value" radius={[6, 6, 0, 0]} barSize={28}>
            {arr.map((_, i) => <Cell key={i} fill={SERIES[i % SERIES.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
