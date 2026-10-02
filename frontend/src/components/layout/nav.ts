import {
  Activity,
  Bot,
  BookOpen,
  Building2,
  ChartColumn,
  ClipboardCheck,
  Compass,
  Database,
  FolderCog,
  GraduationCap,
  House,
  Image,
  LayoutDashboard,
  Map,
  Megaphone,
  ScrollText,
  Search,
  Ship,
  SquarePen,
  Users,
  Bookmark,
  CalendarDays,
  Fingerprint,
  FlaskConical,
  History,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  permission?: string;
  auth?: boolean;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
  tone?: "public" | "pro" | "admin";
}

export const NAV: NavGroup[] = [
  {
    label: "Discover",
    tone: "public",
    items: [
      { href: "/", label: "Home", icon: House },
      { href: "/explore", label: "Explore", icon: Compass },
      { href: "/documents", label: "Documents", icon: BookOpen },
      { href: "/datasets", label: "Datasets", icon: Database },
      { href: "/media", label: "Media", icon: Image },
      { href: "/expeditions", label: "Expeditions", icon: Ship },
      { href: "/stations", label: "Research Stations", icon: Building2 },
      { href: "/activities", label: "Institutional Activities", icon: CalendarDays },
      { href: "/map", label: "Polar Map", icon: Map },
      { href: "/learn", label: "Learn Polar Science", icon: GraduationCap },
    ],
  },
  {
    label: "Intelligence",
    tone: "public",
    items: [
      { href: "/assistant", label: "AI Assistant", icon: Bot },
      { href: "/explore?mode=semantic", label: "Smart Search", icon: Search },
      { href: "/timeline", label: "Knowledge Timeline", icon: History },
      { href: "/impact", label: "Impact & KPIs", icon: TrendingUp },
    ],
  },
  {
    label: "Outreach",
    tone: "pro",
    items: [
      { href: "/outreach", label: "Outreach Feed", icon: Megaphone },
      { href: "/studio", label: "Content Studio", icon: SquarePen, permission: "generate_content" },
      { href: "/review", label: "Review Center", icon: ClipboardCheck, permission: "review" },
      { href: "/workspace", label: "Researcher Workspace", icon: FlaskConical, permission: "upload" },
      { href: "/my-knowledge", label: "My Knowledge", icon: Bookmark, auth: true },
    ],
  },
  {
    label: "Management",
    tone: "admin",
    items: [
      { href: "/admin", label: "Dashboard", icon: LayoutDashboard, permission: "view_analytics" },
      { href: "/admin/repository", label: "Repository", icon: FolderCog, permission: "manage_repository" },
      { href: "/admin/provenance", label: "Provenance & Verification", icon: Fingerprint, permission: "manage_repository" },
      { href: "/admin/activities", label: "Manage Activities", icon: CalendarDays, permission: "manage_repository" },
      { href: "/admin/users", label: "Users & Roles", icon: Users, permission: "manage_users" },
      { href: "/admin/analytics", label: "Analytics", icon: ChartColumn, permission: "view_analytics" },
      { href: "/admin/audit", label: "Audit Logs", icon: ScrollText, permission: "view_audit" },
      { href: "/admin/health", label: "System Health", icon: Activity, permission: "view_analytics" },
    ],
  },
];
